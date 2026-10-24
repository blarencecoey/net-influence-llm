"""LLM-judge tests: fake provider only, no network."""

from __future__ import annotations

import json
import re

import numpy as np

from netinf.agents.client import make_client
from netinf.baselines import rank_of_pair
from netinf.judge import judge_scores, parse_scores, render_prompt

GOOD = json.dumps(
    {
        "most_suspicious_pair": [1, 3],
        "scores": {"0-1": 5, "0-2": 10, "0-3": 0, "1-2": 20, "1-3": 95, "2-3": 15},
    }
)


def _actions(t=30, n=4, seed=0):
    return np.random.default_rng(seed).integers(0, 3, size=(t, n))


def test_good_reply_gives_all_six_pairs():
    c = make_client("fake", responder=lambda m, s: "Here you go:\n" + GOOD)
    res = judge_scores(_actions(), c, model="judge")
    assert res.parse_ok and len(res.completions) == 1
    assert set(res.scores) == {(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)}
    assert res.scores[(1, 3)] == 95 and res.most_suspicious_pair == (1, 3)
    assert rank_of_pair(res.scores, (3, 1)) == 1


def test_malformed_then_good_retries():
    replies = iter(["I think P1 and P3.", '{"scores": {"0-1": 3}}', GOOD])
    seen = []

    def responder(messages, seed):
        seen.append((len(messages), seed))
        return next(replies)

    res = judge_scores(_actions(), make_client("fake", responder=responder), model="judge", seed=7)
    assert res.parse_ok and len(res.completions) == 3
    assert [s for _, s in seen] == [7, 8, 9]  # seed bumped per attempt
    assert [k for k, _ in seen] == [2, 4, 6]  # bad reply + reminder appended
    assert res.scores[(1, 3)] == 95


def test_fallback_all_zero_after_bounded_retries():
    calls = []
    c = make_client("fake", responder=lambda m, s: calls.append(1) or "no json here")
    res = judge_scores(_actions(), c, model="judge", max_attempts=3)
    assert not res.parse_ok and len(calls) == 3
    assert res.scores == {p: 0.0 for p in res.scores} and len(res.scores) == 6
    assert rank_of_pair(res.scores, (0, 1)) == 6  # a failure ranks the true pair last


def test_parse_variants_and_clipping():
    text = '{"scores": {"(0, 1)": 150, "P0-P2": -3, "1,2": 50.5}}'
    scores, pair = parse_scores(text, 3)
    assert scores == {(0, 1): 100.0, (0, 2): 0.0, (1, 2): 50.5} and pair is None


def test_prompt_shows_only_actions_and_truncates():
    acts = _actions(t=50)
    prompt = render_prompt(acts, max_rounds=10)
    assert "the last 10 of 50 rounds" in prompt
    table = [ln for ln in prompt.splitlines() if re.match(r"\d+ \| ", ln)]
    assert len(table) == 10 and table[0].startswith("40 | ")
    assert "payoffs" not in prompt.split("History")[1].split("\n")[1]
    for word in ("primary", "assistant", "honest", "channel"):
        assert word not in prompt.lower()
    with_pay = render_prompt(acts[:5], payoffs=np.ones((5, 4), dtype=int))
    assert "all 5 rounds" in with_pay and "| 1 1 1 1" in with_pay
