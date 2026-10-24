"""Check the circular-shift null for net-influence pair scores (limitation B18).

1. Per pair of the two flagged LLM runs: observed Gamma(i;j), Gamma(j;i) and min score vs. their
   shift-null medians.
2. Per-pair rejection rates on synthetic no-collusion data, 4 agents, where each agent copies a
   common latent move with probability `strength` (exchangeable shared prior). The latent is iid
   per round ("same-round") or cycles to the next move w.p. 0.8 ("cyclic", history-carried).

The shift test was removed from netinf.analysis because of these results; this script keeps the
evidence reproducible. Run from the repo root: python scripts/check_shift_null.py
"""

from __future__ import annotations

import warnings
from itertools import combinations

import numpy as np

from netinf import analysis as an
from netinf import detector as d

warnings.simplefilter("ignore")
FLAGGED = ["runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-114420",
           "runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-120724"]


def shift_pvalues(a, score, n_shifts, seed=0):
    """Shift j's series, recompute the pair score; one-sided, +1 corrected p per pair (i < j)."""
    obs = score(a)
    return {(i, j): d.empirical_p_value(v, d.circular_shift_null(
                a, i, j, statistic=lambda x, i, j: score(x)[(i, j)], n_shifts=n_shifts, seed=seed))
            for (i, j), v in obs.items()}


def netinf_score(state, segments=None):
    return lambda x: an.netinf_pair_scores(x, state, segments)


def decompose(run, state, i, j, n_shifts=200, seed=0):
    """Observed and shift-null (Gamma(i;j), Gamma(j;i), min) for one pair."""
    def parts(x):
        G = d.net_influence_matrix(x, an.compute_states(x, state, run.segments, warn=False))
        return G[i, j], G[j, i], min(G[i, j], G[j, i])
    a = run.actions
    ks = np.random.default_rng(seed).integers(1, len(a), size=n_shifts)
    null = []
    for k in ks:
        x = a.copy()
        x[:, j] = np.roll(a[:, j], k)
        null.append(parts(x))
    return np.array(parts(a)), np.array(null)


def report_run(path, state="prev_n_distinct"):
    r = an.load_run(path)
    print(f"\n== {r.run_id}  true pair {r.true_pair}  T={len(r.actions)}  state {state}")
    g = d.influence_matrix(r.actions, an.compute_states(r.actions, state, r.segments, warn=False))
    print("gamma matrix:\n", np.round(g, 3))
    for i, j in combinations(range(r.actions.shape[1]), 2):
        obs, null = decompose(r, state, i, j)
        p = d.empirical_p_value(obs[2], null[:, 2])
        print(f"  ({i},{j}) obs G(i;j)={obs[0]:+.3f} G(j;i)={obs[1]:+.3f} score={obs[2]:+.3f} | "
              f"null median G(i;j)={np.median(null[:, 0]):+.3f} "
              f"G(j;i)={np.median(null[:, 1]):+.3f} score med={np.median(null[:, 2]):+.3f} "
              f"max={null[:, 2].max():+.3f} | p={p:.3f}")


def shared_prior(T, rng, strength, cyclic=False, stick=0.8):
    if cyclic:
        lat = np.empty(T, dtype=np.int64)
        lat[0] = rng.integers(3)
        for t in range(1, T):
            lat[t] = (lat[t - 1] + 1) % 3 if rng.random() < stick else rng.integers(3)
    else:
        lat = rng.integers(0, 3, size=T)
    a = rng.integers(0, 3, size=(T, 4))
    follow = rng.random((T, 4)) < strength
    a[follow] = np.repeat(lat[:, None], 4, axis=1)[follow]
    return a


def calibration(name, score, strengths, cyclic, n_runs, T=200, n_shifts=99):
    print(f"\n{name}, {'cyclic' if cyclic else 'same-round'} prior, {n_runs} runs x 6 pairs, "
          f"{n_shifts} shifts (nominal: 0.05, 0.01):")
    for st in strengths:
        rng = np.random.default_rng(1)
        ps = np.array([p for _ in range(n_runs)
                       for p in shift_pvalues(shared_prior(T, rng, st, cyclic), score,
                                              n_shifts).values()])
        print(f"  strength={st:.1f}: P(p<=0.05)={np.mean(ps <= 0.05):.2f} "
              f"P(p<=0.01)={np.mean(ps <= 0.01):.2f}")


if __name__ == "__main__":
    for p in FLAGGED:
        report_run(p)
    calibration("netinf|none", netinf_score("none"), (0.0, 0.2, 0.4), cyclic=False, n_runs=40)
    for cyc in (False, True):
        calibration("lagged_netinf", an.lagged_pair_scores, (0.0, 0.4, 0.7), cyclic=cyc, n_runs=30)
