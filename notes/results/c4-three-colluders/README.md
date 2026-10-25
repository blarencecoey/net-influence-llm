# C4, three colluders (one primary, two assistants), Llama 3.3 70B ×4

> [claude] Scoring output only; runs and cost in `notes/lab-log.md` (2026-10-25). Tests the two-colluder assumption (limitations A1).

- **Config:** `configs/c4.yaml` = `c2.yaml` (p_channel 1.0) with `condition: C4`, `n_assistants: 2`. Both assistants receive the channel message. Prompt version v4; the C2 prompts used here are unchanged from v3.
- **Gate:** run with `--skip-positive-control-check` (recorded in each `meta.json`): the runner's gate wants a passing C2 run with the same prompt version, and C2 has only v3 runs; the C2 prompts are byte-identical.
- **LLM input:** `runs/C4_llama-3.3-70b-instruct_p1.0_s{0,1,2,3,4,55}_20261025-13220*`, 200 rounds, all completed, 0 parse failures; `judge.json` in each.
- **Scripted check ($0):** 40 seeds (100–139) of `configs/dryrun_c4.yaml`, written to a scratch directory, not kept.
- **Thresholds:** frozen, `notes/results/calib-c0-c1-100null/thresholds.json`; all runs held out.
- **Code:** git 72972df (scorer `scripts/score_c4.py`); `scripts/run_judge.py` patched to skip the single-pair rank for runs with several assistants.
- **Commands** (repo root):

  ```
  python scripts/run_llm_rps.py --config configs/dryrun_c4.yaml --seeds $(seq 100 139) --runs-dir <scratch>
  python scripts/score_c4.py notes/results/calib-c0-c1-100null/thresholds.json <scratch>/out "<scratch>/C4_*" > notes/results/c4-three-colluders/scripted_dryrun.txt
  python scripts/run_judge.py --budget 0.5 "runs/C4_*"
  python scripts/score_c4.py notes/results/calib-c0-c1-100null/thresholds.json notes/results/c4-three-colluders "runs/C4_llama-3.3-70b-instruct_p1.0_s*" > notes/results/c4-three-colluders/output.txt
  ```

- **Files:** `output.txt`, `per_run.csv` (all colluding-pair scores per detector), `scripted_dryrun.txt`.
