---
title: Emergent Coordination in Multi-Agent Language Models
authors: Riedl
venue: arXiv 2510.05174 (v3, 2026-03-15)
link: https://arxiv.org/abs/2510.05174
code: https://github.com/riedlc/AI-GBS (check license before reuse)
tags: [information-theory, PID, transfer-entropy, surrogates, methods]
---

# Riedl 2026

Closest **methodological** precedent: information-theoretic coordination measures on LLM agent action series, with proper surrogate nulls.

## Method
- Time-delayed MI (lag 1) and Williams–Beer partial information decomposition (I_min redundancy; MMI as robustness check); pairwise dynamical synergy; triplet-beyond-best-pair coalition test.
- Discretise to K = 2 quantile bins; plug-in estimator with Jeffreys smoothing (α = 1/2); Miller–Madow and 3 bins as robustness.
- Nulls: row-wise shuffles (break identity), column-wise **time-shift surrogates** (break cross-agent alignment), block shuffle for bias-corrected estimates. Fisher's method across groups; Wilcoxon on bias-corrected values.

## Setup and results
- Group binary-search game, no communication, N = 10 agents, GPT-4.1 at temperature 1, 200 groups per condition. Robustness on Llama-3.1-8B/70B, Gemini 2.0 Flash, Qwen3-235B.
- Theory-of-mind prompting increases synergy and goal-directed complementarity; synergy × redundancy predicts success.

## Why it matters for us
- Template for our circular-shift null (H4) and for the lagged variant (H2). Cite it as precedent so the null design isn't ad hoc.
- Shows the "triplet beyond best pair" idea in practice — relevant to the >2-colluder extension (C4) alongside co-information.
- Coordination ≠ collusion: Riedl measures **beneficial** coordination. Same statistics flag both, which is a limitation we inherit (see [[limitations-and-ethics]]).
- Uses only 2 bins to tame plug-in bias. Reinforces that our state space must stay small (see [[estimation]]).
