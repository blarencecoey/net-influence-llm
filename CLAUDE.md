# CLAUDE.md

Context for Claude Code working in this repo.

## Project

Apart Research AI Collusion Research Sprint (Oct 23–25, 2026), research question 1.4: apply Bonjour et al. (2022) pairwise net influence to LLM agents and test whether it survives shared priors and tacit coordination. The plan is in `notes/00-plan.md`; read it before starting work.

## Rules

- **Validate before extending.** The estimator must reproduce Bonjour et al.'s scripted RPS results before it is run on LLM data.
- **Positive control first.** Every LLM experiment runs its seeded-collusion condition before any other condition.
- **Freeze thresholds.** Choose detection thresholds on the calibration split only, then evaluate on the held-out split. Never tune on test runs.
- **Log every run.** Each experiment writes its config, seed and model IDs alongside outputs in `runs/`, and gets a short entry in `notes/lab-log.md`.
- **Report variance.** Report results across seeds with spread, never a single run.
- **The report is the author's own writing.** Help with code, analysis and checking drafts, but do not write report prose in `notes/report-draft.md`. The sprint discards reports that read as generated.
- **Disclose external code.** Any vendored or adapted third-party code gets a row in `PRIOR_WORK.md`.

## Conventions

- Python 3.11+, package in `src/netinf/`, tests in `tests/` (pytest).
- Agent actions are logged as integer codes; states as hashable tuples.
- API keys come from `.env`, never committed.
