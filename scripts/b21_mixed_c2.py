"""B21: mixed-family C2 positive control and detection per seed; TPR under frozen thresholds (argv[1]) on seeds outside their calibration split."""
import glob
import json
import sys

from netinf import analysis as an

TH = sys.argv[1]
runs = an.load_runs(sorted(glob.glob(
    "runs/C2_llama-3.3-70b-instruct+mistral-small-3.2-24b-instruct_p1.0_s*_20261024-*")))
runs = [r for r in runs if json.load(open(f"runs/{r.run_id}/meta.json")).get("completed")]
th = an.load_thresholds(TH)
cal_seeds = set(th["calibration_seeds"])

pc = {p["run_id"]: p for p in an.apply_positive_control(runs)}
recs = an.score_units(runs, states=(an.PRIMARY_STATE, "none", "prev_joint"))
fam = {r.run_id: r.families for r in runs}

print("seed pair families  PC(primary vs chance, p)  netinf rank/score  corr rank  lagged rank"
      "  judge rank  calib?")
for r in sorted(runs, key=lambda r: r.seed):
    p = pc[r.run_id]
    i, j = r.true_pair
    tag = lambda k: "L" if "llama" in r.models[k] else "M" if "mistral" in r.models[k] else "?"
    f = f"{tag(r.primary)}->{tag(r.assistant)}"
    get = {(x["detector"], x["state"]): x for x in recs if x["unit_id"] == r.run_id}
    n = get[("netinf", an.PRIMARY_STATE)]
    c = get[("correlation", "-")]
    lg = get[("lagged_netinf", "none")]
    jd = get.get(("judge", "-"))
    print(f"s{r.seed:<3} ({i},{j}) {f:6} {p['primary_mean']:.3f} vs {p['chance_win_rate']:.3f} "
          f"p={p['p_value']:.1g} {'PASS' if p['passed'] else 'FAIL'}  "
          f"rank {n['rank']} true {n['true_score']:.3f} max-other "
          f"{max(v for k, v in n['scores'].items() if k != n['true_pair']):.3f} "
          f"alg1 {n['alg1_correct']}  corr {c['rank']}  lag {lg['rank']}  "
          f"judge {jd['rank'] if jd else '-'}  {'CALIB-SEED' if r.seed in cal_seeds else 'heldout'}")
    print(f"      families {r.families}  other states: none rank "
          f"{get[('netinf', 'none')]['rank']}, prev_joint rank {get[('netinf', 'prev_joint')]['rank']}")

held = [x for x in recs if not set(x["seeds"]) & cal_seeds]
print(f"\nheld-out units: {sorted({x['unit_id'] for x in held})}")
for row in an.evaluate(held, th):
    print(row)
