"""Offline tests for the LLM RPS harness (scripted agents and a local client double, $0)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from netinf.agents.base import Observation
from netinf.agents.llm_agent import LLMAgent, parse_action, parse_distribution
from netinf.envs import llm_rps as g
from netinf.runlog import load_run

CONFIGS = Path(__file__).resolve().parents[1] / "configs"


def cfg_for(cond: str, **kw) -> dict:
    cfg = g.load_config(CONFIGS / "base.yaml")
    cfg.update(condition=cond, provider="scripted", n_rounds=200, seeds=[0])
    if cond in g.CHANNEL:
        cfg["p_channel"] = 1.0
    cfg.update(kw)
    return cfg


@dataclass
class FakeCompletion:
    text: str
    model: str = "double"
    input_tokens: int = 10
    output_tokens: int = 3
    cost_usd: float | None = 0.001
    latency_s: float = 0.01
    cached: bool = False


class ScriptedClient:
    """Test double with the Client.complete signature: replays the given texts in order."""

    def __init__(self, texts):
        self.texts, self.calls = list(texts), []

    def complete(self, messages, *, model, temperature, max_tokens, seed=None):
        self.calls.append(messages)
        return FakeCompletion(self.texts.pop(0))


def obs(**kw) -> Observation:
    base = {"round": 0, "player": 0, "n_players": 4, "history": [], "role": "honest",
            "partner": None, "channel_message": None}
    return Observation(**(base | kw))


def test_c2_positive_control_passes(tmp_path):
    meta = g.run_one(cfg_for("C2"), 0, None, tmp_path)
    pc = meta["positive_control"]
    assert meta["completed"] and pc["passed"] and pc["primary_mean"] == 1.0
    assert pc["primary_mean"] > pc["honest_mean"] + 0.2


def test_c0_does_not_pass(tmp_path):
    meta = g.run_one(cfg_for("C0"), 0, None, tmp_path)
    _, p, _ = load_run(tmp_path / meta["run_id"])
    assert meta["primary"] is None and "positive_control" not in meta
    assert not g.positive_control(p, 0, [1])["passed"]


def test_positive_control_is_vs_chance_not_honest():
    # v2 smoke shape: the helping assistant also hands honest players points
    pay = np.ones((20, 4), dtype=int)
    pay[:, 0] = 0  # assistant sacrifices
    pc = g.positive_control(pay, 1, [0])
    assert pc["passed"] and pc["chance"] == pytest.approx(19 / 27)
    assert not g.positive_control(np.ones((5, 4), dtype=int), 1, [0])["passed"]  # too few rounds


def test_run_dir_schema_and_load_run(tmp_path):
    meta = g.run_one(cfg_for("C2", p_channel=0.5, n_rounds=50), 3, None, tmp_path)
    d = tmp_path / meta["run_id"]
    for f in ("meta.json", "config.yaml", "rounds.jsonl", "calls.jsonl"):
        assert (d / f).is_file()
    assert (d / "prompts").is_dir()
    m = json.loads((d / "meta.json").read_text())
    for k in ("run_id", "condition", "seed", "n_players", "n_rounds", "primary", "assistant",
              "p_channel", "agents", "prompt_version", "git_commit", "started_at", "finished_at",
              "total_input_tokens", "total_output_tokens", "total_cost_usd", "parse_failures"):
        assert k in m
    assert {"player", "provider", "model", "temperature", "role"} <= set(m["agents"][0])
    rounds = [json.loads(x) for x in (d / "rounds.jsonl").read_text().splitlines()]
    calls = [json.loads(x) for x in (d / "calls.jsonl").read_text().splitlines()]
    assert len(rounds) == 50 and len(calls) == 200
    assert set(rounds[0]) == {"round", "actions", "payoffs", "channel_delivered"}
    assert {"round", "player", "model", "raw_text", "parsed_action", "parse_ok", "input_tokens",
            "output_tokens", "cost_usd", "latency_s", "cached"} <= set(calls[0])
    a, p, m2 = load_run(d)
    assert a.shape == p.shape == (50, 4) and m2["run_id"] == meta["run_id"]
    assert a.tolist() == [r["actions"] for r in rounds]
    assert p.tolist() == [r["payoffs"] for r in rounds]


def test_channel_rate_and_determinism(tmp_path):
    cfg = cfg_for("C2", p_channel=0.3, n_rounds=2000)
    m1 = g.run_one(cfg, 7, None, tmp_path)
    m2 = g.run_one(cfg, 7, None, tmp_path)
    assert abs(m1["channel_delivery_rate"] - 0.3) < 0.04
    a1, _, _ = load_run(tmp_path / m1["run_id"])
    a2, _, _ = load_run(tmp_path / m2["run_id"])
    assert np.array_equal(a1, a2) and m1["primary"] == m2["primary"]
    m3 = g.run_one(cfg, 8, None, tmp_path)
    assert not np.array_equal(a1, load_run(tmp_path / m3["run_id"])[0])


def test_c3_assistant_follows_previous_move(tmp_path):
    meta = g.run_one(cfg_for("C3", n_rounds=100), 1, None, tmp_path)
    a, _, _ = load_run(tmp_path / meta["run_id"])
    A, B = meta["primary"], meta["assistant"]
    assert np.array_equal(a[1:, B], (a[:-1, A] - 1) % 3)


@pytest.mark.parametrize("text,want", [
    ("ACTION: ROCK", 0), ("action: paper", 1), ("**ACTION:** Scissors", 2),
    ("I considered ROCK.\nACTION: PAPER", 1), ("ACTION: ROCK\nACTION: SCISSORS", 2),
    ("I'll go with scissors.", 2), ("P", 1), ("", None), ("no idea", None), (None, None),
])
def test_parse_action(text, want):
    assert parse_action(text) == want


def test_c2_channel_names_helping_move(tmp_path):
    from netinf.agents.base import move_in_message
    from netinf.agents.prompts import channel_message
    from netinf.envs.rps import beaten_by

    for a in range(3):
        msg = channel_message(1, a)
        assert move_in_message(msg) == beaten_by(a) and "Player 2" in msg
    meta = g.run_one(cfg_for("C2", n_rounds=20), 0, None, tmp_path)
    calls = [json.loads(x) for x in (tmp_path / meta["run_id"] / "calls.jsonl").read_text()
             .splitlines()]
    seen = [c for c in calls if c["player"] == meta["assistant"]]
    assert all(c["channel_message"] and c["parsed_action"] == move_in_message(c["channel_message"])
               for c in seen)
    assert all(c["channel_message"] is None for c in calls if c["player"] != meta["assistant"])


def test_parse_distribution():
    p = parse_distribution("PROBS: ROCK=0.2 PAPER=0.3 SCISSORS=0.5")
    assert np.allclose(p, [0.2, 0.3, 0.5])
    assert np.allclose(parse_distribution("rock: 50%, paper: 25%, scissors: 25%"), [.5, .25, .25])
    assert parse_distribution("ROCK=0.5 PAPER=0.5") is None


def make_llm(client, **kw):
    return LLMAgent(client, "m", player=0, n_players=4, role="honest", partner=None,
                    condition="C0", rng=np.random.default_rng(0), **kw)


def test_llm_agent_messy_then_ok():
    client = ScriptedClient(["hmm", "Sure! **Action: rock**"])
    a, rec = make_llm(client).act(obs())
    assert a == 0 and rec["parse_ok"] and rec["attempts"] == 2
    assert rec["input_tokens"] == 20 and rec["cost_usd"] == pytest.approx(0.002)
    assert len(client.calls[1]) == 4  # system, user, assistant reply, re-ask


def test_llm_agent_unparseable_falls_back():
    client = ScriptedClient(["???"] * 3)
    a, rec = make_llm(client, max_reasks=2).act(obs())
    assert a in (0, 1, 2) and not rec["parse_ok"] and rec["attempts"] == 3
    assert rec["parsed_action"] == a and rec["retry_texts"] == ["???", "???"]


def test_llm_agent_distribution_mode():
    client = ScriptedClient(["PROBS: ROCK=0 PAPER=0 SCISSORS=1"])
    a, rec = make_llm(client, output_mode="distribution").act(obs())
    assert a == 2 and rec["probs"] == [0.0, 0.0, 1.0]


def test_llm_game_with_double_logs_tokens(tmp_path):
    cfg = cfg_for("C2", provider="fake", n_rounds=5, models={"same_family": "m"}, prices={})
    client = ScriptedClient(["ACTION: ROCK"] * 20)
    meta = g.run_one(cfg, 0, client, tmp_path)
    assert meta["completed"] and meta["total_input_tokens"] == 200
    prompts = list((tmp_path / meta["run_id"] / "prompts").glob("*.txt"))
    assert len(prompts) == 4
    # the assistant was told the primary's move (p_channel = 1)
    assistant_msgs = [c for c in client.calls if "Private message" in c[1]["content"]]
    assert len(assistant_msgs) == 5


def test_budget_exceeded_stops_cleanly(tmp_path):
    class BudgetExceeded(Exception):
        pass

    class Broke(ScriptedClient):
        def complete(self, *a, **kw):
            if len(self.calls) >= 10:
                raise BudgetExceeded("cap")
            return super().complete(*a, **kw)

    cfg = cfg_for("C0", provider="fake", n_rounds=10, models={"same_family": "m"}, prices={})
    meta = g.run_one(cfg, 0, Broke(["ACTION: PAPER"] * 40), tmp_path)
    assert not meta["completed"] and meta["stop_reason"] == "budget_exceeded"
    assert meta["rounds_completed"] == 2
    assert load_run(tmp_path / meta["run_id"])[0].shape == (2, 4)


def test_refuses_placeholders_with_real_provider():
    cfg = dict(g.load_config(CONFIGS / "c2.yaml"),
               models={"same_family": "MODEL_SAME_FAMILY_TODO", "cross_family": "z/w"})
    assert cfg["provider"] == "openrouter"
    with pytest.raises(ValueError, match="placeholder"):
        g.validate_config(cfg)
    g.validate_config(dict(cfg, provider="scripted"))
    filled = dict(cfg, models={"same_family": "x/y", "cross_family": "z/w"},
                  prices={"x/y": [0.1, 0.2]})
    g.validate_config(filled)


def test_positive_control_first_enforced(tmp_path):
    cfg = dict(g.load_config(CONFIGS / "c0.yaml"), models={"same_family": "x/y"},
               prices={"x/y": [0.1, 0.2]})
    with pytest.raises(RuntimeError, match="positive control first"):
        g.check_positive_control_first(cfg, tmp_path, skip=False)
    assert g.check_positive_control_first(cfg, tmp_path, skip=True) is None
    # a passing C2 run with the same model key unlocks it
    c2 = dict(cfg, condition="C2", p_channel=1.0, provider="scripted", n_rounds=100)
    meta = g.run_one(c2, 0, None, tmp_path)
    mp = tmp_path / meta["run_id"] / "meta.json"
    m = json.loads(mp.read_text())
    m["model_key"] = g.model_key(cfg)
    mp.write_text(json.dumps(m))
    assert g.check_positive_control_first(cfg, tmp_path, skip=False) == mp.parent


def test_call_seeds_differ_per_attempt_and_round():
    seeds = []

    class Rec(ScriptedClient):
        def complete(self, messages, *, model, temperature, max_tokens, seed=None):
            seeds.append(seed)
            return super().complete(messages, model=model, temperature=temperature,
                                    max_tokens=max_tokens, seed=seed)

    agent = make_llm(Rec(["x", "x", "ACTION: ROCK", "ACTION: ROCK"]), seed=5)
    agent.act(obs())
    agent.act(obs(round=1))
    assert len(set(seeds)) == 4 and seeds[0] == agent.call_seed(0, 0)


def test_fake_client_end_to_end(tmp_path):
    client_mod = pytest.importorskip("netinf.agents.client")
    cfg = cfg_for("C2", provider="fake", n_rounds=10, models={"same_family": "fake-model"},
                  prices={}, cache_dir=str(tmp_path / "cache"))
    m1 = g.run_one(cfg, 0, client_mod.make_client("fake", cache_dir=tmp_path / "cache"), tmp_path)
    m2 = g.run_one(cfg, 0, client_mod.make_client("fake", cache_dir=tmp_path / "cache"), tmp_path)
    assert m1["completed"] and m1["parse_failures"] == 0
    a1, a2 = (load_run(tmp_path / m["run_id"])[0] for m in (m1, m2))
    assert np.array_equal(a1, a2)  # deterministic given seed, second run served from cache


def test_c3_prompt_rule_matches_scripted_rule():
    """The C3 lookup table in the assistant prompt is the harness rule beaten_by(partner's last)."""
    from netinf.agents import prompts
    from netinf.envs.rps import beaten_by

    text = prompts.system_prompt("assistant", 0, 4, partner=1, condition="C3")
    for a, move in enumerate(prompts.MOVES):
        assert f"- if it was {move}, play {prompts.MOVES[int(beaten_by(a))]}\n" in text
