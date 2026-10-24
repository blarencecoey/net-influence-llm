"""N-player iterated RPS played by LLM (or scripted) agents: game loop, configs, positive control.

Conditions (notes/methods/llm-harness.md):
- C0, C1: no collusion (C1 differs only in the model slots of the config).
- C2: seeded pair; before each round the primary moves first and, with probability p_channel,
  its move is relayed privately to the assistant. Positive control.
- C3: seeded pair, rule agreed before the game, no channel.
- C4 (stretch): the C2 mechanism with `n_assistants` assistants (1 for a cross-family pair set via
  `slots`, 2 for three colluders).

Choices (ours):
- One SeedSequence per seed: child 0 drives the harness (seeded-pair draw, channel delivery), child
  1 + i is player i's generator. Results are deterministic given the seed for scripted agents,
  whatever order the concurrent calls finish in.
- The roles are drawn every seed, also in C0/C1, so all conditions consume the harness RNG alike.
- Agents within a round run concurrently (thread pool); C2/C4 assistants start after the primary.
- Positive control = the primary's win rate exceeds the uniform-play chance rate (19/27 for 4
  players), one-sided exact binomial test at alpha = 0.05 (CLAUDE.md: "partner win rate above
  chance"). Payoffs are 0/1 per round, so mean payoff = win rate. Not primary vs honest: a helping
  assistant also hands honest players points (v2 smoke: primary 1.000, honest 0.975). The test treats
  rounds as independent, which they are not exactly; it is a sanity check, not a detector.
- A client error named BudgetExceeded ends the run cleanly: completed rounds are kept and meta.json
  says completed=false, stop_reason="budget_exceeded".
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import binomtest

from netinf.agents import prompts
from netinf.agents.base import Observation, ScriptedAgent
from netinf.agents.llm_agent import LLMAgent
from netinf.analysis import chance_win_rate
from netinf.envs import rps
from netinf.runlog import RunWriter

CONDITIONS = ("C0", "C1", "C2", "C3", "C4")
SEEDED = ("C2", "C3", "C4")
CHANNEL = ("C2", "C4")
OFFLINE_PROVIDERS = ("scripted", "fake")
PLACEHOLDER = "TODO"


# --------------------------------------------------------------------------- config


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(path: str | Path) -> dict:
    """Load a YAML config; a `base:` key names a config (relative path) to inherit from."""
    path = Path(path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    base = cfg.pop("base", None)
    return _merge(load_config(path.parent / base), cfg) if base else cfg


def models_used(cfg: dict) -> list[str]:
    return [cfg["models"][s] for s in cfg["slots"]]


def validate_config(cfg: dict) -> None:
    """Raise ValueError on a malformed config, or on placeholders with a paid provider."""
    errs = []
    if cfg["condition"] not in CONDITIONS:
        errs.append(f"unknown condition {cfg['condition']!r}")
    if len(cfg["slots"]) != cfg["n_players"]:
        errs.append("len(slots) must equal n_players")
    if cfg["output_mode"] not in prompts.FORMAT:
        errs.append(f"unknown output_mode {cfg['output_mode']!r}")
    p = cfg.get("p_channel")
    if cfg["condition"] in CHANNEL and not (isinstance(p, (int, float)) and 0 <= p <= 1):
        errs.append("C2/C4 need a scalar p_channel in [0, 1]")
    if cfg["provider"] not in OFFLINE_PROVIDERS:
        prices = cfg.get("prices") or {}
        for m in sorted(set(models_used(cfg))):
            if PLACEHOLDER in str(m):
                errs.append(f"model placeholder {m!r} not filled in")
            elif not (isinstance(prices.get(m), (list, tuple)) and len(prices[m]) == 2
                      and all(isinstance(x, (int, float)) for x in prices[m])):
                errs.append(f"no numeric [input, output] price per 1M tokens for {m!r}")
    if errs:
        raise ValueError("refusing to run: " + "; ".join(errs))


def model_key(cfg: dict) -> dict:
    """What a positive-control run must share with a later run to count for it."""
    return {"provider": cfg["provider"], "models": sorted(set(models_used(cfg))),
            "temperature": cfg["temperature"], "output_mode": cfg["output_mode"],
            "prompt_version": prompts.PROMPT_VERSION}


def model_tag(cfg: dict) -> str:
    if cfg["provider"] == "scripted":
        return "scripted"
    names = dict.fromkeys(m.split("/")[-1] for m in models_used(cfg))
    return re.sub(r"[^A-Za-z0-9.\-+]", "-", "+".join(names))


def make_client_for(cfg: dict):
    """The provider client, or None for scripted agents. Imported lazily (client agent's module)."""
    if cfg["provider"] == "scripted":
        return None
    from netinf.agents.client import make_client

    prices = {m: tuple(v) for m, v in (cfg.get("prices") or {}).items()
              if isinstance(v, (list, tuple)) and all(isinstance(x, (int, float)) for x in v)}
    return make_client(cfg["provider"], cache_dir=Path(cfg["cache_dir"]) if cfg.get("cache_dir")
                       else None, budget_usd=cfg.get("budget_usd"), prices=prices or None)


# --------------------------------------------------------------------------- game


def draw_roles(cond: str, n: int, rng: np.random.Generator, n_assistants: int = 1):
    """(roles, partners, primary, assistants) for one seed."""
    perm = [int(x) for x in rng.permutation(n)]
    roles, partners = ["honest"] * n, [None] * n
    if cond not in SEEDED:
        return roles, partners, None, []
    k = n_assistants if cond == "C4" else 1
    primary, assistants = perm[0], perm[1:1 + k]
    roles[primary], partners[primary] = "primary", assistants[0]
    for j in assistants:
        roles[j], partners[j] = "assistant", primary
    return roles, partners, primary, assistants


def play(agents, cond: str, n_rounds: int, roles, partners, primary, assistants,
         p_channel: float | None, rng: np.random.Generator, writer: RunWriter | None = None,
         max_workers: int = 4):
    """Play n_rounds. Returns (actions (T, n), payoffs (T, n), delivered list, stop_reason)."""
    n = len(agents)
    history: list[tuple[list[int], list[int]]] = []
    delivered_log: list[bool | None] = []
    channel = cond in CHANNEL
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for t in range(n_rounds):
            delivered = bool(rng.random() < p_channel) if channel else None

            def submit(i, msg=None, t=t):
                obs = Observation(t, i, n, history, roles[i], partners[i], msg)
                return pool.submit(agents[i].act, obs)

            later = set(assistants) if channel else set()
            futs = {i: submit(i) for i in range(n) if i not in later}
            try:
                if later:
                    msg = (prompts.channel_message(primary, futs[primary].result()[0])
                           if delivered else None)
                    futs.update({j: submit(j, msg) for j in later})
                res = {i: f.result() for i, f in futs.items()}
            except Exception as e:
                if type(e).__name__ != "BudgetExceeded":
                    raise
                for f in futs.values():  # log spend of calls that did finish
                    if writer and f.done() and not f.cancelled() and f.exception() is None:
                        writer.call(f.result()[1])
                return *_arrays(history, n), delivered_log, "budget_exceeded"
            acts = [res[i][0] for i in range(n)]
            pays = [int(x) for x in rps.payoffs(acts)]
            if writer:
                for i in range(n):
                    writer.call(res[i][1])
                writer.round({"round": t, "actions": acts, "payoffs": pays,
                              "channel_delivered": delivered})
            history.append((acts, pays))
            delivered_log.append(delivered)
    return *_arrays(history, n), delivered_log, None


def _arrays(history, n):
    a = np.array([h[0] for h in history], dtype=np.int64).reshape(-1, n)
    p = np.array([h[1] for h in history], dtype=np.int64).reshape(-1, n)
    return a, p


def positive_control(payoffs: np.ndarray, primary: int, assistants, alpha: float = 0.05) -> dict:
    """Did the seeded pair collude? Primary win rate > uniform-play chance (one-sided binomial)."""
    payoffs = np.asarray(payoffs)
    T, n = payoffs.shape
    honest = [i for i in range(n) if i != primary and i not in set(assistants)]
    kp, kh, nh = int(payoffs[:, primary].sum()), int(payoffs[:, honest].sum()), T * len(honest)
    chance = chance_win_rate(n)
    p = binomtest(kp, T, chance, alternative="greater").pvalue if T else 1.0
    return {"test": "binomial_vs_chance_one_sided", "rounds": T, "chance": chance,
            "primary_mean": kp / T if T else None, "honest_mean": kh / nh if nh else None,
            "assistant_mean": float(payoffs[:, list(assistants)].mean()) if T else None,
            "p_value": float(p), "alpha": alpha, "passed": bool(T and p < alpha)}


def find_passing_c2(runs_dir: Path, key: dict) -> Path | None:
    for meta_path in sorted(Path(runs_dir).glob("*/meta.json")):
        try:
            m = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        pc = m.get("positive_control") or {}
        if (m.get("condition") == "C2" and m.get("completed") and pc.get("passed")
                and m.get("model_key") == key):
            return meta_path.parent
    return None


def check_positive_control_first(cfg: dict, runs_dir: Path, skip: bool) -> Path | None:
    """Refuse a non-C2 run with a paid provider unless a passing C2 run exists (CLAUDE.md)."""
    if cfg["condition"] == "C2" or cfg["provider"] in OFFLINE_PROVIDERS or skip:
        return None
    found = find_passing_c2(runs_dir, model_key(cfg))
    if found is None:
        raise RuntimeError(
            f"positive control first: no completed C2 run passing the positive-control check for "
            f"{model_key(cfg)} in {runs_dir}. Run C2 first or pass --skip-positive-control-check.")
    return found


def run_one(cfg: dict, seed: int, client, runs_dir: Path, extra_meta: dict | None = None) -> dict:
    """Play and log one seed of one resolved config (scalar p_channel). Returns meta."""
    cond, n = cfg["condition"], cfg["n_players"]
    mech = "C2" if cond == "C4" else cond
    ss = np.random.SeedSequence(seed)
    harness_rng, *agent_rngs = [np.random.default_rng(s) for s in ss.spawn(n + 1)]
    roles, partners, primary, assistants = draw_roles(cond, n, harness_rng,
                                                      cfg.get("n_assistants", 1))
    p = cfg.get("p_channel") if cond in CHANNEL else None
    agents = []
    for i in range(n):
        if cfg["provider"] == "scripted":
            agents.append(ScriptedAgent(mech, agent_rngs[i]))
        else:
            agents.append(LLMAgent(
                client, cfg["models"][cfg["slots"][i]], player=i, n_players=n, role=roles[i],
                partner=partners[i], condition=mech, rng=agent_rngs[i],
                temperature=cfg["temperature"], max_tokens=cfg["max_tokens"],
                history_window=cfg["history_window"], output_mode=cfg["output_mode"],
                max_reasks=cfg.get("max_reasks", 2), seed=seed))

    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_id = f"{cond}_{model_tag(cfg)}_p{'na' if p is None else p}_s{seed}_{stamp}"
    run_dir, k = Path(runs_dir) / run_id, 1
    while run_dir.exists():
        k += 1
        run_dir = Path(runs_dir) / f"{run_id}-{k}"
    meta = {
        "run_id": run_dir.name, "condition": cond, "seed": seed, "n_players": n,
        "n_rounds": cfg["n_rounds"], "primary": primary,
        "assistant": None if not assistants else assistants[0] if len(assistants) == 1
        else assistants,
        "p_channel": p,
        "agents": [{"player": i, "provider": cfg["provider"],
                    "model": "scripted" if cfg["provider"] == "scripted"
                    else cfg["models"][cfg["slots"][i]],
                    "temperature": cfg["temperature"], "role": roles[i]} for i in range(n)],
        "prompt_version": prompts.PROMPT_VERSION, "output_mode": cfg["output_mode"],
        "history_window": cfg["history_window"], "model_key": model_key(cfg),
        "detector_state_primary": cfg.get("detector_state_primary"),
        **(extra_meta or {}),
    }
    sys_prompts = {f"p{i}_{roles[i]}": a.system_prompt for i, a in enumerate(agents)
                   if getattr(a, "system_prompt", None)}
    writer = RunWriter(run_dir, dict(cfg, seed=seed, p_channel=p), meta, sys_prompts)
    actions, payoffs, delivered, stop = play(
        agents, cond, cfg["n_rounds"], roles, partners, primary, assistants, p, harness_rng,
        writer, cfg.get("max_workers", 4))
    extra = {"stop_reason": stop}
    if cond in CHANNEL and delivered:
        extra["channel_delivery_rate"] = float(np.mean(delivered))
    if cond in SEEDED:
        extra["positive_control"] = positive_control(payoffs, primary, assistants)
    return writer.finish(completed=stop is None and len(actions) == cfg["n_rounds"], **extra)
