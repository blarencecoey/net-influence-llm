"""H1 under each detector state, from a saved analysis (analyze_runs.py --out <dir>): per null
condition, Algorithm 1 false-alarm rate, how often the top pair is a same-model pair, median max
score, held-out FPR at the frozen thresholds, and C1 same- minus cross-family max score.

Usage: python scripts/h1_by_state.py notes/results/calib-c0-c1-100null
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("analysis_dir")
    args = ap.parse_args()
    root = Path(args.analysis_dir)
    units = json.loads((root / "per_unit.json").read_text(encoding="utf-8"))
    th = json.loads((root / "thresholds.json").read_text(encoding="utf-8"))
    cal = set(th["calibration_seeds"])

    by = defaultdict(list)
    for u in units:
        if not u["colluding"] and u["detector"] in ("netinf", "netinf_mm"):
            by[(u["detector"], u["state"], u["condition"])].append(u)

    print(f"thresholds fitted on seeds {min(cal)}-{max(cal)} ({len(cal)} seeds), "
          f"null conditions {th['null_conditions']}")
    print("detector   state            cond   n  alg1_any  top_same_family  median_max  "
          "thr@1%   thr@5%   heldout_fpr@1%  @5%")
    for (det, st, cond), us in sorted(by.items()):
        fam = lambda u, p: tuple(u["families"][int(k)] for k in p.split("-"))
        same = [len(set(fam(u, u["top_pair"]))) == 1 for u in us]
        t = th["detectors"].get(f"{det}|{st}", {})
        held = [u for u in us if not set(u["seeds"]) & cal]
        fpr = {f: np.mean([u["max_score"] > t[f] for u in held]) if held and f in t else np.nan
               for f in ("0.01", "0.05")}
        print(f"{det:10} {st:16} {cond:4} {len(us):3}  "
              f"{np.mean([bool(u.get('alg1_any')) for u in us]):.2f}      "
              f"{np.mean(same):.2f}             {np.median([u['max_score'] for u in us]):.4f}   "
              f"{t.get('0.01', np.nan):.4f}  {t.get('0.05', np.nan):.4f}  "
              f"{fpr['0.01']:.2f} (n={len(held)})      {fpr['0.05']:.2f}")

    print("\nC1: max same-family pair score minus max cross-family pair score, per run")
    for (det, st, cond), us in sorted(by.items()):
        if cond != "C1":
            continue
        diffs = []
        for u in us:
            s, c = [], []
            for p, v in u["scores"].items():
                f = {u["families"][int(k)] for k in p.split("-")}
                (s if len(f) == 1 else c).append(v)
            diffs.append(max(s) - max(c))
        diffs = np.array(diffs)
        print(f"  {det:10} {st:16} mean {diffs.mean():+.4f} (sd {diffs.std(ddof=1):.4f}), "
              f"positive in {np.mean(diffs > 0):.2f} of {len(diffs)}, "
              f"Wilcoxon p = {wilcoxon(diffs).pvalue:.1e}")


if __name__ == "__main__":
    main()
