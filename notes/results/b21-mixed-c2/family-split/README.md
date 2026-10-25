# Mixed C2 split by seeded-pair family (C4 cross-family arm)

> [claude] Re-analysis only, $0, no new games. Runs and costs: `notes/lab-log.md` (B21 entry, 2026-10-24).

- **Input:** `notes/results/b21-mixed-c2/score_seeded/per_unit.json` (the 10 mixed C2 runs, Llama ×2 + Mistral ×2, p = 1.0, seeds 0, 1, 4, 6, 7, 9, 20, 24, 30, 34).
- **Thresholds:** frozen, `notes/results/calib-c0-c1-100null/thresholds.json` (calibration seeds 5–54). Held out: s0 (same-family), s1, s4 (cross-family).
- **Command** (repo root):

  ```
  python scripts/c4_family_split.py notes/results/b21-mixed-c2/score_seeded notes/results/calib-c0-c1-100null/thresholds.json > notes/results/b21-mixed-c2/family-split/output.txt
  ```

- **Output:** `output.txt`: per run (pair, families, positive control, netinf rank, true-pair score, margin over the next-highest pair, Algorithm 1, flags) and per group (same- vs cross-family) for netinf (`prev_n_distinct`, `none`), lagged netinf and correlation.
- **Caveat:** roles were drawn at random, so this is not a planned C4 condition; only 3 runs are held out.
