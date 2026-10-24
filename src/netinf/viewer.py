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
import warnings
from itertools import combinations
from pathlib import Path

import numpy as np

from netinf import analysis as an
from netinf import detector as d
from netinf.baselines import correlation_scores, rank_of_pair

STATES = ("prev_n_distinct", "none", "prev_joint")  # primary (pre-registered) first
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
        return "game"
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


# --------------------------------------------------------------------------- run list


def run_entry(path: Path) -> dict | None:
    kind = kind_of(path)
    if kind is None:
        return None
    e = {"id": path.name, "kind": kind, "mtime": path.stat().st_mtime}
    if kind == "game":
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
                   alpha: float = 0.05) -> dict:
    """Every detector on one run: matrices, ranked pair scores, rank of the true pair, Algorithm 1."""
    T, n = actions.shape
    out = {"n_pairs": n * (n - 1) // 2, "alpha": alpha, "by_state": {}, "state_free": {}}
    if T < 2 or n < 3:
        out["error"] = f"need at least 3 players and 2 rounds (have {n} players, {T} rounds)"
        return out

    def pack(scores, G=None):
        rec = {"ranked": _ranked(scores, true_pair), "matrix": G}
        if true_pair is not None:
            rec["true_rank"] = rank_of_pair(scores, true_pair)
        if G is not None:  # Algorithm 1 applies to the same-round net influence matrix only
            found = d.detect_pair(actions, G=G, alpha=alpha)
            rec["alg1"] = None if found is None else f"{found[0]}-{found[1]}"
        return rec

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for st in states:
            s = an.compute_states(actions, st, warn=False)
            n_states = len(np.unique(s))
            entry = {"n_states": n_states, "bias": 2 * n_states / T,
                     "role": an.state_role(st)}
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


def game_detail(path: Path, states=STATES) -> dict:
    meta = _read_json(path / "meta.json") or {}
    rounds = sorted(_read_jsonl(path / "rounds.jsonl"), key=lambda r: r.get("round", 0))
    calls = _read_jsonl(path / "calls.jsonl")
    n = int(meta.get("n_players") or (len(rounds[0]["actions"]) if rounds else 0))
    actions = np.array([r["actions"] for r in rounds], dtype=np.int64).reshape(len(rounds), n)
    payoffs = (np.array([r["payoffs"] for r in rounds]).reshape(len(rounds), n)
               if rounds and all("payoffs" in r for r in rounds)
               else an.rps.payoffs(actions) if rounds else np.zeros((0, n)))
    assistants = _assistants(meta)
    primary = meta.get("primary")
    true_pair = (tuple(sorted((primary, assistants[0])))
                 if primary is not None and len(assistants) == 1 else None)
    prompts = {p.stem: p.read_text(encoding="utf-8")
               for p in sorted((path / "prompts").glob("*.txt"))} if (path / "prompts").is_dir() \
        else {}
    config_text = ((path / "config.yaml").read_text(encoding="utf-8")
                   if (path / "config.yaml").exists() else None)
    judge = an._load_judge(path / "judge.json")

    pc_analysis = None
    if true_pair is not None and len(rounds):
        run = an.Run(run_id=path.name, condition=str(meta.get("condition")), seed=meta.get("seed"),
                     actions=actions, payoffs=payoffs, primary=primary, assistant=assistants[0])
        pc_analysis = an.positive_control(run)

    T = len(rounds)
    counts = [[int((actions[:, i] == k).sum()) for k in range(an.rps.N_ACTIONS)] for i in range(n)]
    return clean({
        "id": path.name, "kind": "game", "meta": meta, "config_text": config_text,
        "prompts": prompts, "files": _files(path),
        "rounds": {"actions": actions, "payoffs": payoffs,
                   "channel": [r.get("channel_delivered") for r in rounds]},
        "calls": calls, "true_pair": None if true_pair is None else f"{true_pair[0]}-{true_pair[1]}",
        "colluders": [] if primary is None else [primary, *assistants],
        "action_counts": counts,
        "win_rate": [float((payoffs[:, i] > 0).mean()) if T else None for i in range(n)],
        "chance_win_rate": an.chance_win_rate(n) if n else None,
        "positive_control_analysis": pc_analysis,
        "detectors": game_detectors(actions, true_pair, states, judge),
    })


# --------------------------------------------------------------------------- results.json runs


def _text_files(path: Path) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(path.glob("*.md"))}


def results_detail(path: Path, kind: str) -> dict:
    return clean({"id": path.name, "kind": kind, "config": _read_json(path / "config.json"),
                  "results": _read_json(path / "results.json"), "files": _files(path),
                  "texts": _text_files(path)})


def other_detail(path: Path) -> dict:
    return {"id": path.name, "kind": "other", "files": _files(path), "texts": _text_files(path)}


def run_detail(runs_dir: Path, run_id: str) -> dict:
    path = resolve_run(runs_dir, run_id)
    kind = kind_of(path)
    if kind == "game":
        return game_detail(path)
    if kind in ("bonjour_repro", "scripted4"):
        return results_detail(path, kind)
    return other_detail(path)


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
                           "p_channel": e["p_channel"], "passed": e["pc_passed"], "p": e["pc_p"]}
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
