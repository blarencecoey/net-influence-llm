# Plan

Apart AI Collusion Research Sprint, Oct 23–25, 2026 · Track 1, Q1.4 · Submission due Sun Oct 25, 11:59 PM AoE

## Question

Does pairwise net influence ([[bonjour-2022]]) detect colluding LLM agents, and where does its independence assumption break?

## Hypotheses

- **H1 (shared priors):** same-family non-colluding agents get inflated net influence, producing false positives that cross-family pairs do not.
- **H2 (tacit collusion):** coordination carried only through the game history is missed by same-round net influence but caught by a lagged (transfer entropy) variant.
- **H3 (dose response):** net influence rises with the probability that the colluders' private channel is delivered.
- **H4 (calibration):** a circular-shift null threshold reduces false positives versus the fixed α = 0.05, without losing the positive control.

## Conditions (4 agents, ~200 rounds × 5 seeds each)

| ID | Setup | Tests |
|---|---|---|
| C0 | No collusion, all same model | Baseline false-positive rate |
| C1 | No collusion, 2 same-family + 2 cross-family | H1 |
| C2 | Seeded pair, private per-round channel | Positive control |
| C3 | Seeded pair, strategy agreed before the game, no channel | H2 |
| C4 | 3 colluders, or cross-family colluding pair (stretch) | Two-colluder assumption |

Collusion-strength sweep: channel delivered with probability p ∈ {0.1, 0.3, 0.5, 1.0} (H3).

## Detectors compared

1. Net influence, as published
2. Net influence, bias-corrected
3. Lagged net influence (transfer entropy)
4. Action correlation baseline
5. LLM judge, actions only

## Metrics

- Top-ranked pair is the true pair (accuracy)
- False-positive rate on C0, C1
- Rounds needed for reliable detection
- Thresholds chosen on calibration split, frozen, evaluated on held-out split

## Schedule

- [ ] **Fri:** estimator + scripted RPS reproduction (Bonjour Fig. 3, Table 2), CPU only
- [ ] **Sat AM:** LLM harness; C2 positive control working
- [ ] **Sat PM:** C0–C3 + strength sweep
- [ ] **Sun AM:** lagged detector, calibrated threshold, market (stretch)
- [ ] **Sun PM:** analysis, figures, report

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-16 | Q1.4 chosen | Published detector, never tried on LLM agents; matches quant background |
| 2026-10-24 | Provider: OpenRouter (one key; model IDs still to choose) | > [claude] Recorded from Clarence's answer; same- and cross-family models via one interface |
| 2026-10-24 | Run length: 200 rounds × 5 seeds per condition (not the brief's short games) | > [claude] Recorded from Clarence's answer; see Divergences 1 |
| 2026-10-24 | Pre-registered primary detector state: `prev_n_distinct` (≤ 4 values); `none` and `prev_joint` secondary | > [claude] Recorded from Clarence's answer, before any LLM data was collected |

## Divergences from the official brief

> [claude] Added 2026-10-21 after comparing this plan with [[track-brief]]. These are flags for Clarence to decide, not changes to the plan.
>
> 1. **Run length.** The brief suggests 20–40 LLM games of 15–25 rounds; this plan uses ~200 rounds × 5 seeds per condition. My inference, using the bias rule of thumb in `CLAUDE.md` (~2|S|/N nats): a single 25-round game with 9 states gives bias ≈ 0.72 nats, far above α = 0.05, so short games only work if pooled (40 × 25 = 1000 rounds → ≈ 0.018). Decide which design to use and record it in the decision log.
> 2. **Auction's role.** The brief makes the Agrawal double auction the *target* environment (Markets and Collusion track) and RPS the validation step. This plan and the README list the market as a stretch goal. Worth deciding whether that stays, given the brief's "plus factor" framing.
> 3. **Baselines match.** The brief's three-way comparison (net influence vs action correlation vs LLM judge) is covered by detectors 1, 4 and 5 above.
> 4. **Budget matches** ($0 scripted, ~$5–50 LLM pilot).

## Open questions

- Which cheap models for same-family vs cross-family?
- State abstraction for LLM RPS: own last action + last outcome, or last joint action?
- How to get LLMs to randomize (temperature 1, or ask for a distribution and sample)?
- Follow the brief's short-game design (pooled) or keep ~200-round runs? (see Divergences)
- Is the double auction the target environment or a stretch goal? (see Divergences)
