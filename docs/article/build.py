"""Build docs/article/index.html: collect chart data from notes/results/ (no scoring) and embed it in the page.

Usage (repo root): python docs/article/build.py
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

R = Path("notes/results")
HERE = Path(__file__).parent
DETS = ["netinf|prev_n_distinct", "netinf|none", "lagged_netinf|none", "correlation|-"]


def r(x, k=4):
    return None if pd.isna(x) else round(float(x), k)


# ---- Figure 1: RPS games, per detector
th = json.loads((R / "calib-c0-c1-100null/thresholds.json").read_text())["detectors"]
pu = pd.read_csv(R / "calib-c0-c1-100null/per_unit.csv")
games = []
for d in DETS:
    det, st = d.split("|")
    nul = pu[(pu.detector == det) & (pu.state == st) & pu.condition.isin(["C0", "C1"])]
    for _, x in nul.iterrows():
        games.append(dict(det=d, group=x.condition, kind="null", seed=int(str(x.seeds).strip("[]")), score=r(x.max_score),
                          top=x.top_pair, split=x.split))

seeded = pd.concat([pd.read_csv(R / p) for p in
                    ["c3-sweep/per_run.csv", "c3-v4/per_run.csv", "b21-mixed-c2/score_seeded/per_run.csv"]])
seeded = seeded.drop_duplicates("run_id")
for _, x in seeded.iterrows():
    mixed = "mistral" in x.run_id
    if x.label.startswith("C2"):
        p = float(x.p_channel)
        g = f"C2 mixed p=1" if mixed else f"C2 p={p:g}"
    else:
        g = f"C3 {x.prompt_version}"
    for d in DETS:
        games.append(dict(det=d, group=g, kind="seeded", seed=int(x.seed), score=r(x[f"{d}|true_score"]),
                          rank=None if pd.isna(x[f"{d}|rank"]) else int(x[f"{d}|rank"]),
                          heldout=bool(x.heldout), flag1=bool(x.get(f"{d}|flag@0.01", False))))

c4 = pd.read_csv(R / "c4-three-colluders/per_run.csv")
for _, x in c4.iterrows():
    for d in DETS:
        games.append(dict(det=d, group="C4", kind="seeded", seed=int(x.seed), score=r(x[f"{d}|max_coll_score"]),
                          other=r(x[f"{d}|max_other_score"]), top_in_set=bool(x[f"{d}|top_in_set"]),
                          heldout=True, flag1=bool(x[f"{d}|flag@0.01"])))

thresholds = {d: {"1": r(th[d]["0.01"]), "5": r(th[d]["0.05"])} for d in DETS}

# ---- Figure 2: decomposition, per state
txt = (R / "net-decomposition/output.txt").read_text()
decomp = {}
for st in ["prev_n_distinct", "none", "prev_joint"]:
    block = txt.split(f"state {st}\n")[1].split("  state ")[0].split("Gross gamma")[0]
    rows = re.findall(r"(C\d \w\w): gamma ([\d.-]+) \[[^]]*\]\s+subtracted ([\d.-]+) \[[^]]*\]"
                      r"\s+score ([\d.-]+) \[[^]]*\]\s+n=(\d+)", block)
    decomp[st] = [dict(pair=a, gamma=float(b), sub=float(c), score=float(d_), n=int(e)) for a, b, c, d_, e in rows]

# ---- Figure 3: auction
ath = json.loads((R / "auction/thresholds.json").read_text())["detectors"]
apu = pd.read_csv(R / "auction/per_unit.csv")
auction = []
for st in ["prev_price_band", "none"]:
    a = apu[(apu.detector == "netinf") & (apu.state == st)]
    for _, x in a.iterrows():
        mixed = "mistral" in x.unit_id
        g = {"A0": "A0", "A1": "A1"}.get(x.condition, "A2 mixed" if mixed else "A2 Llama")
        seeded_ = x.condition == "A2"
        auction.append(dict(state=st, group=g, seed=int(x.seed), split=x.split,
                            score=r(x.true_score if seeded_ else x.max_score), top=x.top_pair,
                            rank=None if pd.isna(x["rank"]) else int(x["rank"])))
pp = pd.read_csv(R / "auction/price_paths.csv")
paths = [dict(cond=c, mixed="mistral" in m, n=int(g.n_runs.iloc[0]),
              pts=[[int(h) + 5, round(float(v), 3)] for h, v in zip(g.hour, g.mean_ask)])
         for (c, m), g in pp.groupby(["condition", "models"])]
refs = json.loads((R / "auction/references.json").read_text())
a_th = {st: {"1": r(ath[f"netinf|{st}"]["0.01"]), "5": r(ath[f"netinf|{st}"]["0.05"])}
        for st in ["prev_price_band", "none"]}

data = dict(games=games, thresholds=thresholds, decomp=decomp, auction=auction, paths=paths,
            refs=refs, auction_thresholds=a_th)
payload = json.dumps(data, separators=(",", ":"))
assert "</" not in payload
page = (HERE / "article.src.html").read_text(encoding="utf-8").replace("__DATA__", payload)
(HERE / "index.html").write_text(page, encoding="utf-8")
print(len(games), "game rows;", len(auction), "auction rows; wrote", HERE / "index.html", len(page), "bytes")
print(thresholds, a_th, refs)
print(pd.Series([g["group"] for g in games if g["det"] == DETS[0]]).value_counts().to_dict())
