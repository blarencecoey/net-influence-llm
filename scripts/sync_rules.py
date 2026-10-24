"""Per-family move rules for honest players: beats own last move, beats last round's mode,
copy own last; all-same persistence; family marginals. Uniform reference 1/3 each."""
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

beat = lambda x: (x + 1) % 3  # P beats R, S beats P, R beats S
stats = defaultdict(lambda: defaultdict(list))
for d in sorted(Path("runs").iterdir()):
    if not (d / "meta.json").exists() or "scripted" in d.name or "fake" in d.name:
        continue
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    if not meta.get("completed") or meta["condition"] not in ("C0", "C1"):
        continue
    rows = sorted((json.loads(x) for x in (d / "rounds.jsonl").read_text().splitlines() if x.strip()),
                  key=lambda r: r["round"])
    a = np.array([r["actions"] for r in rows])
    T, n = a.shape
    mode_prev = np.array([Counter(r).most_common(1)[0][0] for r in a[:-1]])
    uniq_mode = np.array([Counter(r).most_common(2)[0][1] > (Counter(r).most_common(2) + [(0, 0)])[1][1]
                          for r in a[:-1]])
    for i, ag in enumerate(sorted(meta["agents"], key=lambda z: z["player"])):
        f = f"{meta['condition']} {'Llama' if 'llama' in ag['model'] else 'Mistral'}"
        s = stats[f]
        s["beats_own_last"].append(np.mean(a[1:, i] == beat(a[:-1, i])))
        s["beats_prev_mode"].append(np.mean((a[1:, i] == beat(mode_prev))[uniq_mode]))
        s["repeat_own"].append(np.mean(a[1:, i] == a[:-1, i]))
        for k in range(3):
            s[f"freq_{'RPS'[k]}"].append(np.mean(a[:, i] == k))
    same = (a == a[:, :1]).all(1)
    stats[meta["condition"] + " run"]["P(all same | prev all same)"].append(
        same[1:][same[:-1]].mean() if same[:-1].any() else np.nan)
    stats[meta["condition"] + " run"]["P(all same | prev not)"].append(same[1:][~same[:-1]].mean())
for f, s in sorted(stats.items()):
    print(f, " ".join(f"{k} {np.nanmean(v):.3f}" for k, v in s.items()), f"(n={len(next(iter(s.values())))})")
