# CLAUDE.md

Context for Claude Code working in this repo.

## Project

Apart Research AI Collusion Research Sprint (Oct 23–25, 2026), Track 1, research question 1.4: apply Bonjour et al. (2022) pairwise net influence to LLM agents and test whether it survives shared priors and tacit coordination. Read `notes/00-plan.md` before starting work, then `notes/lit-review.md` and `notes/methods/estimation.md`.

Sprint page: https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25

## Sprint rules this repo must comply with

- **Deadline:** submissions close Sun Oct 25, 2026, 11:59 PM AoE (= Mon Oct 26, 7:59 AM New York). Resubmission before the deadline must use the exact same title.
- **Prior work must be disclosed.** Undisclosed prior work can lead to disqualification.
  - Before Fri Oct 23: notes, plan and scaffolding only. **Do not write estimator, environment or agent code before the sprint starts.** If asked to, say so and stop.
  - Anything done before the sprint gets a line in `PRIOR_WORK.md` under "Done before the sprint". The last pre-sprint commit is tagged `pre-sprint`.
  - Any vendored or adapted third-party code gets a row in `PRIOR_WORK.md` with source and license.
- **AI use = a colleague.** Claude may write and debug code, run analyses, check reasoning, find gaps, and review drafts.
- **The report is the author's own writing.** Do not write report prose in `notes/report-draft.md` or anywhere meant for the report. Comments, checklists, and factual corrections are fine; mark them `> [claude]`. Reports that read as generated (generic framing, padded sections, unsourced claims, no trace of what was done) are not scored.
- **Required report contents:** PDF on the official template; abstract ≤ 150 words; authors and affiliations; Introduction, Related Work, Methodology (replicable), Results (variance, seeds, baselines, always the positive control), Discussion, **Limitations and Dual-Use / Ethical Considerations**, References. Target 4–8 pages.
- **Judging:** impact & innovation (novelty beyond replication), execution quality, presentation & clarity. Keep work pointed at what is new: net influence on LLM agents, shared-prior false positives, lagged variant, calibrated threshold.
- **Budget:** CPU-only laptop plus cheap API models. Sprint estimate: $0 scripted, ~$5–50 LLM pilot. Log spend per run.

## Research rules

- **Validate before extending.** The estimator must reproduce Bonjour et al.'s scripted RPS results (Table 2: e.g. CP = 0.4 → ~79% at 200 games, ~99% at 400) before it is run on LLM data.
- **Positive control first.** Every LLM experiment runs its seeded-collusion condition before any other condition, and checks that the seeded pair actually colluded (partner win rate above chance) before trusting detection.
- **Freeze thresholds.** Choose detection thresholds on the calibration split only, then evaluate on the held-out split. Never tune on test runs.
- **Mind the bias.** Plug-in CMI bias in RPS is ~2|S|/N nats; Bonjour's α is 0.05. Keep the state space small or pool seeds (`notes/methods/estimation.md`).
- **Log every run.** Each experiment writes its config, seed, model IDs, prompts and cost alongside outputs in `runs/`, and gets a short entry in `notes/lab-log.md`. Lab-log entries are the author's; Claude may append a factual `[claude]` line (what ran, where outputs are).
- **Report variance.** Results across seeds with spread, never a single run. Report top-pair accuracy and TPR at fixed FPR (1%, 5%).

## Verification rules

- **Never assume when stating facts or quoting sources.** Do not fill gaps from memory, paraphrase a source you have not read, or attribute a claim, number or definition to a paper, page or person without checking it.
- **Verify before making any claim.** Open the primary source (the paper PDF, official page, repo or data) and confirm the exact wording, numbers and context before stating it, quoting it or writing it into `notes/`, code comments or review comments. Search results, abstracts and secondhand summaries are not verification.
- **Say so when you cannot verify.** If a source cannot be reached or does not say it, state that plainly and mark the claim unverified (e.g. `[unverified: abstract only]`) rather than guessing.
- **Separate source from inference.** When reasoning beyond what a source says, label it as your own inference, not the source's claim.

## Knowledge base (`notes/`, an Obsidian vault)

- `notes/papers/<firstauthor>-<year>.md`: one note per source. Frontmatter: `title`, `authors`, `venue`, `link`, optional `code`, `tags`. Sections: what they did, results with numbers, stated limitations, **Why it matters for us**. Record only what the source says; mark anything unverified (abstract-only, secondhand).
- `notes/lit-review.md`: index of paper notes, hypothesis evidence, open reading list. Update when a note is added.
- `notes/methods/`: estimator and statistics notes.
- `notes/limitations-and-ethics.md`: living tracker for the required appendix. **Add a row whenever a run, bug or reading reveals a limitation or dual-use concern**, and update status (`open` / `mitigated` / `tested`).
- Link with `[[note-name]]`. Every factual claim that may reach the report needs a source link in its note.

## Dual-use guardrails

- Report detector blind spots as findings, but do not build or publish optimised evasion strategies or stealth-tuned collusion prompts.
- Seeded-collusion prompts stay plain and are released for reproducibility only.
- Frame any detection output as a screen, not proof of collusion.

## Conventions

- Python 3.11+, package in `src/netinf/`, tests in `tests/` (pytest).
- Agent actions are logged as integer codes; states as hashable tuples.
- API keys come from `.env`, never committed.
