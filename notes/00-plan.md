# Plan

Apart AI Collusion Research Sprint, Oct 23–25, 2026 · Track 1, Q1.4 · Submission due Sun Oct 25, 11:59 PM AoE

## Question

Does pairwise net influence ([[bonjour-2022]]) detect colluding LLM agents, and where does its independence assumption break?

## Hypotheses

- **H1 (shared priors):** same-family non-colluding agents get inflated net influence, producing false positives that cross-family pairs do not.
- **H2 (tacit collusion):** coordination carried only through the game history is missed by same-round net influence but caught by a lagged (transfer entropy) variant.
  > [claude] 2026-10-25, framing chosen by Clarence (decision log): (A) headline by the pre-registered primary state: not supported on LLM data, same-round net influence already ranks the C3 pair first 6/6 (the pre-stated "against" case); (B) explanation: H2 holds when the state conditions on the history the coupling runs through (prev_joint, a pre-registered secondary state: same-round 0/6, lagged 6/6); (C, revised) the scripted separation between same-round and lagged detectors does not survive predictable LLM players, in either direction (C3 leak into same-round; C2-sweep leak into lagged). Evidence: `notes/results/fact-sheet.md` §7b, §8b-2; tracker A12, B25.
- **H3 (dose response):** net influence rises with the probability that the colluders' private channel is delivered.
- **H4 (calibration):** a circular-shift null threshold reduces false positives versus the fixed α = 0.05, without losing the positive control.
  > [claude] 2026-10-24: the circular-shift null turned out invalid for the net score (B18 in [[limitations-and-ethics]]), so the pipeline now tests H4 with the honest-run (C0/C1) calibrated threshold only. Rewording H4 is the author's call.
  > [claude] 2026-10-25, framing chosen by Clarence (decision log): two parts. **H4a** (this line, circular-shift null) is reported as a negative methods finding: the null does not match the net score and rejects honest pairs under a shared prior (B18). **H4b** is the pre-registration template's wording ("the honest-run threshold has lower held-out FPR than Alg. 1 at α = 0.05 on C0/C1, at similar C2 TPR"), committed in 0c3e9c8 before the first LLM game (template never frozen): lower FPR where Alg. 1 fires (C1 held-out 5/5 → 1/5), with TPR loss at weak collusion (C2 p = 0.3 5/6 → 3/6; C3 v4 5/6 → 4/6 at 1 %). Evidence: `notes/results/fact-sheet.md` §3b; tracker B18, B20.

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
| 2026-10-24 | C2 fix: channel names the move to play (prompt v2); keep the failed v1 run as a finding | > [claude] Recorded from Clarence's answer; v1 assistant countered the revealed move 16/20 |
| 2026-10-24 | Positive-control check: primary win rate vs uniform-play chance (19/27), one-sided binomial, α = 0.05; primary-vs-honest t-test kept as secondary | > [claude] Recorded from Clarence's answer; CLAUDE.md says "partner win rate above chance"; primary vs honest failed on a fully complying pair |
| 2026-10-24 | C2 primary told to vary its moves (prompt v3); the v2 primary locking onto one move is treated as a confound | > [claude] Recorded from Clarence's answer, which asked that the risks be noted: limitations B13 |
| 2026-10-25 | H4 in two parts: H4a circular-shift null reported as invalid (B18); H4b the template's honest-run threshold vs Alg. 1 wording | > [claude] Recorded from Clarence's answer, after seeing the H4 evidence (fact sheet §3b) |
| 2026-10-25 | H2 framing: headline by the primary state (not supported), state-dependence as the explanation (prev_joint), and detector separation not surviving predictable LLM players | > [claude] Recorded from Clarence's answer, after the C3 v4 results and the lagged sweep check (`notes/results/lagged-sweep-check/`) |
| 2026-10-25 | C3 prompt v4: assistant rule given as a lookup table with "follow this rule exactly"; C3 primary gets the C2 "vary your moves" sentence; re-run C3 seeds 0–4, 55. The v3 C3 runs are kept as a finding | > [claude] Recorded from Clarence's answer, after seeing the v3 C3 results (assistant played the inverse rule, B25), so this is a post-hoc change |

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
