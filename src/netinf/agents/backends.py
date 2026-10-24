"""Chat backends for LLM agents.

- OpenRouterBackend: OpenAI-compatible API at https://openrouter.ai/api/v1 (checked 2026-10-24 in
  OpenRouter's "Using the OpenAI SDK" guide). Every non-streaming response carries a `usage` object
  with `cost` in USD (OpenRouter "Usage Accounting" guide, checked 2026-10-24); we log it per call.
- MockBackend: offline stand-in with no network, for tests and dry runs. It answers like a biased
  player and, if the prompt contains a private partner message, follows it. It is not a model of
  LLM behaviour; it only exercises the pipeline.

API keys come from the environment (`.env`), never from code.
"""

from __future__ import annotations

import os
import random
import re
import time
from dataclasses import dataclass, field


@dataclass
class Completion:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0  # USD as reported by the provider
    raw_id: str | None = None
    extra: dict = field(default_factory=dict)


class Backend:
    def complete(self, model: str, messages: list[dict], temperature: float = 1.0,
                 max_tokens: int = 16, seed: int | None = None) -> Completion:
        raise NotImplementedError


class OpenRouterBackend(Backend):
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str | None = None, max_retries: int = 4, timeout: float = 60.0):
        from openai import OpenAI  # optional dependency: pip install -e ".[llm]"

        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set (put it in .env)")
        self.client = OpenAI(base_url=self.BASE_URL, api_key=key, timeout=timeout)
        self.max_retries = max_retries

    def complete(self, model, messages, temperature=1.0, max_tokens=16, seed=None):
        kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens,
                      extra_headers={"X-OpenRouter-Title": "net-influence-llm"})
        if seed is not None:
            kwargs["seed"] = seed  # honoured by some providers only
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            try:
                r = self.client.chat.completions.create(**kwargs)
                u = r.usage
                cost = getattr(u, "cost", None)
                if cost is None and u is not None:
                    cost = (getattr(u, "model_extra", None) or {}).get("cost", 0.0)
                return Completion(
                    text=(r.choices[0].message.content or "") if r.choices else "",
                    model=getattr(r, "model", model),
                    prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(u, "completion_tokens", 0) or 0,
                    cost=float(cost or 0.0),
                    raw_id=getattr(r, "id", None),
                )
            except Exception:  # network, rate limit, provider error
                if attempt == self.max_retries:
                    raise
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")


_MOVE = {"rock": 0, "paper": 1, "scissors": 2}
_NAMES = ["Rock", "Paper", "Scissors"]


class MockBackend(Backend):
    """Offline fake player. Prefers Rock (bias `rock_bias`); obeys a private partner message."""

    def __init__(self, seed: int = 0, rock_bias: float = 0.2):
        self.rng = random.Random(seed)
        self.rock_bias = rock_bias

    def complete(self, model, messages, temperature=1.0, max_tokens=16, seed=None):
        text = messages[-1]["content"]
        m = re.search(r"will play (Rock|Paper|Scissors) this round", text)
        if m:
            partner = _MOVE[m.group(1).lower()]
            move = (partner - 1) % 3  # the move the partner's move beats
        elif self.rng.random() < self.rock_bias:
            move = 0
        else:
            move = self.rng.randrange(3)
        return Completion(text=_NAMES[move], model=f"mock/{model}", prompt_tokens=len(text) // 4,
                          completion_tokens=1, cost=0.0)
