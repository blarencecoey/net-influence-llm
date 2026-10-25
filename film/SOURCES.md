# Sources for every number and claim on screen

Repo paths are relative to the repository root. Fact-sheet sections are in `notes/results/fact-sheet.md`.

| On screen | Value | Source |
|---|---|---|
| Net influence definition: γ(i;j) = conditional MI of actions given state; Γ(i;j) = γ(i;j) − max over other k of γ(k;j); flag if both directions ≥ α = 0.05 | — | `notes/papers/bonjour-2022.md` (Eq. 3–6, α = 0.05). Taken from the repo's paper note; the PDF was not re-opened in this session `[not re-checked]` |
| Bar heights in S04 | illustrative | Not data. Labelled "illustrative" on screen |
| Scripted RPS, CP 0.4, 200 games: paper 79.2 %, ours 83.1 % | 79.2 / 83.1 | Fact sheet §1; `notes/methods/reproduction.md` (nats column) |
| Scripted RPS, CP 0.4, 400 games: paper 99.3 %, ours 98.9 % | 99.3 / 98.9 | Same |
| Four Llama agents, secret channel: colluding pair ranked first in 5/5 runs | 5/5 | Fact sheet §2, row "Llama ×4 (s0–4)", netinf top-1 |
| Published rule (Alg. 1, α = 0.05) flagged a pair in 40 of 55 honest mixed-family games (C1) | 40/55 | Fact sheet §3, state `prev_n_distinct` |
| Top pair was same-model in 98 % of those C1 runs | 0.98 | Fact sheet §3, column "C1 top pair same-model" |
| False alarms over 110 honest games: published rule 45 %, threshold from honest games 0.9 % (cross-validated, nominal 1 %) | 0.45 / 0.009 | Fact sheet §3c |
| Plan agreed before the game (C3 v4, 20 seeds): same-round flagged 12/20, lagged (one move back) 20/20, at the frozen 1 % threshold | 12/20, 20/20 | Fact sheet §8b-2 (prev_n_distinct flag, lagged flag) |
| Three colluders (C4): every colluding pair scores 0.000, flagged 0/6 | 0.000, 0/6 | Fact sheet §8c |
| "Screen, not proof" | — | `CLAUDE.md` dual-use guardrails |

The S01 rounds (who throws what) are a hand-made illustration of assistant collusion, not data from a run.
