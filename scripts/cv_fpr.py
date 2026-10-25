"""Cross-validated false-positive rate of the honest-run thresholds over all 110 C0 + C1 runs ($0).

Usage: python scripts/cv_fpr.py notes/results/calib-c0-c1-100null/per_unit.csv [--repeats 100]

The frozen thresholds are evaluated on 5 held-out runs per null condition (limitation B20). Here
every null run is held out once: 5 folds by seed (fold = seed % 5, so C0 and C1 runs with the same
seed share a fold), thresholds fitted on the other 4 folds with analysis.threshold_at_fpr (the same
rule as the frozen thresholds), alarm = max pair score > threshold. --repeats random seed
partitions into 5 folds give the spread. Algorithm 1 at alpha = 0.05 needs no fit; its any-pair
rate on the same runs is shown for netinf.
Scores come from the saved per_unit.csv, so nothing is re-scored.
"""
import argparse

import numpy as np
import pandas as pd

from netinf import analysis as an

ap = argparse.ArgumentParser()
ap.add_argument("per_unit")
ap.add_argument("--repeats", type=int, default=100)
args = ap.parse_args()

pu = pd.read_csv(args.per_unit)
null = pu[pu.condition.isin(["C0", "C1"]) & (pu.detector != "judge")].copy()
null["seed"] = null.seeds.str.strip("[]").astype(int)
FPRS = (0.01, 0.05)


def cv(g: pd.DataFrame, fold_of: dict[int, int]) -> pd.DataFrame:
    """One row per null run: alarm at each FPR with thresholds fitted without its fold."""
    out = []
    folds = g.seed.map(fold_of)
    for k in sorted(set(fold_of.values())):
        train, test = g[folds != k], g[folds == k]
        for f in FPRS:
            thr = an.threshold_at_fpr(train.max_score.to_numpy(), f)
            out.append(test.assign(fpr=f, thr=thr, alarm=test.max_score > thr))
    return pd.concat(out)


seeds = sorted(null.seed.unique())
print(f"{len(null[(null.detector == 'netinf') & (null.state == an.PRIMARY_STATE)])} null runs "
      f"(C0 + C1, seeds {seeds[0]}-{seeds[-1]}); 5 folds by seed % 5, training n = 88 per fold")
print("threshold rule: analysis.threshold_at_fpr; at 1 % with 88 training nulls it is the "
      "training maximum\n")
print(f"{'detector|state':26} {'CV FPR @1%':>12} {'@5%':>8}   C0 @1/@5     C1 @1/@5     "
      f"thr @1% range     random partitions @1% / @5% mean [min, max]   Alg.1 any")
rng = np.random.default_rng(0)
for (det, st), g in null.groupby(["detector", "state"]):
    r = cv(g, {s: s % 5 for s in seeds})
    rate = lambda d, f: d[d.fpr == f].alarm.mean()
    by = {c: (rate(r[r.condition == c], 0.01), rate(r[r.condition == c], 0.05)) for c in ("C0", "C1")}
    thr = r[r.fpr == 0.01].thr
    reps = []
    for _ in range(args.repeats):
        perm = rng.permutation(seeds)
        rr = cv(g, {s: i % 5 for i, s in enumerate(perm)})
        reps.append((rate(rr, 0.01), rate(rr, 0.05)))
    reps = np.array(reps)
    alg1 = (f"{g.alg1_any.astype(float).mean():.2f}" if det.startswith("netinf")
            and g.alg1_any.notna().all() else "-")
    print(f"{det + '|' + st:26} {rate(r, 0.01):12.3f} {rate(r, 0.05):8.3f}   "
          f"{by['C0'][0]:.2f}/{by['C0'][1]:.2f}    {by['C1'][0]:.2f}/{by['C1'][1]:.2f}    "
          f"{thr.min():.4f}-{thr.max():.4f}    "
          f"{reps[:, 0].mean():.3f} [{reps[:, 0].min():.3f}, {reps[:, 0].max():.3f}] / "
          f"{reps[:, 1].mean():.3f} [{reps[:, 1].min():.3f}, {reps[:, 1].max():.3f}]     {alg1}")
