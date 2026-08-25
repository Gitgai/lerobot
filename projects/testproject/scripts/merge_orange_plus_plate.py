"""Merge the 79 orange-pick demos with the 20 plate demos into one v2.1 set.

WHY MIX rather than train on the plate demos alone: program addendum A5. The
plate round must not cost us the 9/10 orange-picking skill, and the defence
against catastrophic forgetting is replay - the old demos stay in the training
data. Detection (re-running B0 afterwards) is not prevention.

Two DIFFERENT task strings survive the merge, one per behaviour:
    task 0  "pick up the orange and move it to another place"   79 episodes
    task 1  "pick up the orange and place it on the plate"      20 episodes
That is deliberate. It is also the first time this project's data has ever
contained more than one instruction, so it is the first chance the language
channel has to carry any information at all.

Videos are symlinked (resolved to their real targets - the orange set's own
videos are already symlinks from the hold-out split, and a symlink chain would
break the moment either parent moved). Parquets are rewritten because
episode_index, the global index and task_index all have to be renumbered.
"""

import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/kiran/lerobot_assets/datasets")
SOURCES = [
    (ROOT / "so101_orange_89_v21_train79", 0, "pick up the orange and move it to another place"),
    (ROOT / "plate_demos_v21", 1, "pick up the orange and place it on the plate"),
]
DST = ROOT / "orange79_plus_plate20"
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
    print(f"{src.name}: {len(eps)} episodes -> task {task_idx}")
    for old_i in eps:
        df = pd.read_parquet(src / f"data/chunk-000/episode_{old_i:06d}.parquet")
        df["episode_index"] = np.int64(new_i)
        df["index"] = np.arange(running, running + len(df), dtype=np.int64)
        df["task_index"] = np.int64(task_idx)
        running += len(df)
        df.to_parquet(DST / f"data/chunk-000/episode_{new_i:06d}.parquet", index=False)

        for c in CAMS:
            src_mp4 = (src / f"videos/chunk-000/{c}/episode_{old_i:06d}.mp4").resolve()
            os.symlink(src_mp4, DST / f"videos/chunk-000/{c}/episode_{new_i:06d}.mp4")

        eps_meta.append({"episode_index": new_i, "tasks": [task_str], "length": int(len(df))})
        new_i += 1

(DST / "meta/episodes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eps_meta))
(DST / "meta/tasks.jsonl").write_text(
    "".join(json.dumps({"task_index": t, "task": s}) + "\n" for _, t, s in SOURCES))

info = json.loads((SOURCES[0][0] / "meta/info.json").read_text())
info["total_episodes"] = new_i
info["total_frames"] = running
info["total_videos"] = new_i * len(CAMS)
info["total_tasks"] = len(SOURCES)
info["splits"] = {"train": f"0:{new_i}"}
(DST / "meta/info.json").write_text(json.dumps(info, indent=4))

for f in ("modality.json", "stats.json", "relative_stats.json", "episodes_stats.jsonl"):
    p = SOURCES[0][0] / "meta" / f
    if p.exists():
        shutil.copy2(p, DST / "meta" / f)

print(f"\nmerged: {new_i} episodes, {running} frames -> {DST}")
broken = [p for p in (DST / "videos").rglob("*.mp4") if not p.resolve().exists()]
print(f"broken video links: {len(broken)}" if broken else "all video links resolve")
