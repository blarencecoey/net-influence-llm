---
title: Voluntary Collusion in Competing LLM Agents with Secret Tools
authors: Zeng, Rudzicz
venue: arXiv 2605.27593 (v1, 2026-05-26)
link: https://arxiv.org/abs/2605.27593
tags: [elicitation, propensity]
---

# Zeng & Rudzicz 2026

## Setup and findings
- Agents offered a secret channel or secret hint, explicitly described as unfair; must accept and pick a partner who also accepts.
- Liar's Bar (competitive bluffing) and an LLM port of Melting Pot Cleanup.
- 12 models. Most 7B/70B accept the channel near 100%; Qwen2.5-72B and Claude Sonnet 4.5 at 0%.
- Unfairness labels don't deter; only explicit ethical framing reduces uptake.

## Why it matters for us
- A more realistic way to seed collusion than instructing it: **offer** the channel (cf. [[nakamura-2026]]).
- Warns that refusal varies by model: if a chosen model refuses the C2 prompt, the positive control silently fails. **Verify the seeded pair actually colludes** (e.g. partner's win rate above chance) before trusting any detector result on that run.
