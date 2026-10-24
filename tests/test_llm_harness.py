"""Offline tests for the LLM harness (MockBackend, no network)."""

import json

import numpy as np

from netinf.agents import prompts
from netinf.agents.backends import MockBackend
from netinf.envs.llm_rps import GameConfig, load_game, parse_move, play_game
from netinf.envs.rps import beaten_by


def test_parse_move():
    assert parse_move("Rock") == 0
    assert parse_move("  paper.") == 1
    assert parse_move("I choose SCISSORS!") == 2
    assert parse_move("rocket") is None
    assert parse_move("") is None


def test_prompts_plain_and_complete():
    s = prompts.system_prompt(2, 50, "assistant", partner=0)
    assert "You are Player 3" in s and "Player 1" in s and "Scissors" in s
    assert "no wait" not in prompts.TACIT_ASSISTANT
    u = prompts.round_prompt(0, 3, [([0, 1, 2, 0], [1, 1, 1, 1])], [1, 1, 1, 1], 5,
                             __import__("random").Random(0))
    assert "Round 4" in u and "P1 Rock" in u


def test_seeded_game_logs_and_colludes(tmp_path):
    cfg = GameConfig(name="t", condition="seeded", models=["m"], rounds=60, channel_p=1.0)
    r = play_game(cfg, MockBackend(seed=1), seed=3, out_path=tmp_path / "g.jsonl")
    g = load_game(tmp_path / "g.jsonl")
    a = g["actions"]
    assert a.shape == (60, 4)
    p, s = g["header"]["true_pair"]
    assert np.all(a[:, s] == beaten_by(a[:, p]))  # mock assistant always follows the channel
    assert g["payoffs"][:, p].min() == 1  # partner always scores
    assert r.n_calls == 240 and r.n_fallback == 0
    assert len(g["header"]["system_prompts"]) == 4


def test_channel_probability(tmp_path):
    cfg = GameConfig(name="t", condition="seeded", models=["m"], rounds=300, channel_p=0.3)
    play_game(cfg, MockBackend(seed=2), seed=4, out_path=tmp_path / "g.jsonl")
    g = load_game(tmp_path / "g.jsonl")
    assert 0.2 < np.mean(g["channel"]) < 0.4


def test_honest_game_has_no_pair(tmp_path):
    cfg = GameConfig(name="t", condition="honest", models=["a", "a", "b", "c"], rounds=20)
    r = play_game(cfg, MockBackend(), seed=0, out_path=tmp_path / "g.jsonl")
    assert r.true_pair is None
    assert sorted(r.seats_models) == ["a", "a", "b", "c"]
    footer = json.loads((tmp_path / "g.jsonl").read_text().splitlines()[-1])
    assert footer["type"] == "footer"
