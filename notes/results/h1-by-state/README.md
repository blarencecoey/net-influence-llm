# H1 under each detector state

> [claude] Derived from `notes/results/calib-c0-c1-100null/` (per_unit.json, thresholds.json); no new runs.

- **Script:** `python scripts/h1_by_state.py notes/results/calib-c0-c1-100null > notes/results/h1-by-state/output.txt`
- Per null condition and state: Algorithm 1 false-alarm rate (α = 0.05), share of runs whose top pair is a same-model pair, median max score, frozen thresholds, held-out FPR (5 runs per condition), and for C1 the per-run difference between the largest same-family and the largest cross-family pair score (Wilcoxon signed-rank vs 0).
