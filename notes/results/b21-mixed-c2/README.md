# C2 Llama + Mistral (mixed families), positive control and detection

> [claude] Analysis output only, no new API spend. Runs and costs: `notes/lab-log.md` (entry "B21, mixed-family positive control").

- **Input:** the 10 complete runs `runs/C2_llama-3.3-70b-instruct+mistral-small-3.2-24b-instruct_p1.0_s*` (seeds 0, 1, 4, 6, 7, 9, 20, 24, 30, 34).
- **Script:** `scripts/b21_mixed_c2.py <thresholds.json>` (repo root).
- `output_calib_v1.txt`: thresholds from calibration seeds 5–19 (30 nulls; that analysis is not kept). Held out: s0, s1, s4, s20, s24, s30, s34.
- `output_calib_v2.txt`: thresholds from `notes/results/calib-c0-c1-100null/thresholds.json` (seeds 5–54). Only s0, s1, s4 are outside that split, so the held-out TPR rests on 3 runs. The last block scores all 10 runs against the same thresholds without the seed-overlap guard: thresholds are fitted on null runs only, so seeded runs on calibration seeds never enter the fit.
