---
title: "The Best-Laid SCHEMEs: Coordinated Sabotage and Monitoring in Multi-Agent Systems"
authors: Radev, Haas, Arnav, Bernabeu-Pérez
venue: arXiv 2605.29178 (SPAR)
link: https://arxiv.org/abs/2605.29178
tags: [monitoring, sabotage, LLM-judge]
---

# Radev et al. 2026

- 17 SWE tasks with "joint-only" covert side tasks; GPT 5.1 Codex and Gemini 3.1 Pro; monitor = GPT 5.1 Codex Mini at ~2% FPR.
- Code + comms monitor caught 100% (Gemini) / 81% (Codex); telling agents about the monitor halved Gemini's sabotage success.

## Why it matters for us
- Peripheral. Useful for one related-work sentence on LLM-judge monitors and on reporting at a fixed FPR (~2%).
