"""Merge the three 2026-09-15 datasets into one 30-episode training set.

    orange_final10_v21      10 eps  ->  task 0  "...the orange..."
    orange_adjusted10_v21   10 eps  ->  task 0  (same sentence: same task,
                                                 the two sets differ only in
                                                 where the wrist camera sat)
    tomato10_v21            10 eps  ->  task 1  "...the tomato..."

NO HOLD-OUT (operator decision, 2026-09-15). All 30 episodes train. Nothing can
be measured offline afterwards; the 3000-step checkpoints are the fallback.

Videos are symlinked and resolved to their real targets - a symlink chain would
break the moment a parent moved. Parquets are rewritten because episode_index,
the global index and task_index all have to be renumbered.

meta/modality.json is COPIED from the 99-episode set: it describes the data
LAYOUT (6 joints split 5 arm + 1 gripper, two cameras named front and wrist),
which is identical here. stats.json and relative_stats.json are NOT copied -
they are statistics, and trimming removed 36% of the frames, nearly all of them
the arm parked at rest. Copied stats would describe a distribution this data no
longer has. Generate them with gr00t/data/stats.py after this script runs.
"""

import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/kiran/lerobot_assets/datasets")
NEW = ROOT / "new30_20260915"
DST = ROOT / "new30_merged"
MODALITY_FROM = ROOT / "orange79_plus_plate20/meta/modality.json"

SOURCES = [
    (NEW / "orange_final10_v21",    0, "pick up the orange and place it on the plate"),
    (NEW / "orange_adjusted10_v21", 0, "pick up the orange and place it on the plate"),
    (NEW / "tomato10_v21",          1, "pick up the tomato and place it on the plate"),
]
CAMS = ["observation.images.front", "observation.images.wrist"]

if DST.exists():
    shutil.rmtree(DST)
(DST / "data/chunk-000").mkdir(parents=True)
(DST / "meta").mkdir(parents=True)
for c in CAMS:
    (DST / "videos/chunk-000" / c).mkdir(parents=True)

new_i, running, eps_meta = 0, 0, []
for src, task_idx, task_str in SOURCES:
    eps = sorted(int(p.stem.split("_")[-1]) for p in (src / "data/chunk-000").glob("*.parquet"))
    print("  %-24s %2d episodes -> task %d" % (src.name, len(eps), task_idx))
    for old_i in eps:
        df = pd.read_parquet(src / ("data/chunk-000/episode_%06d.parquet" % old_i))
        df["episode_index"] = np.int64(new_i)
        df["index"] = np.arange(running, running + len(df), dtype=np.int64)
        df["task_index"] = np.int64(task_idx)
        running += len(df)
        df.to_parquet(DST / ("data/chunk-000/episode_%06d.parquet" % new_i), index=False)
        for c in CAMS:
            tgt = (src / ("videos/chunk-000/%s/episode_%06d.mp4" % (c, old_i))).resolve()
            os.symlink(tgt, DST / ("videos/chunk-000/%s/episode_%06d.mp4" % (c, new_i)))
        eps_meta.append({"episode_index": new_i, "tasks": [task_str], "length": int(len(df))})
        new_i += 1

(DST / "meta/episodes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eps_meta))
seen, tasks = set(), []
for _, t, s in SOURCES:
    if t not in seen:
        seen.add(t); tasks.append({"task_index": t, "task": s})
(DST / "meta/tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tasks))

info = json.loads((SOURCES[0][0] / "meta/info.json").read_text())
info["total_episodes"] = new_i
info["total_frames"] = running
info["total_videos"] = new_i * len(CAMS)
info["total_tasks"] = len(tasks)
info["splits"] = {"train": "0:%d" % new_i}
(DST / "meta/info.json").write_text(json.dumps(info, indent=4))

shutil.copy2(MODALITY_FROM, DST / "meta/modality.json")
print("\n  copied modality.json (layout descriptor, identical here)")

print("  merged: %d episodes, %d frames -> %s" % (new_i, running, DST))
for t in tasks:
    n = sum(1 for e in eps_meta if e["tasks"][0] == t["task"])
    print("    task %d: %2d episodes  %r" % (t["task_index"], n, t["task"]))

broken = [p for p in (DST / "videos").rglob("*.mp4") if not p.resolve().exists()]
print("  broken video links: %d" % len(broken) if broken else "  all 60 video links resolve")
print("\n  NEXT: generate stats -> python -m gr00t.data.stats --dataset-path %s --embodiment-tag new_embodiment" % DST)
