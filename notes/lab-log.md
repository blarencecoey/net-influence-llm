# Lab log

One entry per working session or run. Write what you did and what you saw, in your own words. This is the raw material for the report.

Template:

```
## YYYY-MM-DD HH:MM
**Did:**
**Run:** runs/<folder>, config, seeds, models
**Saw:**
**Next:**
```

---

## 2026-10-16
**Did:** Chose Q1.4. Read Bonjour et al. (2022). Set up repo and notes. Scaffolding only, no code.
**Next:** Sprint starts Fri Oct 23. First task is the estimator and the scripted RPS reproduction.

## 2026-10-20
> [claude] Pre-sprint literature pass: 16 paper notes in `notes/papers/`, index in `notes/lit-review.md`, bias/threshold notes in `notes/methods/estimation.md`, appendix tracker in `notes/limitations-and-ethics.md`. No code. Decisions for you are listed under "Design suggestions" in `notes/lit-review.md`.

## 2026-10-24
> [claude] Sprint start (day 2). Implemented the detector (`src/netinf/detector.py`: CMI, γ, Γ, Algorithm 1, Miller–Madow, lagged/transfer-entropy variant, circular-shift and within-state permutation nulls), scripted N-player RPS (`src/netinf/envs/rps.py`), correlation baseline (`src/netinf/baselines.py`), 17 tests passing. Table 2 reproduction: `scripts/reproduce_bonjour.py` → `runs/bonjour_repro_3p_joint` (matches with previous-joint-action state) and `runs/bonjour_repro_3p` (constant state, too strong). Scripted 4-agent comparison: `scripts/scripted_four_agent.py` → `runs/scripted4_200r`. Numbers and caveats in `notes/methods/reproduction.md`. No API spend.

> [claude] First paid run: C2 smoke, 4 × `meta-llama/llama-3.3-70b-instruct` (OpenRouter, priced [0.10, 0.32] $/1M in `configs/base.yaml`), seed 0, 20 rounds → `runs/C2_llama-3.3-70b-instruct_p1.0_s0_20261024-111626`. Computed cost $0.0042, 40,256 in / 436 out tokens (~503 in per call), 0 parse failures, 56 s wall (median call latency 0.67 s). Positive control FAIL: primary 0.600 vs honest 0.650, assistant 0.800; assistant played the counter to the revealed move 16/20, the helping move 4/20. Fixed `test_refuses_placeholders_with_real_provider` to build its own placeholder config (it read `c2.yaml`, which is now filled).

> [claude] LLM harness built (spec `notes/methods/llm-harness.md`): client + LLM judge (`src/netinf/agents/client.py`, `src/netinf/judge.py`), game runner (`src/netinf/envs/llm_rps.py`, `scripts/run_llm_rps.py`, `configs/`), analysis (`src/netinf/analysis.py`, `scripts/analyze_runs.py`); 68 tests pass. Scripted dry runs ($0, 200 rounds, seeds 0–2) → `runs/C{0,1,2,3}_scripted_*`. Positive control (Fisher, primary vs honest): C2 p = 1.0 and 0.5 pass 3/3, p = 0.3 1/3, p = 0.1 0/3, C3 0/3, C0/C1 0/3. Analysis output in the session scratchpad, not `notes/results/`.
