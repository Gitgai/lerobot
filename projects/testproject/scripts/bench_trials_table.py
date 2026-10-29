#!/usr/bin/env python3
"""Regenerate results/so101_bench_20261019/TRIALS.md from trials.csv (one row per bench trial, every trial ever run).
Add a line to the CSV after each trial, then run this. Result values: SUCCESS (fruit in the tray, arm released it),
SUCCESS? (in the tray, mechanism or final spot to be adjudicated by the operator), FAIL, VOID (not a trial: camera
fault, aborted, wrong launch, fruit not re-placed)."""
import csv, collections, pathlib
D = pathlib.Path("results/so101_bench_20261019"); rows = list(csv.DictReader(open(D / "trials.csv")))
valid = [r for r in rows if r["result"] != "VOID"]
def summary(keyf, title):
    g = collections.OrderedDict()
    for r in valid: g.setdefault(keyf(r), []).append(r)
    out = [f"### {title}", "", "| " + title + " | valid trials | SUCCESS | SUCCESS? | FAIL | success rate |", "|---|---|---|---|---|---|"]
    for k, rs in g.items():
        s = sum(r["result"] == "SUCCESS" for r in rs); q = sum(r["result"] == "SUCCESS?" for r in rs); f = sum(r["result"] == "FAIL" for r in rs)
        out.append(f"| {k} | {len(rs)} | {s} | {q} | {f} | {s}/{len(rs)}" + (f" (up to {s+q}/{len(rs)} if SUCCESS? count)" if q else "") + " |")
    return out + [""]
md = ["# Bench trials — one row per trial (SO-101, Pune, overhead front camera)", "",
      "Source of truth: `trials.csv` in this folder (add a row per trial, then run `scripts/bench_trials_table.py`).",
      "Full narrative per trial: `bench_runs.md`. VOID rows are not trials (camera fault, aborted, wrong launch, fruit not re-placed) and are left out of every count.",
      "", f"Trials recorded: {len(rows)} ({len(valid)} valid, {len(rows)-len(valid)} void).", ""]
md += summary(lambda r: f"{r['model']} / {r['fruit']}", "model / fruit")
md += summary(lambda r: f"{r['date']} / {r['model']} / {r['fruit']}", "day / model / fruit")
md += ["### Every trial", "", "| date | row | # | model | fruit | cap | placement | result | what happened |", "|---|---|---|---|---|---|---|---|---|"]
for r in rows: md.append(f"| {r['date']} | {r['row']} | {r['trial']} | {r['model']} | {r['fruit']} | {r['cap']} | {r['placement']} | **{r['result']}** | {r['what_happened']} |")
(D / "TRIALS.md").write_text("\n".join(md) + "\n"); print("\n".join(md[:30]))
