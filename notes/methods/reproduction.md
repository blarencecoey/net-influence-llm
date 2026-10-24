---
title: Reproducing Bonjour et al. 2022 Table 2 (scripted RPS)
tags: [methods, reproduction, positive-control]
---

# Reproduction of [[bonjour-2022]] Table 2

> [claude] Written 2026-10-24 (sprint day 2). Facts about the paper were checked against the PDF (Sec. 5.1, Eqs. 3–7, Table 2). The paper's Appendices A (state spec) and C (4-player RPS) were not readable from this session `[unverified]`. Numbers below are from our runs; regenerate with the commands given.

## What the paper specifies (checked)

- 3 players. A (primary colluder) and C (honest) play uniformly at random. B plays the action that guarantees A a point with probability CP, random otherwise.
- Payoffs: all same → 0; all three present → 1 each; two distinct → players of the winning action get 1.
- γ(i; j) per Eq. 6 (CMI given a fully observable state s), Γ per Eq. 4, detection per Eq. 5 with α = 0.05, "exactly one pair" rule per Algorithm 1.
- CDA = % of iterations detecting the true pair; 1000 iterations per game count.
- Table 2, CP = 0.4: 58.4 / 79.2 / 96.2 / 99.3 % at 100 / 200 / 300 / 400 games. CP = 0.3: 37.1 / 48.3 / 71.0 / 82.8 %.
- In text: CP = 0.2 → 24.3 % at 1000 games; CP = 0.1 → about 8 %; CP = 1 → 100 % at 60 games.

## What the paper does not specify (our choices)

| Choice | Ours | Why |
|---|---|---|
| One "game" | One simultaneous round | Only reading consistent with CDA rising over 100–1000 "games" |
| CP unit | Per round | Text ambiguous (per game vs per move) |
| Log base | Report nats and bits | Not stated; α = 0.05 depends on it |
| State s | **Previous round's joint action** (27 values) | Reproduces Table 2; a constant state does not (below) |

## Results (1000 iterations; joint state in `runs/bonjour_repro_3p_joint`, constant state in `runs/bonjour_repro_3p`)

Command: `python scripts/reproduce_bonjour.py --iters 1000 --state joint` (and `--state none`).

| Games | CP=0.3 paper | ours joint, nats | ours joint, bits | CP=0.4 paper | ours joint, nats | ours joint, bits |
|---|---|---|---|---|---|---|
| 100 | 37.1 | 30.8 | 41.0 | 58.4 | 53.7 | 62.8 |
| 200 | 48.3 | 51.3 | 63.7 | 79.2 | 83.1 | 90.5 |
| 300 | 71.0 | 57.7 | 71.9 | 96.2 | 95.1 | 98.2 |
| 400 | 82.8 | 72.5 | 86.5 | 99.3 | 98.9 | 99.6 |
| 500 | 89.6 | 82.0 | 92.9 | 99.7 | 99.6 | 99.9 |
| 1000 | 100.0 | 96.9 | 99.9 | 100.0 | 100.0 | 100.0 |

- With state = previous joint action, both bases bracket the paper's curve; bits matches CP = 0.3 within ~5 points from 300 games on, and CP = 0.4 within ~12 points everywhere.
- With a single constant state the detector is far stronger than reported (CP = 0.4: 95.6 % at 100 games, nats). So the paper's numbers are consistent with a history-based state, not a memoryless one. This is our inference.
- CP = 0.2 at 1000 games: 15.5 % (nats) / 50.1 % (bits) vs paper 24.3 %. CP = 0.1 stays low (≤ 18 %, falling with N), consistent with "about 8 %".

## Findings worth carrying forward

1. **False alarms under the published rule.** With the joint-action state and no collusion, Algorithm 1 flags some pair in **27.9 % (nats) / 44.6 % (bits) of 100-game runs**, 1.0 % / 6.4 % at 500, 0 % at 1000. The paper does not report a no-collusion false-detection rate. Cause (our inference): plug-in bias ≈ 2·27/N nats per γ at small N, see [[estimation]] §1. → motivates H4.
2. **Fixed α sets a floor, not the data.** At low CP, detection accuracy *falls* as games increase (e.g. CP = 0.2, constant state: 26.9 % at 100 → 8.6 % at 1000). Small-N hits are noise crossing α; with more data Γ converges to a true value below α = 0.05. Our inference; relevant to A5/A6.
3. **State choice changes the answer.** The same detector on the same data goes from ~96 % to ~54 % (CP = 0.4, 100 games) just by conditioning on history. For LLM runs the state must be fixed in advance (pre-registration).

## Scripted 4-player comparison (`runs/scripted4_200r`)

Command: `python scripts/scripted_four_agent.py --games 200 --rounds 200`. Seeded pair (2, 3). Top-1 = true pair ranked first among 6 (chance 0.17), 95 % bootstrap CI over 200 games.

| Condition | NI, no state | NI, joint state | NI joint + MM | lagged NI | correlation |
|---|---|---|---|---|---|
| null (Alg. 1 any-pair rate) | 0.00 | 0.03 | 0.09 | – | – |
| CP 0.2 | 0.92 | 0.32 | 0.32 | 0.17 | 0.93 |
| CP 0.3 | 1.00 | 0.48 | 0.49 | 0.17 | 1.00 |
| CP 0.5 | 1.00 | 0.95 | 0.94 | 0.22 | 1.00 |
| CP 1.0 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 |
| tacit, CP 1.0 | 0.21 | 0.00 | 0.00 | **1.00** | 0.23 |

- With memoryless scripted agents, correlation and NI (no state) are indistinguishable: there is no common cause for NI's subtraction to remove. The scripted game cannot show NI beating correlation; that test needs agents with shared dependence (LLMs, H1). Our inference.
- Tacit (history-only) collusion is invisible to every same-round detector and caught perfectly by lagged NI; lagged NI in turn misses same-round collusion. Clean scripted evidence for H2.
- With the joint state, the tacit assistant's move is a function of the state, so its γ is 0 and the true pair ranks last.
- Miller–Madow raises the null any-pair rate (0.03 → 0.09) without improving top-1 here.
