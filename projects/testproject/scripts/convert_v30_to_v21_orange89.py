"""Convert the 89-episode real dataset from LeRobot v3.0 to v2.1 for gr00t.

WHY: the gr00t fine-tuner (launch_finetune.py) loads datasets through
LeRobotEpisodeLoader, which expects LeRobot v2.1 layout - meta/episodes.jsonl,
one parquet per episode, one mp4 per episode per camera. The 89-episode set is
v3.0: packed multi-episode files addressed by timestamp windows. The smoke test
failed on exactly this (FileNotFoundError: meta/episodes.jsonl, 2026-08-17).
LeRobot ships only the v2.1 -> v3.0 upgrade converter, so this is the downgrade,
written against the layout of the KNOWN-WORKING LeIsaac v2.1 dataset as the
template.

Deliberate choices:
  - output carries ONLY front + wrist (the modality config's two cameras).
    The v3 set's third camera (`top`) is dropped - the policy never consumes it,
    and the known-working template dataset declares exactly two.
  - FOCUS episodes (40 of the 89) reference the same source video through
    overlapping timestamp windows. Each gets its own physical clip in v2.1;
    duplicated pixels are the cost of the format, ~35% extra video.
  - video cutting is done with ffmpeg input-seek + re-encode (libx264 yuv420p,
    matching both datasets' existing codec), which is frame-accurate; every
    clip's frame count is VERIFIED against the episode length afterwards.
    Stream-copy would cut at keyframes and silently misalign frames from
    states - the exact class of quiet corruption this project keeps paying for.
  - the ORIGINAL v3 dataset is never touched.

Output: ~/lerobot_assets/datasets/so101_orange_89_v21
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path.home() / "lerobot_assets/datasets/so101_orange_49_plus_grasp_pick_move_focus"
DST = Path.home() / "lerobot_assets/datasets/so101_orange_89_v21"
TPL = Path.home() / "lerobot_assets/datasets/leisaac_pick_orange"  # v2.1 template
MODALITY = Path.home() / "lerobot_assets/checkpoints/gr00t_n16_leisaac_orange/configs_for_gr00t/modality.json"
CAMS = ["front", "wrist"]
FPS = 30

if DST.exists():
    sys.exit(f"refusing to overwrite {DST} - remove it first if you mean to redo this")

# ---- load v3 metadata ------------------------------------------------------
eps_meta = (
    pd.concat([pd.read_parquet(p) for p in sorted(SRC.glob("meta/episodes/**/*.parquet"))])
    .sort_values("episode_index")
    .reset_index(drop=True)
)
data = (
    pd.concat([pd.read_parquet(p) for p in sorted(SRC.glob("data/**/*.parquet"))])
    .sort_values(["episode_index", "frame_index"])
    .reset_index(drop=True)
)
task_tbl = pd.read_parquet(SRC / "meta/tasks.parquet")
TASK = task_tbl.index[0] if task_tbl.index.dtype == object else str(task_tbl.iloc[0].name)
print(f"episodes: {len(eps_meta)}   rows: {len(data)}   task: {TASK!r}", flush=True)

for d in ("meta", "data/chunk-000"):
    (DST / d).mkdir(parents=True)
for cam in CAMS:
    (DST / f"videos/chunk-000/observation.images.{cam}").mkdir(parents=True)


# ---- per-episode data parquets + video clips -------------------------------
def stats_of(a: np.ndarray) -> dict:
    return {
        "min": a.min(0).tolist(),
        "max": a.max(0).tolist(),
        "mean": a.mean(0).tolist(),
        "std": a.std(0).tolist(),
        "count": [int(a.shape[0])],
    }


episodes_jsonl, ep_stats_jsonl = [], []
global_index = 0
fail = 0
for _, em in eps_meta.iterrows():
    ei = int(em["episode_index"])
    rows = data[data["episode_index"] == ei].copy().sort_values("frame_index")
    n = len(rows)
    assert n == int(em["length"]), f"ep {ei}: rows {n} != meta length {em['length']}"

    rows["frame_index"] = np.arange(n, dtype=np.int64)
    rows["timestamp"] = (np.arange(n) / FPS).astype(np.float32)
    rows["episode_index"] = np.int64(ei)
    rows["task_index"] = np.int64(0)
    rows["index"] = np.arange(global_index, global_index + n, dtype=np.int64)
    global_index += n
    keep = ["action", "observation.state", "timestamp", "frame_index", "episode_index", "index", "task_index"]
    rows[keep].to_parquet(DST / f"data/chunk-000/episode_{ei:06d}.parquet", index=False)

    for cam in CAMS:
        fi = int(em[f"videos/observation.images.{cam}/file_index"])
        ci = int(em[f"videos/observation.images.{cam}/chunk_index"])
        t0 = float(em[f"videos/observation.images.{cam}/from_timestamp"])
        src = SRC / f"videos/observation.images.{cam}/chunk-{ci:03d}/file-{fi:03d}.mp4"
        out = DST / f"videos/chunk-000/observation.images.{cam}/episode_{ei:06d}.mp4"
        r = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{t0:.6f}",
                "-i",
                str(src),
                "-frames:v",
                str(n),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-g",
                "2",
                "-y",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(f"ep {ei} {cam}: FFMPEG FAILED: {r.stderr[:200]}", flush=True)
            fail += 1
            continue
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-count_frames",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=nb_read_frames",
                "-of",
                "csv=p=0",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        got = int(probe.stdout.strip() or 0)
        if got != n:
            print(f"ep {ei} {cam}: FRAME MISMATCH clip={got} expected={n}", flush=True)
            fail += 1

    episodes_jsonl.append({"episode_index": ei, "tasks": [TASK], "length": n})
    st = {
        "action": stats_of(np.stack(rows["action"].to_numpy())),
        "observation.state": stats_of(np.stack(rows["observation.state"].to_numpy())),
    }
    ep_stats_jsonl.append({"episode_index": ei, "stats": st})
    if ei % 10 == 0:
        print(f"  episode {ei}/{len(eps_meta) - 1} done", flush=True)

# ---- metadata --------------------------------------------------------------
with open(DST / "meta/episodes.jsonl", "w") as f:
    for e in episodes_jsonl:
        f.write(json.dumps(e) + "\n")
with open(DST / "meta/tasks.jsonl", "w") as f:
    f.write(json.dumps({"task_index": 0, "task": TASK}) + "\n")
with open(DST / "meta/episodes_stats.jsonl", "w") as f:
    for e in ep_stats_jsonl:
        f.write(json.dumps(e) + "\n")

A = np.stack(data["action"].to_numpy())
S = np.stack(data["observation.state"].to_numpy())
with open(DST / "meta/stats.json", "w") as f:
    json.dump({"action": stats_of(A), "observation.state": stats_of(S)}, f, indent=2)

tpl_info = json.loads((TPL / "meta/info.json").read_text())
src_info = json.loads((SRC / "meta/info.json").read_text())
info = dict(tpl_info)
info.update(
    {
        "total_episodes": len(episodes_jsonl),
        "total_frames": int(sum(e["length"] for e in episodes_jsonl)),
        "total_videos": len(episodes_jsonl) * len(CAMS),
        "splits": {"train": f"0:{len(episodes_jsonl)}"},
    }
)
feats = {}
for k in ("action", "observation.state"):
    feats[k] = src_info["features"][k]
for cam in CAMS:
    fv = dict(tpl_info["features"][f"observation.images.{cam}"])
    feats[f"observation.images.{cam}"] = fv
for k in ("timestamp", "frame_index", "episode_index", "index", "task_index"):
    feats[k] = tpl_info["features"][k]
info["features"] = feats
(DST / "meta/info.json").write_text(json.dumps(info, indent=2))
shutil.copy(MODALITY, DST / "meta/modality.json")

print(
    f"\nDONE. {len(episodes_jsonl)} episodes, {global_index} rows, "
    f"{len(episodes_jsonl) * len(CAMS)} clips, verification failures: {fail}"
)
print(f"output: {DST}")
if fail:
    sys.exit(1)
