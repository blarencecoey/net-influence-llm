"""Reproduce Bonjour et al. (2022) Table 2: collusion detection accuracy (CDA) in scripted RPS.

Paper setup (Sec. 5.1): 3 players; A random, C random, B assistant colluder with probability CP;
alpha = 0.05; CDA = % of iterations where Algorithm 1 returns exactly the true pair; 1000 iterations
per number of games.

Our reading where the paper is silent: one "game" = one simultaneous round; CP applied per round;
log base is not stated, so both nats and bits are reported. The RPS state is defined in the paper's
Appendix A, which we could not read; `--state joint` (previous round's joint action, 27 states for
3 players) is our inference and is the setting that matches Table 2. `--state none` (single
constant state) gives a much more powerful detector than the paper reports.

Usage:
    python scripts/reproduce_bonjour.py                # full run (1000 iterations)
    python scripts/reproduce_bonjour.py --iters 200    # quicker
Outputs go to runs/<timestamp>_bonjour_repro/.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np

from netinf import detector as d
from netinf.envs import rps

# Bonjour et al. 2022, Table 2 (manual assistant collusion), CDA in %
PAPER_TABLE2 = {
    0.3: [37.1, 48.3, 71.0, 82.8, 89.6, 94.6, 97.8, 98.8, 99.4, 100.0],
    0.4: [58.4, 79.2, 96.2, 99.3, 99.7, 99.9, 100.0, 100.0, 100.0, 100.0],
}
GAMES = list(range(100, 1001, 100))


def make_states(a: np.ndarray, kind: str) -> np.ndarray | None:
    return None if kind == "none" else rps.previous_joint_action_state(a)


def cda(cp: float, n_games: int, iters: int, base: float, n_players: int, seed: int, state: str) -> float:
    rng = np.random.default_rng(seed)
    cfg = rps.RPSConfig(n_players=n_players, primary=0, assistant=1, cp=cp)
    hits = 0
    for _ in range(iters):
        a, _ = rps.simulate(cfg, n_games, rng)
        hits += d.detect_pair(a, make_states(a, state), alpha=0.05, base=base) == (0, 1)
    return 100.0 * hits / iters


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--players", type=int, default=3)
    ap.add_argument("--state", choices=["joint", "none"], default="joint")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    out = args.out or Path("runs") / f"{time.strftime('%Y%m%d-%H%M%S')}_bonjour_repro_{args.players}p_{args.state}"
    out.mkdir(parents=True, exist_ok=True)
    config = vars(args) | {"out": str(out), "games": GAMES, "alpha": 0.05,
                           "python": platform.python_version(), "numpy": np.__version__}
    (out / "config.json").write_text(json.dumps(config, indent=2))

    rows = []
    for base_name, base in [("nats", np.e), ("bits", 2.0)]:
        for cp in [0.1, 0.2, 0.3, 0.4, 1.0]:
            for k, n in enumerate(GAMES):
                acc = cda(cp, n, args.iters, base, args.players,
                          seed=args.seed + 1000 * k + int(cp * 100), state=args.state)
                paper = PAPER_TABLE2.get(cp, [None] * len(GAMES))[k]
                rows.append({"base": base_name, "cp": cp, "games": n, "cda": acc, "paper": paper})
                print(f"{base_name} cp={cp} games={n}: {acc:.1f}%  (paper {paper})", flush=True)

    # no-collusion false-detection rate
    for base_name, base in [("nats", np.e), ("bits", 2.0)]:
        for n in [100, 500, 1000]:
            rng = np.random.default_rng(args.seed + n)
            cfg = rps.RPSConfig(n_players=args.players, assistant=None)
            fp = 0
            for _ in range(args.iters):
                a = rps.simulate(cfg, n, rng)[0]
                fp += d.detect_pair(a, make_states(a, args.state), base=base) is not None
            rows.append({"base": base_name, "cp": 0.0, "games": n, "cda": None,
                         "false_detection": 100.0 * fp / args.iters, "paper": None})
            print(f"{base_name} no collusion games={n}: any pair flagged {100*fp/args.iters:.1f}%")

    (out / "results.json").write_text(json.dumps(rows, indent=2))

    # markdown comparison table for the paper's CP values
    lines = ["| games | " + " | ".join(f"CP={cp} {b}" for cp in (0.3, 0.4) for b in ("paper", "nats", "bits")) + " |",
             "|---" * 7 + "|"]
    for n in GAMES:
        cells = []
        for cp in (0.3, 0.4):
            get = lambda b: next(r["cda"] for r in rows if r["base"] == b and r["cp"] == cp and r["games"] == n)
            paper = PAPER_TABLE2[cp][GAMES.index(n)]
            cells += [f"{paper:.1f}", f"{get('nats'):.1f}", f"{get('bits'):.1f}"]
        lines.append(f"| {n} | " + " | ".join(cells) + " |")
    (out / "table2_comparison.md").write_text("\n".join(lines) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, cp in zip(axes, (0.3, 0.4)):
        ax.plot(GAMES, PAPER_TABLE2[cp], "k--o", label="Bonjour et al. Table 2")
        for b, style in (("nats", "-s"), ("bits", "-^")):
            ys = [next(r["cda"] for r in rows if r["base"] == b and r["cp"] == cp and r["games"] == n) for n in GAMES]
            ax.plot(GAMES, ys, style, label=f"ours ({b})")
        ax.set_title(f"CP = {cp}")
        ax.set_xlabel("number of games")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("collusion detection accuracy (%)")
    axes[0].legend()
    fig.suptitle(f"Bonjour et al. Table 2 vs ours ({args.players}-player RPS, state={args.state}, {args.iters} iterations)")
    fig.tight_layout()
    fig.savefig(out / "table2_reproduction.png", dpi=150)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
