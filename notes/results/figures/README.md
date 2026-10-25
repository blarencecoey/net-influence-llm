# Report figures

> [claude] Rendered from saved outputs, no scoring. Command (repo root):
>
> ```
> python scripts/make_figures.py notes/results/figures notes/results/calib-c0-c1-100null notes/results/c3-sweep/per_run.csv notes/results/c3-v4/per_run.csv notes/results/b21-mixed-c2/score_seeded/per_run.csv
> ```

- `scores.png`: net influence, state `prev_n_distinct`, one dot per run. Null runs (C0, C1 seeds 0–54) show their largest pair score; seeded runs show the true pair's score (which is what the threshold is compared against only when the true pair is also the top pair). Lines: frozen 1 % / 5 % thresholds. "C2 mixed" includes 7 runs on calibration seeds (6, 7, 9, 20, 24, 30, 34); seeded runs never enter the threshold fit, but those 7 are not counted in held-out TPR.
- `decomposition.png`: mean gross γ(i; j) and the subtracted third-agent term by pair type, state `prev_n_distinct`, from `notes/results/net-decomposition/output.txt`.
