"""Results viewer: data layer on scripted run dirs, and the HTTP routes ($0, offline)."""

from __future__ import annotations

import importlib.util
import json
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from netinf import viewer as v
from netinf.analysis import write_scripted_run

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "view_results.py"


@pytest.fixture()
def runs(tmp_path):
    for seed in (0, 1, 2):
        write_scripted_run(tmp_path, "C0", seed, n_rounds=150)
        write_scripted_run(tmp_path, "C2", seed, n_rounds=150, p_channel=1.0)
    (tmp_path / "x_bonjour").mkdir()
    (tmp_path / "x_bonjour" / "results.json").write_text(json.dumps(
        [{"base": "nats", "cp": 0.4, "games": 100, "cda": 50.0, "paper": 58.4}]))
    (tmp_path / "x_notes").mkdir()
    (tmp_path / "x_notes" / "readme.md").write_text("| a | b |\n|---|---|\n| 1 | 2 |\n")
    return tmp_path


def test_list_runs_detects_kinds(runs):
    kinds = {e["id"]: e["kind"] for e in v.list_runs(runs)}
    assert kinds["x_bonjour"] == "bonjour_repro"
    assert kinds["x_notes"] == "other"
    assert sum(k == "game" for k in kinds.values()) == 6


def test_game_detail_ranks_seeded_pair_first(runs):
    rid = next(e["id"] for e in v.list_runs(runs) if e.get("condition") == "C2")
    d = v.run_detail(runs, rid)
    det = d["detectors"]["by_state"]["none"]["netinf"]
    assert det["ranked"][0]["true"] and det["true_rank"] == 1
    assert det["alg1"] == d["true_pair"]
    assert d["positive_control_analysis"]["passed"]
    json.dumps(d, allow_nan=False)  # NaN diagonals must be cleaned to null


def test_summary_covers_conditions_and_heldout(runs):
    s = v.summary(runs)
    assert {r["label"] for r in s["summary"]} == {"C0", "C2 p=1"}
    c2 = next(r for r in s["summary"] if r["label"] == "C2 p=1" and r["detector"] == "netinf"
              and r["state"] == "none")
    assert c2["top1"] == 1.0
    te = s["threshold_eval"]
    assert "not frozen" in te["source"] and te["rows"]
    json.dumps(s, allow_nan=False)


def test_summary_keeps_model_sets_apart(runs):
    write_scripted_run(runs, "C2", 7, n_rounds=150, p_channel=1.0, models=["llm-x"] * 4)
    s = v.summary(runs)  # default: the model set with the most runs
    assert s["model_sets"] == {"scripted/uniform": 6, "llm-x": 1}
    assert s["model_set"] == "scripted/uniform" and s["n_games"] == 6
    assert v.summary(runs, "llm-x")["n_games"] == 1
    assert v.summary(runs, "*")["n_games"] == 7


def test_tail_reads_only_new_complete_lines(runs):
    rid = next(e["id"] for e in v.list_runs(runs) if e.get("condition") == "C2")
    path = runs / rid
    meta = json.loads((path / "meta.json").read_text())
    (path / "meta.json").write_text(json.dumps(meta | {"completed": False}))
    lines = (path / "rounds.jsonl").read_text().splitlines(keepends=True)
    (path / "rounds.jsonl").write_text("".join(lines[:3]) + lines[3][:10])  # writer mid-line

    t = v.tail(runs, rid)
    assert [r["round"] for r in t["rounds"]] == [0, 1, 2]
    assert t["status"] == "live"
    entry = next(e for e in v.list_runs(runs) if e["id"] == rid)
    assert entry["status"] == "live" and entry["rounds_completed"] == 3

    with open(path / "rounds.jsonl", "a") as f:  # the writer finishes the line and adds one
        f.write(lines[3][10:] + lines[4])
    t2 = v.tail(runs, rid, t["offsets"]["rounds"], t["offsets"]["calls"])
    assert [r["round"] for r in t2["rounds"]] == [3, 4] and t2["calls"] == []
    assert v.tail(runs, rid, t2["offsets"]["rounds"])["rounds"] == []


def test_run_status_stalled_and_done(runs):
    rid = next(e["id"] for e in v.list_runs(runs) if e.get("condition") == "C0")
    path = runs / rid
    assert v.run_status(path, {"completed": True})["status"] == "done"
    old = time.time() - 2 * v.LIVE_SECONDS
    for f in path.iterdir():
        os.utime(f, (old, old))
    assert v.run_status(path, {"completed": False})["status"] == "stalled"


def test_resolve_run_refuses_escape(runs):
    with pytest.raises(FileNotFoundError):
        v.resolve_run(runs, "../" + runs.name)


def test_server_routes(runs):
    spec = importlib.util.spec_from_file_location("view_results", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), mod.make_handler(runs, mod.Cache(runs)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"

    def get(path):
        with urllib.request.urlopen(base + path, timeout=30) as r:
            return r.status, r.read()

    try:
        assert b"<title>" in get("/")[1]
        ids = [e["id"] for e in json.loads(get("/api/runs")[1])]
        assert json.loads(get(f"/api/run/{ids[0]}")[1])["id"] == ids[0]
        assert json.loads(get("/api/summary")[1])["n_games"] == 6
        assert get("/files/x_notes/readme.md")[1].startswith(b"| a")
        game = next(i for i in ids if i.startswith("C2"))
        t = json.loads(get(f"/api/tail/{game}?r=0&c=0")[1])
        assert len(t["rounds"]) == 150 and t["status"] == "done"
        for bad in ("/files/x_notes/../x_bonjour/results.json", "/api/run/nope"):
            with pytest.raises(urllib.error.HTTPError) as e:
                get(bad)
            assert e.value.code == 404
    finally:
        srv.shutdown()
        srv.server_close()
