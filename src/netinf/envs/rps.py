"""N-player iterated Rock-Paper-Scissors with scripted players.

Payoff rules (Bonjour et al. 2022, Sec. 5.1, checked against the PDF 2026-10-24):
1. All actions the same: everyone gets 0.
2. All three actions present: everyone gets 1.
3. Exactly two distinct actions: every player of the winning action gets 1, the others 0.

Assistant collusion (Sec. 5.1): the primary colluder A and the honest players act uniformly at
random; the assistant B plays, with probability `cp`, the action that A's action beats (which
guarantees A a point whatever the others play) and a random action otherwise. The paper is
ambiguous whether `cp` applies per move or per game; we apply it per round (our choice).

Tacit colluder (our extension, H2): B helps A based on A's *previous* move, so the coordination
lives only in the history and same-round mutual information is zero by construction.

Each round is one simultaneous move; the scripted players are memoryless, so the state is a
single constant (our reading: the paper does not spell out the RPS state in the main text).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ROCK, PAPER, SCISSORS = 0, 1, 2
N_ACTIONS = 3


def beats(a):
    """The action that beats `a` (paper beats rock, scissors beat paper, rock beats scissors)."""
    return (np.asarray(a) + 1) % 3


def beaten_by(a):
    """The action that `a` beats. Playing it as the assistant guarantees the partner a point."""
    return (np.asarray(a) - 1) % 3


def payoffs(actions) -> np.ndarray:
    """Payoffs for one round (1-D) or many rounds (2-D, rounds x players)."""
    a = np.atleast_2d(np.asarray(actions, dtype=np.int64))
    present = np.stack([(a == k).any(axis=1) for k in range(N_ACTIONS)], axis=1)  # (T, 3)
    n_distinct = present.sum(axis=1)
    out = np.zeros_like(a)
    out[n_distinct == 3] = 1
    two = n_distinct == 2
    if two.any():
        # with exactly two actions {x, y}, the winner is whichever beats the other
        idx = np.flatnonzero(two)
        for t in idx:
            x, y = np.flatnonzero(present[t])
            winner = x if beats(y) == x else y
            out[t] = (a[t] == winner).astype(np.int64)
    return out[0] if np.asarray(actions).ndim == 1 else out


@dataclass
class RPSConfig:
    n_players: int = 3
    primary: int = 0  # A
    assistant: int | None = 1  # B; None means no collusion
    cp: float = 0.0  # probability B helps A on a round
    mode: str = "assistant"  # "assistant" (same round) or "tacit" (reacts to A's previous move)


def simulate(cfg: RPSConfig, n_rounds: int, rng: np.random.Generator | int | None = None):
    """Simulate `n_rounds` rounds. Returns (actions (T, n), payoffs (T, n))."""
    rng = np.random.default_rng(rng)
    a = rng.integers(0, N_ACTIONS, size=(n_rounds, cfg.n_players))
    if cfg.assistant is not None and cfg.cp > 0:
        help_mask = rng.random(n_rounds) < cfg.cp
        if cfg.mode == "assistant":
            target = beaten_by(a[:, cfg.primary])
        elif cfg.mode == "tacit":
            prev = np.roll(a[:, cfg.primary], 1)
            target = beaten_by(prev)
            help_mask[0] = False  # no previous move on round 0
        else:
            raise ValueError(f"unknown mode {cfg.mode!r}")
        a[help_mask, cfg.assistant] = target[help_mask]
    return a, payoffs(a)


def previous_joint_action_state(actions: np.ndarray) -> np.ndarray:
    """State code = previous round's joint action (3**n values; round 0 gets its own code).

    Our inference of the paper's RPS state: it reproduces Bonjour et al. Table 2, whereas a single
    constant state does not. See notes/methods/reproduction.md.
    """
    a = np.asarray(actions, dtype=np.int64)
    T, n = a.shape
    codes = (a * (3 ** np.arange(n))).sum(axis=1)
    out = np.empty(T, dtype=np.int64)
    out[0] = 3**n  # "no previous round"
    out[1:] = codes[:-1]
    return out
