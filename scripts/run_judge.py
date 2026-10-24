"""Run the LLM-judge baseline on run directories and write judge.json into each.

Usage:
  python scripts/run_judge.py runs/C2_* [runs/C0_* ...]
  python scripts/run_judge.py --dry-run runs/C2_...   # print the prompt, no API

- Judge model, provider, prices, cache dir and budget come from --config (default
  configs/base.yaml, key `judge_model`); --model overrides. A paid provider is refused unless the
  judge model has a numeric price there.
- The judge sees actions only by default (detector 5 in notes/00-plan.md); --with-payoffs adds the
  payoff columns. It never sees prompts, roles or channel messages (src/netinf/judge.py).
- --max-tokens defaults to 2000: Claude Sonnet 5.5 via OpenRouter spends hidden reasoning tokens
  inside the output budget (at 400 a 95-character reply cost 396 output tokens, and replies on
  another run came back empty), so a small cap reads as a parse failure.
- Runs that already have judge.json are skipped unless --overwrite.
- analysis.load_run reads judge.json, so scripts/analyze_runs.py picks the scores up.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from netinf.baselines import rank_of_pair
from netinf.envs import llm_rps as g
from netinf.judge import judge_run, render_prompt
from netinf.runlog import load_run


def run_dirs(patterns: list[str]) -> list[Path]:
    out = []
    for pat in patterns:
        for p in sorted(glob.glob(pat)):
            d = Path(p)
            if (d / "meta.json").is_file() and (d / "rounds.jsonl").is_file() and d not in out:
                out.append(d)
    return out


def true_pair(meta: dict) -> tuple[int, int] | None:
    if meta.get("primary") is None or meta.get("assistant") is None:
        return None
    return tuple(sorted((meta["primary"], meta["assistant"])))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+", help="run directories or globs")
    ap.add_argument("--model", help="judge model id (default: judge_model in --config)")
    ap.add_argument("--config", type=Path, default=Path("configs/base.yaml"))
    ap.add_argument("--provider", help="override the config's provider")
    ap.add_argument("--with-payoffs", action="store_true")
    ap.add_argument("--max-rounds", type=int, default=200)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=2000, help="output cap incl. reasoning")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--budget", type=float, help="USD cap for this invocation (default: config)")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the first prompt, no API calls")
    args = ap.parse_args(argv)

    dirs = run_dirs(args.runs)
    if not dirs:
        print("no run directories matched", file=sys.stderr)
        return 1
    todo = [d for d in dirs if args.overwrite or not (d / "judge.json").exists()]
    print(f"{len(dirs)} runs matched, {len(dirs) - len(todo)} already judged, {len(todo)} to judge")
    cfg = g.load_config(args.config)
    model = args.model or cfg.get("judge_model")
    if not model:
        raise SystemExit(f"no --model given and no judge_model in {args.config}")
    if args.dry_run:
        if todo:
            a, p, _ = load_run(todo[0])
            prompt = render_prompt(a, p if args.with_payoffs else None, args.max_rounds)
            print(f"--- prompt for {todo[0].name} ({len(prompt)} chars) ---\n{prompt}")
        return 0

    provider = args.provider or cfg["provider"]
    if provider in g.OFFLINE_PROVIDERS:
        raise SystemExit(f"provider {provider!r} cannot run the judge; use --dry-run instead")
    price = (cfg.get("prices") or {}).get(model)
    if not (isinstance(price, (list, tuple)) and len(price) == 2
            and all(isinstance(x, (int, float)) for x in price)):
        raise SystemExit(f"refusing to run: no numeric [input, output] price for {model!r} "
                         f"in {args.config}")
    budget = args.budget if args.budget is not None else cfg.get("budget_usd")
    client = g.make_client_for(dict(cfg, provider=provider, budget_usd=budget))

    total = 0.0
    for d in todo:
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        try:
            out = judge_run(d, client, model=model, provider=provider,
                            with_payoffs=args.with_payoffs, temperature=args.temperature,
                            max_tokens=args.max_tokens,
                            seed=args.seed, max_rounds=args.max_rounds)
        except Exception as e:
            if type(e).__name__ == "BudgetExceeded":
                print(f"budget reached, stopping: {e}")
                break
            raise
        total += out["cost_usd"] or 0.0
        scores = {tuple(int(x) for x in k.split("-")): v for k, v in out["scores"].items()}
        top = max(scores, key=scores.get)
        tp = true_pair(meta)
        rank = f" true {tp} rank {rank_of_pair(scores, tp)}" if tp else ""
        print(f"[{d.name}] parse_ok={out['parse_ok']} attempts {out['attempts']} top {top} "
              f"{scores[top]:.0f}{rank} tokens in/out {out['input_tokens']}/"
              f"{out['output_tokens']} cost ${out['cost_usd'] or 0:.4f}")
    print(f"done: total cost ${total:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
