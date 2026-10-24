# C2, Llama 3.3 70B ×4, prompt v3, seeds 0–4

> [claude] Analysis output only, no new API spend. The runs and their costs are in `notes/lab-log.md`.

- **Input:** the five complete 200-round v3 runs, each with a `judge.json`:
  - `runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-120724`
  - `runs/C2_llama-3.3-70b-instruct_p1.0_s{1,2,3,4}_20261024-123914`

  Left out: the 20-round smoke runs (v1, v2, v3), the v2 run `…114420`, and the Llama + Mistral runs, most of which were still running at analysis time (`completed: false`).
- **Code:** branch `sprint/shift-null-b18` at ca363d1. That is the pipeline without the circular-shift test (limitation B18).
- **Command** (from the repo root):

  ```
  python scripts/analyze_runs.py "runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-120724" "runs/C2_llama-3.3-70b-instruct_p1.0_s?_20261024-123914" --out notes/results/c2-llama-v3
  ```

- **Positive control:** all 5 runs pass (primary win rate 1.00 vs chance 0.704, binomial p = 3e-31 each). See `positive_control.csv`.
- **What this output cannot show yet:**
  - There are no C0/C1 runs, so no thresholds are fitted (`thresholds.json` has no detectors) and there are no held-out TPR/FPR numbers.
  - Seeds 0–1 are still labelled `calibration` in `per_unit.csv`. `summary.csv` pools all 5 seeds.
  - There are no C1 runs, so no H1 comparison: `h1.json` is empty.
  - The `prev_joint` state has 25 states over 200 rounds, so its plug-in bias (~0.25 nats) is above α = 0.05.
