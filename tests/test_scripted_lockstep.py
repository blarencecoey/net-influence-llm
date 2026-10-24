"""Scripted lockstep control: the move rules do what scripts/scripted_lockstep.py says ($0)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scripted_lockstep.py"
spec = importlib.util.spec_from_file_location("scripted_lockstep", SCRIPT)
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)

R, P, S = 0, 1, 2


def test_own_last_q1_cycles_from_rock():
    a = sl.simulate([("own_last", 1.0)] * 4, 6, np.random.default_rng(0))
    assert a[:, 0].tolist() == [R, P, S, R, P, S]
    assert (a == a[:, :1]).all()


def test_shared_mode_q1_beats_previous_mode():
    rng = np.random.default_rng(0)
    a = sl.simulate([("shared_mode", 1.0)] * 3 + [("uniform", 0.0)], 300, rng)
    for t in range(1, 300):
        counts = np.bincount(a[t - 1], minlength=3)
        modes = np.flatnonzero(counts == counts.max())
        assert all(a[t, i] in {(m + 1) % 3 for m in modes} for i in range(3))


def test_mistral_like_frequencies():
    a = sl.simulate([("mistral_like", 0.0)], 20000, np.random.default_rng(1))
    np.testing.assert_allclose(np.bincount(a[:, 0], minlength=3) / 20000, sl.MISTRAL_FREQ, atol=0.01)


def test_score_game_uniform_is_quiet():
    a = sl.simulate([("uniform", 0.0)] * 4, 200, np.random.default_rng(2))
    rec = sl.score_game(a, alpha=0.05)
    assert 0.0 <= rec["all_same"] < 0.15
    assert set(rec["agree_excess"]) == {"0-1", "0-2", "0-3", "1-2", "1-3", "2-3"}
    assert rec["netinf|prev_n_distinct"]["max"] < 0.1
