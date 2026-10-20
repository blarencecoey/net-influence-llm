---
title: "Audit the Whisper: Detecting Steganographic Collusion in Multi-Agent LLMs"
authors: Tailor
venue: arXiv 2510.04303 (v2)
link: https://arxiv.org/abs/2510.04303
code: https://github.com/Ostailor/Steganographic_Collusion (cited in paper; verify)
tags: [mutual-information, calibration, FPR, black-box]
---

# Tailor 2025 (ColludeBench-v0)

## Method
- Detector union: cross-run MI, permutation invariance, watermark variance, fairness acceptance bias, welfare-shift guard.
- MI via Donsker–Varadhan / NWJ neural critics on whitened transcript features, plus a discretised plug-in estimator.
- Union via Holm–Bonferroni (main), Bonferroni, Westfall–Young maxT; e-value martingale for optional stopping.
- **Calibration: 200 honest seeds per task** set null distributions and thresholds; targets FPR 10⁻² and 10⁻³.

## Environments
Pricing duopoly (logit demand), 3-bidder first-price auction, 3-reviewer peer review, external continuous double auction; Gemini 2.5 Flash → Groq Llama 3 transfer.

## Results
- cross_run_mi alone: TPR 0.66 at 10⁻², 0.60 at 10⁻³; ablation table gives 0.12 alone — internally inconsistent.
- Thresholds set on Gemini transfer to Groq within FPR budget.

## Caution
Summary flagged several internal inconsistencies (union TPR claims vs Table 1; Clopper–Pearson bound; run counts). Cite for the **calibration protocol**, not for headline numbers.

## Why it matters for us
- Closest existing "MI as collusion detector on LLM agents" — but MI over transcript features, not actions given state, and no pairwise identification of *which* agents collude.
- Gives a defensible protocol for H4: honest-seed calibration + explicit FPR budget + multiple-testing correction across the 6 ordered pairs (12 directed).
- We should report TPR at a fixed FPR, not just accuracy, so results are comparable.
