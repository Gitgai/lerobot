"""Merge ALL 89 orange-pick demos (so101_orange_89_v21) with the 20 plate demos (plate_demos_v21) into one v2.1
set: orange89_plus_plate20 (109 episodes, 55,660 frames). For R5 (LoRA on top of dongyoonkim/so101-pi05-base).

Why a new merge: orange79_plus_plate20 holds only the 79-episode TRAIN split of the orange set (its 10 hold-out
episodes were kept out for the August/September evaluations). R5 has its own gate (Isaac + the bench), so the
10 hold-out episodes go INTO training here; the open-loop sanity check in the R5 plan uses them only as a
"seen-data" floor, not as a held-out metric. Same mechanics as merge_orange_plus_plate.py: parquets rewritten
(episode_index / index / task_index renumbered), videos symlinked to their resolved targets, two task strings kept.

Refuses to overwrite an existing destination (deleting a dataset is RED).
"""
import json, os, shutil, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path("/home/kiran/lerobot_assets/datasets")
SOURCES = [
    (ROOT / "so101_orange_89_v21", 0, "pick up the orange and move it to another place"),
    (ROOT / "plate_demos_v21", 1, "pick up the orange and place it on the plate"),
]
DST = ROOT / "orange89_plus_plate20"
CAMS = ["observation.images.front", "observation.images.wrist"]

if DST.exists():
    sys.exit(f"refusing to overwrite {DST} (delete it yourself if you mean it)")
(DST / "data/chunk-000").mkdir(parents=True); (DST / "meta").mkdir(parents=True)
for c in CAMS: (DST / "videos/chunk-000" / c).mkdir(parents=True)

new_i, running, eps_meta, stats_lines = 0, 0, [], []
for src, task_idx, task_str in SOURCES:
    eps = sorted(int(p.stem.split("_")[-1]) for p in (src / "data/chunk-000").glob("*.parquet"))
    ep_stats = {}
    p = src / "meta/episodes_stats.jsonl"
    if p.exists():
        for l in p.read_text().splitlines():
            if l.strip(): d = json.loads(l); ep_stats[d["episode_index"]] = d["stats"]
    print(f"{src.name}: {len(eps)} episodes -> task {task_idx}")
    for old_i in eps:
        df = pd.read_parquet(src / f"data/chunk-000/episode_{old_i:06d}.parquet")
        df["episode_index"] = np.int64(new_i); df["index"] = np.arange(running, running + len(df), dtype=np.int64)
        df["task_index"] = np.int64(task_idx); running += len(df)
        df.to_parquet(DST / f"data/chunk-000/episode_{new_i:06d}.parquet", index=False)
        for c in CAMS:
            os.symlink((src / f"videos/chunk-000/{c}/episode_{old_i:06d}.mp4").resolve(), DST / f"videos/chunk-000/{c}/episode_{new_i:06d}.mp4")
        eps_meta.append({"episode_index": new_i, "tasks": [task_str], "length": int(len(df))})
        if old_i in ep_stats: stats_lines.append(json.dumps({"episode_index": new_i, "stats": ep_stats[old_i]}))
        new_i += 1

(DST / "meta/episodes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eps_meta))
(DST / "meta/tasks.jsonl").write_text("".join(json.dumps({"task_index": t, "task": s}) + "\n" for _, t, s in SOURCES))
if stats_lines: (DST / "meta/episodes_stats.jsonl").write_text("\n".join(stats_lines) + "\n")
info = json.loads((SOURCES[0][0] / "meta/info.json").read_text())
info.update(total_episodes=new_i, total_frames=running, total_videos=new_i * len(CAMS), total_tasks=len(SOURCES), splits={"train": f"0:{new_i}"})
(DST / "meta/info.json").write_text(json.dumps(info, indent=4))
for f in ("modality.json", "stats.json", "relative_stats.json"):
    p = SOURCES[0][0] / "meta" / f
    if p.exists(): shutil.copy2(p, DST / "meta" / f)
print(f"merged: {new_i} episodes, {running} frames, {len(stats_lines)} per-episode stats -> {DST}")
broken = [p for p in (DST / "videos").rglob("*.mp4") if not p.resolve().exists()]
print(f"broken video links: {len(broken)}" if broken else "all video links resolve")
