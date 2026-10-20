---
title: "Secret Collusion among AI Agents: Multi-Agent Deception via Steganography"
authors: Motwani, Baranchuk, Strohmeier, Bolina, Torr, Hammond, Schroeder de Witt
venue: NeurIPS 2024
link: https://arxiv.org/abs/2402.07510
tags: [steganography, theory, threat-model]
---

# Motwani et al. 2024

## Content
- Defines secret collusion (steganographic multi-agent deception); DecAI setting with monitors.
- CASE evaluation framework; steganographic capability grows with model capability; information-theoretically secure stego is still weak in current models.
- Paraphrasing is an insufficient defence; monitoring messages cannot stop perfectly secure stego.

## Why it matters for us
- Key positioning argument: **perfectly secure steganography hides the message, not the coordinated action.** If colluders change payoff-relevant actions, that dependence is visible in the action stream regardless of how the channel is encoded. Action-level net influence is complementary to channel monitoring.
- Converse limit: if the coordinated payload only shifts actions slightly, CMI is small → see bound in [[ghanem-2026]].
