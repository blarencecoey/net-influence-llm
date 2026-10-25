"""Run double-auction conditions (netinf.envs.auction) and log each seed to runs/<run_id>/.

Usage:
  python scripts/run_auction.py --config configs/auction_a2.yaml [--seeds 0 1 2] [--rounds N] [--dry-run]

- A2 configs run first (positive control first, CLAUDE.md).
- A non-A2 condition with a paid provider is refused unless a completed A2 run with the same model
  set and prompt version passed the positive-control check, or --skip-positive-control-check.
- --dry-run swaps the provider for scripted sellers ($0, no API).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from netinf.envs import auction as au


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", nargs="+", type=Path, required=True)
    ap.add_argument("--seeds", nargs="+", type=int)
    ap.add_argument("--rounds", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-positive-control-check", action="store_true")
    ap.add_argument("--runs-dir", type=Path, default=Path("runs"))
    args = ap.parse_args(argv)

    cfgs = []
    for path in args.config:
        cfg = au.load_config(path)
        cfg["config_file"] = str(path)
        if args.rounds:
            cfg["n_rounds"] = args.rounds
        if args.seeds is not None:
            cfg["seeds"] = args.seeds
        if args.dry_run:
            cfg["provider"] = "scripted"
        au.validate_config(cfg)
        cfgs.append(cfg)
    cfgs.sort(key=lambda c: c["condition"] != "A2")

    total, clients = 0.0, {}
    for cfg in cfgs:
        pc_run = None
        if cfg["condition"] != "A2" and cfg["provider"] not in ("scripted", "fake") \
                and not args.skip_positive_control_check:
            pc_run = au.find_passing_a2(args.runs_dir, au.model_key(cfg))
            if pc_run is None:
                raise RuntimeError(f"positive control first: no passing A2 run for "
                                   f"{au.model_key(cfg)} in {args.runs_dir}")
        ck = (cfg["provider"], cfg.get("cache_dir"), cfg.get("budget_usd"))
        if ck not in clients:
            clients[ck] = au.make_client_for(cfg)
        extra = {"skip_positive_control_check": args.skip_positive_control_check,
                 "positive_control_run": pc_run.name if pc_run else None}
        for seed in cfg["seeds"]:
            m = au.run_one(cfg, seed, clients[ck], args.runs_dir, extra)
            total += m["total_cost_usd"]
            pc = m.get("positive_control")
            print(f"[{m['run_id']}] rounds {m['rounds_completed']}/{m['n_rounds']} "
                  f"completed={m['completed']} cost ${m['total_cost_usd']:.4f} "
                  f"parse_failures {m['parse_failures']} mean_ask {m.get('mean_ask', float('nan')):.2f}"
                  + (f"\n  positive control: match {pc['match_rate_delivered']:.3f} "
                     f"(min {pc['min_match']}) -> {'PASS' if pc['passed'] else 'FAIL'}; pair ask "
                     f"{pc['pair_mean_ask']:.2f} vs honest {pc['honest_mean_ask']:.2f}" if pc else ""))
            if m["stop_reason"] == "budget_exceeded":
                print("budget exceeded: stopping", file=sys.stderr)
                return 2
    print(f"done: total cost ${total:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
