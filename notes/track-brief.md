---
title: Official brief for research question 1.4
source: AI Collusion Research Sprint research-question list, as pasted by Clarence on 2026-10-21
tags: [brief, scope]
---

# Q1.4 — Can information-theoretic methods identify colluding pairs?

Copied from the sprint's research-question list. This is the organisers' suggestion, not our plan; [[00-plan]] records where we follow it and where we deviate.

## Starter code

- [[bonjour-2022]]: https://proceedings.mlr.press/v180/bonjour22a.html. It defines pairwise net influence mathematically, but no public author implementation was located. The brief says the statistic is compact enough to implement and validate before applying it to an LLM game.
- [[agrawal-2025]] auction code: https://github.com/andyjliu/llm-agent-collusion. A richer follow-up once the method works.

## Suggested weekend project

1. Implement pairwise net influence and test it for free on scripted iterated Rock-Paper-Scissors with one known coordinating pair.
2. Run a four-agent discrete game with exactly one seeded pair. Compare how well three methods rank the true pair: net influence, ordinary action correlation, and an LLM judge.
3. Under the Markets and Collusion track, treat the Agrawal double auction as the target environment. A dependence statistic validated there doubles as a quantitative *plus factor* for market cases.

## Resources

- Low-to-medium engineering risk; the initial harness should be a few hundred lines.
- Local CPU for the statistic, then 20–40 LLM games of 15–25 rounds.
- A 16 GB laptop is enough.
- Budget: $0 for the scripted test, about $5–50 for the LLM pilot.
