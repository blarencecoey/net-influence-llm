"""Where the C1 false positives come from: split each honest pair's net score into the gross
dependence gamma(i; j) and the third-agent term it subtracts, by pair type (C0 Llama-Llama;
C1 Llama-Llama, Llama-Mistral, Mistral-Mistral), and compare pairs at matched marginal entropy.

Pair score = min(Gamma(i; j), Gamma(j; i)) = gamma(i; j) - max(sub_j, sub_i), where
sub_j = max_{k != i, j} gamma(k; j) (detector.net_from_influence, analysis pair score).

Usage (repo root): python scripts/net_decomposition.py "runs/C0_llama*" "runs/C1_llama*"
"""

from __future__ import annotations

import argparse
import warnings
from collections import defaultdict
from itertools import combinations

import numpy as np

from netinf import analysis as an
from netinf import detector as d

STATES = ("prev_n_distinct", "none", "prev_joint")
ENTROPY_BINS = ((0.6, 0.8), (0.8, 0.9), (0.9, 1.0), (1.0, 1.1))


def entropy(x: np.ndarray) -> float:
    p = np.bincount(x, minlength=3) / len(x)
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


def family_tag(model: str) -> str:
    return "L" if "llama" in model else "M" if "mistral" in model else "?"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="+")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", message="skipping incomplete run")
    runs = [r for r in an.load_runs(args.runs) if not r.colluding]

    rows = defaultdict(lambda: defaultdict(list))  # (cond, pair type, state) -> metric -> values
    ent = defaultdict(list)  # (cond, family) -> player entropies
    matched = defaultdict(list)  # (cond, pair type) -> (min entropy, gamma prev_n_distinct)
    for r in runs:
        a, fam = r.actions, [family_tag(m) for m in r.models]
        for i in range(a.shape[1]):
            ent[(r.condition, fam[i])].append(entropy(a[:, i]))
        for st in STATES:
            g = d.influence_matrix(a, an.compute_states(a, st, warn=False))
            for i, j in combinations(range(a.shape[1]), 2):
                others = [k for k in range(a.shape[1]) if k not in (i, j)]
                sub = max(max(g[k, j] for k in others), max(g[k, i] for k in others))
                key = (r.condition, "".join(sorted(fam[i] + fam[j])), st)
                rows[key]["gamma"].append(g[i, j])
                rows[key]["subtracted"].append(sub)
                rows[key]["score"].append(g[i, j] - sub)
                if st == an.PRIMARY_STATE:
                    matched[key[:2]].append((min(entropy(a[:, i]), entropy(a[:, j])), g[i, j]))

    print(f"{len(runs)} null runs: " + ", ".join(
        f"{c} {sum(r.condition == c for r in runs)}" for c in sorted({r.condition for r in runs})))
    print("\nPlayer move entropy (nats; uniform = 1.099)")
    for k in sorted(ent):
        print(f"  {k[0]} {k[1]}: mean {np.mean(ent[k]):.3f}  median {np.median(ent[k]):.3f}  "
              f"n={len(ent[k])}")

    print("\nPair score = gamma - subtracted (means; medians in brackets)")
    for st in STATES:
        print(f"  state {st}")
        for k in sorted(k for k in rows if k[2] == st):
            m = rows[k]
            print(f"    {k[0]} {k[1]}: " + "  ".join(
                f"{name} {np.mean(v):.4f} [{np.median(v):.4f}]" for name, v in m.items())
                  + f"  n={len(m['gamma'])}")

    print(f"\nGross gamma ({an.PRIMARY_STATE}) at matched min(H_i, H_j)")
    for lo, hi in ENTROPY_BINS:
        cells = []
        for k in sorted(matched):
            x = np.array(matched[k])
            sel = x[(x[:, 0] >= lo) & (x[:, 0] < hi), 1]
            cells.append(f"{k[0]} {k[1]} " + (f"{sel.mean():.4f} (n={len(sel)})" if len(sel)
                                                 else "- (n=0)"))
        print(f"  [{lo}, {hi}): " + " | ".join(cells))


if __name__ == "__main__":
    main()
