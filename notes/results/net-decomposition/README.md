# Net-score decomposition for honest pairs, and an entropy-matched check

> [claude] No new runs. Reads the C0 and C1 null runs directly.

- **Script:** `python scripts/net_decomposition.py "runs/C0_llama*" "runs/C1_llama*" > notes/results/net-decomposition/output.txt`
- For each honest pair: gross dependence γ(i; j) = I(a_i; a_j | s), the third-agent term the net score subtracts, max(max_k γ(k; j), max_k γ(k; i)), and the pair score (their difference), by pair type (C0 Llama–Llama; C1 Llama–Llama, Llama–Mistral, Mistral–Mistral) and state.
- Entropy-matched block: gross γ (pre-registered state) for pairs binned by the lower of the two players' move entropies, to check whether Mistral's lower entropy explains the low cross-family scores.
- Plug-in values, no bias correction. With 4 states, 3×3 actions and N = 200, the plug-in bias is of order (3−1)²·4/(2·200) = 0.04 nats (our arithmetic from the usual Miller–Madow form), so gross γ near 0.04 is consistent with no dependence.
