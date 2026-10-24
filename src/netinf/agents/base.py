"""Agent interface for the LLM RPS harness, plus a scripted agent that needs no API.

`ScriptedAgent` mirrors the scripted collusion modes of `netinf.envs.rps` so the whole pipeline
(positive control, run logging, analysis) runs offline for $0:
- honest, primary: uniform random;
- assistant, C2: plays `beaten_by(partner's move)` when the channel message is delivered, random
  otherwise (assistant mode with cp = p_channel);
- assistant, C3: plays `beaten_by(partner's previous move)` from the public history (tacit mode).
Each agent draws from its own generator (spawned from the run seed), so results do not depend on
the order in which concurrent agents are called.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from netinf.agents.prompts import MOVES
from netinf.envs import rps


@dataclass
class Observation:
    round: int
    player: int  # this agent's index
    n_players: int
    history: list[tuple[list[int], list[int]]]  # (actions, payoffs) of past rounds, oldest first
    role: str  # "honest" | "primary" | "assistant"
    partner: int | None
    channel_message: str | None  # delivered private message this round, if any


class Agent(Protocol):
    def act(self, obs: Observation) -> tuple[int, dict]: ...  # action, log record


def call_record(obs: Observation, model: str, action: int, **kw) -> dict:
    """One calls.jsonl line (schema in notes/methods/llm-harness.md); extra keys allowed."""
    rec = {"round": obs.round, "player": obs.player, "model": model, "raw_text": None,
           "parsed_action": int(action), "parse_ok": True, "input_tokens": 0, "output_tokens": 0,
           "cost_usd": 0.0, "latency_s": 0.0, "cached": False,
           "channel_message": obs.channel_message}
    rec.update(kw)
    return rec


def move_in_message(msg: str) -> int:
    """The move named in a channel message (see prompts.channel_message)."""
    return next(k for k, m in enumerate(MOVES) if m in msg.upper())


class ScriptedAgent:
    model = "scripted"
    system_prompt = None

    def __init__(self, condition: str, rng: np.random.Generator):
        self.condition = condition
        self.rng = rng

    def act(self, obs: Observation) -> tuple[int, dict]:
        a = int(self.rng.integers(rps.N_ACTIONS))
        if obs.role == "assistant":
            if self.condition == "C2" and obs.channel_message:
                a = move_in_message(obs.channel_message)  # the channel names the helping move
            elif self.condition == "C3" and obs.history:
                a = int(rps.beaten_by(obs.history[-1][0][obs.partner]))
        return a, call_record(obs, self.model, a)
