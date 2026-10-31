#!/usr/bin/env python3
"""Sort the policy server's raw frame dump into one folder per trial with plain names, so a trial can be browsed.
Writes results/bench_frames_by_trial/<date>_<day>_row<X>_<model>_<fruit>/trial<N>_<RESULT>/{front,wrist}_chunk<NNN>.jpg
as HARD LINKS to the raw files (no extra disk, raw folder untouched). Re-run after each bench row and add the row to
ROWS below. Blocks lost to the 2026-10-28 recorder overwrite get a LOST.txt instead of frames."""
import os, csv, pathlib
R3 = "results/so101_lora_on_top_20261019/bench_frames_row3_010000"; BASE = "results/so101_bench_20261019/frames"
OUT = pathlib.Path("results/bench_frames_by_trial")
# row -> (raw dir, prefix, cap, first call of trial 1, lost call ranges)
# the 16 public-base trials (Oct 19-20) were served one connection per launch: trials 1-6 = c05..c10 (45 calls each),
# trials 7-10 = c11 (4 x 45), trials 11-16 = c12 (6 x 45); (prefix, first call) per trial
BASE_TRIALS = {1: ("c05", 1), 2: ("c06", 1), 3: ("c07", 1), 4: ("c08", 1), 5: ("c09", 1), 6: ("c10", 1), 7: ("c11", 1), 8: ("c11", 46), 9: ("c11", 91), 10: ("c11", 136),
               11: ("c12", 1), 12: ("c12", 46), 13: ("c12", 91), 14: ("c12", 136), 15: ("c12", 181), 16: ("c12", 226)}
M_TRIALS = {1: ("c13", 1), 2: ("c14", 1), 3: ("c14", 76), 4: ("c14", 151), 5: ("c14", 226)}
N_TRIALS = {1: ("c15", 1), 2: ("c15", 76), 3: ("c17", 1), 4: ("c17", 76), 5: ("c17", 151)}
O_TRIALS = {1: ("c18", 1), 2: ("c19", 1), 3: ("c20", 1), 4: ("c20", 76), 5: ("c20", 151)}
P_TRIALS = {1: ("c22", 1)}
Q_TRIALS = {1: ("c25", 1)}
R_TRIALS = {n: ("c26", 1 + (n - 1) * 75) for n in range(1, 6)}
S_TRACE = "results/so101_lora_on_top_20261019/bench_trace_row3s_orange_live_20261031/frames"
T_TRACE = "results/so101_lora_on_top_20261019/bench_trace_row3t_orange_live_gpu1_20261031/frames"
U1_TRACE = "results/so101_lora_on_top_20261019/bench_trace_ft3_jpeg_no_rtc_trial_u1_20261031/frames"
U2_U5_TRACE = "results/so101_lora_on_top_20261019/bench_trace_ft3_jpeg_no_rtc_row_u2_u5_20261031/frames"
V1_TRACE = "results/so101_lora_on_top_20261019/bench_trace_ft3_jpeg_no_rtc_trial_v1_tomato_20261031/frames"
V2_TRACE = "results/so101_lora_on_top_20261019/bench_trace_ft3_jpeg_no_rtc_trial_v2_tomato_20261031/frames"
V3_TRACE = "results/so101_lora_on_top_20261019/bench_trace_ft3_jpeg_no_rtc_trial_v3_tomato_20261031/frames"
V4_TRACE = "results/so101_lora_on_top_20261019/bench_trace_ft3_jpeg_no_rtc_trial_v4_tomato_20261031/frames"
ROWS = {"base": (BASE, None, 45, 1, []), "M": (R3, None, 75, 1, []), "N": (R3, None, 75, 1, []), "O": (R3, None, 75, 1, []), "P": (R3, None, 75, 1, []), "Q": (R3, None, 75, 1, []), "R": (R3, None, 75, 1, []), "S": (S_TRACE, None, 75, 1, []), "T": (T_TRACE, None, 75, 1, []), "U": (U1_TRACE, None, 75, 1, []), "V": (V1_TRACE, None, 75, 1, []), "ctrl": (BASE, "c01", 45, 1, []), "A": (R3, "c01", 45, 1, [(1, 48)]), "B": (R3, "c02", 75, 1, [(1, 348)]), "C": (R3, "c03", 75, 1, [(1, 65)]),
        "D": (R3, "c04", 75, 1, [(1, 75)]), "E": (R3, "c05", 75, 1, []), "F": (R3, "c02", 75, 1, []), "G": (R3, "c04", 75, 1, []),
        "H": (R3, "c07", 75, 1, []), "I": (R3, "c08", 75, 1, []), "J": (R3, "c10", 75, 1, []), "K": (R3, "c11", 75, 1, []), "L": (R3, "c12", 120, 1, [])}
DAY = {"2026-10-26": "sun", "2026-10-28": "tue", "2026-10-29": "wed", "2026-10-30": "thu", "2026-10-31": "fri"}
trials = list(csv.DictReader(open("results/so101_bench_20261019/trials.csv")))
made = 0; readme = ["# Bench frames, one folder per trial", "", "Hard links into the raw server dump (see scripts/sort_bench_frames.py). "
          "Names: `<date>_<day>_row<X>_<model>_<fruit>/trial<N>_<RESULT>/front_chunk<NNN>.jpg` (overhead camera) and `wrist_chunk<NNN>.jpg`. "
          "Chunk NNN = the NNN-th policy call of that trial (one call = 20 arm steps at 30 Hz ≈ 0.7 s of motion + the round trip).", "", "| folder | trials | note |", "|---|---|---|"]
for row, (raw, pref, cap, first, lost) in ROWS.items():
    tr = [t for t in trials if t["row"] == row]
    if not tr: continue
    t0 = tr[0]; model = "base" if t0["model"] == "base" else "ft3"; fruit = t0["fruit"].split()[0]
    folder = OUT / ("2026-10-19_20_rowbase_base_citrus_onion_orange" if row == "base" else f"{t0['date']}_{DAY.get(t0['date'],'')}_row{row}_{model}_{fruit}"); folder.mkdir(parents=True, exist_ok=True)
    notes = []
    for t in tr:
        if not t["trial"].isdigit(): continue
        n = int(t["trial"]); d = folder / f"trial{n}_{t['result'].replace('?','_pending')}"; d.mkdir(exist_ok=True)
        raw_trial, ep_idx = raw, n
        if row == "base": pref, a = BASE_TRIALS[n]; b = a + cap - 1
        elif row == "M": pref, a = M_TRIALS[n]; b = a + cap - 1
        elif row == "N": pref, a = N_TRIALS[n]; b = a + cap - 1
        elif row == "O": pref, a = O_TRIALS[n]; b = a + cap - 1
        elif row == "P": pref, a = P_TRIALS[n]; b = a + cap - 1
        elif row == "Q": pref, a = Q_TRIALS[n]; b = a + cap - 1
        elif row == "R": pref, a = R_TRIALS[n]; b = a + cap - 1
        elif row in {"S", "T"}: a, b = 1, cap
        elif row == "U":
            a, b = 1, cap
            raw_trial, ep_idx = (U1_TRACE, 1) if n == 1 else (U2_U5_TRACE, n - 1)
        elif row == "V":
            a, b = 1, cap
            raw_trial, ep_idx = {1: (V1_TRACE, 1), 2: (V2_TRACE, 1), 3: (V3_TRACE, 1), 4: (V4_TRACE, 1)}[n]
        else: a, b = first + (n - 1) * cap, first + n * cap - 1
        lost_here = [(max(a, x), min(b, y)) for x, y in lost if x <= b and y >= a]
        if lost_here and lost_here[0][0] == a and lost_here[0][1] >= b - 2:
            (d / "LOST.txt").write_text(f"raw frames {pref} calls {a}-{b} were overwritten by the 2026-10-28 server restart; see results/so101_lora_on_top_20261019/bench_row3*_T{n}.jpg for the composite built before the loss\n"); notes.append(f"trial {n} frames lost"); continue
        for c in range(a, b + 1):
            if any(x <= c <= y for x, y in lost_here): continue
            for cam in ("front", "wrist"):
                src = (pathlib.Path(raw_trial) / f"ep{ep_idx:02d}_chunk{c:03d}_{cam}.jpg" if row in {"S", "T", "U", "V"} else pathlib.Path(raw) / f"{pref}_call{c:06d}_{cam}.jpg"); dst = d / f"{cam}_chunk{c - a + 1:03d}.jpg"
                if src.exists() and not dst.exists():
                    try: os.link(src, dst)
                    except OSError: import shutil; shutil.copy2(src, dst)
                    made += 1
        (d / "WHAT_HAPPENED.txt").write_text(f"{t['date']} {t['model']} / {t['fruit']}\n{t['result']} — {t['what_happened']}\nplacement: {t['placement']}; tray: {t['tray']}; instruction: {t['instruction']}; cap {cap} chunks\n")
    readme.append(f"| {folder.name} | {len(tr)} | {'; '.join(notes) if notes else ''} |")
# end-of-trial snapshots saved by the client on the Acer (bench_client.py snap(): after_last_chunk, at_rest) — pull with --pull
import sys, subprocess, shutil
if "--pull" in sys.argv:
    subprocess.run(["rsync", "-a", "--include=*/", "--include=*.jpg", "--exclude=*", "gaikwad-prakash@192.168.194.228:bench_client_frames/", "results/bench_client_frames/"], check=False)
SNAP = pathlib.Path("results/bench_client_frames"); pulled = 0
for row, (raw, pref, cap, first, lost) in ROWS.items():
    tr = [t for t in trials if t["row"] == row]
    for t in tr:
        src_dir = SNAP / t["log"]
        if not src_dir.is_dir() or not t["trial"].isdigit(): continue
        t0 = tr[0]; model = "base" if t0["model"] == "base" else "ft3"; fruit = t0["fruit"].split()[0]
        d = OUT / f"{t0['date']}_{DAY.get(t0['date'],'')}_row{row}_{model}_{fruit}" / f"trial{int(t['trial'])}_{t['result'].replace('?','_pending')}"
        for tag in ("start", "after_last_chunk", "at_rest"):
            for cam in ("front", "wrist"):
                src = src_dir / f"ep{int(t['ep_in_log'])}_{tag}_{cam}.jpg"; dst = d / (f"{cam}_start.jpg" if tag == "start" else f"{cam}_end_{tag}.jpg")
                if src.exists() and d.is_dir() and not dst.exists(): shutil.copy2(src, dst); pulled += 1
readme += ["", "Trials run from 2026-10-29 on also have `front_start.jpg` (the scene as the trial begins), `front_end_after_last_chunk.jpg` (the pose the policy left the arm in) and `front_end_at_rest.jpg` (back at rest), plus the same for the wrist camera. Earlier trials have no such frames (the client never captured them) and their `chunk001` frame is stale — use chunk002 as the true start frame (bench_runs.md 2026-10-29)."]
(OUT / "README.md").write_text("\n".join(readme) + "\n"); print("linked files:", made, "end snapshots copied:", pulled)
