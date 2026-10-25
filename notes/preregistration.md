---
title: Pre-registration for the LLM experiments
tags: [preregistration, methods]
---

# Pre-registration (freeze before the first real LLM game)

> [claude] Template, 2026-10-24. The choices are Clarence's. Lines marked `[claude suggestion]` are defaults wired into the code and configs, with the reason; replace or confirm each, then commit this file **before** running any non-mock game. The commit timestamp is the pre-registration record. Any later change goes in the deviations table at the bottom with a reason.

> [claude] 2026-10-24, merge into `sprint/llm-harness-local`: this template was written for the merged-in harness, whose code was removed. Its commands and `[claude suggestion]` defaults (e.g. window 5) no longer match the code. Local equivalents: `scripts/run_llm_rps.py --config configs/<c>.yaml` (runner, C2 first), `scripts/analyze_runs.py` (analysis), `netinf.judge` (LLM judge); defaults live in `configs/base.yaml` (e.g. `history_window: 10`, 200 rounds, seeds 0–4). Four Llama 3.3 70B C2 runs (three 20-round smokes, one 200-round, prompts v1–v3, ~$0.06) were made before this file was frozen; see `notes/lab-log.md`. If you use this file, record those runs in the deviations table.

## Fixed before running

| Item | Decision | [claude suggestion] and why |
|---|---|---|
| Primary detector | | Net influence, `--state none` (single state). With 4 players the joint-action state has 82 values; at 200 rounds plug-in bias is several times α ([[estimation]] §1). |
| Ranking score | | min(Γ(i;j), Γ(j;i)) per pair (follows Eq. 5). Lagged: max over directions (help can be one-way). |
| Log base | | Nats. Only matters for the fixed α = 0.05 rule; ranks and calibrated thresholds don't depend on it. |
| Detection rules reported | | (a) Bonjour Alg. 1 at α = 0.05; (b) per-game maxT permutation p < 0.05; (c) honest-run calibrated threshold at FPR 5 %. |
| Calibration split | | Even seeds calibrate, odd seeds evaluate (`--calib-split even`). Thresholds come only from calibration null games. |
| Primary metric | | Top-1 accuracy of the true pair (chance 1/6), 95 % bootstrap CI over games; held-out TPR at FPR 5 %. FPR 1 % only if ≥ 100 calibration games (otherwise state it is not estimable). |
| H1 metric | | In C1, how often the same-family honest pair ranks first (chance 1/6), vs C0 baseline. |
| Positive-control gate | | C2 runs first. Proceed only if assistant compliance ≥ 0.8 and the primary's mean payoff is above the honest players'. If not, fix the prompt once, log it as a deviation, re-run C2. |
| Rounds per game | | 200, window 5. |
| Games per condition | | C2 p=1.0: 6 · C2 sweep p ∈ {0.1, 0.3, 0.5}: 6 each · C0: 20 · C1: 20 · C3: 6. About 76 games. |
| Models | | Players: `meta-llama/llama-3.3-70b-instruct` (same-family). C1 cross-family: `mistralai/mistral-small-3.2-24b-instruct`, `google/gemini-2.5-flash-lite`. Judge: `openai/gpt-4o-mini`. Prices from a third-party list dated 2026-10-20 `[unverified]`; check on openrouter.ai/models. |
| Temperature, prompts | | Temperature 1.0, option order shuffled per call, prompts as in `src/netinf/agents/prompts.py` (copied into each run folder). |
| Stopping rule | | Fixed game counts above; no peeking-driven extra games. Budget cap $15 total (`--max-cost` per invocation). |
| Exclusions | | A game is excluded only if > 5 % of its moves are random fallbacks (unparseable output). Report how many. |

## Hypotheses and what would count against them

- **H1:** same-family honest pairs rank first more often than 1/6 in C1. Against: same-family top-1 rate within the CI of 1/6.
- **H2:** in C3, same-round net influence ranks the true pair near chance; lagged net influence ranks it first. Against: lagged no better than chance, or same-round already high.
- **H3:** in the C2 sweep, the true pair's net influence rises with p. Against: no monotone trend across p.
- **H4:** the honest-run threshold has lower held-out FPR than Alg. 1 at α = 0.05 on C0/C1, at similar C2 TPR. Against: no FPR reduction, or TPR collapses.

## Run order

1. `python scripts/run_llm_games.py configs/c2_seeded.yaml --games 6` → `python scripts/analyze_llm_runs.py runs/<c2>` → check the gate.
2. C0, C1, C3, then the sweep (`--channel-p 0.1`, `0.3`, `0.5`).
3. `python scripts/llm_judge.py runs/<all dirs>`, hand-check 5 verdicts.
4. `python scripts/analyze_llm_runs.py runs/<all dirs> --judge runs/<judge>`.

## Status of this file

> [claude] 2026-10-25: the "Decision" column above was never filled and the file was never frozen, so it is not a pre-registration record. Decisions made before LLM data are in the decision log of [[00-plan]] (e.g. primary state `prev_n_distinct`, 2026-10-24, "before any LLM data was collected"). For reference, where the runs differ from this template's suggestions (facts from `configs/`, `notes/lab-log.md` and `notes/results/`; whether to call any of it pre-registered is the author's call):
>
> | Item | Template suggestion | What the runs used | Source |
> |---|---|---|---|
> | Primary detector state | `none` | `prev_n_distinct` (`none`, `prev_joint` secondary) | [[00-plan]] decision log |
> | Detection rules | Alg. 1; maxT permutation; calibrated threshold | Alg. 1 and calibrated threshold; the circular-shift test was dropped (B18) and no maxT test is in the local harness | `scripts/analyze_runs.py`, [[limitations-and-ethics]] B18 |
> | Calibration split | even / odd seeds | calibration seeds 5–54 (100 C0 + C1 nulls), held-out seeds 0–4 | `notes/results/calib-c0-c1-100null/` |
> | Positive-control gate | compliance ≥ 0.8 and primary > honest | primary win rate vs uniform-play chance 19/27, one-sided binomial, α = 0.05 | [[00-plan]] decision log |
> | History window | 5 | 10 | `configs/base.yaml` |
> | Games | C2 6, sweep 6 per p, C0 20, C1 20, C3 6 | C2 Llama 5 (+ seed 55 on 2026-10-25), mixed C2 10, C0 55, C1 55; C3 and sweep 6 each (seeds 0–4, 55) on 2026-10-25 | lab log |
> | Models | C1 cross-family Mistral Small 3.2 and Gemini 2.5 Flash Lite; judge gpt-4o-mini | Mistral Small 3.2 only; judge Claude Sonnet 5.5 | `configs/base.yaml` |
> | Prompt | as in `prompts.py` | v1 → v2 → v3 changes to the C2 prompts after smoke runs | [[00-plan]] decision log, lab log |

## Deviations after freezing

| Date/time | Change | Reason |
|---|---|---|
