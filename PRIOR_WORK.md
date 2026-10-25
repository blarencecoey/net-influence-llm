# Prior work disclosure

The sprint rules allow building on existing work but require clearly identifying what was done during the sprint. Undisclosed prior work can lead to disqualification.

**Sprint window:** Fri Oct 23, 2026 to Sun Oct 25, 2026, 11:59 PM AoE.

## Done before the sprint

- Repository scaffolding: directory layout, README, packaging config, empty module stubs, notes templates.
- Research plan in `notes/00-plan.md` (question, hypotheses, condition grid). No code, data or results.
- Literature notes (2026-10-20, with Claude as research assistant): 16 paper notes in `notes/papers/`, the index `notes/lit-review.md`, estimator/statistics notes in `notes/methods/estimation.md` (including a throwaway bias simulation, not committed), and the limitations tracker `notes/limitations-and-ethics.md`. Reading and notes only; no detector, environment or agent code.
- Updated `CLAUDE.md` with sprint compliance rules.
- Copied the official 1.4 track brief into `notes/track-brief.md` and aligned notes with it and the submission template (2026-10-21, with Claude). Notes only.
- Background survey of AI loss-of-control threat models (2026-10-19/20, with Claude as research assistant): `notes/loss-of-control-survey.md`. Reading notes only; no code or results.

No estimator, environment or agent code was written before the sprint. All function bodies in `src/netinf/` raise `NotImplementedError` as of the last pre-sprint commit.

## Done during the sprint

Everything committed on or after Oct 23, 2026. The git history is the record; the last pre-sprint commit is tagged `pre-sprint`.

> [claude] Tagged 2026-10-24: annotated tag `pre-sprint` → `643b0b2` (2026-10-21, the last commit before the first sprint commit `039e94f` on 2026-10-24), pushed to origin.

- 2026-10-24: detector, scripted RPS, correlation baseline, tests, Table 2 reproduction and scripted 4-agent comparison scripts (with Claude as coding colleague).
- > [claude] 2026-10-24 (with Claude as coding colleague): LLM RPS harness and runner, LLM-judge baseline, analysis pipeline with calibrated thresholds, results viewer; C2 prompts v1–v3; all LLM runs (C2, C0, C1, mixed C2) and judge runs; removal of the circular-shift test (B18); scripted lockstep control; re-analyses in `notes/results/`. Commits `0c3e9c8` to `5e0f050`.
- > [claude] 2026-10-25: C3 and H3-sweep LLM runs (`configs/c3.yaml`, `configs/c2_sweep_low.yaml`) and their analysis.

- > [claude] 2026-10-25: 75-second explainer film in `film/` (with Claude as writer, designer and render engineer; not report prose). Numbers on screen are taken from `notes/results/fact-sheet.md`, see `film/SOURCES.md`.

## External code used

| Source | What | License |
|---|---|---|
| Inter typeface (Rasmus Andersson), from the Debian `fonts-inter` package | Font files in `film/src/fonts/` for the explainer film | OFL-1.1 (`film/src/fonts/LICENSE-Inter.txt`) |
| DejaVu Sans Mono, from the Debian `fonts-dejavu` package | Font file in `film/src/fonts/` for the explainer film | Bitstream Vera license (`film/src/fonts/LICENSE-DejaVu.txt`) |

Add a row whenever third-party code is vendored or adapted (e.g. the Agrawal et al. double-auction harness, https://github.com/andyjliu/llm-agent-collusion).
