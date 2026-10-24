---
title: Estimation, bias and thresholds for net influence
tags: [methods, sample-size, null]
---

# Estimation notes

Pre-sprint working notes. Standard results, written out so the state-abstraction choice is made with numbers. Verify each against a simulation on Friday before relying on it.

## 1. Plug-in CMI bias (Miller–Madow)

Plug-in entropy is biased low by about (m − 1) / (2N) nats for m categories. For MI of two variables with |X|, |Y| categories and N samples:

    E[Î] − I ≈ (|X| − 1)(|Y| − 1) / (2N)

For conditional MI over |S| visited states, summing per-stratum bias (N_s ≈ N/|S|):

    bias(γ̂) ≈ |S| (|X| − 1)(|Y| − 1) / (2N)

RPS has |X| = |Y| = 3, so **bias ≈ 2|S| / N nats**. Bonjour's threshold is α = 0.05.

Formula vs a quick simulation (independent uniform agents, uniform states, 200 reps; scratch check on 2026-10-20, not committed code). Values are mean γ̂ in nats:

| State abstraction (4 players) | \|S\| | N = 200 formula / sim | N = 1000 formula / sim |
|---|---|---|---|
| None (memoryless) | 1 | 0.010 / 0.009 | 0.002 / 0.002 |
| Pair's own last actions (3×3), or last outcome per agent | 9 | 0.090 / 0.110 | 0.018 / 0.018 |
| Last joint action, all 4 players | 81 | 0.81 / **0.34** | 0.16 / 0.21 |

The formula fails when strata are sparse (81 states × 200 rounds ≈ 2.5 rounds per state), but the simulated bias is still ~7× α.

Takeaways:
- With the full last joint action as state and ~200 LLM rounds, **bias alone is several times α**. Plain Bonjour thresholding is meaningless there.
- Net influence subtracts a term with the same expected bias, so bias roughly cancels in Γ — but the variance does not, and the max over k adds positive bias to the subtracted term (makes Γ smaller). Expect Γ to be noisy and slightly negative under H₀.
- Answers the plan's open question on state abstraction: **keep |S| ≤ 9** for 200-round LLM runs, or pool seeds.

## 2. Analytic null (G-test)

Under conditional independence with iid rounds, 2N · γ̂ (nats) ~ χ² with df = |S|(|X| − 1)(|Y| − 1). Gives a p-value per pair for free, and mean df/(2N) matches the bias above.
- Breaks when rounds are not iid (LLM agents conditioned on history) → use a permutation null as the main threshold, χ² as a sanity check.

## 3. Permutation nulls

- **Within-state permutation** (discrete analogue of [[runge-2018]]'s local permutation): shuffle a_j among rounds with the same s. Preserves p(a_j | s) exactly; null of γ(i; j) = 0. Best for same-round CMI.
- **Circular shift** of agent j's series (plan, H4; cf. [[riedl-2026]] time-shift surrogates): preserves j's autocorrelation; needed for the lagged variant.
  > [claude] 2026-10-24: valid for γ(i; j) = 0, but not for the *net* pair score. Shifting j makes j independent of every agent, while i's dependence on third agents stays in Γ(j; i), so the null sits below zero and honest pairs are rejected under shared priors (per-pair P(p ≤ 0.05) = 0.57 for netinf, 0.22 for lagged_netinf, in synthetic checks). Removed from the analysis pipeline; see limitation B18 and `scripts/check_shift_null.py`.
- **Honest-run calibration** ([[tailor-2025]]): thresholds from C0 runs of the same model mix. Only option that captures shared-prior dependence ([[xu-2026]]): permutation nulls treat shared priors as signal, honest-run nulls treat them as noise. This difference *is* H1 vs H4 — report both.

## 4. Multiple testing

4 agents → 6 unordered pairs, 12 directed Γ. Bonjour's "exactly one pair passes" rule is an implicit correction. If using p-values, use Holm across pairs or a max-statistic null (maxT, cf. Westfall–Young in [[tailor-2025]]).

## 5. Lagged variant (H2)

Conditional transfer entropy from i to j:

    TE(i → j) = I(a_j,t ; a_i,t−1 | s_t, a_j,t−1)

Conditioning on a_j,t−1 adds a factor 3 to |S|. Keep the base state tiny (none or own last action), or bias swamps signal (Section 1).

## 6. More than two colluders (C4)

- Bonjour suggests co-information (Bell 2003) on the lattice. Interaction information over three agents can be negative (synergy) or positive (redundancy); sign is not interpretable as "collusion" by itself.
- O-information (Rosas et al. 2019, https://arxiv.org/abs/1902.11239) is the standard multivariate extension separating redundancy- vs synergy-dominated triplets. Data-hungry: triple joint has 27 cells per state.
- [[riedl-2026]]'s triplet-beyond-best-pair test is a practical alternative.

## 7. Detectability floor

Γ is built from a KL divergence between joint and product policies. By Pinsker (cf. [[ghanem-2026]]), if colluders keep γ ≤ ε, no test on the same observations does much better than chance. Bonjour's CP = 0.1 failure is this floor in practice.
