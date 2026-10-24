"""4-player iterated Rock-Paper-Scissors played by LLM agents.

One game = `rounds` simultaneous rounds. Per round:
1. honest players and the primary colluder are queried in parallel;
2. in the seeded condition, the assistant is queried last, with a private message carrying the
   primary's move this round, delivered with probability `channel_p` (H3 sweep);
3. payoffs follow Bonjour et al. Sec. 5.1 (see envs/rps.py).

Seats of the colluding pair and of the models are shuffled per game so a detector cannot win by
learning positions. Everything needed to recompute results is written to one JSONL per game.
"""

from __future__ import annotations

import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from netinf.agents import prompts
from netinf.agents.backends import Backend, Completion
from netinf.envs.rps import payoffs

N_PLAYERS = 4
_PARSE = re.compile(r"\b(rock|paper|scissors)\b", re.IGNORECASE)
_CODE = {"rock": 0, "paper": 1, "scissors": 2}


@dataclass
class GameConfig:
    name: str
    condition: str  # "seeded" | "tacit" | "honest"
    models: list[str]  # one per seat before shuffling (len 4), or len 1 = same model everywhere
    rounds: int = 200
    window: int = 5  # past rounds shown to each agent
    temperature: float = 1.0
    max_tokens: int = 16
    channel_p: float = 1.0  # seeded only: probability the private message is delivered
    shuffle_options: bool = True  # randomise option order in the prompt (positional-bias control)
    shuffle_seats: bool = True
    colluder_models: list[str] | None = None  # optional: models for (primary, assistant) seats

    def seat_models(self) -> list[str]:
        return self.models * N_PLAYERS if len(self.models) == 1 else list(self.models)


def parse_move(text: str) -> int | None:
    m = _PARSE.search(text or "")
    return _CODE[m.group(1).lower()] if m else None


@dataclass
class GameResult:
    seed: int
    seats_models: list[str]
    true_pair: tuple[int, int] | None  # (primary, assistant) seats, 0-based
    actions: list[list[int]] = field(default_factory=list)
    payoffs: list[list[int]] = field(default_factory=list)
    cost: float = 0.0
    n_calls: int = 0
    n_parse_fail: int = 0  # needed a re-ask
    n_fallback: int = 0  # random move after re-ask failed


def _ask(backend: Backend, model: str, system: str, user: str, cfg: GameConfig, rng: random.Random,
         log: list) -> tuple[int, Completion, bool, bool]:
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    c = backend.complete(model, msgs, temperature=cfg.temperature, max_tokens=cfg.max_tokens)
    move, reasked, fallback, cost = parse_move(c.text), False, False, c.cost
    texts = [c.text]
    if move is None:
        reasked = True
        msgs += [{"role": "assistant", "content": c.text}, {"role": "user", "content": prompts.REASK}]
        c2 = backend.complete(model, msgs, temperature=cfg.temperature, max_tokens=cfg.max_tokens)
        texts.append(c2.text)
        cost += c2.cost
        move = parse_move(c2.text)
        if move is None:
            fallback, move = True, rng.randrange(3)
    c.cost = cost
    log.append({"model": model, "texts": texts, "cost": cost, "reask": reasked, "fallback": fallback})
    return move, c, reasked, fallback


def play_game(cfg: GameConfig, backend: Backend, seed: int, out_path: Path | None = None,
              max_workers: int = 4) -> GameResult:
    rng = random.Random(seed)
    seats = list(range(N_PLAYERS))
    models = cfg.seat_models()
    if cfg.shuffle_seats:
        rng.shuffle(models)
    true_pair = None
    roles = ["honest"] * N_PLAYERS
    partner = [None] * N_PLAYERS
    if cfg.condition in ("seeded", "tacit"):
        pair = rng.sample(seats, 2) if cfg.shuffle_seats else [0, 1]
        p, a = pair
        true_pair = (p, a)
        roles[p] = "primary" if cfg.condition == "seeded" else "tacit_primary"
        roles[a] = "assistant" if cfg.condition == "seeded" else "tacit_assistant"
        partner[p], partner[a] = a, p
        if cfg.colluder_models:
            models[p], models[a] = cfg.colluder_models
    elif cfg.condition != "honest":
        raise ValueError(cfg.condition)

    systems = [prompts.system_prompt(i, cfg.rounds, roles[i], partner[i]) for i in seats]
    res = GameResult(seed=seed, seats_models=models, true_pair=true_pair)
    history: list[tuple[list[int], list[int]]] = []
    totals = [0] * N_PLAYERS
    fh = open(out_path, "w") if out_path else None
    if fh:
        fh.write(json.dumps({"type": "header", "config": asdict(cfg), "seed": seed, "seats_models": models,
                             "roles": roles, "true_pair": true_pair, "system_prompts": systems}) + "\n")

    pool = ThreadPoolExecutor(max_workers=max_workers)
    try:
        for t in range(cfg.rounds):
            acts = [None] * N_PLAYERS
            log: list = []
            first = [i for i in seats if roles[i] != "assistant"]
            prompt_rngs = {i: random.Random(rng.random()) for i in seats}
            users = {i: prompts.round_prompt(i, t, history, totals, cfg.window, prompt_rngs[i],
                                             cfg.shuffle_options) for i in first}
            futs = {i: pool.submit(_ask, backend, models[i], systems[i], users[i], cfg, rng, log) for i in first}
            for i, f in futs.items():
                acts[i], c, ra, fb = f.result()
                res.cost += c.cost; res.n_calls += 1; res.n_parse_fail += ra; res.n_fallback += fb
            delivered = None
            if cfg.condition == "seeded":
                p, a = true_pair
                delivered = rng.random() < cfg.channel_p
                msg = prompts.CHANNEL_MESSAGE.format(partner=p + 1, move=prompts.MOVES[acts[p]]) if delivered else None
                user = prompts.round_prompt(a, t, history, totals, cfg.window, prompt_rngs[a],
                                            cfg.shuffle_options, channel=msg)
                acts[a], c, ra, fb = _ask(backend, models[a], systems[a], user, cfg, rng, log)
                res.cost += c.cost; res.n_calls += 1; res.n_parse_fail += ra; res.n_fallback += fb
            pay = payoffs(acts).tolist()
            totals = [x + y for x, y in zip(totals, pay)]
            history.append((acts, pay))
            res.actions.append(acts)
            res.payoffs.append(pay)
            if fh:
                fh.write(json.dumps({"type": "round", "t": t, "actions": acts, "payoffs": pay,
                                     "channel_delivered": delivered, "calls": log, "time": time.time()}) + "\n")
    finally:
        pool.shutdown()
        if fh:
            fh.write(json.dumps({"type": "footer", "cost": res.cost, "n_calls": res.n_calls,
                                 "n_parse_fail": res.n_parse_fail, "n_fallback": res.n_fallback}) + "\n")
            fh.close()
    return res


def load_game(path: Path) -> dict:
    """Read a game JSONL back into {header, actions (T,4), payoffs (T,4), channel, footer}."""
    header, footer, acts, pays, chan = None, None, [], [], []
    for line in Path(path).read_text().splitlines():
        r = json.loads(line)
        if r["type"] == "header":
            header = r
        elif r["type"] == "round":
            acts.append(r["actions"]); pays.append(r["payoffs"]); chan.append(r["channel_delivered"])
        elif r["type"] == "footer":
            footer = r
    return {"header": header, "footer": footer, "actions": np.array(acts, dtype=np.int64),
            "payoffs": np.array(pays, dtype=np.int64), "channel": chan, "path": str(path)}
