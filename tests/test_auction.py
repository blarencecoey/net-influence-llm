"""Offline tests for the double auction (scripted sellers and a fake client, $0)."""

from __future__ import annotations

import json

import numpy as np

from netinf.agents import auction_agent as aa
from netinf.agents.client import make_client
from netinf.envs import auction as au


def test_match_highest_bids_with_lowest_asks_at_midpoint():
    rng = np.random.default_rng(0)
    trades = au.match([82, 100, 88, 94, 93], [93, 94, 95, 87, 86], rng)
    assert [(b, s) for b, s, _ in trades] == [(1, 4), (3, 3), (4, 0)]
    assert [p for *_, p in trades] == [93.0, 90.5, 93.0]


def test_match_no_trade_when_best_bid_below_best_ask():
    assert au.match([85, 84], [90, 91], np.random.default_rng(0)) == []


def test_band_edges():
    assert au.band([80, 89, 90, 94, 95, 100]).tolist() == [0, 0, 1, 1, 2, 2]


def test_parse_ask():
    assert aa.parse_ask("ASK: 92") == 92
    assert aa.parse_ask("I will post **ASK: $95**") == 95
    assert aa.parse_ask("93") == 93
    assert aa.parse_ask("ASK: 92.6") == 93
    assert aa.parse_ask("ASK: 120") is None
    assert aa.parse_ask("no idea") is None


def test_prompts_are_plain_and_state_the_rule():
    s = aa.system_prompt("assistant", 0, 5, partner=2)
    assert "post the same ask as Seller 3" in s and "$80" in s
    assert "Seller 1 has privately agreed" in aa.system_prompt("primary", 2, 5, partner=0)
    assert "agreed" not in aa.system_prompt("honest", 1, 5, None)


def scripted_cfg(**kw) -> dict:
    cfg = au.load_config("configs/auction_a2.yaml")
    cfg.update(provider="scripted", n_rounds=50, seeds=[0])
    cfg.update(kw)
    return cfg


def test_scripted_a2_run_logs_and_passes_positive_control(tmp_path):
    m = au.run_one(scripted_cfg(), 0, None, tmp_path)
    assert m["completed"] and m["positive_control"]["passed"]
    rows = [json.loads(x) for x in (tmp_path / m["run_id"] / "rounds.jsonl").read_text().splitlines()]
    assert len(rows) == 50 and all(len(r["asks"]) == 5 for r in rows)
    r = rows[0]
    assert r["actions"] == au.band(r["asks"]).tolist()
    for _, s, p in r["trades"]:
        assert r["payoffs"][s] == p - au.SELLER_VALUE


def test_llm_seller_with_fake_client(tmp_path):
    def responder(messages, seed):
        if "Private message" in messages[-1]["content"]:
            return "ASK: " + messages[-1]["content"].split("ask of $")[1].split(" ")[0]
        return "ASK: 93"

    client = make_client("fake", responder=responder)
    cfg = scripted_cfg(provider="fake", n_rounds=10, prices={})
    m = au.run_one(cfg, 1, client, tmp_path)
    assert m["completed"] and m["parse_failures"] == 0
    assert m["positive_control"]["match_rate_delivered"] == 1.0
