# Cross-validated FPR of the honest-run thresholds

> [claude] $0 re-analysis, no new games. Addresses limitation B20 (held-out FPR rested on 5 runs per null condition).

- **Input:** `notes/results/calib-c0-c1-100null/per_unit.csv` (saved max pair scores of the 110 C0 + C1 runs, seeds 0–54, every detector and state).
- **Method:** 5 folds by seed (fold = seed % 5, so C0 and C1 runs with the same seed share a fold); thresholds refitted on the other 4 folds (88 runs) with `analysis.threshold_at_fpr`, the rule used for the frozen thresholds; alarm = max pair score > threshold; each run held out once. 100 random seed partitions (rng seed 0) for spread. Algorithm 1 at α = 0.05 any-pair rate on the same runs for comparison.
- **Caveat:** if null runs are exchangeable, CV FPR near nominal is expected by construction; the informative parts are the C0 / C1 split and the comparison with Algorithm 1. Thresholds are refitted per fold, so this does not re-evaluate the frozen thresholds.
- **Code:** `scripts/cv_fpr.py`. **Command** (repo root): `python scripts/cv_fpr.py notes/results/calib-c0-c1-100null/per_unit.csv > notes/results/cv-fpr/output.txt`
