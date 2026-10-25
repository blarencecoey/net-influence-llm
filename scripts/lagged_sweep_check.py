"""Why lagged net influence ranks the C2 pair first at p = 0.3 / 0.5 but not at p = 1.0 ($0).

Usage: python scripts/lagged_sweep_check.py [--games 200]

Hypothesis (ours): on delivered rounds the assistant plays beaten_by(P_t). If the primary is
predictable from its own last move (P_t = beats(P_t-1) often), the assistant's move is then
predictable from P_t-1, i.e. TE(P -> A) = I(A_t; P_t-1 | A_t-1) > 0. At p = 1, A_t-1 is always
beaten_by(P_t-1), so conditioning on it already reveals P_t-1 and TE(P -> A) = 0.

Part 1 reads the LLM C2 runs (sweep and p = 1.0, Llama x4): primary cycle rate, TE(P -> A),
TE(A -> P), the subtracted third-agent term, and the lagged pair score.
Part 2 is a scripted ablation: primary cycles with probability c (else uniform), assistant plays
the helping move with probability p (else uniform), honest players uniform; 4 players, 200 rounds.
"""
import argparse
import glob
import json
from pathlib import Path

import numpy as np

from netinf import analysis as an
from netinf import detector as d
from netinf.envs.rps import beaten_by, beats

ap = argparse.ArgumentParser()
ap.add_argument("--games", type=int, default=200)
args = ap.parse_args()

RUNS = (["runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-120724"]
        + sorted(glob.glob("runs/C2_llama-3.3-70b-instruct_p1.0_s[1-4]_20261024-123914"))
        + sorted(glob.glob("runs/C2_llama-3.3-70b-instruct_p*_20261025-*")))


def te_parts(a: np.ndarray, P: int, A: int) -> dict:
    te = d.lagged_matrix(a)
    G = d.lagged_net_matrix(a)
    others = [k for k in range(a.shape[1]) if k not in (P, A)]
    return {"te_PA": te[P, A], "te_AP": te[A, P], "sub_A": max(te[k, A] for k in others),
            "net_PA": G[P, A], "net_AP": G[A, P], "score": max(G[P, A], G[A, P])}


print("Part 1: LLM C2 runs (Llama 3.3 70B x4, prompt v3)")
print(" p    seed  cycle  A_t=P_t-1  TE(P->A) TE(A->P) max TE(k->A)  net(P->A)  score  lagged rank")
rows = []
for path in RUNS:
    meta = json.loads(Path(path, "meta.json").read_text(encoding="utf-8"))
    if not meta.get("completed") or meta["n_rounds"] != 200:
        continue
    r = an.load_run(path)
    a = np.asarray(r.actions)
    P, A = r.primary, r.assistant
    cyc = float(np.mean(a[1:, P] == beats(a[:-1, P])))
    a_prev = float(np.mean(a[1:, A] == a[:-1, P]))
    t = te_parts(a, P, A)
    rank = an.rank_of_pair(an.lagged_pair_scores(a), r.true_pair)
    rows.append((r.p_channel, cyc, t))
    print(f"{r.p_channel:4} {r.seed:5}  {cyc:.2f}   {a_prev:.2f}      {t['te_PA']:.3f}    "
          f"{t['te_AP']:.3f}    {t['sub_A']:.3f}        {t['net_PA']:+.3f}    {t['score']:+.3f}  {rank}")
for p in sorted({x[0] for x in rows}):
    g = [x for x in rows if x[0] == p]
    print(f"  p = {p}: mean cycle {np.mean([x[1] for x in g]):.2f}, TE(P->A) "
          f"{np.mean([x[2]['te_PA'] for x in g]):.3f}, net(P->A) "
          f"{np.mean([x[2]['net_PA'] for x in g]):+.3f}  (n = {len(g)})")


def simulate(c: float, p: float, rng: np.random.Generator, T: int = 200) -> np.ndarray:
    a = rng.integers(3, size=(T, 4))  # players 0, 1 honest; 2 primary; 3 assistant
    for t in range(1, T):
        if rng.random() < c:
            a[t, 2] = beats(a[t - 1, 2])
    help_ = rng.random(T) < p
    a[help_, 3] = beaten_by(a[help_, 2])
    return a


print(f"\nPart 2: scripted ablation, {args.games} games per cell; true pair (2, 3), "
      "lagged top-1 (chance 1/6) and mean TE(P->A)")
rng = np.random.default_rng(0)
print("   c \\ p " + "".join(f"   p={p:<4}        " for p in (0.1, 0.3, 0.5, 1.0)))
for c in (0.0, 0.5, 0.9):
    line = f"  c={c:<4} "
    for p in (0.1, 0.3, 0.5, 1.0):
        top, te = 0, []
        for _ in range(args.games):
            a = simulate(c, p, rng)
            top += an.rank_of_pair(an.lagged_pair_scores(a), (2, 3)) == 1
            te.append(d.lagged_influence(a, 2, 3))
        line += f"  {top / args.games:.2f} ({np.mean(te):.3f})  "
    print(line)
