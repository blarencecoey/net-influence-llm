"""Scripted lockstep control (limitations B22): do shared move rules, with no communication, make
net influence false-alarm? CPU only, $0.

Honest LLM agents in C0 play the same move far more often than their own move frequencies predict
(B22). This script reproduces two candidate mechanisms with scripted agents and scores them with
the same detectors as the LLM runs:

- own_last(q): round 1 Rock; then with prob. q play the move that beats your own last move, else
  uniform. Players share only the opening.
- shared_mode(q): round 1 Rock; then with prob. q play the move that beats the most common move of
  the previous round (ties broken by the player's own RNG), else uniform. Players share the public
  history, a common cause.
- mistral_like: iid draws from the C1 Mistral move frequencies (R 0.072, P 0.695, S 0.233; measured
  over 82 C1 player-runs, 2026-10-24).

Layouts: all4 (every player on the rule; C0 analogue) and subset2 (players 0, 1 on the rule, 2, 3
mistral_like; C1 analogue, rule pair = (0, 1)). The LLM C0 / C1 runs in runs/ are scored alongside.

Per condition: all-same round rate, honest-pair agreement minus the rate expected from each
player's own move frequencies, max pair score per game (median / 95th pct / max), how often the
top pair is (0, 1), Algorithm 1 flag rate at alpha, and the false-alarm rate at the frozen LLM
thresholds when --thresholds is given (reference only: those thresholds were fitted on LLM nulls).

Usage: python scripts/scripted_lockstep.py --games 200 --rounds 200 \
           --thresholds <calib dir>/thresholds.json
"""

from __future__ import annotations

import argparse
import glob
import json
import shutil
import time
from itertools import combinations
from pathlib import Path

import numpy as np

from netinf import analysis as an
from netinf import detector as d
from netinf.baselines import correlation_scores
from netinf.envs import rps

MISTRAL_FREQ = np.array([0.072, 0.695, 0.233])
STATES = ("prev_n_distinct", "none", "prev_joint")
RULE_PAIR = "0-1"


def beats(x):
    return (x + 1) % rps.N_ACTIONS  # PAPER beats ROCK, SCISSORS beats PAPER, ROCK beats SCISSORS


def simulate(policies: list[tuple[str, float]], n_rounds: int, rng: np.random.Generator) -> np.ndarray:
    n = len(policies)
    a = np.zeros((n_rounds, n), dtype=np.int64)
    for t in range(n_rounds):
        prev = a[t - 1] if t else None
        counts = np.bincount(prev, minlength=3) if t else None
        for i, (kind, q) in enumerate(policies):
            if kind == "mistral_like":
                a[t, i] = rng.choice(3, p=MISTRAL_FREQ)
            elif kind == "uniform":
                a[t, i] = rng.integers(3)
            elif t == 0:
                a[t, i] = rps.ROCK
            elif rng.random() >= q:
                a[t, i] = rng.integers(3)
            elif kind == "own_last":
                a[t, i] = beats(prev[i])
            elif kind == "shared_mode":
                modes = np.flatnonzero(counts == counts.max())
                a[t, i] = beats(rng.choice(modes))
            else:
                raise ValueError(kind)
    return a


def conditions(qs):
    out = {"uniform all4": [("uniform", 0.0)] * 4}
    for rule in ("own_last", "shared_mode"):
        for q in qs:
            out[f"{rule} q={q:g} all4"] = [(rule, q)] * 4
    out["uniform+mistral_like subset2"] = [("uniform", 0.0)] * 2 + [("mistral_like", 0.0)] * 2
    for rule in ("own_last", "shared_mode"):
        for q in qs:
            out[f"{rule} q={q:g} subset2"] = [(rule, q)] * 2 + [("mistral_like", 0.0)] * 2
    return out


def score_game(a: np.ndarray, alpha: float) -> dict:
    T = len(a)
    rec = {"all_same": float((a == a[:, :1]).all(1).mean())}
    exc = {}
    for i, j in combinations(range(a.shape[1]), 2):
        fi, fj = (np.bincount(a[:, k], minlength=3) / T for k in (i, j))
        exc[f"{i}-{j}"] = float((a[:, i] == a[:, j]).mean() - fi @ fj)
    rec["agree_excess"] = exc
    for st in STATES:
        s = an.compute_states(a, st, warn=False)
        G = d.net_influence_matrix(a, s)
        sc = d.pair_scores(G)
        top = max(sc, key=sc.get)
        rec[f"netinf|{st}"] = {"max": sc[top], "top": f"{top[0]}-{top[1]}",
                               "alg1": d.detect_pair(a, G=G, alpha=alpha) is not None}
    sc = correlation_scores(a)
    top = max(sc, key=sc.get)
    rec["correlation|-"] = {"max": sc[top], "top": f"{top[0]}-{top[1]}", "alg1": None}
    return rec


def summarize(name: str, games: list[dict], th: dict | None) -> dict:
    row = {"condition": name, "n_games": len(games),
           "all_same": float(np.mean([g["all_same"] for g in games]))}
    pairs = games[0]["agree_excess"].keys()
    row["agree_excess"] = {p: float(np.mean([g["agree_excess"][p] for g in games])) for p in pairs}
    for det in [f"netinf|{s}" for s in STATES] + ["correlation|-"]:
        m = np.array([g[det]["max"] for g in games])
        r = {"median": float(np.median(m)), "p95": float(np.quantile(m, 0.95)), "max": float(m.max()),
             "top_is_0-1": float(np.mean([g[det]["top"] == RULE_PAIR for g in games]))}
        if det.startswith("netinf"):
            r["alg1_rate"] = float(np.mean([g[det]["alg1"] for g in games]))
        if th and det in th["detectors"]:
            for f in th["fprs"]:
                r[f"fa@{f}"] = float(np.mean(m > th["detectors"][det][str(f)]))
        row[det] = r
    return row


def fmt_row(r: dict) -> str:
    n, c = r["netinf|prev_n_distinct"], r["correlation|-"]
    e = r["agree_excess"]
    fa = lambda x: " ".join(f"{x[k]:.2f}" for k in x if k.startswith("fa@"))
    return (f"{r['condition']:32} n={r['n_games']:3} same {r['all_same']:.3f} "
            f"excess 0-1 {e[RULE_PAIR]:+.3f} 2-3 {e['2-3']:+.3f} 0-2 {e['0-2']:+.3f} | netinf "
            f"med {n['median']:.3f} p95 {n['p95']:.3f} max {n['max']:.3f} top01 {n['top_is_0-1']:.2f} "
            f"alg1 {n['alg1_rate']:.2f} fa {fa(n)} | corr p95 {c['p95']:.3f} fa {fa(c)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--games", type=int, default=200, help="independent games per condition")
    ap.add_argument("--rounds", type=int, default=200)
    ap.add_argument("--q", type=float, nargs="+", default=[0.4, 0.7, 0.9])
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--thresholds", type=Path, help="frozen thresholds.json (reference only)")
    ap.add_argument("--llm-runs", nargs="*", default=["runs/C0_llama-*", "runs/C1_llama-*"])
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    out = args.out or Path("runs") / f"{time.strftime('%Y%m%d-%H%M%S')}_scripted_lockstep_{args.rounds}r"
    out.mkdir(parents=True, exist_ok=True)
    th = an.load_thresholds(args.thresholds) if args.thresholds else None
    if args.thresholds:
        shutil.copy(args.thresholds, out / "thresholds_reference.json")
    (out / "config.json").write_text(json.dumps(
        vars(args) | {"out": str(out), "thresholds": str(args.thresholds),
                      "mistral_freq": MISTRAL_FREQ.tolist(), "states": STATES}, indent=2, default=str))

    rows = []
    for k, (name, pol) in enumerate(conditions(args.q).items()):
        games = [score_game(simulate(pol, args.rounds, np.random.default_rng([args.seed, k, g])),
                            args.alpha) for g in range(args.games)]
        rows.append(summarize(name, games, th))
        print(fmt_row(rows[-1]), flush=True)

    # LLM nulls, completed runs only, same metrics. C1 players 0, 1 are Llama, 2, 3 Mistral.
    for label, pat in zip(("LLM C0 Llama x4", "LLM C1 Llama+Mistral"), args.llm_runs):
        dirs = [Path(p) for p in sorted(glob.glob(pat))
                if json.loads((Path(p) / "meta.json").read_text(encoding="utf-8")).get("completed")]
        games = [score_game(an.load_run(p).actions, args.alpha) for p in dirs]
        if games:
            rows.append(summarize(label, games, th) | {"run_ids": [p.name for p in dirs]})
            print(fmt_row(rows[-1]), flush=True)

    (out / "results.json").write_text(json.dumps(rows, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
