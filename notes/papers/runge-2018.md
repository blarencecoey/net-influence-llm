---
title: Conditional independence testing based on a nearest-neighbor estimator of conditional mutual information
authors: Runge
venue: AISTATS 2018, PMLR 84:938–947
link: https://proceedings.mlr.press/v84/runge18a.html
tags: [CMI, CI-test, permutation-null, methods]
---

# Runge 2018

- Non-parametric CI test: kNN estimator of CMI + a **local permutation** null (permute X among samples with similar Z, preserving p(X|Z)).
- For continuous data; basis of PCMCI causal discovery (used by [[lee-park-2026]]).

## Why it matters for us
- Discrete analogue for our null: **permute agent j's actions within each state stratum**. This keeps p(a_j | s) exactly and destroys only the i–j dependence given s — the precise null of γ(i; j) = 0. Cleaner than a circular shift for same-round CMI.
- Circular shift (plan, H4) still needed for the lagged variant, where within-state permutation would destroy autocorrelation. Compare both. See [[estimation]].
