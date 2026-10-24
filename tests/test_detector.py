"""Estimator and environment tests."""

import numpy as np
import pytest

from netinf import detector as d
from netinf.baselines import correlation_scores, rank_of_pair
from netinf.envs import rps


# ------------------------------------------------------------------ conditional MI


def test_independent_agents_near_zero():
    rng = np.random.default_rng(0)
    a = rng.integers(0, 3, size=(20000, 3))
    g = d.individual_influence(a, 0, 1)
    # plug-in bias ~ (3-1)(3-1)/(2N) = 1e-4 nats
    assert 0 <= g < 1e-3


def test_copy_equals_entropy():
    rng = np.random.default_rng(1)
    x = rng.integers(0, 3, size=50000)
    a = np.stack([x, x, rng.integers(0, 3, size=50000)], axis=1)
    assert d.individual_influence(a, 0, 1) == pytest.approx(np.log(3), abs=1e-3)


def test_hand_computed_joint():
    # joint over (x, y) in {0,1}^2 with p = [[0.4, 0.1], [0.1, 0.4]]
    x = np.array([0] * 40 + [0] * 10 + [1] * 10 + [1] * 40)
    y = np.array([0] * 40 + [1] * 10 + [0] * 10 + [1] * 40)
    p = np.array([[0.4, 0.1], [0.1, 0.4]])
    expected = np.sum(p * np.log(p / 0.25))
    assert d.conditional_mi(x, y) == pytest.approx(expected, abs=1e-12)


def test_conditioning_removes_common_cause():
    # x and y both copy the state; given the state they are independent
    rng = np.random.default_rng(2)
    s = rng.integers(0, 3, size=10000)
    x, y = s.copy(), s.copy()
    assert d.conditional_mi(x, y) > 1.0
    assert d.conditional_mi(x, y, s) == pytest.approx(0.0, abs=1e-12)


def test_base_conversion():
    rng = np.random.default_rng(3)
    x = rng.integers(0, 3, size=5000)
    a = np.stack([x, x], axis=1)
    nats = d.conditional_mi(a[:, 0], a[:, 1])
    bits = d.conditional_mi(a[:, 0], a[:, 1], base=2)
    assert bits == pytest.approx(nats / np.log(2))


def test_miller_madow_reduces_bias():
    rng = np.random.default_rng(4)
    s = rng.integers(0, 9, size=(300, 200))
    plain, mm = [], []
    for r in range(300):
        a = rng.integers(0, 3, size=(200, 2))
        plain.append(d.conditional_mi(a[:, 0], a[:, 1], s[r]))
        mm.append(d.conditional_mi(a[:, 0], a[:, 1], s[r], bias_correct=True))
    assert np.mean(plain) > 0.05  # ~2|S|/N = 0.09 nats
    # MM undercorrects with ~22 rounds per stratum (0.109 -> ~0.037 nats here); require it halves bias
    assert abs(np.mean(mm)) < abs(np.mean(plain)) / 2


def test_from_rounds_roundtrip():
    rounds = [(("a",), [0, 1, 2]), (("b",), [1, 1, 0]), (("a",), [2, 0, 1])]
    actions, states = d.from_rounds(rounds)
    assert actions.shape == (3, 3)
    assert list(states) == [0, 1, 0]


# ------------------------------------------------------------------ net influence


def test_net_influence_requires_three_agents():
    with pytest.raises(ValueError):
        d.net_influence_matrix(np.zeros((10, 2), dtype=int))


def test_cp_one_detected_three_players():
    a, _ = rps.simulate(rps.RPSConfig(n_players=3, cp=1.0), 500, rng=0)
    assert d.detect_pair(a) == (0, 1)


def test_cp_one_detected_four_players():
    a, _ = rps.simulate(rps.RPSConfig(n_players=4, cp=1.0), 500, rng=0)
    assert d.detect_pair(a) == (0, 1)


def test_no_collusion_not_detected_often():
    hits = 0
    for seed in range(200):
        a, _ = rps.simulate(rps.RPSConfig(n_players=3, assistant=None), 500, rng=seed)
        hits += d.detect_pair(a) is not None
    assert hits / 200 < 0.05


def test_net_influence_ranks_true_pair_first():
    a, _ = rps.simulate(rps.RPSConfig(n_players=4, primary=2, assistant=3, cp=0.5), 1000, rng=5)
    scores = d.pair_scores(d.net_influence_matrix(a))
    assert rank_of_pair(scores, (2, 3)) == 1


# ------------------------------------------------------------------ lagged variant and nulls


def test_tacit_collusion_invisible_same_round_visible_lagged():
    cfg = rps.RPSConfig(n_players=3, cp=1.0, mode="tacit")
    a, _ = rps.simulate(cfg, 2000, rng=6)
    assert d.individual_influence(a, 0, 1) < 0.01
    assert d.lagged_influence(a, 0, 1) > 0.5
    assert d.lagged_influence(a, 1, 0) < 0.01  # directed


def test_nulls_give_small_p_for_real_dependence():
    a, _ = rps.simulate(rps.RPSConfig(n_players=3, cp=0.5), 500, rng=7)
    obs = d.individual_influence(a, 0, 1)
    assert d.empirical_p_value(obs, d.circular_shift_null(a, 0, 1, n_shifts=99)) <= 0.02
    assert d.empirical_p_value(obs, d.within_state_permutation_null(a, 0, 1, n_perm=99)) <= 0.02


# ------------------------------------------------------------------ environment and baseline


def test_payoff_rules():
    R, P, S = rps.ROCK, rps.PAPER, rps.SCISSORS
    assert list(rps.payoffs([R, R, R])) == [0, 0, 0]
    assert list(rps.payoffs([R, P, S])) == [1, 1, 1]
    assert list(rps.payoffs([R, R, P])) == [0, 0, 1]
    assert list(rps.payoffs([R, S, S])) == [1, 0, 0]
    assert list(rps.payoffs([S, P, P, S])) == [1, 0, 0, 1]


def test_assistant_guarantees_partner_point():
    a, pay = rps.simulate(rps.RPSConfig(n_players=4, cp=1.0), 1000, rng=8)
    assert pay[:, 0].min() == 1


def test_correlation_baseline_finds_strong_pair():
    a, _ = rps.simulate(rps.RPSConfig(n_players=4, cp=1.0), 500, rng=9)
    assert rank_of_pair(correlation_scores(a), (0, 1)) == 1
