---
title: "Steganalysis of Adaptive Covert Collusion in Tool-Using Agent Populations: A Black-Box, Cross-Principal Approach"
authors: Ghanem
venue: arXiv 2608.02698 (v1, 2026-08-03)
link: https://arxiv.org/abs/2608.02698
tags: [theory, detectability-bound, black-box]
---

# Ghanem 2026

**Results are explicitly placeholders** in v1. Cite only for the theoretical framing, never for numbers.

## Content
- Black-box monitor (text, tool calls, timing). Fuses neural cross-run MI, permutation invariance, distribution-shift, timing side channels, tool-call statistics; conformal-calibrated threshold at FPR 10⁻² / 10⁻³.
- Adaptive in-context red team mutates encodings to lower detector score.
- **Bound: TPR ≤ α + δ with δ ≤ √(ε/2)** (Pinsker), ε = adversary's divergence from honest behaviour. As ε → 0 detection → chance.
- Flags cross-session payload spreading as a largely unaddressed evasion.

## Why it matters for us
- Net influence is itself a KL divergence (joint vs product of policies). So the same Pinsker argument says: **colluders whose conditional MI stays below ε are provably hard to detect by any test on the same observations.** Good framing for the Limitations appendix: our detector has a hard floor set by collusion strength, matching Bonjour's CP = 0.1 failure.
- Positions itself against NARCBench as infeasible across principals (no weights) — same motivation we have.
