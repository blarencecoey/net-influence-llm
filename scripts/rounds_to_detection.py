"""Rounds needed for detection: truncate every run to its first T rounds, refit the thresholds on
the truncated calibration nulls, and evaluate on the truncated held-out runs.

Seeded sets: C2 Llama 3.3 70B x4 (prompt v3, 200 rounds) and C2 Llama + Mistral (c2_mixed). The
held-out split follows the calibration seeds (same seed-overlap rule as analysis.check_heldout).
Top-1 and Algorithm 1 need no threshold, so they are also reported over all seeded runs.

Usage (repo root):
  python scripts/rounds_to_detection.py --calib-seeds 5-54 --out notes/results/rounds-to-detection
"""

from __future__ import annotations

import argparse
import csv
import json
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np

from netinf import analysis as an

ROUNDS = (25, 50, 75, 100, 125, 150, 175, 200)
STATES = (an.PRIMARY_STATE, "none")
SETS = {
    "C0": ["runs/C0_llama*"],
    "C1": ["runs/C1_llama*"],
    "C2 Llama": ["runs/C2_llama-3.3-70b-instruct_p1.0_s*"],
    "C2 mixed": ["runs/C2_llama-3.3-70b-instruct+mistral-small-3.2-24b-instruct_p1.0_s*"],
}


def load_sets() -> dict[str, list[an.Run]]:
    out = {}
    for name, pats in SETS.items():
        runs = [r for r in an.load_runs(pats) if len(r.actions) == 200]
        if name.startswith("C2"):  # 200-round v3 runs only (drops the v1/v2/smoke runs)
            runs = [r for r in runs if r.meta.get("prompt_version") == "v3"]
        out[name] = runs
    return out


def seeds(spec: str) -> set[int]:
    lo, hi = spec.split("-")
    return set(range(int(lo), int(hi) + 1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--calib-seeds", default="5-54", help="inclusive range, e.g. 5-54")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    warnings.filterwarnings("ignore", message="skipping incomplete run")
    warnings.filterwarnings("ignore", message=".*plug-in bias.*")
    cal = seeds(args.calib_seeds)
    sets = load_sets()
    print("runs: " + ", ".join(f"{k} {len(v)}" for k, v in sets.items()))

    rows = []
    for T in ROUNDS:
        recs = {}
        for name, runs in sets.items():
            cut = [replace(r, actions=r.actions[:T], payoffs=r.payoffs[:T], segments=(T,),
                           judge=None) for r in runs]
            recs[name] = an.score_units(cut, states=STATES)
        null_cal = [x for k in ("C0", "C1") for x in recs[k] if x["seeds"][0] in cal]
        th = an.fit_thresholds(null_cal)
        for name, rs in recs.items():
            for st in STATES:
                sel = [x for x in rs if x["detector"] == "netinf" and x["state"] == st]
                held = [x for x in sel if x["seeds"][0] not in cal]
                t = th["detectors"][f"netinf|{st}"]
                row = {"rounds": T, "set": name, "state": st, "n_all": len(sel),
                       "n_heldout": len(held), "thr_1pct": t["0.01"], "thr_5pct": t["0.05"]}
                if name.startswith("C2"):
                    hit = lambda x, f: x["max_score"] > t[f] and x["top_pair"] == x["true_pair"]
                    row |= {"top1_all": np.mean([x["top1"] for x in sel]),
                            "alg1_correct_all": np.mean([x["alg1_correct"] for x in sel]),
                            "tpr_1pct_heldout": np.mean([hit(x, "0.01") for x in held]),
                            "tpr_5pct_heldout": np.mean([hit(x, "0.05") for x in held]),
                            "min_true_score_all": min(x["true_score"] for x in sel)}
                else:
                    row |= {"alg1_any_all": np.mean([x["alg1_any"] for x in sel]),
                            "fpr_1pct_heldout": np.mean([x["max_score"] > t["0.01"] for x in held]),
                            "fpr_5pct_heldout": np.mean([x["max_score"] > t["0.05"] for x in held])}
                rows.append(row)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k)
                  if k in rows[0] else 99)
    with open(out / "rounds_to_detection.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    (out / "config.json").write_text(json.dumps(
        {"calib_seeds": args.calib_seeds, "rounds": ROUNDS, "states": STATES, "sets": SETS,
         "runs": {k: [r.run_id for r in v] for k, v in sets.items()}}, indent=2),
        encoding="utf-8")
    for st in STATES:
        print(f"\nstate {st}")
        print("  T    thr@1%   C2L top1 alg1 tpr1% tpr5% (n)   C2M top1 alg1 tpr1% tpr5% (n)   "
              "C0 alg1 fpr1% fpr5%   C1 alg1 fpr1% fpr5%")
        for T in ROUNDS:
            g = {r["set"]: r for r in rows if r["rounds"] == T and r["state"] == st}
            c2 = lambda s: (f"{g[s]['top1_all']:.2f} {g[s]['alg1_correct_all']:.2f} "
                            f"{g[s]['tpr_1pct_heldout']:.2f} {g[s]['tpr_5pct_heldout']:.2f} "
                            f"({g[s]['n_all']}/{g[s]['n_heldout']})")
            nl = lambda s: (f"{g[s]['alg1_any_all']:.2f} {g[s]['fpr_1pct_heldout']:.2f} "
                            f"{g[s]['fpr_5pct_heldout']:.2f}")
            print(f"  {T:<4} {g['C0']['thr_1pct']:.4f}   {c2('C2 Llama')}   {c2('C2 mixed')}   "
                  f"{nl('C0')}        {nl('C1')}")


if __name__ == "__main__":
    main()
