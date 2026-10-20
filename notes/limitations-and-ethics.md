---
title: Limitations and dual-use / ethics tracker
tags: [limitations, ethics, appendix]
---

# Limitations and dual-use tracker

Living list feeding the required report appendix ("Limitations and Dual-Use / Ethical Considerations"). The sprint asks for: what the result does and does not establish, and any way the setup or findings could make real-world collusion easier to carry out or harder to detect.

Add a line whenever a run, bug or reading reveals one. Mark status: `open` (applies), `mitigated` (with how), `tested` (with run).

## A. Method limitations (inherited from net influence)

| # | Limitation | Source | Status |
|---|---|---|---|
| A1 | Assumes exactly two colluders | [[bonjour-2022]] | open; C4 stretch |
| A2 | Assumes honest agents are conditionally independent given state; shared LLM priors violate it | [[bonjour-2022]], [[xu-2026]], [[guo-2025]] | open; H1 |
| A3 | Same-round CMI misses coordination carried through history (tacit collusion, punishment) | [[fish-2024]], [[eschenbaum-meylahn-2026]] | open; H2 lagged variant |
| A4 | Needs discrete actions and a small state space; plug-in bias ≈ 2\|S\|/N nats in RPS | [[estimation]] §1 | open |
| A5 | No theory for α; fixed α = 0.05 not calibrated | [[bonjour-2022]] | open; H4 |
| A6 | Detectability floor: weak collusion (small CMI) is undetectable by any test on the same data | [[ghanem-2026]], Bonjour CP = 0.1 | open |
| A7 | Measures statistical dependence, not intent, harm or causation | [[xu-2026]], [[eschenbaum-meylahn-2026]] | open |
| A8 | Flags beneficial coordination as readily as collusion | [[riedl-2026]] | open |
| A9 | Multiple testing across 12 directed pairs inflates false positives without correction | [[estimation]] §4 | open |

## B. Experimental-design limitations

| # | Limitation | Status |
|---|---|---|
| B1 | Collusion is instructed/seeded, not emergent; detection of emergent collusion is not established | open |
| B2 | Toy game (RPS), not a market; transfer to pricing/auctions untested unless the stretch market runs | open |
| B3 | Small budget → ~200 rounds × 5 seeds; few models; results may not generalise across model families | open |
| B4 | LLM randomisation is poor and prompt-sensitive; results depend on prompt wording and temperature | open |
| B5 | Colluder compliance varies by model; a non-complying "colluder" silently weakens the positive control | open; verify per run |
| B6 | Adaptive adversary not tested: colluders don't know the detector | open |
| B7 | LLM-judge baseline depends on the judge model and prompt | open |

## C. Dual-use and ethical considerations

| # | Concern | Mitigation / stance |
|---|---|---|
| C1 | Publishing a detector and its thresholds tells colluders what to avoid: keep same-round CMI under the threshold, move coordination into lags not tested, spread it across sessions, or add more than two colluders | Report detector blind spots as findings for defenders; do not publish optimised evasion strategies or prompts |
| C2 | The seeded-collusion prompts are a recipe for eliciting collusion | Low uplift (instructed collusion in a toy game; similar recipes are public in [[rose-2026]], [[nakamura-2026]], [[agrawal-2025]]); release prompts for reproducibility, no tuning for stealth |
| C3 | False positives from shared priors could wrongly implicate operators who merely run the same model | Report same-family false-positive rates prominently; frame output as a screen requiring further evidence, not proof (cf. [[xu-2026]], [[hespanhol-aswani-2020]]) |
| C4 | Over-trust: a "no collusion detected" result could be read as a clean bill of health | State the detectability floor (A6) and the untested channels (A3, B6) explicitly |
| C5 | Surveillance creep: pairwise dependence monitoring could be applied to people or legitimate cooperation | Scope the claim to AI agents in competitive settings |
| C6 | No human subjects, no personal data; API use within provider terms; keys kept out of the repo | n/a |

## D. What the result will and won't establish (fill in after runs)

- Establishes:
- Does not establish:
