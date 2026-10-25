# C3 (H2) and C2 sweep (H3), Llama 3.3 70B ×4, prompt v3

> [claude] Scoring output only; runs and cost in `notes/lab-log.md` (2026-10-25).

- **Input:** C2 p ∈ {0.1, 0.3, 0.5}, seeds 0–4 and 55 (`runs/C2_llama-3.3-70b-instruct_p0.{1,3,5}_s*_20261025-*`); C2 p = 1.0 seeds 0–4 (`runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-120724`, `..._s{1..4}_20261024-123914`) and seed 55 (`..._s55_20261025-120036`); C3 seeds 0–4 and 55 (`runs/C3_llama-3.3-70b-instruct_pna_s*_20261025-*`). All 30 completed, 0 parse failures.
- **Thresholds:** frozen, `notes/results/calib-c0-c1-100null/thresholds.json` (calibration seeds 5–54). Every run here is held out.
- **Code:** `sprint/c3-sweep` (runs at d5d34e4; scorer `scripts/score_seeded.py`).
- **Command** (repo root):

  ```
  python scripts/score_seeded.py notes/results/calib-c0-c1-100null/thresholds.json notes/results/c3-sweep runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-120724 "runs/C2_llama-3.3-70b-instruct_p1.0_s[1-4]_20261024-123914" "runs/C2_llama-3.3-70b-instruct_p*_20261025-*" "runs/C3_llama-3.3-70b-instruct_pna_s*_20261025-*" > notes/results/c3-sweep/output.txt
  ```

- **Files:** `output.txt` (per-run table and per-condition summary, gated and ungated), `per_run.csv`, `per_unit.json` (all pair scores).
- **Compliance column:** C2 = assistant played the helping move on rounds with the channel delivered (`compliance_off_channel` = same move on the other rounds); C3 = assistant played the instructed rule move, i.e. the move the primary's previous move beats. C3 compliance is near 0 because the assistant played the inverse rule (limitations B25).
