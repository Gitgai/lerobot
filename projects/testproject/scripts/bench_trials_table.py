#!/usr/bin/env python3
"""Regenerate the comprehensive bench-trial table.
  results/so101_bench_20261019/trials.csv       hand-kept: one row per trial (conditions, placement, result, failure mode)
  results/so101_bench_20261019/trials_full.csv  = trials.csv + numbers computed from the trial's jsonl log
  results/so101_bench_20261019/TRIALS.md        readable: summaries, then the full table
Computed per trial from the log: utc, chunks run, wall s, median round trip, first-move chunk (any joint > 5 deg from the
start pose), lowest gripper reading and its chunk, max |wrist_roll|, end pose.  Result words: SUCCESS, SUCCESS? (operator
to adjudicate), FAIL, VOID (not a trial; excluded from every count)."""
import csv, json, collections, pathlib
D = pathlib.Path("results/so101_bench_20261019"); L = {p.stem: p for p in list(D.glob("*.jsonl")) + list(pathlib.Path("results/so101_lora_on_top_20261019").glob("*.jsonl"))}
rows = list(csv.DictReader(open(D / "trials.csv")))

def metrics(log, ep):
    p = L.get(log)
    if p is None: return {}
    recs = [json.loads(l) for l in open(p)]; ch = [r for r in recs if "chunk" in r and r.get("ep") == ep]; res = [r for r in recs if "result" in r and r.get("ep") == ep]
    m = {}
    if res: r = res[0]; m.update(utc=r.get("utc", ""), chunks_run=r.get("chunks", ""), wall_s=r.get("wall_s", ""), rtt_median_s=r.get("latency_median_s", ""), end_pose=[round(x) for x in r["end_state"]] if r.get("end_state") else "")
    elif ch: m.update(chunks_run=len(ch))
    if ch and "state" in ch[0]:
        s0 = ch[0]["state"]; mv = next((r["chunk"] for r in ch if max(abs(a - b) for a, b in zip(r["state"][:5], s0[:5])) > 5), "")
        g = [(r["state"][5], r["chunk"]) for r in ch]; gm = min(g)
        m.update(first_move_chunk=mv, grip_min=round(gm[0]), grip_min_chunk=gm[1], wrist_roll_max=round(max(abs(r["state"][4]) for r in ch)))
    return m

COMP = ["utc", "chunks_run", "wall_s", "rtt_median_s", "first_move_chunk", "grip_min", "grip_min_chunk", "wrist_roll_max", "end_pose"]
full = []
for r in rows:
    m = metrics(r["log"], int(r["ep_in_log"])); full.append({**r, **{k: m.get(k, "") for k in COMP}})
cols = list(rows[0].keys()) + COMP
w = csv.DictWriter(open(D / "trials_full.csv", "w"), fieldnames=cols); w.writeheader(); w.writerows(full)

valid = [r for r in full if r["result"] != "VOID"]
def summary(keyf, title):
    g = collections.OrderedDict()
    for r in valid: g.setdefault(keyf(r), []).append(r)
    out = [f"### By {title}", "", f"| {title} | valid | SUCCESS | SUCCESS? | FAIL | rate |", "|---|---|---|---|---|---|"]
    for k, rs in g.items():
        s = sum(r["result"] == "SUCCESS" for r in rs); q = sum(r["result"] == "SUCCESS?" for r in rs); f = sum(r["result"] == "FAIL" for r in rs)
        out.append(f"| {k} | {len(rs)} | {s} | {q} | {f} | {s}/{len(rs)}" + (f" (up to {s+q}/{len(rs)})" if q else "") + " |")
    return out + [""]
import re
def primary(m): return re.split(r",| then | \(|;", m)[0].strip()
fm = collections.Counter(primary(r["failure_mode"]) for r in valid if r["result"] == "FAIL")
md = ["# Bench trials — comprehensive table (SO-101, Pune)", "",
      "Source: `trials.csv` (hand-kept, one row per trial). `trials_full.csv` adds the numbers computed from each trial's log. Regenerate with `python3 scripts/bench_trials_table.py`.",
      "Narrative per trial: `bench_runs.md`. VOID = not a trial (camera fault, stop, wrong launch, fruit not re-placed); excluded from every count.", "",
      f"Trials: {len(full)} recorded, {len(valid)} valid, {len(full)-len(valid)} void.", ""]
md += summary(lambda r: f"{r['model']} / {r['fruit']}", "model / fruit")
md += summary(lambda r: f"{r['date']} / {r['model']} / {r['fruit']}", "day / model / fruit")
md += summary(lambda r: f"{r['model']} / {r['fruit']} / cap {r['cap']}", "model / fruit / cap")
md += ["### Failure modes (valid FAIL trials; the FIRST mode when a trial shows two in sequence)", "", "| failure mode | count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in fm.most_common()] + [""]
md += ["### Every trial — conditions", "", "| date | row | # | model | checkpoint | server | fruit | instruction | cap | front camera | tray | placement |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in full: md.append(f"| {r['date']} | {r['row']} | {r['trial']} | {r['model']} | {r['checkpoint']} | {r['server']} | {r['fruit']} | {r['instruction']} | {r['cap']} | {r['front_camera']} | {r['tray']} | {r['placement']} |")
md += ["", "### Every trial — outcome", "", "| date | row | # | result | failure mode | what happened | first move | grip min (chunk) | wrist roll max | chunks | wall s | RTT s | adjudication | log / frames |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in full: md.append(f"| {r['date']} | {r['row']} | {r['trial']} | **{r['result']}** | {r['failure_mode']} | {r['what_happened']} | {r['first_move_chunk']} | {r['grip_min']} ({r['grip_min_chunk']}) | {r['wrist_roll_max']} | {r['chunks_run']} | {r['wall_s']} | {r['rtt_median_s']} | {r['adjudication']} | {r['log']} ep{r['ep_in_log']}; {r['frames']} |")
(D / "TRIALS.md").write_text("\n".join(md) + "\n"); print("\n".join(md[:48]))
