"""Collusion detectors.

Implements, during the sprint:
- individual influence gamma(i; j): conditional mutual information between two agents'
  actions given the state (Bonjour et al. 2022, Eq. 3 / Eq. 6)
- net influence Gamma(i; j) = gamma(i; j) - max_{k != i, j} gamma(k; j)  (Eq. 4)
- detection rule: Gamma(i; j) >= alpha and Gamma(j; i) >= alpha  (Eq. 5)
- extensions: Miller-Madow bias correction, lagged (transfer entropy) variant,
  circular-shift null for a calibrated threshold

Data format: a trajectory is a sequence of rounds; each round has a state (hashable tuple)
and an action per agent (int).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Hashable

State = Hashable
Round = tuple[State, Sequence[int]]


def individual_influence(rounds: Sequence[Round], i: int, j: int, bias_correct: bool = False) -> float:
    """gamma(i; j): conditional mutual information I(a_i; a_j | s), in nats."""
    raise NotImplementedError


def net_influence(rounds: Sequence[Round], i: int, j: int, **kwargs) -> float:
    """Gamma(i; j) = gamma(i; j) - max over other agents k of gamma(k; j)."""
    raise NotImplementedError


def net_influence_matrix(rounds: Sequence[Round], n_agents: int, **kwargs):
    """Gamma for every ordered pair, as an (n_agents, n_agents) array."""
    raise NotImplementedError


def detect_pair(rounds: Sequence[Round], n_agents: int, alpha: float = 0.05, **kwargs):
    """Return the colluding pair (i, j) if exactly one pair exceeds alpha both ways, else None."""
    raise NotImplementedError


def lagged_influence(rounds: Sequence[Round], i: int, j: int, lag: int = 1) -> float:
    """Conditional transfer entropy from i's past actions to j's present action."""
    raise NotImplementedError


def circular_shift_null(rounds: Sequence[Round], i: int, j: int, n_shifts: int = 200, seed: int = 0):
    """Null distribution of the statistic with one agent's action series circularly shifted."""
    raise NotImplementedError
