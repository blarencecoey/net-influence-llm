# Synthetic dry run of the analysis pipeline

> [claude] Scripted runs only, no LLM data and no API spend. This checks that the pipeline runs; it is not a result.

- **Input:** 35 scripted run dirs written by `scripts/analyze_runs.py --synthetic`: C0, C1 and C3, plus C2 at p_channel 0.1, 0.3, 0.5 and 1.0, each with seeds 0–4 and 200 rounds. The run dirs go to `runs/synthetic-dryrun/` (gitignored) and can be regenerated with the same seeds.
- **Code:** branch `sprint/shift-null-b18` at f4030da. That is the pipeline after the circular-shift test was removed (limitation B18), so this output has no shift columns.
- **Command** (from the repo root):

  ```
  python scripts/analyze_runs.py --synthetic runs/synthetic-dryrun --out notes/results/synthetic-dryrun
  ```

- **Files:** listed in the docstring of `scripts/analyze_runs.py`. Thresholds are fitted on calibration seeds 0–1 and evaluated on seeds 2–4. Rerunning reproduces everything except the `fitted_at` timestamp in `thresholds.json`.
