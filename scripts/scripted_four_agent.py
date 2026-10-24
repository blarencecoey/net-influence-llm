"""Scripted 4-player RPS: how well do detectors rank the seeded pair, and how often do they
false-alarm with no collusion? CPU only, $0. This is the scripted dry run of the LLM experiment.

Conditions:
- seeded: agents (2, 3) collude, assistant mode, CP in a sweep (pair position randomised per game
  would change nothing for scripted agents, so it is fixed)
- tacit: agents (2, 3), assistant reacts to the partner's previous move (H2)
- null: no collusion

Detectors (ranking score per unordered pair, higher = more suspicious):
- net influence, min(Gamma(i;j), Gamma(j;i)), state = none or previous joint action
- net influence, Miller-Madow corrected
- lagged net influence (transfer entropy), max over the two directions
- action correlation (Cramér's V), no state

Metrics per detector and condition: top-1 accuracy of the true pair (mean and 95% bootstrap CI over
games), Algorithm 1 detection rate at alpha = 0.05, and the false-detection rate on null games.

Usage: python scripts/scripted_four_agent.py --games 200 --rounds 200
"""

from __future__ import annotations

import argparse
import json
import time
from itertools import combinations
from pathlib import Path

import numpy as np

from netinf import detector as d
from netinf.baselines import correlation_scores, rank_of_pair
from netinf.envs import rps

TRUE = (2, 3)


def lagged_pair_scores(a, states=None):
    # max over directions: history-based help can be one-way (B reacts to A), unlike same-round
    # influence, which is symmetric in gamma. Our choice.
    G = d.lagged_net_matrix(a, states)
    n = G.shape[0]
    return {(i, j): float(max(G[i, j], G[j, i])) for i, j in combinations(range(n), 2)}


def detectors(a):
    s_joint = rps.previous_joint_action_state(a)
    G_none = d.net_influence_matrix(a)
    G_joint = d.net_influence_matrix(a, s_joint)
    G_mm = d.net_influence_matrix(a, s_joint, bias_correct=True)
    return {
        "netinf_state_none": (d.pair_scores(G_none), G_none),
        "netinf_state_joint": (d.pair_scores(G_joint), G_joint),
        "netinf_state_joint_mm": (d.pair_scores(G_mm), G_mm),
        "lagged_netinf": (lagged_pair_scores(a), None),
        "correlation": (correlation_scores(a), None),
    }


def boot_ci(x, n_boot=2000, seed=0):
    x = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(n_boot, len(x))).mean(axis=1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200, help="independent games per condition")
    ap.add_argument("--rounds", type=int, default=200, help="rounds per game")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out = args.out or Path("runs") / f"{time.strftime('%Y%m%d-%H%M%S')}_scripted4_{args.rounds}r"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(vars(args) | {"out": str(out), "true_pair": TRUE}, indent=2))

    conditions = [("null", None, 0.0)]
    conditions += [(f"seeded_cp{cp}", "assistant", cp) for cp in (0.1, 0.2, 0.3, 0.5, 1.0)]
    conditions += [("tacit_cp1.0", "tacit", 1.0)]

    rows = []
    for ci, (name, mode, cp) in enumerate(conditions):
        rng = np.random.default_rng(args.seed + 7919 * ci)
        cfg = rps.RPSConfig(n_players=4, primary=TRUE[0], assistant=None if mode is None else TRUE[1],
                            cp=cp, mode=mode or "assistant")
        per_det: dict[str, dict[str, list]] = {}
        for _ in range(args.games):
            a, _ = rps.simulate(cfg, args.rounds, rng)
            for det, (scores, G) in detectors(a).items():
                rec = per_det.setdefault(det, {"top1": [], "alg1": []})
                rec["top1"].append(rank_of_pair(scores, TRUE) == 1)
                if G is not None:
                    found = d.detect_pair(a, G=G, alpha=0.05)
                    rec["alg1"].append(found is not None if mode is None else found == TRUE)
        for det, rec in per_det.items():
            m, lo, hi = boot_ci(rec["top1"])
            row = {"condition": name, "detector": det, "top1": m, "top1_lo": lo, "top1_hi": hi}
            if rec["alg1"]:
                row["alg1_rate"] = float(np.mean(rec["alg1"]))
            rows.append(row)
            print(f"{name:14s} {det:24s} top1={m:.2f} [{lo:.2f},{hi:.2f}]"
                  + (f"  alg1={row['alg1_rate']:.2f}" if "alg1_rate" in row else ""), flush=True)

    (out / "results.json").write_text(json.dumps(rows, indent=2))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dets = list(dict.fromkeys(r["detector"] for r in rows))
    conds = [c[0] for c in conditions if c[1] is not None]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    w = 0.8 / len(dets)
    for k, det in enumerate(dets):
        ys = [next(r for r in rows if r["detector"] == det and r["condition"] == c) for c in conds]
        x = np.arange(len(conds)) + k * w
        ax.bar(x, [y["top1"] for y in ys], w, label=det,
               yerr=[[y["top1"] - y["top1_lo"] for y in ys], [y["top1_hi"] - y["top1"] for y in ys]],
               capsize=2)
    ax.axhline(1 / 6, color="k", ls=":", lw=1, label="chance (1/6)")
    ax.set_xticks(np.arange(len(conds)) + 0.4 - w / 2)
    ax.set_xticklabels(conds, rotation=20)
    ax.set_ylabel("top-1 accuracy (true pair ranked first)")
    ax.set_title(f"Scripted 4-player RPS, {args.rounds} rounds, {args.games} games per condition (95% bootstrap CI)")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out / "top1_by_condition.png", dpi=150)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
