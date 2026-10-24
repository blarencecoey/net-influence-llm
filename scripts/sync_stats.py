"""Synchronisation stats over completed LLM runs: all-same rounds, pairwise agreement vs the
rate expected from each player's own move frequencies, time trend, move bias, shared openings."""
import glob
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

M = "RPS"


def load(d):
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    if not meta.get("completed"):
        return None
    rows = [json.loads(x) for x in (d / "rounds.jsonl").read_text(encoding="utf-8").splitlines()
            if x.strip()]
    a = np.array([r["actions"] for r in sorted(rows, key=lambda r: r["round"])])
    p = np.array([r["payoffs"] for r in sorted(rows, key=lambda r: r["round"])])
    return meta, a, p


def group(meta, name):
    if "scripted" in name or "fake" in name:
        return None
    c = meta["condition"]
    mixed = "mistral" in name
    if c == "C2" and meta.get("prompt_version") != "v3":
        return None
    return f"{c} {'Llama+Mistral' if mixed else 'Llama x4'}"


G = defaultdict(list)
for d in sorted(Path("runs").iterdir()):
    if not (d / "meta.json").exists():
        continue
    x = load(d)
    if x is None:
        continue
    g = group(x[0], d.name)
    if g:
        G[g].append((d.name, *x))

U_SAME_ALL = 3 / 81
print("Uniform iid reference: P(all 4 same) = 0.037, P(all 3 moves present) = 0.444, "
      "pair same-move = 0.333\n")
for g in sorted(G):
    runs = G[g]
    allsame, three, pay0 = [], [], []
    obs_pair, exp_pair = [], []
    quarters = np.zeros(4)
    move_freq = Counter()
    open3 = Counter()
    repeat, follow_prev_mode = [], []
    fam_pairs = defaultdict(lambda: [[], []])
    for name, meta, a, p in runs:
        T, n = a.shape
        same = (a == a[:, :1]).all(1)
        allsame.append(same.mean())
        three.append(np.mean([len(set(r)) == 3 for r in a]))
        pay0.append((p.sum(1) == 0).mean())
        for q in range(4):
            quarters[q] += same[q * T // 4:(q + 1) * T // 4].mean() / len(runs)
        move_freq.update(a.ravel().tolist())
        open3[" ".join("".join(M[v] for v in a[t]) for t in range(3))] += 1
        fams = ["L" if "llama" in ag["model"] else "M"
                for ag in sorted(meta["agents"], key=lambda z: z["player"])]
        seeded = {meta.get("primary"), meta.get("assistant")} - {None}
        for i, j in combinations(range(n), 2):
            if {i, j} & seeded:
                continue  # honest pairs only
            o = (a[:, i] == a[:, j]).mean()
            fi = np.bincount(a[:, i], minlength=3) / T
            fj = np.bincount(a[:, j], minlength=3) / T
            e = float(fi @ fj)
            obs_pair.append(o)
            exp_pair.append(e)
            fam_pairs["".join(sorted(fams[i] + fams[j]))][0].append(o)
            fam_pairs["".join(sorted(fams[i] + fams[j]))][1].append(e)
        for i in range(n):
            if i in seeded:
                continue
            repeat.append((a[1:, i] == a[:-1, i]).mean())
    tot = sum(move_freq.values())
    obs, exp = np.array(obs_pair), np.array(exp_pair)
    print(f"== {g}: {len(runs)} runs")
    print(f"  all 4 same: mean {np.mean(allsame):.3f} (min {np.min(allsame):.3f}, max "
          f"{np.max(allsame):.3f}); by quarter " + " ".join(f"{q:.3f}" for q in quarters))
    print(f"  all 3 moves present: {np.mean(three):.3f}; rounds where nobody scores: "
          f"{np.mean(pay0):.3f}")
    print("  move freq " + " ".join(f"{M[k]} {move_freq[k] / tot:.3f}" for k in range(3)))
    print(f"  honest-pair same-move: observed {obs.mean():.3f} (sd {obs.std():.3f}) vs expected "
          f"from own marginals {exp.mean():.3f}; excess {np.mean(obs - exp):+.3f}, "
          f"pairs with excess > 0: {np.mean(obs > exp):.2f} of {len(obs)}")
    for k, (o, e) in sorted(fam_pairs.items()):
        print(f"    {k}: observed {np.mean(o):.3f} expected {np.mean(e):.3f} excess "
              f"{np.mean(np.array(o) - np.array(e)):+.3f} (n={len(o)})")
    print(f"  honest self-repeat rate {np.mean(repeat):.3f} (uniform 0.333)")
    print("  most common first-3-round openings: " + "; ".join(
        f"{k} x{v}" for k, v in open3.most_common(3)))
    print()
