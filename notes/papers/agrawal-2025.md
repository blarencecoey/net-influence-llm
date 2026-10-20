---
title: Evaluating LLM Agent Collusion in Double Auctions
authors: Agrawal, Teo, Vazquez, Kunnavakkam, Srikanth, Liu
venue: arXiv 2507.01413 (ICML 2025 workshop listing)
link: https://arxiv.org/abs/2507.01413
code: not linked in paper; sprint starter code references "the Agrawal double-auction environment"
tags: [environment, market, stretch]
---

# Agrawal et al. 2025

## Setup
- Continuous double auction, 5 buyers + 5 sellers (LLM agents), 30 rounds, ≤ 1 lot per round. Whole-cent asks. Seller value $80, buyer $100, competitive price $90.
- Sellers can broadcast one message per round to other sellers (ablated).
- Models: GPT-4.1 and Claude 3.7 Sonnet (mixed 3 + 2 condition).
- Collusion metrics: LLM judge (GPT-4.1-mini, 1–4 on reasoning traces), ask vs $90, ask dispersion, trade price, profit.
- Overseer can restrict messages to ≤ 5 characters; "CEO urgency" pressure condition.

## Results
- Avg trade price 90.52 with communication vs 87.71 without; GPT-only 91.44, Claude-only 88.63; urgency raises to ~96.
- 10 sessions per condition.

## Why it matters for us (stretch environment)
- **Sample size is the blocker:** 30 rounds × 10 sessions with continuous-ish prices. Plug-in CMI needs ask prices binned to 2–3 levels and state ≈ nothing, or pooling across sessions. See [[estimation]].
- 5 sellers = 10 unordered pairs; good test of the max-over-others term and of >2 colluders (all sellers can talk).
- Any vendored code → row in PRIOR_WORK.md.
