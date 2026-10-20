---
title: Literature map for Q1.4
updated: 2026-10-20
tags: [index, related-work]
---

# Literature map

Index of `notes/papers/`. Notes, not report prose. Each row links a note with a source link and the claims we may cite.

## Detection paradigms

| Paradigm | Needs | Papers |
|---|---|---|
| Observational stats on actions given state | Discrete action logs, many rounds | [[bonjour-2022]] (CMI, net influence), [[xu-2026]] (residual correlation), [[hespanhol-aswani-2020]] (equilibrium residual test) |
| Info-theoretic coordination measures on LLM agents | Action time series | [[riedl-2026]] (TDMI, PID, surrogates) |
| MI / statistical tests on transcripts | Text, honest calibration runs | [[tailor-2025]], [[ghanem-2026]] (theory only) |
| Causal discovery on actions vs CoT | Price series + reasoning traces | [[lee-park-2026]] (Granger, PCMCI+) |
| Interpretability probes | Open weights, GPUs | [[rose-2026]] (NARCBench) |
| Query the policy | Frozen deterministic policy | [[eschenbaum-meylahn-2026]] |
| LLM judge on messages | Channel transcripts | [[nakamura-2026]], [[agrawal-2025]], [[radev-2026]] |

Background and threat models: [[fish-2024]] (tacit LLM pricing collusion), [[motwani-2024]] (steganographic collusion), [[zeng-rudzicz-2026]] (voluntary uptake of collusion tools), [[guo-2025]] (LLMs fail to randomize in RPS).

Broader loss-of-control framing (why collusion breaks monitor-based control protocols): [[loss-of-control-survey]].

Methods: [[estimation]], [[runge-2018]].

## Answer to "has anyone done this?"

- **Net influence on LLM agents: not found.** No paper among those read cites Bonjour et al. or applies it to LLMs. Rose et al. (the Q1.4 alternative) doesn't cite it either. Searched 2026-10-20; re-check Friday.
- **No public implementation of Bonjour et al. found** — reimplementation needed, as planned.
- Closest: [[tailor-2025]] uses MI on LLM transcripts (not actions given state, no pair identification); [[riedl-2026]] uses MI/PID on LLM actions (coordination, not collusion, no seeded pair); [[xu-2026]] measures same-model dependence (correlation, not MI, no detector of which pair).

## Evidence bearing on the hypotheses

- **H1 (shared priors):** [[xu-2026]] same-model residual correlation +0.053 vs ~0 cross-model, falling with temperature; [[guo-2025]] shared positional biases. Strong prior that H1 holds. Novelty is in measuring it with net influence and showing how calibration handles it.
- **H2 (tacit / history-based):** [[fish-2024]] LLM collusion is tacit; [[eschenbaum-meylahn-2026]] punishment branches hide; [[lee-park-2026]] lagged CI tests on price series. Supports adding the lagged variant.
- **H3 (dose response):** [[bonjour-2022]] Table 2 shows accuracy vs CP and games; reproduce first.
- **H4 (calibration):** [[tailor-2025]] honest-seed calibration; [[riedl-2026]] shift surrogates; [[runge-2018]] local permutation. See [[estimation]] §3 for why permutation and honest-run nulls disagree.
- **Two-colluder assumption:** shared by [[bonjour-2022]] and [[rose-2026]] (Deception Split k = 2). C4 tests it for both families of method.

## Design suggestions from the reading (for Clarence to accept or reject)

1. Keep the state abstraction at ≤ 9 states for 200-round runs ([[estimation]] §1). Decision for the plan's decision log.
2. Add a temperature contrast to C0 (cheap; [[xu-2026]] predicts the false-positive rate moves).
3. Add an option-order shuffle ablation to C0/C1 ([[guo-2025]]).
4. Verify the seeded pair actually colludes before trusting detection on that run ([[zeng-rudzicz-2026]]: some models refuse).
5. Report TPR at fixed FPR (1%, 5%) as well as top-pair accuracy, for comparability with [[tailor-2025]] and [[rose-2026]].
6. Optional emergent condition: offer the private channel without instructing collusion ([[nakamura-2026]]).

## Unread or unverified

- Das et al. 2026, "You Can't Escape Your Own Activations" (arXiv 2609.03035): PDF not machine-readable when checked; known only via [[rose-2026]].
- Other papers on the sprint page not yet read: Keppo et al. 2026, Eschenbaum et al. 2022, Aharon et al. 2026, Rippin et al. 2026, Collina et al. 2025, Bracale Syrnikov et al. 2026, Dhanda 2026, Liu et al. 2026, Tomašev et al. 2026.
- [[xu-2026]] and [[agrawal-2025]] read from abstract/summary; confirm numbers from PDFs before citing.
