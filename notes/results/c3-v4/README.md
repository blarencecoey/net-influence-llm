# C3, prompt v4, Llama 3.3 70B ×4

> [claude] Scoring output only; runs and cost in `notes/lab-log.md` (2026-10-25). Prompt v4 = C3 assistant rule as a lookup table with "follow this rule exactly", C3 primary asked to vary its moves (`src/netinf/agents/prompts.py`; decision log in [[00-plan]]). Post-hoc change after the v3 C3 runs (`notes/results/c3-sweep/`, limitations B25).

- **Input:** `runs/C3_llama-3.3-70b-instruct_pna_s{0,1,2,3,4,55}_20261025-123954`, 200 rounds, all completed, 0 parse failures. The 20-round smoke `..._s0_20261025-123912` is not included.
- **Gate:** run with `--skip-positive-control-check` (recorded in each `meta.json`): the runner keys the C2 gate on prompt version, and the C2 prompts are byte-identical between v3 and v4, so the passing v3 C2 runs apply.
- **Thresholds:** frozen, `notes/results/calib-c0-c1-100null/thresholds.json`; all six runs held out.
- **Code:** git f9c21cc.
- **Command** (repo root):

  ```
  python scripts/run_judge.py --budget 0.5 "runs/C3_llama-3.3-70b-instruct_pna_s*_20261025-123954"
  python scripts/score_seeded.py notes/results/calib-c0-c1-100null/thresholds.json notes/results/c3-v4 "runs/C3_llama-3.3-70b-instruct_pna_s*_20261025-123954" > notes/results/c3-v4/output.txt
  ```
