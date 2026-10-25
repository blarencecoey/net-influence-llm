"""Data layer for the local results viewer (scripts/view_results.py, page in viewer/index.html).

Read-only: turns the folders in runs/ into JSON for the page. Nothing here writes to runs/.

Run kinds (detected from the files present):
- game: an RPS run dir in the harness format (meta.json + rounds.jsonl, notes/methods/llm-harness.md),
  LLM or scripted. Detector scores are recomputed here with netinf.analysis / netinf.detector.
- bonjour_repro: output of scripts/reproduce_bonjour.py (config.json + results.json, CDA rows).
- scripted4: output of scripts/scripted_four_agent.py (config.json + results.json, top-1 rows).
- other: any other folder; files are listed and served as-is.

Overview (`summary`), for one model set at a time: positive control per seeded game run,
analysis.summarize over the completed game runs (one unit per run), and TPR / FPR at fixed FPR on
held-out seeds. Thresholds come from
runs/thresholds.json if it exists (frozen, written by analysis.save_thresholds), otherwise they are
fitted on the default calibration seeds at view time and labelled as not frozen.
"""

from __future__ import annotations

import json
import math
import time
import warnings
from itertools import combinations
from pathlib import Path

import numpy as np

from netinf import analysis as an
from netinf import auction_analysis as aq
from netinf import detector as d
from netinf.baselines import correlation_scores, rank_of_pair

STATES = ("prev_n_distinct", "none", "prev_joint")  # primary (pre-registered) first
AUCTION_MIN_ROUNDS = 100  # shorter auction runs (smoke tests) are left out of the auction overview
LIVE_SECONDS = 180  # an unfinished run written to within this many seconds counts as live
THRESHOLDS_FILE = "thresholds.json"
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".jsonl", ".csv", ".log"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".gif"}


# --------------------------------------------------------------------------- helpers


def clean(x):
    """JSON-safe copy: numpy scalars/arrays to Python, NaN/inf to None, tuple keys to 'i-j'."""
    if isinstance(x, dict):
        return {(f"{k[0]}-{k[1]}" if isinstance(k, tuple) else str(k)): clean(v)
                for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, np.generic):
        x = x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:  # a crash can leave a half-written last line
            continue
    return out


def _files(path: Path) -> list[dict]:
    out = []
    for p in sorted(path.rglob("*")):
        if p.is_file():
            out.append({"path": p.relative_to(path).as_posix(), "size": p.stat().st_size,
                        "kind": "image" if p.suffix.lower() in IMAGE_SUFFIXES
                        else "text" if p.suffix.lower() in TEXT_SUFFIXES else "binary"})
    return out


def kind_of(path: Path) -> str | None:
    if not path.is_dir():
        return None
    if (path / "meta.json").exists() and (path / "rounds.jsonl").exists():
        return "auction" if aq.is_auction(path) else "game"
    if (path / "results.json").exists():
        rows = _read_json(path / "results.json")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            if "cda" in rows[0] and "games" in rows[0]:
                return "bonjour_repro"
            if "top1" in rows[0] and "detector" in rows[0]:
                return "scripted4"
    return "other" if any(path.iterdir()) else None


def resolve_run(runs_dir: Path, run_id: str) -> Path:
    """runs_dir / run_id, refusing anything that escapes runs_dir."""
    root = Path(runs_dir).resolve()
    p = (root / run_id).resolve()
    if p.parent != root or not p.is_dir():
        raise FileNotFoundError(run_id)
    return p


def _assistants(meta: dict) -> list[int]:
    a = meta.get("assistant")
    return [] if a is None else list(a) if isinstance(a, list) else [a]


def run_status(path: Path, meta: dict) -> dict:
    """'done', 'live' (unfinished, written to recently) or 'stalled' (unfinished, quiet: crashed,
    killed, or a very slow API), with seconds since the last write."""
    mtimes = [p.stat().st_mtime for p in (path / "meta.json", path / "rounds.jsonl",
                                          path / "calls.jsonl") if p.exists()]
    age = time.time() - max(mtimes) if mtimes else None
    if meta.get("completed") or meta.get("finished_at"):
        status = "done"
    else:
        status = "live" if age is not None and age < LIVE_SECONDS else "stalled"
    return {"status": status, "age_s": age}


# --------------------------------------------------------------------------- run list


def run_entry(path: Path) -> dict | None:
    kind = kind_of(path)
    if kind is None:
        return None
    e = {"id": path.name, "kind": kind, "mtime": path.stat().st_mtime}
    if kind in ("game", "auction"):
        m = _read_json(path / "meta.json") or {}
        pc = m.get("positive_control") or {}
        e |= {k: m.get(k) for k in (
            "condition", "seed", "p_channel", "n_players", "n_rounds", "rounds_completed",
            "completed", "stop_reason", "total_cost_usd", "cost_complete", "total_input_tokens",
            "total_output_tokens", "parse_failures", "primary", "started_at", "prompt_version")}
        e["assistants"] = _assistants(m)
        e["models"] = sorted({str(a.get("model")) for a in m.get("agents") or []})
        e["provider"] = next((a.get("provider") for a in m.get("agents") or []), None)
        e["pc_passed"] = pc.get("passed")
        e["pc_p"] = pc.get("p_value")
        e["pc_test"] = pc.get("test")  # the harness's test changed over time; label from the run
        if kind == "auction":
            e["pc_match"] = pc.get("match_rate_delivered")
            e["mean_ask"] = m.get("mean_ask")
        e |= run_status(path, m)
        if e["status"] != "done":  # meta.json is only rewritten at the end; count logged rounds
            with open(path / "rounds.jsonl", "rb") as f:
                e["rounds_completed"] = f.read().count(b"\n")
    else:
        cfg = _read_json(path / "config.json") or {}
        e["config"] = cfg
    return e


def list_runs(runs_dir: Path) -> list[dict]:
    runs_dir = Path(runs_dir)
    if not runs_dir.is_dir():
        return []
    out = [e for p in runs_dir.iterdir() if (e := run_entry(p))]
    return clean(sorted(out, key=lambda e: -e["mtime"]))


# --------------------------------------------------------------------------- one game run


def _ranked(scores: dict, true_pair) -> list[dict]:
    rows = [{"pair": f"{i}-{j}", "score": v} for (i, j), v in scores.items()]
    rows.sort(key=lambda r: -r["score"] if r["score"] is not None and math.isfinite(r["score"])
              else math.inf)
    for k, r in enumerate(rows, 1):
        r["rank"] = k
        r["true"] = true_pair is not None and r["pair"] == f"{true_pair[0]}-{true_pair[1]}"
    return rows


def game_detectors(actions: np.ndarray, true_pair, states=STATES, judge=None,
                   alpha: float = 0.05, state_codes: dict | None = None,
                   primary_state: str = an.PRIMARY_STATE) -> dict:
    """Every detector on one run: matrices, ranked pair scores, rank of the true pair, Algorithm 1.
    `state_codes` ({name: codes per round}) replaces analysis.compute_states, for states that are
    not a function of the actions (the auction's previous trade price band)."""
    T, n = actions.shape
    out = {"n_pairs": n * (n - 1) // 2, "alpha": alpha, "by_state": {}, "state_free": {}}
    if T < 2 or n < 3:
        out["error"] = f"need at least 3 players and 2 rounds (have {n} players, {T} rounds)"
        return out

    def pack(scores, G=None):
        rec = {"ranked": _ranked(scores, true_pair), "matrix": G}
        if true_pair is not None and true_pair in scores:  # a judge may leave pairs unscored
            rec["true_rank"] = rank_of_pair(scores, true_pair)
        if G is not None:  # Algorithm 1 applies to the same-round net influence matrix only
            found = d.detect_pair(actions, G=G, alpha=alpha)
            rec["alg1"] = None if found is None else f"{found[0]}-{found[1]}"
        return rec

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for st in (state_codes or states):
            s = (np.asarray(state_codes[st]) if state_codes
                 else an.compute_states(actions, st, warn=False))
            n_states = len(np.unique(s))
            entry = {"n_states": n_states, "bias": 2 * n_states / T,
                     "role": "primary (pre-registered)" if st == primary_state else "secondary"}
            for det, mm in (("netinf", False), ("netinf_mm", True)):
                G = d.net_influence_matrix(actions, s, bias_correct=mm)
                entry[det] = pack(d.pair_scores(G), G)
            entry["gamma"] = d.influence_matrix(actions, s)
            out["by_state"][st] = entry
        lag = d.lagged_net_matrix(actions)
        lag_scores = {(i, j): float(max(lag[i, j], lag[j, i]))
                      for i, j in combinations(range(n), 2)}
        out["state_free"]["lagged_netinf"] = pack(lag_scores) | {"matrix": lag}
        out["state_free"]["correlation"] = pack(correlation_scores(actions))
        if judge:
            out["state_free"]["judge"] = pack(judge)
    return out


def game_detection(path: Path, states=STATES) -> dict:
    """The part of a game run that changes every round: rounds, detectors, win rates, positive
    control and run status. Light enough to poll while a run is live (no calls or prompts)."""
    meta = _read_json(path / "meta.json") or {}
    rounds = sorted(_read_jsonl(path / "rounds.jsonl"), key=lambda r: r.get("round", 0))
    n = int(meta.get("n_players") or (len(rounds[0]["actions"]) if rounds else 0))
    actions = np.array([r["actions"] for r in rounds], dtype=np.int64).reshape(len(rounds), n)
    payoffs = (np.array([r["payoffs"] for r in rounds]).reshape(len(rounds), n)
               if rounds and all("payoffs" in r for r in rounds)
               else an.rps.payoffs(actions) if rounds else np.zeros((0, n)))
    assistants = _assistants(meta)
    primary = meta.get("primary")
    true_pair = (tuple(sorted((primary, assistants[0])))
                 if primary is not None and len(assistants) == 1 else None)
    judge = an._load_judge(path / "judge.json")

    pc_analysis = None
    if true_pair is not None and len(rounds):
        run = an.Run(run_id=path.name, condition=str(meta.get("condition")), seed=meta.get("seed"),
                     actions=actions, payoffs=payoffs, primary=primary, assistant=assistants[0])
        pc_analysis = an.positive_control(run)

    T = len(rounds)
    counts = [[int((actions[:, i] == k).sum()) for k in range(an.rps.N_ACTIONS)] for i in range(n)]
    return clean({
        "id": path.name, "kind": "game", "meta": meta, **run_status(path, meta),
        "rounds": {"actions": actions, "payoffs": payoffs,
                   "channel": [r.get("channel_delivered") for r in rounds]},
        "true_pair": None if true_pair is None else f"{true_pair[0]}-{true_pair[1]}",
        "colluders": [] if primary is None else [primary, *assistants],
        "action_counts": counts,
        "win_rate": [float((payoffs[:, i] > 0).mean()) if T else None for i in range(n)],
        "chance_win_rate": an.chance_win_rate(n) if n else None,
        "positive_control_analysis": pc_analysis,
        "detectors": game_detectors(actions, true_pair, states, judge),
    })


def game_detail(path: Path, states=STATES) -> dict:
    prompts = {p.stem: p.read_text(encoding="utf-8")
               for p in sorted((path / "prompts").glob("*.txt"))} if (path / "prompts").is_dir() \
        else {}
    config_text = ((path / "config.yaml").read_text(encoding="utf-8")
                   if (path / "config.yaml").exists() else None)
    return game_detection(path, states) | clean({
        "config_text": config_text, "prompts": prompts, "files": _files(path),
        "calls": _read_jsonl(path / "calls.jsonl")})


# --------------------------------------------------------------------------- live tail


def _read_from(path: Path, offset: int) -> tuple[list[dict], int]:
    """Complete JSON lines after byte `offset`, and the offset just past the last one. A line the
    writer has not finished (no newline yet) is left for the next call."""
    if not path.exists():
        return [], 0
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read()
    end = data.rfind(b"\n") + 1
    recs = []
    for line in data[:end].splitlines():
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return recs, offset + end


def tail(runs_dir: Path, run_id: str, rounds_offset: int = 0, calls_offset: int = 0) -> dict:
    """New rounds and calls of a game run since the given byte offsets (0 = from the start), for
    following a run while it plays or stepping through it afterwards. The harness writes a
    round's calls, then the round line, once all agents have moved, so the unit is one round."""
    path = resolve_run(runs_dir, run_id)
    if kind_of(path) != "game":
        raise FileNotFoundError(f"{run_id} is not a game run")
    meta = _read_json(path / "meta.json") or {}
    rounds, r_off = _read_from(path / "rounds.jsonl", rounds_offset)
    calls, c_off = _read_from(path / "calls.jsonl", calls_offset)
    return clean({"id": path.name, "meta": meta, **run_status(path, meta),
                  "rounds": rounds, "calls": calls,
                  "offsets": {"rounds": r_off, "calls": c_off}})


# --------------------------------------------------------------------------- results.json runs


def _text_files(path: Path) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(path.glob("*.md"))}


def results_detail(path: Path, kind: str) -> dict:
    return clean({"id": path.name, "kind": kind, "config": _read_json(path / "config.json"),
                  "results": _read_json(path / "results.json"), "files": _files(path),
                  "texts": _text_files(path)})


def other_detail(path: Path) -> dict:
    return {"id": path.name, "kind": "other", "files": _files(path), "texts": _text_files(path)}


# --------------------------------------------------------------------------- auction runs


def auction_detail(path: Path) -> dict:
    """One double-auction run: per-hour order book, market series, positive control, detectors
    (on the banded asks, with the auction's states), calls, prompts and config."""
    run = aq.load(path)
    meta, a, T = run["meta"], run["actions"], len(run["actions"])
    tp = aq.true_pair(meta)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dets = (game_detectors(a, tp, state_codes=aq.states(run), primary_state=aq.PRIMARY_STATE)
                if T >= 2 else {"error": "fewer than 2 hours logged", "by_state": {}, "state_free": {}})
    stats = aq.market_stats(run) if T else {}
    prompts = {p.stem: p.read_text(encoding="utf-8")
               for p in sorted((path / "prompts").glob("*.txt"))} if (path / "prompts").is_dir() \
        else {}
    return clean({
        "id": path.name, "kind": "auction", "meta": meta, **run_status(path, meta),
        "rounds": [{k: r.get(k) for k in ("round", "asks", "actions", "bids", "trades", "payoffs",
                                          "channel_delivered")} for r in run["rounds"]],
        "series": {"trade_price": run["trade_price"], "n_trades": run["n_trades"],
                   "mean_ask": a.shape[0] and run["asks"].mean(axis=1)},
        "true_pair": None if tp is None else f"{tp[0]}-{tp[1]}",
        "colluders": [] if tp is None else [meta["primary"], meta["assistant"]],
        "market": stats, "references": {"equilibrium_ask": aq.symmetric_equilibrium(),
                                        "joint_optimal_ask": aq.joint_optimal_ask(),
                                        "midpoint": 90},
        "detectors": dets, "primary_state": aq.PRIMARY_STATE,
        "config_text": (path / "config.yaml").read_text(encoding="utf-8")
        if (path / "config.yaml").exists() else None,
        "prompts": prompts, "files": _files(path), "calls": _read_jsonl(path / "calls.jsonl")})


def auction_summary(runs_dir: Path) -> dict:
    """Overview of the double-auction runs: per condition and model set, market statistics, the
    mean ask and trade price by 10-hour block, positive control, and detection at the run level."""
    runs_dir = Path(runs_dir)
    out = {"runs_dir": str(runs_dir.resolve()), "groups": [], "runs": [],
           "references": {"equilibrium_ask": aq.symmetric_equilibrium(),
                          "joint_optimal_ask": aq.joint_optimal_ask(), "midpoint": 90},
           "primary_state": aq.PRIMARY_STATE}
    paths = [p for p in sorted(runs_dir.iterdir()) if kind_of(p) == "auction"] \
        if runs_dir.is_dir() else []
    groups: dict[tuple, list] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in paths:
            run = aq.load(p)
            m = run["meta"]
            if not m.get("completed") or not len(run["actions"]):
                continue
            if (m.get("n_rounds") or 0) < AUCTION_MIN_ROUNDS:
                out.setdefault("skipped", []).append(
                    {"id": p.name, "reason": f"short run ({m.get('n_rounds')} hours, e.g. a smoke test)"})
                continue
            ms = model_set(a.get("model") for a in m.get("agents") or [])
            recs = {(x["detector"], x["state"]): x for x in aq.score(run)}
            prim = recs[("netinf", aq.PRIMARY_STATE)]
            row = {"id": p.name, "condition": m["condition"], "seed": m["seed"], "models": ms,
                   **aq.market_stats(run), "pc": m.get("positive_control"),
                   "true_pair": prim.get("true_pair"), "netinf_max": prim["max_score"],
                   "netinf_top": prim["top_pair"], "netinf_rank": prim.get("rank"),
                   "alg1_any": prim.get("alg1_any"), "alg1_correct": prim.get("alg1_correct"),
                   "lagged_rank": recs[("lagged_netinf", "none")].get("rank"),
                   "corr_rank": recs[("correlation", "-")].get("rank"),
                   "cost": m.get("total_cost_usd")}
            out["runs"].append(row)
            groups.setdefault((m["condition"], ms), []).append((row, run))
    for (cond, ms), items in sorted(groups.items()):
        rows = [r for r, _ in items]
        T = min(len(run["asks"]) for _, run in items)
        ask = np.mean([run["asks"][:T].mean(axis=1) for _, run in items], axis=0)
        price = np.nanmean([run["trade_price"][:T] for _, run in items], axis=0)
        seeded = [r for r in rows if r["true_pair"]]
        out["groups"].append({
            "condition": cond, "models": ms, "n": len(rows),
            "mean_ask": float(np.mean([r["mean_ask"] for r in rows])),
            "mean_trade_price": float(np.nanmean([r["mean_trade_price"] for r in rows])),
            "share_ask_supra": float(np.mean([r["share_ask_supra"] for r in rows])),
            "trades_per_hour": float(np.mean([r["trades_per_hour"] for r in rows])),
            "ask_blocks": aq.blocks(ask), "price_blocks": aq.blocks(price),
            "pc_pass": sum(bool((r["pc"] or {}).get("passed")) for r in seeded),
            "top1": sum(r["netinf_rank"] == 1 for r in seeded) if seeded else None,
            "alg1_any": sum(bool(r["alg1_any"]) for r in rows),
            "cost": float(sum(r["cost"] or 0 for r in rows))})
    return clean(out)


def run_detail(runs_dir: Path, run_id: str) -> dict:
    path = resolve_run(runs_dir, run_id)
    kind = kind_of(path)
    if kind == "auction":
        return auction_detail(path)
    if kind == "game":
        return game_detail(path)
    if kind in ("bonjour_repro", "scripted4"):
        return results_detail(path, kind)
    return other_detail(path)


def run_detection(runs_dir: Path, run_id: str) -> dict:
    path = resolve_run(runs_dir, run_id)
    if kind_of(path) != "game":
        raise FileNotFoundError(f"{run_id} is not a game run")
    return game_detection(path)


# --------------------------------------------------------------------------- overview


def model_set(models) -> str:
    """Key for the set of models in a run, e.g. 'scripted' or 'model-a+model-b'."""
    return "+".join(sorted({str(m) for m in models})) or "unknown"


def load_game_runs(runs_dir: Path, models: str | None = None) -> tuple[list, list[dict]]:
    """Completed game runs as analysis.Run (only model set `models` if given), plus notes on the
    ones left out and why."""
    runs, skipped = [], []
    for p in sorted(Path(runs_dir).iterdir()) if Path(runs_dir).is_dir() else []:
        if kind_of(p) != "game":
            continue
        meta = _read_json(p / "meta.json") or {}
        if models is not None and model_set(a.get("model") for a in meta.get("agents") or []) \
                != models:
            continue
        if meta.get("completed") is False:
            skipped.append({"id": p.name, "reason": "incomplete (completed=false)"})
        elif len(_assistants(meta)) > 1:
            skipped.append({"id": p.name, "reason": "more than one assistant (C4): no single "
                                                    "true pair for the pairwise metrics"})
        else:
            try:
                runs.append(an.load_run(p))
            except (ValueError, KeyError, IndexError, OSError) as e:
                skipped.append({"id": p.name, "reason": f"could not load: {e}"})
    return runs, skipped


def threshold_eval(records: list[dict], runs_dir: Path) -> dict:
    frozen = Path(runs_dir) / THRESHOLDS_FILE
    if frozen.exists():
        th = an.load_thresholds(frozen)
        source = f"frozen: {THRESHOLDS_FILE}"
    else:
        cal = [r for r in records if r["split"] == "calibration"]
        if not any(not r["colluding"] for r in cal):
            return {"error": "no no-collusion (C0/C1) runs on the calibration seeds "
                             f"{list(an.DEFAULT_CALIB_SEEDS)}; nothing to fit thresholds on"}
        th = an.fit_thresholds(cal)
        source = (f"fitted at view time on calibration seeds {list(an.DEFAULT_CALIB_SEEDS)} "
                  f"(not frozen; save with analysis.save_thresholds to runs/{THRESHOLDS_FILE})")
    held = [r for r in records if r["split"] == "heldout"]
    try:
        rows = an.evaluate(held, th) if held else []
    except ValueError as e:
        return {"error": str(e), "source": source, "thresholds": th}
    return {"source": source, "thresholds": th, "rows": rows}


def summary(runs_dir: Path, models: str | None = None, states=STATES) -> dict:
    """Overview for one model set (`models`, see model_set). Defaults to the model set with the
    most game runs: pooling scripted dry runs with LLM runs under one condition label would mix
    two different experiments. `models="*"` pools everything."""
    runs_dir = Path(runs_dir)
    entries = list_runs(runs_dir)
    all_games = [e for e in entries if e["kind"] == "game"]
    counts: dict[str, int] = {}
    for e in all_games:
        counts[model_set(e["models"])] = counts.get(model_set(e["models"]), 0) + 1
    if models is None and counts:
        models = max(counts, key=lambda k: (counts[k], k))
    if models == "*":
        models = None
    games = [e for e in all_games if models is None or model_set(e["models"]) == models]
    spend = {"total_cost_usd": sum(e.get("total_cost_usd") or 0 for e in games),
             "cost_complete": all(e.get("cost_complete") is not False for e in games),
             "input_tokens": sum(e.get("total_input_tokens") or 0 for e in games),
             "output_tokens": sum(e.get("total_output_tokens") or 0 for e in games),
             "parse_failures": sum(e.get("parse_failures") or 0 for e in games)}
    runs, skipped = load_game_runs(runs_dir, models)
    out = {"runs_dir": str(runs_dir.resolve()), "n_runs": len(entries), "n_games": len(games),
           "model_sets": counts, "model_set": "*" if models is None else models,
           "spend": spend, "skipped": skipped, "states": list(states),
           "primary_state": an.PRIMARY_STATE, "calib_seeds": list(an.DEFAULT_CALIB_SEEDS),
           "harness_pc": [{"id": e["id"], "condition": e["condition"], "seed": e["seed"],
                           "p_channel": e["p_channel"], "passed": e["pc_passed"], "p": e["pc_p"],
                           "test": e.get("pc_test")}
                          for e in games if e.get("pc_passed") is not None],
           "other_results": [e for e in entries if e["kind"] in ("bonjour_repro", "scripted4")]}
    if not runs:
        return clean(out)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pc = an.apply_positive_control(runs)
        cal, held = an.split_runs(runs) if all(r.seed is not None for r in runs) else ([], runs)
        records = (an.score_units(cal, states, split="calibration")
                   + an.score_units(held, states, split="heldout"))
        out["positive_control"] = pc
        out["summary"] = an.summarize(records)
        out["threshold_eval"] = threshold_eval(records, runs_dir)
        n = runs[0].actions.shape[1]
        out["chance_top1"] = 2 / (n * (n - 1))  # one true pair among n choose 2
        if any(r.condition == "C1" for r in runs):
            out["h1"] = {st: an.h1_family_comparison(records, state=st) for st in states}
    return clean(out)
