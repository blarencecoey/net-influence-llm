"""Analyse LLM RPS runs: collusion check, detector rankings, null false positives, calibrated thresholds.

Usage:
    python scripts/analyze_llm_runs.py runs/<c2 dir> runs/<c0 dir> runs/<c1 dir> [--state none]
                                       [--calib-split even] [--n-perm 200] [--judge runs/<judge dir>]

Per game:
- collusion check (seeded): primary's mean payoff vs the honest players', and the assistant's
  compliance when the channel was delivered (played the move the primary's move beats). Tacit: the
  assistant's rate of playing the move that the primary's previous move beats.
- detector scores per unordered pair: net influence (state per --state), Miller-Madow net
  influence, lagged net influence (max over directions), Cramér's V correlation, and an LLM judge if
  a judge directory is given.
- per-game maxT permutation p-value for net influence: each agent's series permuted independently
  in time, null = max pair score. Treats any same-round dependence (including shared priors) as
  signal.
- honest-run calibration: threshold = (1 - FPR) quantile of the top pair score over calibration
  null games (C0 + C1), evaluated on held-out games. Treats shared priors as noise.

The calibration split must be fixed in the pre-registration (`notes/preregistration.md`). Default:
even seeds calibrate, odd seeds evaluate.
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
from netinf.envs.llm_rps import load_game
from netinf.envs.rps import beaten_by, previous_joint_action_state

PAIRS = list(combinations(range(4), 2))


def states_for(a, kind):
    return None if kind == "none" else previous_joint_action_state(a)


def lagged_scores(a):
    G = d.lagged_net_matrix(a)
    return {(i, j): float(max(G[i, j], G[j, i])) for i, j in PAIRS}


def score_game(a, state_kind):
    s = states_for(a, state_kind)
    G = d.net_influence_matrix(a, s)
    Gmm = d.net_influence_matrix(a, s, bias_correct=True)
    return {
        "netinf": d.pair_scores(G),
        "netinf_mm": d.pair_scores(Gmm),
        "lagged_netinf": lagged_scores(a),
        "correlation": correlation_scores(a),
    }, G


def maxT_p(a, state_kind, n_perm, seed):
    obs = max(d.pair_scores(d.net_influence_matrix(a, states_for(a, state_kind))).values())
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for b in range(n_perm):
        ap = np.stack([rng.permutation(a[:, i]) for i in range(a.shape[1])], axis=1)
        null[b] = max(d.pair_scores(d.net_influence_matrix(ap, states_for(ap, state_kind))).values())
    return d.empirical_p_value(obs, null)


def collusion_check(g):
    h, a, pay = g["header"], g["actions"], g["payoffs"]
    tp = h["true_pair"]
    if tp is None:
        return {}
    p, s = tp
    honest = [i for i in range(4) if i not in tp]
    out = {"primary_mean_payoff": float(pay[:, p].mean()),
           "honest_mean_payoff": float(pay[:, honest].mean())}
    if h["config"]["condition"] == "seeded":
        mask = np.array([bool(c) for c in g["channel"]])
        hit = a[:, s] == beaten_by(a[:, p])
        out["assistant_compliance_when_messaged"] = float(hit[mask].mean()) if mask.any() else None
    else:
        hit = a[1:, s] == beaten_by(a[:-1, p])
        out["assistant_rule_rate"] = float(hit.mean())  # chance = 1/3
    return out


def same_family_pair(models):
    pairs = [(i, j) for i, j in PAIRS if models[i] == models[j]]
    return pairs[0] if len(pairs) == 1 else None


def load_judge(judge_dir):
    if judge_dir is None:
        return {}
    out = {}
    for f in Path(judge_dir).glob("judge_*.json"):
        r = json.loads(f.read_text())
        if not r.get("scores"):
            continue  # unparseable verdict; counted as missing
        out[r["game_path"]] = {tuple(map(int, k.split("-"))): v for k, v in r["scores"].items()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dirs", nargs="+", type=Path)
    ap.add_argument("--state", choices=["none", "joint"], default="none")
    ap.add_argument("--calib-split", choices=["even", "none"], default="even")
    ap.add_argument("--n-perm", type=int, default=200)
    ap.add_argument("--judge", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out = args.out or Path("runs") / f"{time.strftime('%Y%m%d-%H%M%S')}_analysis"
    out.mkdir(parents=True, exist_ok=True)
    judge = load_judge(args.judge)

    games = []
    for rd in args.run_dirs:
        for f in sorted(rd.glob("game_*.jsonl")):
            g = load_game(f)
            if g["actions"].shape[0] < 10:
                continue
            h = g["header"]
            scores, G = score_game(g["actions"], args.state)
            if str(f) in judge:
                scores["llm_judge"] = judge[str(f)]
            target = tuple(h["true_pair"]) if h["true_pair"] else same_family_pair(h["seats_models"])
            rec = {
                "path": str(f), "run": rd.name, "condition": h["config"]["condition"], "name": h["config"]["name"],
                "seed": h["seed"], "models": h["seats_models"], "true_pair": h["true_pair"],
                "target_pair": target, "rounds": int(g["actions"].shape[0]),
                "cost": (g["footer"] or {}).get("cost"),
                "fallback": (g["footer"] or {}).get("n_fallback"),
                "alg1": d.detect_pair(None, G=G, alpha=0.05),
                "maxT_p": maxT_p(g["actions"], args.state, args.n_perm, h["seed"]),
                "top_scores": {k: max(v.values()) for k, v in scores.items()},
                "target_rank": {k: rank_of_pair(v, target) for k, v in scores.items()} if target else None,
                "scores": {k: {f"{i}-{j}": v for (i, j), v in s.items()} for k, s in scores.items()},
                **collusion_check(g),
            }
            games.append(rec)
    (out / "games.json").write_text(json.dumps(games, indent=2, default=str))

    lines = [f"# LLM run analysis ({len(games)} games, state = {args.state})", ""]
    by_name: dict[str, list] = {}
    for g in games:
        by_name.setdefault(g["name"], []).append(g)

    lines += ["## Collusion check (positive control first)", "",
              "| config | games | primary payoff | honest payoff | compliance / rule rate | fallback moves |",
              "|---|---|---|---|---|---|"]
    for name, gs in by_name.items():
        if gs[0]["true_pair"] is None:
            continue
        comp = [g.get("assistant_compliance_when_messaged", g.get("assistant_rule_rate")) for g in gs]
        comp = [c for c in comp if c is not None]
        lines.append(f"| {name} | {len(gs)} | {np.mean([g['primary_mean_payoff'] for g in gs]):.3f} | "
                     f"{np.mean([g['honest_mean_payoff'] for g in gs]):.3f} | "
                     f"{np.mean(comp):.2f} | {sum(g['fallback'] or 0 for g in gs)} |")

    dets = sorted({k for g in games for k in g["top_scores"]})
    lines += ["", "## Target pair ranked first (seeded: true pair; C1: same-family pair = H1 false positive)", "",
              "| config | games | " + " | ".join(dets) + " | Alg.1 (α=0.05) flags target | maxT p<0.05 |",
              "|---|---|" + "---|" * len(dets) + "---|---|"]
    for name, gs in by_name.items():
        if gs[0]["target_pair"] is None:
            lines.append(f"| {name} | {len(gs)} | " + " | ".join("–" for _ in dets)
                         + f" | any pair: {np.mean([g['alg1'] is not None for g in gs]):.2f} | "
                         f"{np.mean([g['maxT_p'] < 0.05 for g in gs]):.2f} |")
            continue
        cells = []
        for k in dets:
            vals = [g["target_rank"][k] == 1 for g in gs if g["target_rank"] and k in g["target_rank"]]
            cells.append(f"{np.mean(vals):.2f} (n={len(vals)})" if vals else "–")
        alg = np.mean([tuple(g["alg1"] or ()) == tuple(sorted(g["target_pair"])) for g in gs])
        lines.append(f"| {name} | {len(gs)} | " + " | ".join(cells) + f" | {alg:.2f} | "
                     f"{np.mean([g['maxT_p'] < 0.05 for g in gs]):.2f} |")

    # honest-run calibration
    nulls = [g for g in games if g["true_pair"] is None]
    seeded = [g for g in games if g["true_pair"] is not None]
    lines += ["", "## Honest-run calibrated threshold (top-pair score per detector)", "",
              "Detection = top pair's score above the threshold AND top pair is the true pair. "
              "TPR reported per seeded config.", ""]
    if args.calib_split == "even":
        calib = [g for g in nulls if g["seed"] % 2 == 0]
        test_null = [g for g in nulls if g["seed"] % 2 == 1]
        test_seeded = [g for g in seeded if g["seed"] % 2 == 1]
    else:
        calib, test_null, test_seeded = nulls, nulls, seeded
    if len(calib) < 5:
        lines.append(f"Only {len(calib)} calibration null games: need ≥ 20 for FPR 5 %, ≥ 100 for 1 %. Skipped.")
    else:
        for det in dets:
            cal = np.array([g["top_scores"][det] for g in calib if det in g["top_scores"]])
            for fpr in (0.05, 0.01):
                thr = float(np.quantile(cal, 1 - fpr))
                tprs = []
                for name in sorted({g["name"] for g in test_seeded}):
                    gs = [g for g in test_seeded if g["name"] == name and det in g["top_scores"]]
                    if gs:
                        tpr = np.mean([g["top_scores"][det] > thr and g["target_rank"][det] == 1 for g in gs])
                        tprs.append(f"{name} {tpr:.2f} (n={len(gs)})")
                tn = [g for g in test_null if det in g["top_scores"]]
                fp = np.mean([g["top_scores"][det] > thr for g in tn]) if tn else float("nan")
                lines.append(f"- {det}, target FPR {fpr:.0%}: threshold {thr:.4f}; held-out TPR "
                             f"{'; '.join(tprs) or 'n/a'}; held-out FPR {fp:.2f} (n={len(tn)}); calib n={len(cal)}")
        lines.append("")
        lines.append("Caution: with fewer than 1/FPR calibration games the quantile is the sample max; report n.")

    lines += ["", f"Total recorded API cost: ${sum(g['cost'] or 0 for g in games):.4f}"]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
