---
title: Hypothesis Testing Approach to Detecting Collusion in Competitive Environments
authors: Hespanhol, Aswani (UC Berkeley)
venue: arXiv 2003.09967 (venue not confirmed)
link: https://arxiv.org/abs/2003.09967
tags: [hypothesis-testing, equilibrium, pricing]
---

# Hespanhol & Aswani 2020

## Method
- Inverse variational inequality → residuals → Lilliefors (KS) test of H₀: agents play an ε-Nash equilibrium with exponential ε.
- Needs a parametric utility model and observed shocks.

## Results
- 2-agent Bertrand: no false positives N = 10–500; collusion (joint-profit max) rejected for N ≥ 20. Each N run once only.
- Authors: rejecting H₀ is evidence, not proof, of collusion.

## Why it matters for us
- Pre-Bonjour example of framing detection as a calibrated hypothesis test. Contrast: theirs needs a utility model; net influence is model-free but needs discrete actions/states.
- Their single-run-per-N weakness is exactly what the sprint asks us to avoid (report variance across seeds).
