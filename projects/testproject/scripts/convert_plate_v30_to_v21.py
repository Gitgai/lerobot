"""Convert the plate-demo dataset (LeRobot v3.0) to v2.1 for GR00T training.

Simpler than convert_v30_to_v21_orange89.py: that one had to CUT episodes out
of packed multi-episode video files with frame-accurate ffmpeg. Here the
recorder wrote one file per episode already, so each video is copied whole and
each parquet is renamed - no re-encoding, no cutting, no frame drift.

Only the demos that passed verification are carried over; the rejects (no
grasp / already-holding) are dropped by episode index.

    v3.0  data/chunk-000/file-NNN.parquet
          videos/observation.images.CAM/chunk-000/file-NNN.mp4
    v2.1  data/chunk-000/episode_NNNNNN.parquet
          videos/chunk-000/observation.images.CAM/episode_NNNNNN.mp4

Every output episode is verified: parquet row count must equal the video's
frame count, or the conversion fails loudly rather than training on skew.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path("/home/kiran/lerobot_assets/datasets/plate_demos_v30")
DST = Path("/home/kiran/lerobot_assets/datasets/plate_demos_v21")
# episodes rejected during recording: 1, 3 (gripper never closed), 6 (already
# holding at frame 0 - a crashed attempt left the orange in the gripper)
REJECT = {1, 3, 6}
CAMS = ["observation.images.front", "observation.images.wrist"]


def frame_count(mp4: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(mp4)],
        capture_output=True, text=True).stdout.strip()
    return int(out) if out.isdigit() else -1


meta = pd.concat([pd.read_parquet(p)
                  for p in sorted((SRC / "meta/episodes").rglob("*.parquet"))])
keep = [e for e in sorted(meta["episode_index"].unique()) if int(e) not in REJECT]
print(f"source episodes {len(meta)}, rejected {sorted(REJECT)}, converting {len(keep)}")

if DST.exists():
    shutil.rmtree(DST)
(DST / "data/chunk-000").mkdir(parents=True)
(DST / "meta").mkdir(parents=True)
for c in CAMS:
    (DST / "videos/chunk-000" / c).mkdir(parents=True)

rows, running, failures = [], 0, []
for new_i, old_i in enumerate(keep):
    r = meta[meta["episode_index"] == old_i].iloc[0]
    fi = int(r["data/file_index"])
    df = pd.read_parquet(SRC / f"data/chunk-000/file-{fi:03d}.parquet")
    df = df[df["episode_index"] == old_i].copy()
    df["episode_index"] = np.int64(new_i)
    df["index"] = np.arange(running, running + len(df), dtype=np.int64)
    df["frame_index"] = np.arange(len(df), dtype=np.int64)
    running += len(df)
    df.to_parquet(DST / f"data/chunk-000/episode_{new_i:06d}.parquet", index=False)

    for c in CAMS:
        vfi = int(r[f"videos/{c}/file_index"])
        src_mp4 = SRC / f"videos/{c}/chunk-000/file-{vfi:03d}.mp4"
        dst_mp4 = DST / f"videos/chunk-000/{c}/episode_{new_i:06d}.mp4"
        shutil.copy2(src_mp4, dst_mp4)
        n = frame_count(dst_mp4)
        if n != len(df):
            failures.append(f"ep {new_i} ({c}): {n} video frames vs {len(df)} rows")

    rows.append({"episode_index": new_i,
                 "tasks": [r["tasks"][0] if isinstance(r["tasks"], (list, np.ndarray)) else r["tasks"]],
                 "length": int(len(df))})
    print(f"  ep {old_i:>3} -> {new_i:>3}  {len(df)} frames")

(DST / "meta/episodes.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))

info = json.loads((SRC / "meta/info.json").read_text())
info["codebase_version"] = "v2.1"
info["total_episodes"] = len(rows)
info["total_frames"] = running
info["total_videos"] = len(rows) * len(CAMS)
info["total_chunks"] = 1
info["splits"] = {"train": f"0:{len(rows)}"}
info["data_path"] = "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet"
info["video_path"] = "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"
(DST / "meta/info.json").write_text(json.dumps(info, indent=4))

tasks = pd.read_parquet(SRC / "meta/tasks.parquet")
task_str = tasks.index[0] if tasks.index.name == "task" else tasks.iloc[0, 0]
(DST / "meta/tasks.jsonl").write_text(json.dumps({"task_index": 0, "task": str(task_str)}) + "\n")

print(f"\nwrote {len(rows)} episodes, {running} frames -> {DST}")
if failures:
    print("FRAME-COUNT MISMATCHES (do not train on this):")
    for f in failures:
        print("  " + f)
    raise SystemExit(1)
print("all episodes verified: video frames == parquet rows")
