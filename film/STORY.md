# Story

**Question the film answers (viewer's words):** "How would you even tell if two AI agents are secretly teaming up, and does the 2022 method still work on LLMs?"

**Hook (the belief that turns out wrong):** "If two agents' moves line up, they must be colluding." Copies of the same model line up without colluding (honest twins), and the published threshold flags them.

**Metaphor:** none. The film shows the real game (4-player Rock-Paper-Scissors) and the real statistic (influence minus the best rival explanation), drawn as bars.

## Must-know
1. Collusion = secret coordination that helps the colluders at the others' expense. In our game: one agent (B) throws the move that lets its partner (A) win.
2. It matters beyond games (auctions, pricing, trading); the question is whether you can catch it from moves alone.
3. Net influence (Bonjour et al., UAI 2022): how much one agent's move tells you about another's given the state, minus the most any other agent explains. Flag a pair if it is ≥ 0.05 in both directions.
4. We rebuilt it and matched the paper's scripted results; it found a seeded Llama pair in 5/5 runs.
5. Twist: honest copies of the same model share habits. The published rule flagged 40/55 honest mixed-family games, top pair the same-model twins in 98 % of runs. A threshold set from honest games cuts false alarms from 45 % to 0.9 % (cross-validated, target 1 %).
6. Blind spots: a plan agreed before the game shows only one move later (lagged variant 20/20 vs same-round 12/20); three colluders score exactly 0.
7. It is a screen, not proof.

## Cut list (true, but stays out)
- Plug-in bias formula, nats vs bits, state abstractions (`prev_n_distinct`, `prev_joint`).
- H3 dose-response sweep, LLM-judge and correlation baselines, mixed-family C2 runs.
- Circular-shift null (H4a), C3 v3 inverse-rule finding, Miller–Madow.
- Cost per run.

## Arc (75 s)
| Beat | % | Seconds | Scenes |
|---|---|---|---|
| Question | 0–10 | 0–7 | S01 |
| Model | 10–35 | 7–24 (+ S04 to 36) | S02, S03, S04 |
| Proof | 35–75 | 36–60 | S05, S06 |
| Turn | 75–90 | 60–68 | S07 |
| Payoff | 90–100 | 68–75 | S08 |
