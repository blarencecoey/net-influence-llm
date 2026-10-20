# net-influence-llm

Detecting collusion between LLM agents with information-theoretic net influence: does Bonjour et al.'s detector survive shared priors and tacit coordination?

Entry for the [Apart Research AI Collusion Research Sprint](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25) (Oct 23–25, 2026), Track 1, research question 1.4.

## Research question

[Bonjour, Aggarwal & Bhargava (UAI 2022)](https://proceedings.mlr.press/v180/bonjour22a.html) detect colluding pairs in multi-agent games using **pairwise net influence**: conditional mutual information between two agents' actions given the state, minus the largest influence any other agent has. It has not been applied to LLM agents.

Its core assumption is that honest agents act independently given the state. We test two ways LLM agents may break it:

1. **Shared priors.** Copies of the same model share habits, which may produce false positives between same-family agents that are not colluding.
2. **Tacit collusion.** Coordination carried through the game history (reacting to a rival's last move) does not show up as same-round mutual information, so the published metric may miss it.

## Research approach

### 1. Overall pipeline

Each stage gates the next: nothing runs on LLM data until the estimator reproduces the published results, and no stress test is trusted until the positive control fires.

```mermaid
flowchart LR
    A["📚 Literature<br/>16 sources"] --> B["🎯 Gap + hypotheses<br/>H1–H4"]
    B --> C["🧮 Reimplement<br/>net influence"]
    C --> D{"Reproduces<br/>Bonjour Table 2?"}
    D -- no --> C
    D -- yes --> E["✅ Positive control<br/>C2 seeded pair"]
    E --> F{"Seeded pair<br/>detected?"}
    F -- no --> E
    F -- yes --> G["🔬 Stress tests<br/>C0 · C1 · C3 · sweep"]
    G --> H["➕ Extensions<br/>lagged · calibrated · C4"]
    H --> I["📝 Report +<br/>limitations appendix"]

    classDef lit fill:#e8eefc,stroke:#4a6cd4,color:#1a2a55
    classDef build fill:#fff4e0,stroke:#d4912a,color:#4a3000
    classDef gate fill:#fde8e8,stroke:#c94a4a,color:#4a1010
    classDef out fill:#e6f5ea,stroke:#3a9a5a,color:#0f3a1d
    class A,B lit
    class C,E,G,H build
    class D,F gate
    class I out
```

### 2. From sources to hypotheses

Papers are grouped by the role they play; each arrow shows which hypothesis a group of papers motivates. The detector and its alternatives define the gap the whole project fills. Full notes are in [`notes/papers/`](notes/papers/), indexed in [`notes/lit-review.md`](notes/lit-review.md).

```mermaid
flowchart LR
    P0["<b>Detector</b><br/>Bonjour et al. 2022<br/><i>net influence, assumes 2 colluders</i>"]
    P4["<b>Alternative detectors</b><br/>Rose et al. 2026: activation probes, also k = 2<br/>Nakamura et al. 2026 · Agrawal et al. 2025: LLM judges"]
    P1["<b>Shared priors</b><br/>Xu et al. 2026: same-model coupling +0.053 vs ~0<br/>Guo et al. 2025: LLMs fail to randomize in RPS"]
    P2["<b>Tacit / history-based collusion</b><br/>Fish et al. 2024 · Eschenbaum & Meylahn 2026<br/>Lee & Park 2026"]
    P3["<b>Estimation and nulls</b><br/>Riedl 2026 · Runge 2018 · Tailor 2025"]
    P5["<b>Detectability limits</b><br/>Ghanem 2026 · Motwani et al. 2024"]

    GAP(["<b>Gap</b><br/>No prior application of net influence<br/>to LLM agents; no public implementation"])

    H1["<b>H1 Shared priors</b><br/>same-family honest pairs → false positives"]
    H2["<b>H2 Tacit collusion</b><br/>same-round metric misses it,<br/>lagged variant catches it"]
    H3["<b>H3 Dose response</b><br/>net influence rises with collusion strength"]
    H4["<b>H4 Calibration</b><br/>calibrated null beats fixed α = 0.05"]
    A1["<b>Two-colluder assumption</b><br/>tested in C4 (stretch)"]
    LIM[["Limitations & dual-use tracker"]]

    P0 --> GAP
    P4 --> GAP
    P1 --> H1
    P2 --> H2
    P0 --> H3
    P3 --> H4
    P0 --> A1
    P4 --> A1
    P5 --> LIM

    classDef src fill:#e8eefc,stroke:#4a6cd4,color:#1a2a55
    classDef gap fill:#f3e8fc,stroke:#8a4ad4,color:#2e1050
    classDef hyp fill:#fff4e0,stroke:#d4912a,color:#4a3000
    classDef lim fill:#fde8e8,stroke:#c94a4a,color:#4a1010
    class P0,P1,P2,P3,P4,P5 src
    class GAP gap
    class H1,H2,H3,H4,A1 hyp
    class LIM lim
```

### 3. From hypotheses to the preliminary experiment

Solid arrows are the planned steps. Dashed arrows are design choices suggested by the reading and still to be confirmed (see "Design suggestions" in [`notes/lit-review.md`](notes/lit-review.md)).

```mermaid
flowchart TB
    subgraph S0["Step 0 · Scripted RPS reproduction · CPU, $0"]
        R1["3- and 4-player RPS<br/>assistant colluder, CP sweep"]
        R2["Match Bonjour Table 2<br/>e.g. CP 0.4 → ~79% at 200 games"]
        R1 --> R2
    end

    subgraph S1["Step 1 · LLM positive control"]
        L1["4-player RPS, ~200 rounds × 5 seeds<br/>C2: seeded pair with private channel"]
        L2["Check the pair really colluded<br/>partner win rate above chance"]
        L3["Compare detectors on the true pair<br/>net influence · correlation · LLM judge"]
        L1 --> L2 --> L3
    end

    subgraph S2["Step 2 · Stress tests"]
        T1["C0 / C1: honest agents<br/>same-family vs cross-family"]
        T2["C3: strategy agreed before game,<br/>no channel"]
        T3["C2 sweep: channel delivered<br/>with p = 0.1 · 0.3 · 0.5 · 1.0"]
    end

    E1["Bias ≈ 2·|S|/N nats<br/>→ keep state ≤ 9 values"]
    E2["Temperature contrast<br/>option-order shuffle"]
    E3["Lagged net influence<br/>conditional transfer entropy"]
    E4["Calibrated threshold<br/>circular-shift or honest-run null,<br/>frozen on calibration split"]

    H1["H1"] --> T1
    H2["H2"] --> T2
    H3["H3"] --> T3
    H4["H4"] --> E4

    R2 --> L1
    L3 --> S2
    E1 -.-> L1
    E2 -.-> T1
    E3 -.-> T2
    E4 --> S2

    classDef step fill:#fff4e0,stroke:#d4912a,color:#4a3000
    classDef hyp fill:#e8eefc,stroke:#4a6cd4,color:#1a2a55
    classDef design fill:#f3e8fc,stroke:#8a4ad4,color:#2e1050,stroke-dasharray: 4 3
    class R1,R2,L1,L2,L3,T1,T2,T3,E4 step
    class H1,H2,H3,H4 hyp
    class E1,E2,E3 design
```

## Planned components

| Component | Status |
|---|---|
| Net influence estimator (Bonjour et al. Eq. 3–5) | Not started |
| Bias-corrected estimator (Miller–Madow) | Not started |
| Lagged variant (conditional transfer entropy) | Not started |
| Calibrated threshold (circular-shift null) | Not started |
| Scripted 3/4-player Rock-Paper-Scissors reproduction | Not started |
| LLM agent harness (4-player RPS, seeded colluding pair) | Not started |
| Discrete-price market environment (stretch) | Not started |

## Layout

```
src/netinf/     detector, environments, LLM agents
configs/        experiment configs (one per condition)
scripts/        entry points for running experiments
tests/          unit tests for the estimators
runs/           raw run outputs (gitignored)
notes/          research notes; open this folder as an Obsidian vault
  papers/       one note per source
  methods/      estimator and statistics notes
  lit-review.md index of sources and evidence per hypothesis
  limitations-and-ethics.md   tracker for the required appendix
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # add API keys
pytest
```

## Prior work disclosure

See [PRIOR_WORK.md](PRIOR_WORK.md). Everything committed before the sprint start (Fri Oct 23, 2026) is scaffolding only.

## Citation

Bonjour, T., Aggarwal, V. & Bhargava, B. (2022). Information theoretic approach to detect collusion in multi-agent games. *Proceedings of UAI 2022*, PMLR 180:223–232.
