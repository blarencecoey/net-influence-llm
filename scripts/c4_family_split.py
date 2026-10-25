"""C4 (cross-family colluding pair) from the mixed C2 runs: split score_seeded output by whether
the seeded pair is same-family or cross-family. No new games.

Usage: python scripts/c4_family_split.py <score_seeded out_dir> <thresholds.json>
  e.g. notes/results/b21-mixed-c2/score_seeded notes/results/calib-c0-c1-100null/thresholds.json
Flags (max score > frozen threshold and top pair true) are shown for all seeds and for held-out seeds;
thresholds come from null runs only, so seeded runs on calibration seeds never entered the fit.
"""
import ast
import json
import sys
from pathlib import Path

import numpy as np

from netinf import analysis as an

OUT, TH = Path(sys.argv[1]), sys.argv[2]
th = an.load_thresholds(TH)
cal_seeds = set(th["calibration_seeds"])
SHOW = (("netinf", an.PRIMARY_STATE), ("netinf", "none"), ("lagged_netinf", "none"),
        ("correlation", "-"))
TAG = {"meta-llama": "L", "mistralai": "M"}


def lit(v):
    return ast.literal_eval(v) if isinstance(v, str) else v


units = json.loads((OUT / "per_unit.json").read_text(encoding="utf-8"))
rows = {}
for u in units:
    fam = lit(u["families"])
    i, j = (int(x) for x in u["true_pair"].split("-"))
    seed = lit(u["seeds"])[0]
    r = rows.setdefault(u["unit_id"], {"seed": seed, "pair": u["true_pair"],
                                       "fam": TAG[fam[i]] + TAG[fam[j]], "pc": u["pc_passed"]})
    scores = lit(u["scores"])
    other = max(v for k, v in scores.items() if k != u["true_pair"])
    t = th["detectors"].get(f"{u['detector']}|{u['state']}")
    r[(u["detector"], u["state"])] = {
        "rank": u["rank"], "true": u["true_score"], "margin": u["true_score"] - other,
        "alg1": u.get("alg1_correct"),
        "flag": {f: u["max_score"] > t[str(f)] and u["top_pair"] == u["true_pair"]
                 for f in th["fprs"]} if t else {}}
for r in rows.values():
    r["group"] = "same" if r["fam"][0] == r["fam"][1] else "cross"
    r["heldout"] = r["seed"] not in cal_seeds

print(f"input: {OUT}; thresholds: {TH} (calibration seeds {min(cal_seeds)}-{max(cal_seeds)})")
print("pair families: L = Llama 3.3 70B, M = Mistral Small 3.2; held out = seed outside calibration\n")
k0 = ("netinf", an.PRIMARY_STATE)
print(f"seed pair fam group  PC    held  netinf|{an.PRIMARY_STATE}: rank true  margin alg1 "
      "flag@1% flag@5%")
for r in sorted(rows.values(), key=lambda r: (r["group"], r["seed"])):
    x = r[k0]
    print(f"{r['seed']:>4} {r['pair']}  {r['fam']}  {r['group']:5}  {'PASS' if r['pc'] else 'FAIL'}  "
          f"{'yes' if r['heldout'] else 'no ':3}   {x['rank']}  {x['true']:.3f} {x['margin']:+.3f} "
          f"{str(x['alg1']):5} {str(x['flag'][0.01]):7} {x['flag'][0.05]}")

for group in ("same", "cross"):
    g = [r for r in rows.values() if r["group"] == group]
    h = [r for r in g if r["heldout"]]
    print(f"\n{group}-family colluding pair: n = {len(g)} (held out {len(h)}: seeds "
          f"{sorted(r['seed'] for r in h)}), families {sorted(r['fam'] for r in g)}, "
          f"PC pass {sum(r['pc'] for r in g)}/{len(g)}")
    for det, st in SHOW:
        xs = [r[(det, st)] for r in g]
        tr = np.array([x["true"] for x in xs])
        mg = np.array([x["margin"] for x in xs])
        line = (f"  {det + '|' + st:28} top-1 {sum(x['rank'] == 1 for x in xs)}/{len(xs)}  true score "
                f"{tr.mean():.3f} (sd {tr.std(ddof=1):.3f}, min {tr.min():.3f})  margin min "
                f"{mg.min():+.3f}")
        if xs[0]["alg1"] is not None:
            line += f"  alg1 {sum(bool(x['alg1']) for x in xs)}/{len(xs)}"
        for f in th["fprs"] if xs[0]["flag"] else ():
            line += (f"  flag@{f:.0%} all {sum(x['flag'][f] for x in xs)}/{len(xs)}, held out "
                     f"{sum(r[(det, st)]['flag'][f] for r in h)}/{len(h)}")
        print(line)
