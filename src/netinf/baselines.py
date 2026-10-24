"""Baseline detectors compared against net influence.

- Action correlation: Cramér's V between two agents' same-round actions, ignoring state and
  ignoring the other agents. This is the "ordinary action correlation" baseline in the track brief.
  Unlike net influence, it does not subtract the strongest third-party dependence.
- (LLM judge lives with the LLM harness, since it needs API calls.)

All rankers return {(i, j): score} over unordered pairs with i < j; higher = more suspicious.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np


def cramers_v(x: np.ndarray, y: np.ndarray) -> float:
    """Cramér's V of a contingency table built from two discrete arrays (0 if degenerate)."""
    _, xc = np.unique(x, return_inverse=True)
    _, yc = np.unique(y, return_inverse=True)
    r, c = xc.max() + 1, yc.max() + 1
    if r < 2 or c < 2:
        return 0.0
    table = np.bincount(xc * c + yc, minlength=r * c).reshape(r, c).astype(float)
    n = table.sum()
    expected = table.sum(1, keepdims=True) * table.sum(0, keepdims=True) / n
    chi2 = np.sum((table - expected) ** 2 / expected)
    return float(np.sqrt(chi2 / (n * (min(r, c) - 1))))


def correlation_scores(actions: np.ndarray) -> dict[tuple[int, int], float]:
    """Cramér's V for every unordered pair."""
    actions = np.asarray(actions)
    n = actions.shape[1]
    return {(i, j): cramers_v(actions[:, i], actions[:, j]) for i, j in combinations(range(n), 2)}


def agreement_scores(actions: np.ndarray) -> dict[tuple[int, int], float]:
    """Fraction of rounds where two agents play the same action (a cruder baseline)."""
    actions = np.asarray(actions)
    n = actions.shape[1]
    return {
        (i, j): float(np.mean(actions[:, i] == actions[:, j])) for i, j in combinations(range(n), 2)
    }


def rank_of_pair(scores: dict[tuple[int, int], float], pair: tuple[int, int]) -> int:
    """1-based rank of `pair` among all pairs (ties broken pessimistically)."""
    pair = tuple(sorted(pair))
    s = scores[pair]
    return 1 + sum(1 for p, v in scores.items() if p != pair and v >= s)
