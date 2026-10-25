"""Report figures from saved analysis outputs (no scoring, no API).

Usage:
  python scripts/make_figures.py <out_dir> <calib_dir> <seeded per_run.csv> [...] [--auction <dir>]

- scores.png: net influence (pre-registered state) per run. Null runs (C0, C1; calibration and
  held-out) show their largest pair score, seeded runs the true pair's score; dashed lines are
  the frozen 1% / 5% thresholds from <calib_dir>/thresholds.json.
- decomposition.png: mean gross gamma vs the subtracted third-agent term by pair type, parsed from
  notes/results/net-decomposition/output.txt.
- auction.png (with --auction, e.g. notes/results/auction): left, net influence per auction run
  (state prev_price_band; nulls A0 / A1 max pair score, A2 seeded pair's score) against that
  analysis' frozen thresholds; right, mean ask per 10-hour block per condition against the
  reference asks (price_paths.csv, references.json).
Colours: the first three categorical slots of the dataviz reference palette (light mode).
"""
import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out", type=Path)
ap.add_argument("calib", type=Path)
ap.add_argument("seeded", nargs="+")
ap.add_argument("--auction", type=Path)
args = ap.parse_args()
OUT, CALIB, SEEDED, AUCTION = args.out, args.calib, args.seeded, args.auction
STATE = "prev_n_distinct"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def short(label: str, families: str, version: str) -> str:
    mixed = "mistral" in families
    if label.startswith("C2"):
        p = label.split("=")[1]
        return f"C2 mixed\np={p}" if mixed else f"C2 Llama\np={p}"
    return f"{label}\nprompt {version}" if label == "C3" else label


def scores_figure() -> None:
    th = json.loads((CALIB / "thresholds.json").read_text(encoding="utf-8"))
    t = th["detectors"][f"netinf|{STATE}"]
    pu = pd.read_csv(CALIB / "per_unit.csv")
    null = pu[(pu.detector == "netinf") & (pu.state == STATE) & pu.condition.isin(["C0", "C1"])]
    groups = [(f"{c} null\n(n={len(g)})", g.max_score.to_numpy(), BLUE)
              for c, g in null.groupby("condition")]
    seeded = pd.concat([pd.read_csv(p) for p in SEEDED]).drop_duplicates("run_id")
    seeded["group"] = [short(lab, rid, v) for lab, rid, v
                       in zip(seeded.label, seeded.run_id, seeded.prompt_version)]
    order = sorted(seeded.group.unique(), key=lambda g: (g.startswith("C3"), "mixed" in g, g))
    for gname in order:
        g = seeded[seeded.group == gname]
        groups.append((f"{gname}\n(n={len(g)})", g[f"netinf|{STATE}|true_score"].to_numpy(),
                       ORANGE))

    fig, ax = plt.subplots(figsize=(8.0, 3.5))
    rng = np.random.default_rng(0)
    for k, (name, y, col) in enumerate(groups):
        x = k + rng.uniform(-0.18, 0.18, len(y))
        ax.scatter(x, y, s=16, color=col, edgecolor=SURFACE, linewidth=0.6, zorder=3)
    for f, ls, va in (("0.01", "--", "bottom"), ("0.05", ":", "top")):  # 1% above, 5% below
        ax.axhline(t[f], color=INK2, lw=1, ls=ls, zorder=2)
        ax.text(1.01, t[f], f"{float(f):.0%} FPR\nthreshold {t[f]:.3f}", va=va, ha="left",
                fontsize=7, color=INK2, transform=ax.get_yaxis_transform(), clip_on=False)
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


def auction_figure() -> None:
    st = "prev_price_band"
    th = json.loads((AUCTION / "thresholds.json").read_text(encoding="utf-8"))["detectors"][f"netinf|{st}"]
    pu = pd.read_csv(AUCTION / "per_unit.csv")
    pu = pu[(pu.detector == "netinf") & (pu.state == st)]
    mixed = pu.unit_id.str.contains("mistral")
    groups = [("A0 null\n5 Llama", pu[pu.condition == "A0"].max_score, BLUE),
              ("A1 null\n3 Llama +\n2 Mistral", pu[pu.condition == "A1"].max_score, BLUE),
              ("A2 seeded\n5 Llama", pu[(pu.condition == "A2") & ~mixed].true_score, ORANGE),
              ("A2 seeded\n3 Llama +\n2 Mistral", pu[(pu.condition == "A2") & mixed].true_score, ORANGE)]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(8.0, 3.3), gridspec_kw={"width_ratios": [1, 1.15]})
    rng = np.random.default_rng(0)
    for k, (_, y, col) in enumerate(groups):
        ax.scatter(k + rng.uniform(-0.18, 0.18, len(y)), y, s=16, color=col, edgecolor=SURFACE,
                   linewidth=0.6, zorder=3)
    for f, ls, va in (("0.01", "--", "bottom"), ("0.05", ":", "top")):  # labels in the empty gap
        ax.axhline(th[f], color=INK2, lw=1, ls=ls, zorder=2)
        ax.text(2.0, th[f], f"{float(f):.0%}: {th[f]:.3f}", va=va, ha="center", fontsize=7, color=INK2)
    ax.axhline(0, color=GRID, lw=1, zorder=1)
    ax.set_xticks(range(len(groups)), [f"{g[0]}\n(n={len(g[1])})" for g in groups], fontsize=7)
    ax.set_xlim(-0.6, len(groups) - 0.4)
    ax.set_ylabel(f"net influence (state {st})")
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_title("Detection", fontsize=9, loc="left")

    pp = pd.read_csv(AUCTION / "price_paths.csv")
    ref = json.loads((AUCTION / "references.json").read_text(encoding="utf-8"))
    style = {"A0": (BLUE, "-"), "A1": (BLUE, "--"), "A2": (ORANGE, None)}
    for (cond, models), g in pp.groupby(["condition", "models"]):
        col, ls = style[cond]
        ls = ls or ("--" if "mistral" in models else "-")
        who = "3 Llama + 2 Mistral" if "mistral" in models else "5 Llama"
        bx.plot(g.hour + 4.5, g.mean_ask, color=col, ls=ls, lw=1.8,
                label=f"{cond} {'seeded' if cond == 'A2' else 'null'}, {who} (n={g.n_runs.iloc[0]})")
    for key, name in (("midpoint", "midpoint"), ("joint_optimal_ask", "joint optimum"),
                      ("equilibrium_ask", "equilibrium")):
        bx.axhline(ref[key], color=INK2, lw=0.9, ls=(0, (4, 3)), zorder=1)
        bx.text(200, ref[key], f"{name} ${ref[key]}", va="top" if key == "midpoint" else "bottom",
                ha="right", fontsize=7, color=INK2)  # midpoint label below its line, clear of the asks
    bx.set_ylim(ref["equilibrium_ask"] - 1.5, 94)
    bx.set_xlim(0, 200)
    bx.set_xlabel("hour")
    bx.set_ylabel("mean ask ($, 10-hour blocks)")
    bx.yaxis.grid(True, color=GRID, lw=0.6)
    bx.set_axisbelow(True)
    bx.legend(frameon=False, fontsize=6.5, loc="center left", bbox_to_anchor=(0.02, 0.36))
    bx.set_title("Asks over the run", fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "auction.png", dpi=200)
    plt.close(fig)


OUT.mkdir(parents=True, exist_ok=True)
scores_figure()
decomposition_figure()
written = [OUT / "scores.png", OUT / "decomposition.png"]
if AUCTION:
    auction_figure()
    written.append(OUT / "auction.png")
print("wrote " + ", ".join(map(str, written)))
