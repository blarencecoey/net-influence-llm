# Prior work disclosure

The sprint rules allow building on existing work but require clearly identifying what was done during the sprint. Undisclosed prior work can lead to disqualification.

**Sprint window:** Fri Oct 23, 2026 to Sun Oct 25, 2026, 11:59 PM AoE.

## Done before the sprint

- Repository scaffolding: directory layout, README, packaging config, empty module stubs, notes templates.
- Research plan in `notes/00-plan.md` (question, hypotheses, condition grid). No code, data or results.
- Literature notes (2026-10-20, with Claude as research assistant): 16 paper notes in `notes/papers/`, the index `notes/lit-review.md`, estimator/statistics notes in `notes/methods/estimation.md` (including a throwaway bias simulation, not committed), and the limitations tracker `notes/limitations-and-ethics.md`. Reading and notes only; no detector, environment or agent code.
- Updated `CLAUDE.md` with sprint compliance rules.

No estimator, environment or agent code was written before the sprint. All function bodies in `src/netinf/` raise `NotImplementedError` as of the last pre-sprint commit.

## Done during the sprint

Everything committed on or after Oct 23, 2026. The git history is the record; the last pre-sprint commit is tagged `pre-sprint`.

## External code used

| Source | What | License |
|---|---|---|
| _none yet_ | | |

Add a row whenever third-party code is vendored or adapted (e.g. the Agrawal et al. double-auction harness).
