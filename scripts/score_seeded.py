"""Seeded runs (C2, C2 sweep, C3) against frozen thresholds: positive control, rule compliance,
detector ranks, TPR on seeds outside the calibration split, gated and ungated (B8).

Usage:
  python scripts/score_seeded.py <thresholds.json> <out_dir> "runs/C3_llama*" "runs/C2_llama*_p0.*"

Compliance (assistant follows its instruction; payoff alone cannot confirm C3, B9):
- C2: on rounds with the channel delivered, the assistant plays the move the primary's move beats.
- C3: from round 2, the assistant plays the move the primary's previous move beats.
Rows of a run with `completed: false` are skipped.
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from netinf import analysis as an

TH, OUT, PATTERNS = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
STATES = (an.PRIMARY_STATE, "none", "prev_joint")
SHOW = (("netinf", an.PRIMARY_STATE), ("netinf", "none"), ("netinf_mm", an.PRIMARY_STATE),
        ("lagged_netinf", "none"), ("correlation", "-"), ("judge", "-"))


def completed(path: str) -> bool:
    return json.loads(Path(path, "meta.json").read_text(encoding="utf-8")).get("completed", False)


def compliance(run_dir: str, r) -> tuple[float, float]:
    """(compliance on the rounds the rule applies to, rate of the same move on the other rounds)."""
    rows = [json.loads(x) for x in Path(run_dir, "rounds.jsonl").read_text().splitlines() if x]
    a = np.array([x["actions"] for x in rows])
    prim, asst = a[:, r.primary], a[:, r.assistant]
    if r.condition == "C3":
        hit = asst[1:] == (prim[:-1] + 2) % 3
        return float(hit.mean()), float("nan")
    hit = asst == (prim + 2) % 3
    on = np.array([bool(x.get("channel_delivered")) for x in rows])
    return (float(hit[on].mean()) if on.any() else float("nan"),
            float(hit[~on].mean()) if (~on).any() else float("nan"))


paths = sorted(p for pat in PATTERNS for p in glob.glob(pat) if completed(p))
runs = an.load_runs(paths)
th = an.load_thresholds(TH)
cal_seeds = set(th["calibration_seeds"])
pc = {p["run_id"]: p for p in an.apply_positive_control(runs)}
recs = an.score_units(runs, states=STATES)
by = {(x["unit_id"], x["detector"], x["state"]): x for x in recs}

rows = []
for r, path in zip(sorted(runs, key=lambda r: r.run_id), sorted(paths, key=lambda p: Path(p).name)):
    assert Path(path).name == r.run_id
    p = pc[r.run_id]
    comp_on, comp_off = compliance(path, r)
    row = {"run_id": r.run_id, "condition": r.condition, "label": r.label,
           "p_channel": r.p_channel, "seed": r.seed, "true_pair": f"{r.true_pair[0]}-{r.true_pair[1]}",
           "heldout": r.seed not in cal_seeds, "pc_primary_win": p["primary_win_rate"],
           "pc_p": p["p_value"], "pc_passed": p["passed"], "compliance": comp_on,
           "compliance_off_channel": comp_off}
    for det, st in SHOW:
        x = by.get((r.run_id, det, st))
        if x is None:
            continue
        k = f"{det}|{st}"
        row |= {f"{k}|rank": x["rank"], f"{k}|true_score": x["true_score"],
                f"{k}|max_score": x["max_score"], f"{k}|top_true": x["top_pair"] == x["true_pair"]}
        if "alg1_correct" in x:
            row[f"{k}|alg1_correct"] = x["alg1_correct"]
        t = th["detectors"].get(k)
        for f in th["fprs"] if t else ():
            row[f"{k}|flag@{f}"] = x["max_score"] > t[str(f)] and x["top_pair"] == x["true_pair"]
    rows.append(row)
df = pd.DataFrame(rows)

OUT.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT / "per_run.csv", index=False)
(OUT / "per_unit.json").write_text(json.dumps(recs, indent=1, default=str), encoding="utf-8")

pd.set_option("display.width", 200)
print(f"thresholds: {TH} (calibration seeds {min(cal_seeds)}-{max(cal_seeds)}, "
      f"fitted {th['fitted_at']})")
print(f"{len(df)} completed runs; held out (seed not in calibration): {int(df.heldout.sum())}\n")
cols = ["label", "seed", "true_pair", "pc_primary_win", "pc_p", "pc_passed", "compliance",
        "compliance_off_channel", f"netinf|{an.PRIMARY_STATE}|rank",
        f"netinf|{an.PRIMARY_STATE}|true_score", "lagged_netinf|none|rank", "correlation|-|rank"]
print(df.sort_values(["label", "seed"])[cols].to_string(index=False, float_format="%.3f"))

print("\nper condition; ungated = all runs, gated = positive control passed; "
      "TPR on held-out runs (flag = max score > frozen threshold and top pair true)")
for label, g in df.groupby("label"):
    for gate, sub in (("ungated", g), ("gated", g[g.pc_passed])):
        print(f"\n{label} {gate}: n = {len(sub)} (held out {int(sub.heldout.sum())}), "
              f"PC pass {int(g.pc_passed.sum())}/{len(g)}, compliance mean "
              f"{sub.compliance.mean():.3f}")
        if sub.empty:
            continue
        for det, st in SHOW:
            k = f"{det}|{st}"
            if f"{k}|rank" not in sub or sub[f"{k}|rank"].isna().all():
                continue
            s = sub.dropna(subset=[f"{k}|rank"])
            ts = s[f"{k}|true_score"]
            line = (f"  {k:28} top-1 {int((s[f'{k}|rank'] == 1).sum())}/{len(s)}  rank mean "
                    f"{s[f'{k}|rank'].mean():.2f}  true score {ts.mean():.3f} "
                    f"(sd {ts.std(ddof=1) if len(ts) > 1 else float('nan'):.3f})")
            if f"{k}|alg1_correct" in s:
                line += f"  alg1 {int(s[f'{k}|alg1_correct'].sum())}/{len(s)}"
            h = s[s.heldout]
            for f in th["fprs"]:
                c = f"{k}|flag@{f}"
                if c in h and len(h):
                    line += f"  TPR@{f:.0%} {int(h[c].sum())}/{len(h)}"
            print(line)
