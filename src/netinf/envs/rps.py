"""N-player iterated Rock-Paper-Scissors.

Payoff rules (Bonjour et al. 2022, Sec. 5.1):
1. All actions the same: everyone gets 0.
2. All three actions present: everyone gets 1.
3. Two distinct actions: winners of the pairwise matchup get 1.

Scripted players for the reproduction:
- random player
- assistant colluder: with probability `cp`, plays the move that guarantees its partner a point
- tacit colluder (extension): reacts to its partner's previous move
"""

ROCK, PAPER, SCISSORS = 0, 1, 2


def payoffs(actions: list[int]) -> list[int]:
    raise NotImplementedError
