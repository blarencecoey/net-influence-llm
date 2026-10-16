---
title: Information theoretic approach to detect collusion in multi-agent games
authors: Bonjour, Aggarwal, Bhargava
venue: UAI 2022, PMLR 180:223-232
link: https://proceedings.mlr.press/v180/bonjour22a.html
pdf: https://proceedings.mlr.press/v180/bonjour22a/bonjour22a.pdf
---

# Bonjour et al. 2022

## Method

- **Individual influence** γ(i; j): conditional MI between i's and j's actions given the joint state, against the baseline that each acts only on its own observed state (Eq. 3). Fully observable simultaneous games: Eq. 6, symmetric in i and j.
- **Net influence** Γ(i; j) = γ(i; j) − max over other agents k of γ(k; j) (Eq. 4). Not symmetric.
- **Detection:** collusion between i and j if both Γ(i; j) and Γ(j; i) ≥ α (Eq. 5). α = 0.05 in all experiments.
- **Estimation:** plug-in probabilities from counts (hash table).
- Sequential games: only count cases where j acts after i.

## Experiments

- 3-player iterated RPS (4-player in appendix). Assistant collusion: B plays the move guaranteeing A a point with probability CP. Also DDQN-trained colluders.
- 3-player Leduc Hold'em. Association collusion (colluders see each other's cards); RL colluders with high or near-zero payoff.

## Results

- Detects CP > 0.2 at 1000 games. CP = 0.1 stays around 8% accuracy even with more data.
- Stronger collusion needs fewer games; Γ appears to track collusion strength.
- Detects low-payoff collusion that payoff analysis alone would miss.

## Stated limitations

- Exactly two colluders. Suggests co-information for more.
- No theory for the threshold α.
- Collusion is hand-crafted or RL-trained; no public dataset.

## Why it matters for us

- Core assumption: honest agents are conditionally independent given the state. Shared LLM priors and coarse state abstraction may violate it → [[00-plan]] H1.
- If the state includes past actions, reacting to a rival's last move is part of each agent's own policy and adds no MI → tacit collusion invisible → H2.
- No public implementation; must reimplement and validate against Fig. 3 and Table 2.
