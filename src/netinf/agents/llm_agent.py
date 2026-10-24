"""LLM-backed RPS agent: renders prompts, calls the client, parses the move.

Parsing (ours): the last `ACTION: <move>` in the reply (case-insensitive, markdown tolerated);
failing that, the last bare ROCK/PAPER/SCISSORS word, or a reply that is just R, P or S.
Distribution mode parses `ROCK=x PAPER=y SCISSORS=z` (any non-negative numbers, normalised) and
samples the move with the agent's generator, which is spawned from the run seed.
Unparseable replies get up to `max_reasks` follow-up asks in the same conversation; after that the
move is uniform random from the agent's generator and the record has `parse_ok=False`.
Each call gets a seed derived from (run seed, round, player, attempt): the client caches only seeded
calls, and a re-ask needs a new seed or the cached bad reply would come back.

One record per act() (one per round and player): tokens, cost and latency are summed over all
attempts, `raw_text` is the last reply, `retry_texts` holds earlier ones.
"""

from __future__ import annotations

import re

import numpy as np

from netinf.agents import prompts
from netinf.agents.base import Observation, call_record

_ACTION = re.compile(r"ACTION[^A-Z]{0,6}(ROCK|PAPER|SCISSORS?)", re.IGNORECASE)
_WORD = re.compile(r"\b(ROCK|PAPER|SCISSORS?)\b", re.IGNORECASE)
_PROB = {m: re.compile(rf"{m[:4]}\w*\W{{0,4}}(\d+(?:\.\d*)?|\.\d+)", re.IGNORECASE) for m in prompts.MOVES}
_CODE = {"ROCK": 0, "PAPER": 1, "SCISSOR": 2, "SCISSORS": 2, "R": 0, "P": 1, "S": 2}


def parse_action(text: str | None) -> int | None:
    if not text:
        return None
    hits = _ACTION.findall(text) or _WORD.findall(text)
    if hits:
        return _CODE[hits[-1].upper()]
    bare = text.strip().strip("*`.'\"").upper()
    return _CODE.get(bare) if bare in ("R", "P", "S") else None


def parse_distribution(text: str | None) -> np.ndarray | None:
    if not text:
        return None
    vals = []
    for m in prompts.MOVES:
        hits = _PROB[m].findall(text)
        if not hits:
            return None
        vals.append(float(hits[-1]))
    p = np.asarray(vals)
    return p / p.sum() if p.sum() > 0 else None


class LLMAgent:
    def __init__(self, client, model: str, *, player: int, n_players: int, role: str,
                 partner: int | None, condition: str, rng: np.random.Generator,
                 temperature: float = 1.0, max_tokens: int = 20, history_window: int = 10,
                 output_mode: str = "action", max_reasks: int = 2, seed: int = 0):
        if output_mode not in prompts.FORMAT:
            raise ValueError(f"unknown output_mode {output_mode!r}")
        self.client, self.model, self.rng = client, model, rng
        self.player, self.run_seed = player, seed
        self.temperature, self.max_tokens = temperature, max_tokens
        self.history_window, self.output_mode, self.max_reasks = history_window, output_mode, max_reasks
        self.system_prompt = prompts.system_prompt(role, player, n_players, partner, condition,
                                                   output_mode)

    def _parse(self, text: str | None) -> tuple[int | None, list[float] | None]:
        if self.output_mode == "action":
            return parse_action(text), None
        p = parse_distribution(text)
        if p is None:
            return None, None
        return int(self.rng.choice(3, p=p)), [round(float(x), 4) for x in p]

    def call_seed(self, round_: int, attempt: int) -> int:
        ss = np.random.SeedSequence([self.run_seed, round_, self.player, attempt])
        return int(ss.generate_state(1)[0] & 0x7FFFFFFF)

    def act(self, obs: Observation) -> tuple[int, dict]:
        user = prompts.user_prompt(obs.round, obs.history, self.history_window,
                                   obs.channel_message, self.output_mode)
        messages = [{"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user}]
        texts: list[str] = []
        tot = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "latency_s": 0.0}
        cost_known, cached, action, probs = True, True, None, None
        for attempt in range(1 + self.max_reasks):
            c = self.client.complete(messages, model=self.model, temperature=self.temperature,
                                     max_tokens=self.max_tokens,
                                     seed=self.call_seed(obs.round, attempt))
            texts.append(c.text)
            tot["input_tokens"] += c.input_tokens
            tot["output_tokens"] += c.output_tokens
            tot["latency_s"] += c.latency_s
            cost_known &= c.cost_usd is not None
            tot["cost_usd"] += c.cost_usd or 0.0  # per-call spend; cache hits are 0.0
            cached &= bool(c.cached)
            action, probs = self._parse(c.text)
            if action is not None:
                break
            messages += [{"role": "assistant", "content": c.text or ""},
                         {"role": "user", "content": prompts.REASK.format(
                             fmt=prompts.FORMAT[self.output_mode])}]
        parse_ok = action is not None
        if not parse_ok:
            action = int(self.rng.integers(3))
        tot["cost_usd"] = tot["cost_usd"] if cost_known else None
        tot["latency_s"] = round(tot["latency_s"], 3)
        return action, call_record(obs, self.model, action, raw_text=texts[-1], parse_ok=parse_ok,
                                   cached=cached, attempts=len(texts), retry_texts=texts[:-1],
                                   probs=probs, **tot)
