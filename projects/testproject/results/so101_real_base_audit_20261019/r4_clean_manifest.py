"""R4: the cleaned manifest — which of the 13,969 episodes WE would train on, and how (rules in the R plan).
Inputs: manifest.csv (R0.5 per-episode verdicts), sources.csv (per-source fps/cams), meta/*. Output: manifest_clean.csv
with one row per episode: keep flag, slot_fix flag, bucket (real30 / real10 / sim), quality flags, orange_real flag; and counts.
"""

import collections
import csv
import json
import pathlib
import re
import sys

D = sys.argv[1]
OUT = pathlib.Path(sys.argv[2])
SWAP = {
    "5hadytru/so101_grasp_1",
    "5hadytru/so101_grasp_2",
    "5hadytru/so101_grasp_3",
    "y1y2y3/so101_test8",
    "sabinMlminator/so101_pickplace_cubes_test1",
}  # visual pass: wrist/external swapped
TWO_EXTERNAL = {"TzuShian/so101_white_chess_20251021"}  # visual pass: no wrist view
DARK = {
    "5hadytru/so101_grasp_1",
    "5hadytru/so101_grasp_2",
    "5hadytru/so101_grasp_3",
    "y1y2y3/so101_test8",
    "zacapa/SO101_AVE_07",
}
HAND = {"5hadytru/so101_grasp_2", "LeRobot-worldwide-hackathon/241-Sushi_Shinkansen_So101-pick_sushi"}
SIM = re.compile(r"isaac|sim_|leisaac|mujoco|genesis|maniskill|gazebo|mimic", re.I)
ORANGE_REAL = {
    "LightwheelAI/so101-place-orange",
    "aaronsu11/so101_fruit",
}  # real orange FRUIT (fruit set: orange tasks only)
src = {r["source"]: r for r in csv.DictReader(open(OUT / "sources.csv"))}
eps = {e["episode_index"]: e for e in map(json.loads, open(D + "/meta/episodes.jsonl"))}
rows = []
for r in csv.DictReader(open(OUT / "manifest.csv")):
    ep = int(r["episode_index"])
    s = r["source"]
    tasks = eps[ep]["tasks"]
    fps = int(float(src[s]["fps"])) if src[s]["fps"] else 30
    sim = bool(SIM.search(s))
    bucket = "sim" if sim else ("real10" if fps <= 12 else "real30")
    flags = []
    if s in SWAP:
        flags.append("slot_swap_fix")
    if s in TWO_EXTERNAL:
        flags.append("two_external_no_wrist")
    if s in DARK:
        flags.append("dark_wrist")
    if s in HAND:
        flags.append("hand_in_frame")
    drop = []
    if r["verdict"] != "keep":
        drop.append(r["verdict"])  # exact_dup / short / static
    if bucket == "sim":
        drop.append("sim")
    if bucket == "real10":
        drop.append("fps10")
    orange_real = (s in ORANGE_REAL) and any("orange" in t.lower() for t in tasks)
    rows.append(
        dict(
            episode_index=ep,
            source=s,
            bucket=bucket,
            keep=int(not drop),
            drop_reason=",".join(drop),
            flags=",".join(flags),
            orange_real=int(orange_real),
            length=r["length"],
            task=r["task"],
        )
    )
with open(OUT / "manifest_clean.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
n = len(rows)
keep = [r for r in rows if r["keep"]]
print(f"episodes {n}; KEEP (real, 30 fps, not dup/degenerate) {len(keep)} = {100 * len(keep) / n:.1f}%")
print(
    "dropped by reason:", dict(collections.Counter(d for r in rows for d in r["drop_reason"].split(",") if d))
)
print("kept by flag:", dict(collections.Counter(fl for r in keep for fl in r["flags"].split(",") if fl)))
print("kept needing the slot swap:", sum(1 for r in keep if "slot_swap_fix" in r["flags"]))
print(
    "kept with 1/2/3 real cameras:",
    {
        k: sum(1 for r in keep if sum(float(src[r["source"]][c]) > 0.5 for c in ("base", "lw", "rw")) == k)
        for k in (1, 2, 3)
    },
)
print(
    "real orange-fruit episodes kept:",
    sum(r["orange_real"] for r in keep),
    "| sources:",
    dict(collections.Counter(r["source"] for r in keep if r["orange_real"])),
)
print("kept sources:", len({r["source"] for r in keep}), "of", len(src))
print("wrote", OUT / "manifest_clean.csv")
