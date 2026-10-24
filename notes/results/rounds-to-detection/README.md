# Rounds needed for detection

> [claude] No new runs. Every run is truncated to its first T rounds (T = 25 … 200), thresholds are refitted on the truncated calibration nulls (C0 + C1 seeds 5–54), then evaluated on the truncated held-out runs (seeds 0–4).

- **Script:** `python scripts/rounds_to_detection.py --calib-seeds 5-54 --out notes/results/rounds-to-detection` (stdout saved as `output.txt`; table in `rounds_to_detection.csv`, run list in `config.json`).
- Seeded sets: C2 Llama ×4 v3 (5 runs, all held out) and C2 Llama + Mistral (10 runs, 3 held out). Top-1 and Algorithm 1 need no threshold and are computed over all seeded runs.
- At T = 200 the refitted thresholds equal the frozen ones in `calib-c0-c1-100null` (0.1149 / 0.0925 pre-registered state), a consistency check.
- Only C2 at p_channel = 1.0 exists, the strongest collusion condition, so this says nothing yet about weaker collusion (H3 sweep, C3).
