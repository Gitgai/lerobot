#!/usr/bin/env python3
"""Sort the policy server's raw frame dump into one folder per trial with plain names, so a trial can be browsed.
Writes results/bench_frames_by_trial/<date>_<day>_row<X>_<model>_<fruit>/trial<N>_<RESULT>/{front,wrist}_chunk<NNN>.jpg
as HARD LINKS to the raw files (no extra disk, raw folder untouched). Re-run after each bench row and add the row to
ROWS below. Blocks lost to the 2026-10-28 recorder overwrite get a LOST.txt instead of frames."""
import os, csv, pathlib
R3 = "results/so101_lora_on_top_20261019/bench_frames_row3_010000"; BASE = "results/so101_bench_20261019/frames"
OUT = pathlib.Path("results/bench_frames_by_trial")
# row -> (raw dir, prefix, cap, first call of trial 1, lost call ranges)
ROWS = {"ctrl": (BASE, "c01", 45, 1, []), "A": (R3, "c01", 45, 1, [(1, 48)]), "B": (R3, "c02", 75, 1, [(1, 348)]), "C": (R3, "c03", 75, 1, [(1, 65)]),
        "D": (R3, "c04", 75, 1, [(1, 75)]), "E": (R3, "c05", 75, 1, []), "F": (R3, "c02", 75, 1, []), "G": (R3, "c04", 75, 1, []),
        "H": (R3, "c07", 75, 1, []), "I": (R3, "c08", 75, 1, [])}
DAY = {"2026-10-26": "sun", "2026-10-28": "tue", "2026-10-29": "wed"}
trials = list(csv.DictReader(open("results/so101_bench_20261019/trials.csv")))
made = 0; readme = ["# Bench frames, one folder per trial", "", "Hard links into the raw server dump (see scripts/sort_bench_frames.py). "
          "Names: `<date>_<day>_row<X>_<model>_<fruit>/trial<N>_<RESULT>/front_chunk<NNN>.jpg` (overhead camera) and `wrist_chunk<NNN>.jpg`. "
          "Chunk NNN = the NNN-th policy call of that trial (one call = 20 arm steps at 30 Hz ≈ 0.7 s of motion + the round trip).", "", "| folder | trials | note |", "|---|---|---|"]
for row, (raw, pref, cap, first, lost) in ROWS.items():
    tr = [t for t in trials if t["row"] == row]
    if not tr: continue
    t0 = tr[0]; model = "base" if t0["model"] == "base" else "ft3"; fruit = t0["fruit"].split()[0]
    folder = OUT / f"{t0['date']}_{DAY.get(t0['date'],'')}_row{row}_{model}_{fruit}"; folder.mkdir(parents=True, exist_ok=True)
    notes = []
    for t in tr:
        n = int(t["trial"]); d = folder / f"trial{n}_{t['result'].replace('?','_pending')}"; d.mkdir(exist_ok=True)
        a, b = first + (n - 1) * cap, first + n * cap - 1
        lost_here = [(max(a, x), min(b, y)) for x, y in lost if x <= b and y >= a]
        if lost_here and lost_here[0][0] == a and lost_here[0][1] >= b - 2:
            (d / "LOST.txt").write_text(f"raw frames {pref} calls {a}-{b} were overwritten by the 2026-10-28 server restart; see results/so101_lora_on_top_20261019/bench_row3*_T{n}.jpg for the composite built before the loss\n"); notes.append(f"trial {n} frames lost"); continue
        for c in range(a, b + 1):
            if any(x <= c <= y for x, y in lost_here): continue
            for cam in ("front", "wrist"):
                src = pathlib.Path(raw) / f"{pref}_call{c:06d}_{cam}.jpg"; dst = d / f"{cam}_chunk{c - a + 1:03d}.jpg"
                if src.exists() and not dst.exists():
                    try: os.link(src, dst)
                    except OSError: import shutil; shutil.copy2(src, dst)
                    made += 1
        (d / "WHAT_HAPPENED.txt").write_text(f"{t['result']} — {t['what_happened']}\nplacement: {t['placement']}; tray: {t['tray']}; instruction: {t['instruction']}; cap {cap} chunks\n")
    readme.append(f"| {folder.name} | {len(tr)} | {'; '.join(notes) if notes else ''} |")
(OUT / "README.md").write_text("\n".join(readme) + "\n"); print("linked files:", made)
