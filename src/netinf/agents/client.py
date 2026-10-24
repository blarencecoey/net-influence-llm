"""Chat-completion clients for the LLM harness: providers, retry, disk cache, usage and budget cap.

Interface (notes/methods/llm-harness.md): `make_client(provider, ...)` returns an object with
`complete(messages, *, model, temperature, max_tokens, seed=None) -> Completion`. Messages use the
OpenAI chat shape; the Anthropic adapter converts them (system messages -> `system=`).

Choices:
- Providers: "openai", "anthropic", "openrouter" (OpenAI SDK pointed at OpenRouter's base URL) and
  "fake" (no network, deterministic given seed and messages). SDKs are imported lazily, so "fake"
  works without them or any key. Keys come from the environment / `.env` and are never logged.
- Retry: our own bounded exponential backoff with jitter on rate-limit, timeout, connection and
  5xx/overloaded errors; the SDKs' built-in retries are switched off so attempts are counted once.
- Cache: one JSON file per request, keyed by a SHA-256 of (provider, model, messages, temperature,
  max_tokens, seed). A request is cached only if `seed is not None` or `temperature == 0`; an
  unseeded sample at temperature > 0 is meant to be a fresh draw, and replaying it from the cache
  would silently make repeated prompts (e.g. round 0 of every game) identical. Callers who want
  reruns to be free should pass a per-call seed (e.g. from run seed, round, player). The seed is
  forwarded to OpenAI/OpenRouter (best effort there) and only tags the cache key for Anthropic.
- Cost: tokens x per-million (input, output) prices from config, looked up by the requested model
  id. No prices are hard-coded. `cost_usd` is None when no price is configured; a cache hit costs
  0 and does not count toward the budget. With a budget set, a real-provider call to an unpriced
  model raises ValueError, because the cap could not be enforced.
- Budget: `BudgetExceeded` is raised before a call if spend is already at/over `budget_usd`, and
  after a call that pushed it past (the response is still cached and counted). With parallel
  threads, calls already in flight can overshoot the cap by at most one call each.
- Thread safety: usage is updated under a lock; each cache key has its own lock, so concurrent
  identical requests make one paid call and the rest read the cache; files are written atomically.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
import warnings
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
RETRY_NAMES = {
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "InternalServerError",
    "OverloadedError",
    "ServiceUnavailableError",
}

Messages = list[dict]
Responder = Callable[[Messages, "int | None"], str]


@dataclass
class Completion:
    text: str
    model: str  # model id echoed by the provider
    input_tokens: int
    output_tokens: int
    cost_usd: float | None  # tokens x configured price; None if no price configured
    latency_s: float
    cached: bool  # served from the disk cache


@dataclass
class Usage:
    calls: int = 0  # API calls actually made (cache misses)
    cached_calls: int = 0
    input_tokens: int = 0  # uncached calls only
    output_tokens: int = 0
    cost_usd: float = 0.0
    unpriced_calls: int = 0  # calls whose model had no configured price


class Client(Protocol):
    def complete(
        self,
        messages: Messages,
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
    ) -> Completion: ...


class BudgetExceeded(RuntimeError):
    """Cumulative spend reached or passed `budget_usd`."""


class TransientError(RuntimeError):
    """A retryable failure (for fake responders and tests)."""


def is_transient(err: BaseException) -> bool:
    """Rate limits, timeouts, connection drops and 5xx/overloaded responses are worth retrying."""
    if isinstance(err, (TransientError, TimeoutError, ConnectionError)):
        return True
    if getattr(err, "status_code", None) in RETRY_STATUS:
        return True
    return any(cls.__name__ in RETRY_NAMES for cls in type(err).__mro__)


def to_anthropic_messages(messages: Messages) -> tuple[str | None, Messages]:
    """OpenAI-shaped messages -> (system, messages) for the Anthropic Messages API.

    System messages are joined into `system`; consecutive same-role turns are merged.
    """
    system = [m["content"] for m in messages if m["role"] == "system"]
    out: Messages = []
    for m in messages:
        if m["role"] == "system":
            continue
        if m["role"] not in ("user", "assistant"):
            raise ValueError(f"unsupported role {m['role']!r}")
        if out and out[-1]["role"] == m["role"]:
            out[-1] = {"role": m["role"], "content": out[-1]["content"] + "\n\n" + m["content"]}
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return ("\n\n".join(system) if system else None), out


def default_fake_responder(messages: Messages, seed: int | None) -> str:
    """Uniform random move, deterministic given (seed, messages); sometimes a reasoning line first."""
    h = hashlib.sha256(json.dumps([seed, messages], sort_keys=True).encode()).hexdigest()
    rng = random.Random(int(h[:16], 16))
    move = rng.choice(["ROCK", "PAPER", "SCISSORS"])
    reason = "No pattern yet, picking at random.\n" if rng.random() < 0.5 else ""
    return f"{reason}ACTION: {move}"


class BaseClient:
    """Cache, retry, usage and budget logic; subclasses implement `_call`."""

    provider = "base"
    needs_price_for_budget = True

    def __init__(
        self,
        *,
        cache_dir: Path | str | None = None,
        budget_usd: float | None = None,
        prices: dict[str, tuple[float, float]] | None = None,
        max_attempts: int = 6,
        backoff_s: float = 1.0,
        max_backoff_s: float = 30.0,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.budget_usd = budget_usd
        self.prices = dict(prices or {})
        self.max_attempts = max_attempts
        self.backoff_s = backoff_s
        self.max_backoff_s = max_backoff_s
        self._sleep: Callable[[float], None] = time.sleep  # swapped out in tests
        self._usage = Usage()
        self._lock = threading.Lock()
        self._key_locks: dict[str, threading.Lock] = {}

    @property
    def usage(self) -> Usage:
        """A snapshot of cumulative usage."""
        with self._lock:
            return Usage(**asdict(self._usage))

    def _call(
        self, messages: Messages, model: str, temperature: float, max_tokens: int, seed: int | None
    ) -> tuple[str, str, int, int]:
        """One provider call -> (text, echoed model, input tokens, output tokens)."""
        raise NotImplementedError

    def complete(
        self,
        messages: Messages,
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
    ) -> Completion:
        request = {
            "provider": self.provider,
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "seed": seed,
        }
        if self.cache_dir is None or (seed is None and temperature != 0):
            return self._fresh(request, None)
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        with self._lock:
            key_lock = self._key_locks.setdefault(key, threading.Lock())
        with key_lock:
            path = self.cache_dir / key[:2] / f"{key}.json"
            if path.exists():
                resp = json.loads(path.read_text(encoding="utf-8"))["response"]
                with self._lock:
                    self._usage.cached_calls += 1
                return Completion(
                    text=resp["text"],
                    model=resp["model"],
                    input_tokens=resp["input_tokens"],
                    output_tokens=resp["output_tokens"],
                    cost_usd=0.0 if model in self.prices else None,
                    latency_s=0.0,
                    cached=True,
                )
            return self._fresh(request, path)

    def _fresh(self, request: dict, cache_path: Path | None) -> Completion:
        model = request["model"]
        with self._lock:
            if self.budget_usd is not None:
                if self.needs_price_for_budget and model not in self.prices:
                    raise ValueError(f"budget set but no price configured for model {model!r}")
                if self._usage.cost_usd >= self.budget_usd:
                    raise BudgetExceeded(
                        f"spent ${self._usage.cost_usd:.4f} of ${self.budget_usd:.2f} budget"
                    )
        t0 = time.perf_counter()
        text, echoed, n_in, n_out = self._with_retries(
            request["messages"],
            model,
            request["temperature"],
            request["max_tokens"],
            request["seed"],
        )
        latency = time.perf_counter() - t0
        cost = None
        if model in self.prices:
            p_in, p_out = self.prices[model]
            cost = (n_in * p_in + n_out * p_out) / 1e6
        if cache_path is not None:
            resp = {"text": text, "model": echoed, "input_tokens": n_in, "output_tokens": n_out}
            try:
                _write_atomic(cache_path, {"request": request, "response": resp}, self._sleep)
            except OSError as err:  # the cache is an optimisation; never lose a paid call to it
                warnings.warn(f"cache write failed, response not cached: {err}", RuntimeWarning,
                              stacklevel=2)
        with self._lock:
            u = self._usage
            u.calls += 1
            u.input_tokens += n_in
            u.output_tokens += n_out
            if cost is None:
                u.unpriced_calls += 1
            else:
                u.cost_usd += cost
            over = self.budget_usd is not None and u.cost_usd > self.budget_usd
            spent = u.cost_usd
        if over:
            raise BudgetExceeded(f"spent ${spent:.4f}, past the ${self.budget_usd:.2f} budget")
        return Completion(text, echoed, n_in, n_out, cost, latency, cached=False)

    def _with_retries(self, *args) -> tuple[str, str, int, int]:
        for attempt in range(self.max_attempts):
            try:
                return self._call(*args)
            except Exception as err:
                if attempt == self.max_attempts - 1 or not is_transient(err):
                    raise
                delay = min(self.max_backoff_s, self.backoff_s * 2**attempt)
                self._sleep(delay * (1 + 0.25 * random.random()))
        raise AssertionError("unreachable")


def _write_atomic(path: Path, obj: dict, sleep: Callable[[float], None] = time.sleep,
                  attempts: int = 5) -> None:
    """Write via a temp file and os.replace. On Windows the replace raises PermissionError while
    another process (a reader, an indexer) holds the target open, so it is retried briefly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    try:
        for attempt in range(attempts):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == attempts - 1:
                    raise
                sleep(0.05 * 2**attempt)
    finally:
        tmp.unlink(missing_ok=True)


class FakeClient(BaseClient):
    """No network. Token counts are a rough chars/4 stand-in."""

    provider = "fake"
    needs_price_for_budget = False

    def __init__(self, responder: Responder | None = None, **kwargs):
        super().__init__(**kwargs)
        self.responder = responder or default_fake_responder

    def _call(self, messages, model, temperature, max_tokens, seed):
        text = self.responder(messages, seed)
        n_in = sum(len(m["content"]) for m in messages) // 4 + 1
        return text, model, n_in, len(text) // 4 + 1


class OpenAIClient(BaseClient):
    """OpenAI Chat Completions; also OpenRouter via its OpenAI-compatible endpoint."""

    def __init__(self, provider: str, *, timeout_s: float = 60.0, **kwargs):
        super().__init__(**kwargs)
        import openai

        self.provider = provider
        base_url = OPENROUTER_BASE_URL if provider == "openrouter" else None
        self._client = openai.OpenAI(
            api_key=_api_key(provider), base_url=base_url, timeout=timeout_s, max_retries=0
        )

    def _call(self, messages, model, temperature, max_tokens, seed):
        # the installed SDK documents `max_tokens` as deprecated for OpenAI in favour of
        # `max_completion_tokens`; OpenRouter gets the classic field
        limit = "max_tokens" if self.provider == "openrouter" else "max_completion_tokens"
        extra = {} if seed is None else {"seed": seed}
        resp = self._client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, **{limit: max_tokens}, **extra
        )
        if not resp.choices:  # OpenRouter can answer 200 with an error body and no choices
            raise TransientError(f"no choices in response: {getattr(resp, 'error', None)}")
        usage = resp.usage
        return (
            resp.choices[0].message.content or "",
            resp.model or model,
            getattr(usage, "prompt_tokens", 0) or 0,
            getattr(usage, "completion_tokens", 0) or 0,
        )


class AnthropicClient(BaseClient):
    provider = "anthropic"

    def __init__(self, *, timeout_s: float = 60.0, **kwargs):
        super().__init__(**kwargs)
        import anthropic

        self._client = anthropic.Anthropic(
            api_key=_api_key("anthropic"), timeout=timeout_s, max_retries=0
        )

    def _call(self, messages, model, temperature, max_tokens, seed):
        system, msgs = to_anthropic_messages(messages)
        kwargs = {} if system is None else {"system": system}
        # the installed SDK's `messages.create` has no named `temperature` parameter, so it goes
        # in the request body; whether a given model accepts it is unverified
        resp = self._client.messages.create(
            model=model,
            messages=msgs,
            max_tokens=max_tokens,
            extra_body={"temperature": temperature},
            **kwargs,
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return text, resp.model or model, resp.usage.input_tokens, resp.usage.output_tokens


def _api_key(provider: str) -> str:
    from dotenv import load_dotenv

    load_dotenv(override=False)
    var = KEY_ENV[provider]
    key = os.environ.get(var)
    if not key:
        raise RuntimeError(f"{var} is not set (environment or .env)")
    return key


def make_client(
    provider: str,
    *,
    cache_dir: Path | str | None = None,
    budget_usd: float | None = None,
    prices: dict[str, tuple[float, float]] | None = None,
    responder: Responder | None = None,
    timeout_s: float = 60.0,
    max_attempts: int = 6,
) -> BaseClient:
    """Build a client. `responder(messages, seed) -> str` applies to the fake provider only."""
    common = {"cache_dir": cache_dir, "budget_usd": budget_usd, "prices": prices}
    common["max_attempts"] = max_attempts
    if provider == "fake":
        return FakeClient(responder, **common)
    if provider in ("openai", "openrouter"):
        return OpenAIClient(provider, timeout_s=timeout_s, **common)
    if provider == "anthropic":
        return AnthropicClient(timeout_s=timeout_s, **common)
    raise ValueError(f"unknown provider {provider!r}")
