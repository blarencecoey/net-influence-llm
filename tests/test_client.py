"""Client tests: fake provider only, no network. Prices below are made up."""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from netinf.agents.client import (
    BaseClient,
    BudgetExceeded,
    FakeClient,
    OpenAIClient,
    TransientError,
    make_client,
    to_anthropic_messages,
)

MSGS = [{"role": "system", "content": "sys"}, {"role": "user", "content": "your move"}]
PRICES = {"m": (1_000_000.0, 1_000_000.0)}  # made-up: $1 per token, so cost = total tokens


def _call(client, msgs=MSGS, seed=1, temperature=1.0):
    return client.complete(msgs, model="m", temperature=temperature, max_tokens=20, seed=seed)


def test_fake_deterministic_given_seed():
    c = make_client("fake")
    a, b = _call(c, seed=3), _call(c, seed=3)
    assert a.text == b.text and "ACTION: " in a.text
    texts = {_call(c, seed=s).text.splitlines()[-1] for s in range(30)}
    assert texts == {"ACTION: ROCK", "ACTION: PAPER", "ACTION: SCISSORS"}


def test_cache_hit_and_miss(tmp_path):
    calls = []
    c = make_client(
        "fake",
        cache_dir=tmp_path,
        prices=PRICES,
        responder=lambda m, s: calls.append(s) or "ACTION: ROCK",
    )
    first = _call(c, seed=1)
    second = _call(c, seed=1)
    assert not first.cached and second.cached and second.text == first.text
    assert second.cost_usd == 0.0 and len(calls) == 1
    _call(c, seed=2)  # different seed -> miss
    _call(c, seed=None, temperature=1.0)  # unseeded sample at T>0 -> never cached
    _call(c, seed=None, temperature=1.0)
    assert len(calls) == 4
    u = c.usage
    assert (u.calls, u.cached_calls) == (4, 1)
    # a new client on the same directory reuses the cache
    c2 = make_client("fake", cache_dir=tmp_path, responder=lambda m, s: "ACTION: PAPER")
    assert _call(c2, seed=1).text == "ACTION: ROCK"


def test_usage_and_cost():
    c = make_client("fake", prices=PRICES, responder=lambda m, s: "ACTION: ROCK")
    comp = _call(c)
    assert comp.cost_usd == pytest.approx(comp.input_tokens + comp.output_tokens)
    _call(c)
    u = c.usage
    assert u.calls == 2 and u.input_tokens == 2 * comp.input_tokens
    assert u.cost_usd == pytest.approx(2 * comp.cost_usd)
    # unpriced model -> cost None, counted separately
    other = c.complete(MSGS, model="unpriced", temperature=0, max_tokens=5)
    assert other.cost_usd is None and c.usage.unpriced_calls == 1


def test_budget_cap():
    c = make_client("fake", prices=PRICES, budget_usd=100.0, responder=lambda m, s: "x" * 40)
    one = _call(c)  # costs input+output tokens dollars
    per_call = one.cost_usd
    assert 0 < per_call < 100
    with pytest.raises(BudgetExceeded):
        for _ in range(20):
            _call(c)
    spent = c.usage.cost_usd
    assert spent > 100.0 and spent <= 100.0 + per_call + 1e-9  # raised by the call that passed it
    n = c.usage.calls
    with pytest.raises(BudgetExceeded):  # already over -> refused before any call
        _call(c)
    assert c.usage.calls == n


def test_budget_requires_price_for_real_providers():
    c = FakeClient(budget_usd=1.0)
    c.needs_price_for_budget = True  # as for openai/anthropic/openrouter
    with pytest.raises(ValueError, match="no price"):
        _call(c)


def test_retry_on_transient_error():
    attempts = []

    def flaky(messages, seed):
        attempts.append(1)
        if len(attempts) < 3:
            raise TransientError("rate limited")
        return "ACTION: PAPER"

    c = make_client("fake", responder=flaky)
    c._sleep = lambda s: None
    assert _call(c).text == "ACTION: PAPER" and len(attempts) == 3

    def broken(messages, seed):
        raise KeyError("not transient")

    c2 = make_client("fake", responder=broken)
    with pytest.raises(KeyError):
        _call(c2)


def test_openai_response_without_choices_is_retried():
    # OpenRouter can answer 200 with an error body and choices = None (seen 2026-10-24)
    replies = [SimpleNamespace(choices=None, usage=None, model=None, error={"code": 502}),
               SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ACTION: ROCK"))],
                               usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3), model="m")]
    c = object.__new__(OpenAIClient)
    BaseClient.__init__(c)  # client state without the SDK or an API key
    c.provider = "openrouter"
    c._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: replies.pop(0))))
    c._sleep = lambda s: None
    out = _call(c)
    assert out.text == "ACTION: ROCK" and out.input_tokens == 7 and not replies


def test_cache_write_failure_does_not_lose_the_call(tmp_path, monkeypatch):
    # Windows: os.replace onto a cache file another process holds open raises PermissionError
    def locked(src, dst):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(os, "replace", locked)
    c = make_client("fake", cache_dir=tmp_path, prices=PRICES, responder=lambda m, s: "ACTION: ROCK")
    c._sleep = lambda s: None
    with pytest.warns(RuntimeWarning, match="cache write failed"):
        assert _call(c).text == "ACTION: ROCK"
    assert not list(tmp_path.rglob("*.tmp"))


def test_thread_safety(tmp_path):
    lock = threading.Lock()
    n_calls = [0]

    def responder(messages, seed):
        with lock:
            n_calls[0] += 1
        return f"ACTION: {['ROCK', 'PAPER', 'SCISSORS'][seed % 3]}"

    c = make_client("fake", cache_dir=tmp_path, prices=PRICES, responder=responder)
    seeds = [s % 25 for s in range(200)]  # 25 distinct requests, each asked 8 times
    with ThreadPoolExecutor(max_workers=8) as pool:
        out = list(pool.map(lambda s: _call(c, seed=s), seeds))
    assert n_calls[0] == 25  # one paid call per distinct request
    u = c.usage
    assert (u.calls, u.cached_calls) == (25, 175)
    assert u.cost_usd == pytest.approx(sum(o.cost_usd for o in out if not o.cached))
    assert all(o.text.endswith(["ROCK", "PAPER", "SCISSORS"][s % 3]) for o, s in zip(out, seeds))


def test_anthropic_message_conversion():
    msgs = [
        {"role": "system", "content": "rules"},
        {"role": "system", "content": "more rules"},
        {"role": "user", "content": "a"},
        {"role": "user", "content": "b"},
        {"role": "assistant", "content": "c"},
    ]
    system, out = to_anthropic_messages(msgs)
    assert system == "rules\n\nmore rules"
    assert out == [{"role": "user", "content": "a\n\nb"}, {"role": "assistant", "content": "c"}]
    assert to_anthropic_messages([{"role": "user", "content": "x"}]) == (
        None,
        [{"role": "user", "content": "x"}],
    )


def test_unknown_provider():
    with pytest.raises(ValueError):
        make_client("nope")
