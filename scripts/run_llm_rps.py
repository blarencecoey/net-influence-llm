"""Run LLM (or scripted) 4-player RPS conditions and log each seed to runs/<run_id>/.

Usage:
  python scripts/run_llm_rps.py --config configs/c2.yaml [--seeds 0 1 2] [--rounds N] [--dry-run]
  python scripts/run_llm_rps.py --config configs/dryrun_c0.yaml configs/dryrun_c2.yaml ...

- Several configs may be given; C2 configs always run first (positive control first, CLAUDE.md).
- `p_channel` may be a list (the H3 sweep); each value is a separate run per seed.
- --dry-run swaps the provider for scripted agents ($0, no API), keeping everything else.
- A non-C2 condition with a paid provider is refused unless a completed C2 run for the same model
  config passed the positive-control check, or --skip-positive-control-check is given (recorded).
- Paid providers are refused while the config still holds *_TODO model or price placeholders.
- Token usage and cost are printed after every run and stored in its meta.json.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from netinf.envs import llm_rps as g


def expand(cfg: dict) -> list[dict]:
    p = cfg.get("p_channel")
    return [dict(cfg, p_channel=x) for x in p] if isinstance(p, list) else [cfg]


def report(meta: dict) -> None:
    cost = meta["total_cost_usd"]
    cost_s = f"${cost:.4f}" + ("" if meta["cost_complete"] else " (some calls unpriced)")
    print(f"[{meta['run_id']}] rounds {meta['rounds_completed']}/{meta['n_rounds']}"
          f" completed={meta['completed']} tokens in/out {meta['total_input_tokens']}/"
          f"{meta['total_output_tokens']} cost {cost_s} parse_failures {meta['parse_failures']}"
          + (f" channel_rate {meta['channel_delivery_rate']:.2f}"
             if "channel_delivery_rate" in meta else ""))
    pc = meta.get("positive_control")
    if pc:
        print(f"  positive control ({meta['condition']}): primary {pc['primary_mean']:.3f} vs "
              f"honest {pc['honest_mean']:.3f} (assistant {pc['assistant_mean']:.3f}), "
              f"one-sided Fisher p = {pc['p_value']:.2g} -> "
              f"{'PASS' if pc['passed'] else 'FAIL'}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", nargs="+", type=Path, required=True)
    ap.add_argument("--seeds", nargs="+", type=int)
    ap.add_argument("--rounds", type=int)
    ap.add_argument("--dry-run", action="store_true", help="scripted agents, no API calls")
    ap.add_argument("--skip-positive-control-check", action="store_true")
    ap.add_argument("--runs-dir", type=Path, default=Path("runs"))
    args = ap.parse_args(argv)

    cfgs = []
    for path in args.config:
        cfg = g.load_config(path)
        cfg["config_file"] = str(path)
        if args.rounds:
            cfg["n_rounds"] = args.rounds
        if args.seeds is not None:
            cfg["seeds"] = args.seeds
        if args.dry_run:
            cfg["provider"] = "scripted"
        cfgs += expand(cfg)
    cfgs.sort(key=lambda c: c["condition"] != "C2")  # stable: C2 first
    for cfg in cfgs:
        g.validate_config(cfg)  # fail before spending anything

    summary, clients = [], {}
    for cfg in cfgs:
        pc_run = g.check_positive_control_first(cfg, args.runs_dir,
                                                args.skip_positive_control_check)
        ck = (cfg["provider"], cfg.get("cache_dir"), cfg.get("budget_usd"))
        if ck not in clients:  # one client (and budget) per provider setup per invocation
            clients[ck] = g.make_client_for(cfg)
        extra = {"skip_positive_control_check": args.skip_positive_control_check,
                 "positive_control_run": pc_run.name if pc_run else None}
        for seed in cfg["seeds"]:
            meta = g.run_one(cfg, seed, clients[ck], args.runs_dir, extra)
            report(meta)
            summary.append(meta)
            if meta["stop_reason"] == "budget_exceeded":
                print("budget exceeded: stopping all runs", file=sys.stderr)
                return 2

    tot = sum(m["total_cost_usd"] for m in summary)
    print(f"done: {len(summary)} runs, total cost ${tot:.4f}, "
          f"tokens in/out {sum(m['total_input_tokens'] for m in summary)}/"
          f"{sum(m['total_output_tokens'] for m in summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
