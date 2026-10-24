# C0 + C1 null runs, 100-null calibration (C2 Llama v3 seeds 0–4 held out)

> [claude] Analysis output only, no new API spend. Runs and costs: `notes/lab-log.md` (entries "Null runs for calibration" and "More null runs for a 1% threshold").

- **Input:** C2 Llama 3.3 70B ×4, prompt v3, seeds 0–4 (`runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-120724`, `runs/C2_llama-3.3-70b-instruct_p1.0_s{1,2,3,4}_20261024-123914`); C0 Llama ×4 seeds 0–54 and C1 Llama ×2 + Mistral Small 3.2 ×2 seeds 0–54 (`runs/C0_llama*`, `runs/C1_llama*`; the three `completed: false` partial runs are skipped).
- **Split:** calibration seeds 5–54 (100 null runs, so FPR 1% is resolvable); held out seeds 0–4. Not the code default (`DEFAULT_CALIB_SEEDS = (0, 1)`).
- **Code:** main after PR #9 (5c54184).
- **Command** (repo root):

  ```
  python scripts/analyze_runs.py runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-120724 "runs/C2_llama-3.3-70b-instruct_p1.0_s[1-4]_20261024-123914" "runs/C0_llama*" "runs/C1_llama*" --out notes/results/calib-c0-c1-100null --secondary-states none prev_joint --calib-seeds $(seq 5 54)
  ```

- **Limits:** held-out FPR rests on 5 runs per null condition (B20). The mixed-family C2 runs are not in this analysis; see `notes/results/b21-mixed-c2/`.
