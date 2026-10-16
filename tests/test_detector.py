"""Estimator tests. Fill in during the sprint.

Planned checks:
- independent random agents: net influence near zero
- an agent that copies another: influence equals the action entropy
- known small joint distribution: matches a hand-computed conditional MI
- scripted RPS with cp=1.0: the colluding pair is detected
"""

import pytest


@pytest.mark.skip(reason="detector not implemented yet")
def test_independent_agents_near_zero():
    pass
