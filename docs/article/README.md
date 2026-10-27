# Distill-style article

A web version of the report (`notes/report-draft.md`), with interactive figures drawn from the saved results in `notes/results/`. It follows the Apart submission template's section order.

- `article.src.html`: page source (text, styles, chart code). The chart data is left as a `__DATA__` placeholder.
- `build.py`: reads the results files, builds the chart data and writes `index.html`. No scoring and no API calls.
- `index.html`: the built page. It is self-contained apart from Google Fonts and D3 7.8.5 from cdnjs.

Rebuild after changing the source or the results (repo root):

```
python docs/article/build.py
```

Inputs:
- `calib-c0-c1-100null/` (`thresholds.json`, `per_unit.csv`)
- the `per_run.csv` files in `c3-sweep/`, `c3-v4/`, `b21-mixed-c2/score_seeded/` and `c4-three-colluders/`
- `net-decomposition/output.txt`
- `auction/` (`thresholds.json`, `per_unit.csv`, `price_paths.csv`, `references.json`)

The text is the same as the report draft; edit both together.
