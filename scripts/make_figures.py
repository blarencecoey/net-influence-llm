"""Report figures from saved analysis outputs (no scoring, no API).

Usage:
  python scripts/make_figures.py <out_dir> <calib_dir> <seeded per_run.csv> [...]

- scores.png: net influence (pre-registered state) per run. Null runs (C0, C1; calibration and
  held-out) show their largest pair score, seeded runs the true pair's score; dashed lines are
  the frozen 1% / 5% thresholds from <calib_dir>/thresholds.json.
- decomposition.png: mean gross gamma vs the subtracted third-agent term by pair type, parsed from
  notes/results/net-decomposition/output.txt.
Colours: the first three categorical slots of the dataviz reference palette (light mode).
"""
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

OUT, CALIB, SEEDED = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
STATE = "prev_n_distinct"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def short(label: str, families: str) -> str:
    mixed = "mistral" in families
    if label.startswith("C2"):
        p = label.split("=")[1]
        return f"C2 mixed\np={p}" if mixed else f"C2 Llama\np={p}"
    return label


def scores_figure() -> None:
    th = json.loads((CALIB / "thresholds.json").read_text(encoding="utf-8"))
    t = th["detectors"][f"netinf|{STATE}"]
    pu = pd.read_csv(CALIB / "per_unit.csv")
    null = pu[(pu.detector == "netinf") & (pu.state == STATE) & pu.condition.isin(["C0", "C1"])]
    groups = [(f"{c} null\n(n={len(g)})", g.max_score.to_numpy(), BLUE)
              for c, g in null.groupby("condition")]
    seeded = pd.concat([pd.read_csv(p) for p in SEEDED]).drop_duplicates("run_id")
    seeded["group"] = [short(lab, rid) for lab, rid in zip(seeded.label, seeded.run_id)]
    order = sorted(seeded.group.unique(), key=lambda g: (g.startswith("C3"), "mixed" in g, g))
    for gname in order:
        g = seeded[seeded.group == gname]
        groups.append((f"{gname}\n(n={len(g)})", g[f"netinf|{STATE}|true_score"].to_numpy(),
                       ORANGE))

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    rng = np.random.default_rng(0)
    for k, (name, y, col) in enumerate(groups):
        x = k + rng.uniform(-0.18, 0.18, len(y))
        ax.scatter(x, y, s=16, color=col, edgecolor=SURFACE, linewidth=0.6, zorder=3)
    for f, ls, va in (("0.01", "--", "bottom"), ("0.05", ":", "top")):  # 1% above, 5% below
        ax.axhline(t[f], color=INK2, lw=1, ls=ls, zorder=2)
        ax.text(len(groups) - 0.45, t[f], f"{float(f):.0%} FPR threshold {t[f]:.3f}",
                va=va, ha="right", fontsize=7.5, color=INK2)
    ax.axhline(0, color=GRID, lw=1, zorder=1)
    ax.set_xticks(range(len(groups)), [g[0] for g in groups], fontsize=7.5)
    ax.set_xlim(-0.6, len(groups) - 0.4)
    ax.set_ylabel(f"net influence score (state {STATE})")
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(handles=[plt.Line2D([], [], ls="", marker="o", color=BLUE, label="null run: max pair score"),
                       plt.Line2D([], [], ls="", marker="o", color=ORANGE, label="seeded run: true pair score")],
              loc="upper left", frameon=False, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(OUT / "scores.png", dpi=200)
    plt.close(fig)


def decomposition_figure() -> None:
    txt = Path("notes/results/net-decomposition/output.txt").read_text(encoding="utf-8")
    block = txt.split(f"state {STATE}")[1].split("state ")[0]
    rows = re.findall(r"(C\d \w\w): gamma ([\d.-]+) \[[^]]*\]\s+subtracted ([\d.-]+) \[[^]]*\]"
                      r"\s+score ([\d.-]+) \[[^]]*\]\s+n=(\d+)", block)
    names = {"C0 LL": "C0\nLlama–Llama", "C1 LL": "C1\nLlama–Llama",
             "C1 LM": "C1\nLlama–Mistral", "C1 MM": "C1\nMistral–Mistral"}
    lab = [f"{names[r[0]]}\n(n={r[4]})" for r in rows]
    gam, sub, sc = (np.array([float(r[k]) for r in rows]) for k in (1, 2, 3))

    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    x, w = np.arange(len(rows)), 0.36
    ax.bar(x - w / 2 - 0.01, gam, w, color=BLUE, label="gross dependence γ(i; j)")
    ax.bar(x + w / 2 + 0.01, sub, w, color=AQUA, label="subtracted third-agent term")
    for xi, g, s, v in zip(x, gam, sub, sc):
        ax.text(xi, max(g, s) + 0.006, f"score {v:+.3f}", ha="center", fontsize=7.5, color=INK2)
    ax.set_xticks(x, lab, fontsize=7.5)
    ax.set_ylabel(f"mean (nats, state {STATE})")
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(gam.max(), sub.max()) * 1.22)
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "decomposition.png", dpi=200)
    plt.close(fig)


OUT.mkdir(parents=True, exist_ok=True)
scores_figure()
decomposition_figure()
print(f"wrote {OUT / 'scores.png'}, {OUT / 'decomposition.png'}")
