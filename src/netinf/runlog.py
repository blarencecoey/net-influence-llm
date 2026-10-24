"""Run directory writer and reader (format in notes/methods/llm-harness.md).

runs/<run_id>/
  meta.json      written at start (completed=false) and rewritten at finish with totals
  config.yaml    the resolved config exactly as run
  prompts/       rendered system prompt per player (LLM agents only)
  rounds.jsonl   one line per completed round, flushed as it completes
  calls.jsonl    one line per agent decision, flushed as it completes
A crash therefore leaves every completed round on disk.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import yaml


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                             cwd=Path(__file__).parent, timeout=10, check=False)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


class RunWriter:
    def __init__(self, run_dir: Path, config: dict, meta: dict, prompts: dict[str, str]):
        self.dir = Path(run_dir)
        (self.dir / "prompts").mkdir(parents=True, exist_ok=True)
        (self.dir / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                              encoding="utf-8")
        for name, text in prompts.items():
            (self.dir / "prompts" / f"{name}.txt").write_text(text, encoding="utf-8")
        self.meta = dict(meta, git_commit=git_commit(), started_at=now(), finished_at=None,
                         completed=False, rounds_completed=0, total_input_tokens=0,
                         total_output_tokens=0, total_cost_usd=0.0, cost_complete=True,
                         parse_failures=0)
        self._write_meta()
        # kept open for the whole run and flushed per line; closed in finish()
        self._rounds = open(self.dir / "rounds.jsonl", "a", encoding="utf-8")  # noqa: SIM115
        self._calls = open(self.dir / "calls.jsonl", "a", encoding="utf-8")  # noqa: SIM115

    def _write_meta(self):
        (self.dir / "meta.json").write_text(json.dumps(self.meta, indent=2), encoding="utf-8")

    @staticmethod
    def _append(f, rec: dict):
        f.write(json.dumps(rec) + "\n")
        f.flush()

    def round(self, rec: dict):
        self._append(self._rounds, rec)
        self.meta["rounds_completed"] += 1

    def call(self, rec: dict):
        self._append(self._calls, rec)
        m = self.meta
        m["total_input_tokens"] += rec.get("input_tokens") or 0
        m["total_output_tokens"] += rec.get("output_tokens") or 0
        if rec.get("cost_usd") is None:
            m["cost_complete"] = False  # some call had no configured price
        m["total_cost_usd"] += rec.get("cost_usd") or 0.0
        m["parse_failures"] += not rec.get("parse_ok", True)

    def finish(self, completed: bool, **extra) -> dict:
        self._rounds.close()
        self._calls.close()
        self.meta.update(extra, completed=completed, finished_at=now())
        self._write_meta()
        return self.meta


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_run(path: str | Path) -> tuple[np.ndarray, np.ndarray, dict]:
    """(actions (T, n) int, payoffs (T, n) int, meta) for the completed rounds of a run."""
    path = Path(path)
    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    rounds = sorted(read_jsonl(path / "rounds.jsonl"), key=lambda r: r["round"])
    n = meta["n_players"]
    actions = np.array([r["actions"] for r in rounds], dtype=np.int64).reshape(-1, n)
    payoffs = np.array([r["payoffs"] for r in rounds], dtype=np.int64).reshape(-1, n)
    return actions, payoffs, meta
