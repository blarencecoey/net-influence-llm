---
title: Auditing Algorithmic Collusion from Strategy Graphs
authors: Eschenbaum, Meylahn
venue: arXiv 2608.07098 (v1, 2026-08-07), preliminary draft
link: https://arxiv.org/abs/2608.07098
tags: [white-box-policy, RL, pricing]
---

# Eschenbaum & Meylahn 2026

## Method
- Query a frozen deterministic pricing policy in every joint state → successor graph under joint greedy play.
- Graph metrics (max betweenness, attractor in-degree, path length, basin fraction) correlate with the profit-based Collusion Index: betweenness +0.94 on the 101 analytic equilibria, +0.66–0.69 on Q-learning panels.

## Limitations (authors)
- **Grim-trigger collusion hides its punishment branch** and looks competitive.
- Finite deterministic frozen policies only; query count explodes with firms × prices × memory.
- Structure ≠ harm or intent.

## Why it matters for us
- A third detection paradigm (query the policy) beside observational stats (us) and activations ([[rose-2026]]). Useful for a one-line related-work taxonomy.
- Their grim-trigger blind spot has an analogue for us: punishment strategies keyed on the last joint action live in the **history**, which same-round net influence conditions away (H2).
- Not applicable to stochastic LLM policies without many samples per state — which is the same data-hunger we face.
