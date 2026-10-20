---
title: "Faithful yet Collusive: Why Chain-of-Thought Monitoring Cannot Detect Algorithmic Collusion"
authors: Lee, Park
venue: arXiv 2609.18346 (v1, 2026-09-16)
link: https://www.alphaxiv.org/abs/2609.18346
tags: [CoT-monitoring, causal-discovery, pricing]
---

# Lee & Park 2026

## Setup
- Bertrand competition, logit demand, 300 rounds, N = 2 and 3; nine LLMs (GPT-5, Claude Sonnet 4.5, Claude Haiku 4.5, six open models).
- Compare a causal graph stated in CoT against a behavioural graph from prices (Granger causality; PCMCI+ at N = 2).

## Findings
- Collusiveness and CoT faithfulness dissociate (Spearman −0.30 at N = 2, n.s.). Claude Sonnet 4.5 most collusive (Δ = 0.978) with below-median faithfulness; GPT-5 most faithful yet supra-Nash.
- Frontier models stay collusive at N = 3; most open models price below Nash.
- Conclusion: behavioural auditing remains primary; CoT monitoring cannot stand alone.

## Why it matters for us
- Another argument for action-level detection.
- **PCMCI+ is built on conditional-independence tests (Runge's CMI tests)** — i.e. it's a lagged-CMI causal-discovery method on agent action series. Our lagged net influence (H2) is a close cousin; cite this to position H2 and consider Granger/PCMCI as an extra baseline only if time allows.
- Their 300-round horizon is a realistic upper bound for an LLM pilot budget.
