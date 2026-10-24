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
> [claude] LLM harness on branch `sprint/llm-harness`: OpenRouter + mock backends (`src/netinf/agents/backends.py`), plain prompts (`agents/prompts.py`), 4-player game loop with shuffled seats and per-round JSONL logging (`envs/llm_rps.py`), runner with cost cap and parallel games (`scripts/run_llm_games.py`), configs C0–C3, full-trajectory LLM judge (`scripts/llm_judge.py`), analysis with collusion check, maxT permutation p-values and honest-run calibration (`scripts/analyze_llm_runs.py`). Pre-registration template: `notes/preregistration.md`. Tested only with the mock backend (OpenRouter is not reachable from Claude's workspace). No API spend.
