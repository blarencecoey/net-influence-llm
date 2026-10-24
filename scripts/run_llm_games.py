"""Run LLM RPS games for one condition config.

Usage:
    python scripts/run_llm_games.py configs/c2_seeded.yaml --games 5 --backend mock      # free dry run
    python scripts/run_llm_games.py configs/c2_seeded.yaml --games 5 --max-cost 3 --parallel 5  # real

Writes runs/<timestamp>_<config name>/ with config.yaml, one game_<seed>.jsonl per game (header with
seats, models, roles and system prompts; every round with raw model text and cost; footer with
totals) and summary.json. Stops starting new games once --max-cost (USD) is reached.

Positive control rule (CLAUDE.md): run the seeded config first and check the pair colluded
(`scripts/analyze_llm_runs.py` reports the primary's win rate and the assistant's compliance).
"""

from __future__ import annotations

import argparse
import json
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from dotenv import load_dotenv

from netinf.agents.backends import MockBackend, OpenRouterBackend
from netinf.envs.llm_rps import GameConfig, play_game


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("--games", type=int, default=5)
    ap.add_argument("--seed0", type=int, default=0, help="first game seed; games use seed0..seed0+games-1")
    ap.add_argument("--rounds", type=int, default=None, help="override config rounds")
    ap.add_argument("--channel-p", type=float, default=None, help="override config channel_p")
    ap.add_argument("--backend", choices=["openrouter", "mock"], default="openrouter")
    ap.add_argument("--max-cost", type=float, default=5.0, help="USD cap across this invocation")
    ap.add_argument("--parallel", type=int, default=4, help="games run at once (each makes up to 4 concurrent calls)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    load_dotenv()
    raw = yaml.safe_load(args.config.read_text())
    if args.rounds is not None:
        raw["rounds"] = args.rounds
    if args.channel_p is not None:
        raw["channel_p"] = args.channel_p
        raw["name"] = f"{raw['name']}_p{args.channel_p}"
    cfg = GameConfig(**raw)

    out = args.out or Path("runs") / f"{time.strftime('%Y%m%d-%H%M%S')}_{cfg.name}{'_mock' if args.backend == 'mock' else ''}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.yaml").write_text(yaml.safe_dump(raw | {"_backend": args.backend, "_games": args.games,
                                                            "_seed0": args.seed0}))
    shutil.copy(Path(__file__).resolve().parents[1] / "src/netinf/agents/prompts.py", out / "prompts.py")

    backend = MockBackend(seed=args.seed0) if args.backend == "mock" else OpenRouterBackend()
    lock = threading.Lock()
    state = {"spent": 0.0, "done": []}

    def run_one(seed):
        with lock:
            if state["spent"] >= args.max_cost:
                return None  # cap checked at game start; games already running finish
        t0 = time.time()
        r = play_game(cfg, backend, seed, out / f"game_{seed}.jsonl")
        rec = {"seed": seed, "cost": r.cost, "calls": r.n_calls, "parse_fail": r.n_parse_fail,
               "fallback": r.n_fallback, "true_pair": r.true_pair, "seconds": round(time.time() - t0, 1)}
        with lock:
            state["spent"] += r.cost
            state["done"].append(rec)
            print(f"game {seed}: ${r.cost:.4f}, {r.n_calls} calls, reask {r.n_parse_fail}, "
                  f"fallback {r.n_fallback}, {rec['seconds']}s (total ${state['spent']:.4f})", flush=True)
        return rec

    seeds = range(args.seed0, args.seed0 + args.games)
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        results = list(ex.map(run_one, seeds))
    skipped = [s for s, r in zip(seeds, results) if r is None]
    if skipped:
        print(f"cost cap ${args.max_cost} reached; skipped seeds {skipped}")
    spent, done = state["spent"], sorted(state["done"], key=lambda r: r["seed"])
    (out / "summary.json").write_text(json.dumps({"games": done, "total_cost": spent,
                                                  "skipped_seeds": skipped}, indent=2))
    print(f"wrote {out}  total ${spent:.4f}")


if __name__ == "__main__":
    main()
