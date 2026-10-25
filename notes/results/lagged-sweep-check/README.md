# Lagged net influence on the C2 sweep: why p = 0.3 / 0.5 but not p = 1.0

> [claude] $0 analysis, no new games. Question: lagged net influence ranks the C2 pair first 6/6 at p = 0.3 and 0.5 but 5th–6th at p = 1.0 (`notes/results/c3-sweep/`), although C2 collusion is a same-round channel.

- **Hypothesis (ours):** on delivered rounds the assistant plays beaten_by(P_t); if the primary often plays the move that beats its own last move, that move is predictable from P_t-1, so TE(P → A) = I(A_t; P_t-1 | A_t-1) > 0. At p = 1, A_t-1 is always beaten_by(P_t-1), so conditioning on it reveals P_t-1 and TE(P → A) = 0.
- **Part 1, LLM:** C2 Llama 3.3 70B ×4, prompt v3, p = 0.1 / 0.3 / 0.5 / 1.0, seeds 0–4 and 55 (runs as in `notes/results/c3-sweep/README.md`). Per run: primary cycle rate, TE(P → A), TE(A → P), largest third-agent TE into the assistant, lagged net score and rank.
- **Part 2, scripted ablation:** primary cycles with probability c ∈ {0, 0.5, 0.9} (else uniform), assistant plays the helping move with probability p (else uniform), two honest players uniform; 4 players, 200 rounds, 200 games per cell, rng seed 0.
- **Code:** `scripts/lagged_sweep_check.py`; lagged score = `analysis.lagged_pair_scores` (state none).
- **Command** (repo root): `python scripts/lagged_sweep_check.py > notes/results/lagged-sweep-check/output.txt`
- **Not explained here:** TE(A → P) is also non-zero at p < 1 (0.014–0.120); it sets the pair score in one run (p = 0.3, seed 0).
