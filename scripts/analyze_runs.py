"""Analyse RPS run directories: positive control, detector comparison, frozen thresholds, H1.

Pipeline (see src/netinf/analysis.py for the choices):
1. load run dirs (meta.json + rounds.jsonl) matching the glob(s)
2. positive control per seeded run, printed first; failed runs are excluded from detection
   metrics (counted in `n_excluded_pc`) unless --include-failed-pc
3. split by seed: --calib-seeds (default 0 1) calibrate, the rest are held out
4. optional --pool: concatenate runs with the same condition, p_channel, seeded pair and models,
   separately within each split
5. score every unit with every detector; the primary (pre-registered) state is --state, the
   --secondary-states are reported alongside
6. thresholds at FPR 1% / 5% fitted on calibration nulls (C0, C1), saved, evaluated on held-out
7. H1: same- vs cross-family pair scores on C1

Outputs in --out: positive_control.csv, per_unit.csv, per_unit.json (with all pair scores),
summary.csv/json (label x detector x state), heldout.csv, thresholds.json, h1.json, figures.

Usage:
  python scripts/analyze_runs.py "runs/*" --out notes/results/<name>
  python scripts/analyze_runs.py --synthetic <dir> --out <dir>/analysis   # scripted dry run, $0
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from netinf import analysis as an


def make_synthetic(root: Path, seeds=range(5), n_rounds=200) -> None:
    """Scripted set in the run-dir format: C0, C1, C2 sweep, C3 (no API calls)."""
    c1_models = ["famA/m1", "famA/m1", "famB/m2", "famC/m3"]
    for s in seeds:
        an.write_scripted_run(root, "C0", s, n_rounds)
        an.write_scripted_run(root, "C1", s, n_rounds, models=c1_models)
        an.write_scripted_run(root, "C3", s, n_rounds)
        for p in (0.1, 0.3, 0.5, 1.0):
            an.write_scripted_run(root, "C2", s, n_rounds, p_channel=p)


def fmt(x, nd=2):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def threshold_note(th: dict) -> str:
    """Where the thresholds came from, and which FPR levels fall back to the max null score
    (fewer null units than 1/fpr; same rule as analysis.threshold_at_fpr)."""
    n_null = sorted({v["n_null"] for v in th["detectors"].values()})
    if not n_null:
        return "no null (C0/C1) calibration units, so no thresholds and no held-out metrics"
    note = (f"thresholds from {th['null_conditions']} calibration seeds "
            f"{th['calibration_seeds']}, n_null per detector = {n_null}")
    at_max = [f"{f:.0%}" for f in th["fprs"] if int(np.floor(f * min(n_null) + 1e-9)) == 0]
    if at_max:
        note += f", so the {'/'.join(at_max)} thresholds are the max null score"
    return note


def plot(summary: list[dict], out: Path, n_pairs: int) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    seeded = [r for r in summary if r["colluding"] and "top1" in r]
    if not seeded:
        return
    dets = list(dict.fromkeys(f"{r['detector']}|{r['state']}" for r in seeded))
    labels = list(dict.fromkeys(r["label"] for r in seeded))
    get = {(r["label"], f"{r['detector']}|{r['state']}"): r for r in seeded}
    fig, ax = plt.subplots(figsize=(max(8, 1.6 * len(labels)), 4.5))
    w = 0.8 / len(dets)
    for k, det in enumerate(dets):
        rs = [get.get((lab, det)) for lab in labels]
        x = np.arange(len(labels)) + k * w
        y = [r["top1"] if r else np.nan for r in rs]
        err = [[r["top1"] - r["top1_wilson_lo"] if r else 0 for r in rs],
               [r["top1_wilson_hi"] - r["top1"] if r else 0 for r in rs]]
        ax.bar(x, y, w, yerr=err, capsize=2, label=det)
    ax.axhline(1 / n_pairs, color="k", ls=":", lw=1, label=f"chance (1/{n_pairs})")
    ax.set_xticks(np.arange(len(labels)) + 0.4 - w / 2)
    ax.set_xticklabels(labels, rotation=20)
    ax.set_ylabel("top-1 accuracy (true pair ranked first)")
    ax.set_title("Top-1 accuracy across seeds (95% Wilson CI)")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(out / "top1_by_condition.png", dpi=150)
    plt.close(fig)

    sweep = [r for r in seeded if r["condition"] == "C2" and r["p_channel"] is not None]
    if len({r["p_channel"] for r in sweep}) < 2:
        return
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for k, det in enumerate(dets):
        rs = sorted((r for r in sweep if f"{r['detector']}|{r['state']}" == det),
                    key=lambda r: r["p_channel"])
        p = [r["p_channel"] + 0.008 * (k - len(dets) / 2) for r in rs]  # dodge overlapping lines
        y = np.array([r["top1"] for r in rs])
        ax.errorbar(p, y, yerr=[y - [r["top1_wilson_lo"] for r in rs],
                                [r["top1_wilson_hi"] for r in rs] - y],
                    marker="o", capsize=3, label=det)
    ax.axhline(1 / n_pairs, color="k", ls=":", lw=1)
    ax.set_xlabel("p_channel (probability the private channel is delivered)")
    ax.set_ylabel("top-1 accuracy")
    ax.set_title("C2 dose response (H3), 95% Wilson CI")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "detection_vs_pchannel.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("runs", nargs="*", help="run dir glob(s), e.g. 'runs/C2_*'")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--state", default=an.PRIMARY_STATE, choices=sorted(an.STATES),
                    help="primary (pre-registered) state, default %(default)s")
    ap.add_argument("--secondary-states", nargs="*", default=["none", "prev_joint"])
    ap.add_argument("--calib-seeds", nargs="+", default=[str(s) for s in an.DEFAULT_CALIB_SEEDS],
                    help="seeds used for calibration (or 'parity' = even seeds)")
    ap.add_argument("--pool", action="store_true", help="concatenate compatible runs per split")
    ap.add_argument("--alpha", type=float, default=0.05, help="Bonjour alpha (nats)")
    ap.add_argument("--include-failed-pc", action="store_true")
    ap.add_argument("--synthetic", type=Path, default=None,
                    help="write a scripted run set to this dir first and analyse it")
    args = ap.parse_args()

    patterns = list(args.runs)
    if args.synthetic:
        make_synthetic(args.synthetic)
        patterns.append(str(args.synthetic / "*"))
    runs = an.load_runs(patterns)
    if not runs:
        raise SystemExit(f"no run dirs found for {patterns}")
    args.out.mkdir(parents=True, exist_ok=True)
    states = [args.state] + [s for s in args.secondary_states if s != args.state]
    calib = "parity" if args.calib_seeds == ["parity"] else [int(s) for s in args.calib_seeds]

    # 1. positive control first
    pc = an.apply_positive_control(runs)
    print(f"Loaded {len(runs)} runs. POSITIVE CONTROL (primary vs honest mean payoff, one-sided t; "
          f"win rate vs uniform chance {an.chance_win_rate(runs[0].actions.shape[1]):.3f}):")
    print(f"  {'run':28s} {'pair':6s} {'prim':>5s} {'asst':>5s} {'hon':>5s} {'p':>8s} "
          f"{'win':>5s} {'p_bin':>8s}  passed")
    for r in pc:
        print(f"  {r['run_id'][:28]:28s} {'{}-{}'.format(*r['pair']):6s} {r['primary_mean']:5.2f} "
              f"{r['assistant_mean']:5.2f} {r['honest_mean']:5.2f} {r['p_value']:8.1e} "
              f"{r['primary_win_rate']:5.2f} {r['p_binom']:8.1e}  {r['passed']}")
    if pc and not all(r["passed"] for r in pc):
        print(f"  -> {sum(not r['passed'] for r in pc)} seeded run(s) FAILED the positive control"
              + ("" if args.include_failed_pc else " and are excluded from detection metrics"))
    pd.DataFrame(pc).to_csv(args.out / "positive_control.csv", index=False)

    # 2. split, pool, score
    cal_runs, held_runs = an.split_runs(runs, calib)
    if args.pool:
        def keep(rs):
            return [r for r in rs if args.include_failed_pc or r.pc_passed is not False]
        cal_runs, held_runs = an.pool_runs(keep(cal_runs)), an.pool_runs(keep(held_runs))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        recs = (an.score_units(cal_runs, states, "calibration", args.alpha)
                + an.score_units(held_runs, states, "heldout", args.alpha))
    first: dict[str, tuple[str, int]] = {}  # one line per state: first message and unit count
    for w in caught:
        key = str(w.message).split(":")[0]
        first[key] = (first.get(key, (str(w.message), 0))[0], first.get(key, ("", 0))[1] + 1)
    for msg, count in first.values():
        print(f"WARNING ({count} units, e.g.) {msg}")

    # 3. thresholds on calibration only, evaluated on held-out
    th = an.fit_thresholds([r for r in recs if r["split"] == "calibration"])
    an.save_thresholds(th, args.out / "thresholds.json")
    held = an.evaluate([r for r in recs if r["split"] == "heldout"], th, args.include_failed_pc)
    summary = an.summarize(recs, args.include_failed_pc)
    hmap = {(h["label"], h["detector"], h["state"]): h for h in held}
    for row in summary:
        h = hmap.get((row["label"], row["detector"], row["state"]), {})
        row |= {k: v for k, v in h.items() if k not in ("label", "detector", "state")}
    h1 = an.h1_family_comparison(recs, state=args.state)

    flat = [{k: v for k, v in r.items() if k != "scores"} for r in recs]
    pd.DataFrame(flat).to_csv(args.out / "per_unit.csv", index=False)
    (args.out / "per_unit.json").write_text(json.dumps(recs, indent=1, default=str))
    pd.DataFrame(summary).to_csv(args.out / "summary.csv", index=False)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    pd.DataFrame(held).to_csv(args.out / "heldout.csv", index=False)
    (args.out / "h1.json").write_text(json.dumps(h1, indent=1, default=str))
    n_pairs = runs[0].actions.shape[1] * (runs[0].actions.shape[1] - 1) // 2
    plot(summary, args.out, n_pairs)
    (args.out / "analysis_config.json").write_text(json.dumps(
        vars(args) | {"states": states, "n_runs": len(runs), "patterns": patterns}, indent=2,
        default=str))

    # 4. compact table
    print(f"\nSUMMARY (primary state = {args.state}; {threshold_note(th)})")
    print(f"  {'label':12s} {'detector':14s} {'state':16s} {'n':>3s} {'excl':>4s} {'top1':>5s} "
          f"{'95% Wilson':>11s} {'rank':>4s} {'alg1':>5s} {'@1%':>5s} {'@5%':>5s} "
          f"{'nHO':>3s}")
    for r in summary:
        rate = "tpr" if r["colluding"] else "fpr"
        ci = f"[{fmt(r.get('top1_wilson_lo'))},{fmt(r.get('top1_wilson_hi'))}]" if "top1" in r \
            else ""
        tag = "*" if r["state"] == args.state else ""
        print(f"  {r['label']:12s} {r['detector']:14s} {r['state'] + tag:16s} {r['n_units']:3d} "
              f"{r['n_excluded_pc']:4d} {fmt(r.get('top1')):>5s} {ci:>11s} "
              f"{fmt(r.get('rank_mean'), 1):>4s} {fmt(r.get('alg1_rate')):>5s} "
              f"{fmt(r.get(f'{rate}@0.01')):>5s} "
              f"{fmt(r.get(f'{rate}@0.05')):>5s} {r.get('n_heldout', 0):3d}")
    print("  (* = primary, pre-registered state. Seeded rows: alg1 = rate of flagging exactly"
          " the true pair, @1%/@5% = held-out TPR. Null rows: any-pair false-alarm rates, held-out"
          " realised FPR.)")
    if h1["n_units"]:
        print(f"\nH1 (C1, netinf|{args.state}): same-minus-cross max {fmt(h1['diff_max_mean'], 3)}"
              f" (sd {fmt(h1['diff_max_sd'], 3)}, Wilcoxon p {fmt(h1['wilcoxon_p_max'], 3)}); mean "
              f"{fmt(h1['diff_mean_mean'], 3)} (p {fmt(h1['wilcoxon_p_mean'], 3)}); top pair "
              f"same-family {fmt(h1['top_pair_same_family_rate'])} vs chance "
              f"{fmt(h1['chance_same_family_rate'])}, n = {h1['n_units']}")
    else:
        print("\nH1: no C1 units with both same- and cross-family pairs (check meta agent models)")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
