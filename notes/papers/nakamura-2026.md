---
title: "Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems"
authors: Nakamura, Kumar, Das, Abdelnabi, Mahmud, Fioretto, Zilberstein, Bagdasarian
venue: arXiv 2602.15198 (v2, 2026-05-27)
link: https://arxiv.org/abs/2602.15198
code: https://github.com/umass-ai-safety/colosseum
tags: [benchmark, LLM-judge, action-vs-text]
---

# Nakamura et al. 2026

## Setup
- Cooperative MAS as DCOPs (Hospital, Jira, Meeting Scheduling); planning-by-messages then tool-call execution.
- Emergent collusion: give two benign agents a secret channel, no collusive prompt. Prompted collusion: coalition objective λ > 0.
- Metrics: regret, coalition advantage, LLM-judge 0–5 on channel messages (GPT-5.4, T = 0, 3 prompts).

## Findings
- Emergent collusion shows up in both actions and conversations.
- **"Collusion on paper"**: agents plan collusion in text but often act non-collusively.
- Action metrics and transcript judges each miss some cases → use both.

## Why it matters for us
- Justifies comparing net influence against an LLM judge (detector 5 in the plan) and expecting **disagreement**, not one dominating.
- "Collusion on paper" is a concrete failure case for judges that an action-level statistic is immune to — and vice versa (judges can catch planning that never changes actions).
- Their emergent-collusion recipe (secret channel, no instruction) is a cheap extra condition if C2 works early: does net influence fire when collusion is *offered* but not *instructed*?
