"""Collusion detectors based on pairwise net influence (Bonjour, Aggarwal & Bhargava, UAI 2022).

Definitions (checked against the paper PDF, 2026-10-24):
- individual influence, fully observable simultaneous game (Eq. 6):
      gamma(i; j) = sum_s p(s) sum_{a_i, a_j} p(a_i, a_j | s) log[ p(a_i, a_j | s) / (p(a_i | s) p(a_j | s)) ]
  i.e. the conditional mutual information I(a_i; a_j | s). Symmetric in i, j for simultaneous games.
- net influence (Eq. 4): Gamma(i; j) = gamma(i; j) - max_{k != i, j} gamma(k; j). Not symmetric.
- detection (Eq. 5 + Algorithm 1): i, j collude if Gamma(i; j) >= alpha and Gamma(j; i) >= alpha,
  declared only if exactly one pair passes. alpha = 0.05 in the paper.
- estimation: plug-in probabilities from counts.

Our additions (not in the paper):
- Miller-Madow bias correction (option `bias_correct`).
- `pair_scores`: ranking score min(Gamma(i; j), Gamma(j; i)) per unordered pair, so detectors can be
  compared by how they rank the true pair. This is our choice, consistent with Eq. 5.
- lagged variant (conditional transfer entropy) and permutation / circular-shift nulls.

Data format: `actions` is an int array of shape (T, n_agents) with codes 0..n_actions-1.
`states` is an optional int array of shape (T,) (one code per round); None means a single state.
Use `encode_states` to turn hashable state tuples into codes, and `from_rounds` for the
(state, actions) round format.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from itertools import combinations

import numpy as np

State = Hashable
Round = tuple[State, Sequence[int]]


# --------------------------------------------------------------------------- data helpers


def encode_states(states: Sequence[Hashable]) -> np.ndarray:
    """Map hashable states to consecutive int codes (order of first appearance)."""
    table: dict[Hashable, int] = {}
    return np.array([table.setdefault(s, len(table)) for s in states], dtype=np.int64)


def from_rounds(rounds: Sequence[Round]) -> tuple[np.ndarray, np.ndarray]:
    """Convert [(state, actions), ...] to (actions (T, n), state codes (T,))."""
    states = encode_states([r[0] for r in rounds])
    actions = np.asarray([list(r[1]) for r in rounds], dtype=np.int64)
    return actions, states


def _as_states(states: np.ndarray | None, T: int) -> np.ndarray:
    if states is None:
        return np.zeros(T, dtype=np.int64)
    states = np.asarray(states, dtype=np.int64)
    if states.shape != (T,):
        raise ValueError(f"states must have shape ({T},), got {states.shape}")
    return states


# --------------------------------------------------------------------------- core estimator


def conditional_mi(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray | None = None,
    bias_correct: bool = False,
    base: float = np.e,
) -> float:
    """Plug-in I(X; Y | Z) for discrete int arrays.

    With `bias_correct`, applies the Miller-Madow correction stratum by stratum:
    (from H_MM = H + (m - 1) / 2N applied to I = H_X + H_Y - H_XY)
    I_MM = I_plugin + [(r_s - 1) + (c_s - 1) - (m_s - 1)] / (2 N_s), weighted by p(s), where r_s, c_s
    and m_s are the numbers of observed X, Y and (X, Y) values in stratum s. Corrected values can be
    negative.
    """
    x = np.asarray(x, dtype=np.int64)
    y = np.asarray(y, dtype=np.int64)
    T = len(x)
    if T == 0:
        return 0.0
    z = _as_states(z, T)
    # Re-index everything to dense codes so bincount stays small.
    _, xc = np.unique(x, return_inverse=True)
    _, yc = np.unique(y, return_inverse=True)
    _, zc = np.unique(z, return_inverse=True)
    nx, ny, nz = xc.max() + 1, yc.max() + 1, zc.max() + 1
    counts = np.bincount((zc * nx + xc) * ny + yc, minlength=nz * nx * ny).reshape(nz, nx, ny)
    counts = counts.astype(np.float64)
    n_s = counts.sum(axis=(1, 2))  # rounds per state
    n_sx = counts.sum(axis=2)  # (nz, nx)
    n_sy = counts.sum(axis=1)  # (nz, ny)

    with np.errstate(divide="ignore", invalid="ignore"):
        # p(x,y|s) / (p(x|s) p(y|s)) = n_sxy * n_s / (n_sx * n_sy)
        ratio = counts * n_s[:, None, None] / (n_sx[:, :, None] * n_sy[:, None, :])
        terms = np.where(counts > 0, counts * np.log(ratio), 0.0)
    mi = terms.sum() / T

    if bias_correct:
        r = (n_sx > 0).sum(axis=1)
        c = (n_sy > 0).sum(axis=1)
        m = (counts > 0).sum(axis=(1, 2))
        visited = n_s > 0
        # weight p(s) = N_s / T cancels the 1 / (2 N_s): correction is sum_s (...) / (2T)
        corr = ((r - 1) + (c - 1) - (m - 1))[visited].sum() / (2 * T)
        mi += corr  # bracket is usually negative, so this lowers the estimate

    return float(mi / np.log(base))


def individual_influence(
    actions: np.ndarray,
    i: int,
    j: int,
    states: np.ndarray | None = None,
    bias_correct: bool = False,
    base: float = np.e,
) -> float:
    """gamma(i; j) = I(a_i; a_j | s) (Bonjour et al. Eq. 6)."""
    actions = np.asarray(actions)
    return conditional_mi(actions[:, i], actions[:, j], states, bias_correct=bias_correct, base=base)


def influence_matrix(
    actions: np.ndarray,
    states: np.ndarray | None = None,
    bias_correct: bool = False,
    base: float = np.e,
) -> np.ndarray:
    """gamma for every pair, (n, n), symmetric, NaN on the diagonal."""
    actions = np.asarray(actions)
    n = actions.shape[1]
    g = np.full((n, n), np.nan)
    for i, j in combinations(range(n), 2):
        g[i, j] = g[j, i] = individual_influence(actions, i, j, states, bias_correct, base)
    return g


def net_from_influence(gamma: np.ndarray) -> np.ndarray:
    """Gamma(i; j) = gamma(i; j) - max_{k != i, j} gamma(k; j), from an influence matrix."""
    n = gamma.shape[0]
    if n < 3:
        raise ValueError("net influence needs at least 3 agents")
    G = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            others = [gamma[k, j] for k in range(n) if k not in (i, j)]
            G[i, j] = gamma[i, j] - max(others)
    return G


def net_influence_matrix(actions: np.ndarray, states: np.ndarray | None = None, **kwargs) -> np.ndarray:
    """Gamma for every ordered pair as an (n, n) array; entry [i, j] is Gamma(i; j)."""
    return net_from_influence(influence_matrix(actions, states, **kwargs))


def net_influence(actions: np.ndarray, i: int, j: int, states: np.ndarray | None = None, **kwargs) -> float:
    """Gamma(i; j) (Bonjour et al. Eq. 4)."""
    return float(net_influence_matrix(actions, states, **kwargs)[i, j])


def pair_scores(G: np.ndarray) -> dict[tuple[int, int], float]:
    """Ranking score per unordered pair: min(Gamma(i; j), Gamma(j; i)). Our choice, follows Eq. 5."""
    n = G.shape[0]
    return {(i, j): float(min(G[i, j], G[j, i])) for i, j in combinations(range(n), 2)}


def detect_pair(
    actions: np.ndarray,
    states: np.ndarray | None = None,
    alpha: float = 0.05,
    G: np.ndarray | None = None,
    **kwargs,
) -> tuple[int, int] | None:
    """Algorithm 1: the pair (i, j) if exactly one pair has Gamma >= alpha both ways, else None."""
    if G is None:
        G = net_influence_matrix(actions, states, **kwargs)
    passing = [p for p, s in pair_scores(G).items() if s >= alpha]
    return passing[0] if len(passing) == 1 else None


# --------------------------------------------------------------------------- lagged variant (H2)


def lagged_influence(
    actions: np.ndarray,
    i: int,
    j: int,
    states: np.ndarray | None = None,
    lag: int = 1,
    bias_correct: bool = False,
    base: float = np.e,
) -> float:
    """Conditional transfer entropy TE(i -> j) = I(a_j,t ; a_i,t-lag | s_t, a_j,t-lag).

    Directed: measures how much i's past move predicts j's current move beyond j's own past and
    the current state. Conditioning on a_j,t-lag multiplies the number of strata by n_actions,
    so keep the base state small (see notes/methods/estimation.md section 5).
    """
    actions = np.asarray(actions, dtype=np.int64)
    T = actions.shape[0]
    if T <= lag:
        return 0.0
    s = _as_states(states, T)[lag:]
    aj_now = actions[lag:, j]
    ai_past = actions[:-lag, i]
    aj_past = actions[:-lag, j]
    # combine (s, a_j past) into one conditioning code
    z = s * (actions[:, j].max() + 1) + aj_past
    return conditional_mi(aj_now, ai_past, z, bias_correct=bias_correct, base=base)


def lagged_matrix(actions: np.ndarray, states: np.ndarray | None = None, **kwargs) -> np.ndarray:
    """TE(i -> j) for every ordered pair; entry [i, j] is TE(i -> j). NaN on the diagonal."""
    n = np.asarray(actions).shape[1]
    te = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            if i != j:
                te[i, j] = lagged_influence(actions, i, j, states, **kwargs)
    return te


def lagged_net_matrix(actions: np.ndarray, states: np.ndarray | None = None, **kwargs) -> np.ndarray:
    """Net version of the lagged influence: TE(i -> j) - max_{k != i, j} TE(k -> j). Our extension."""
    te = lagged_matrix(actions, states, **kwargs)
    n = te.shape[0]
    G = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            if i != j:
                G[i, j] = te[i, j] - max(te[k, j] for k in range(n) if k not in (i, j))
    return G


# --------------------------------------------------------------------------- nulls (H4)


def circular_shift_null(
    actions: np.ndarray,
    i: int,
    j: int,
    statistic: Callable[[np.ndarray, int, int], float] | None = None,
    n_shifts: int = 200,
    min_shift: int = 1,
    seed: int = 0,
) -> np.ndarray:
    """Null distribution of `statistic(actions, i, j)` with agent j's series circularly shifted.

    Preserves j's own autocorrelation and marginal while breaking alignment with i. Default
    statistic is gamma(i; j) with a single state; pass a closure to use states or another statistic.
    """
    actions = np.asarray(actions)
    T = actions.shape[0]
    if statistic is None:
        statistic = individual_influence
    rng = np.random.default_rng(seed)
    shifts = rng.integers(min_shift, T - min_shift + 1, size=n_shifts)
    out = np.empty(n_shifts)
    for b, k in enumerate(shifts):
        a = actions.copy()
        a[:, j] = np.roll(actions[:, j], k)
        out[b] = statistic(a, i, j)
    return out


def within_state_permutation_null(
    actions: np.ndarray,
    i: int,
    j: int,
    states: np.ndarray | None = None,
    n_perm: int = 200,
    seed: int = 0,
    **kwargs,
) -> np.ndarray:
    """Null of gamma(i; j) = 0: shuffle a_j among rounds that share a state (keeps p(a_j | s))."""
    actions = np.asarray(actions)
    T = actions.shape[0]
    s = _as_states(states, T)
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(s == v) for v in np.unique(s)]
    out = np.empty(n_perm)
    for b in range(n_perm):
        a = actions.copy()
        for idx in groups:
            a[idx, j] = actions[rng.permutation(idx), j]
        out[b] = individual_influence(a, i, j, s, **kwargs)
    return out


def empirical_p_value(observed: float, null: np.ndarray) -> float:
    """One-sided p-value with the +1 correction: P(null >= observed)."""
    return float((1 + np.sum(null >= observed)) / (1 + len(null)))
