"""Merge several v2.1 LeRobot sets (front + wrist, 30 fps, so101) into one, renumbering episodes/index/task_index and
symlinking videos (no re-encode). Generalises merge_orange89_plus_plate20.py. Refuses to overwrite.
  python merge_real_sets_v21.py --out all169_aug_low_sep_overhead \
      --src so101_orange_89_v21 --src plate_demos_v21 --src new30_merged --src recovery30_v21
Task strings are taken from each source's own tasks.jsonl (so a source with two tasks keeps both).
2026-10-24: built for R5 row 3 after finding 60 September episodes (20 orange + 10 tomato + 30 recovery, overhead front
camera) that the row-1/row-2 merge had missed.
"""
import argparse, json, os, shutil, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path("/home/kiran/lerobot_assets/datasets")
CAMS = ["observation.images.front", "observation.images.wrist"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--src", action="append", required=True)
    a = ap.parse_args(); dst = ROOT / a.out
    if dst.exists(): sys.exit(f"refusing to overwrite {dst}")
    (dst / "data/chunk-000").mkdir(parents=True); (dst / "meta").mkdir(parents=True)
    for c in CAMS: (dst / "videos/chunk-000" / c).mkdir(parents=True)
    tasks = {}; new_i = running = 0; eps_meta = []; stats_lines = []; per_src = []
    for name in a.src:
        src = ROOT / name
        src_tasks = {int(json.loads(l)["task_index"]): json.loads(l)["task"] for l in (src / "meta/tasks.jsonl").read_text().splitlines() if l.strip()}
        ep_stats = {}
        p = src / "meta/episodes_stats.jsonl"
        if p.exists():
            for l in p.read_text().splitlines():
                if l.strip(): d = json.loads(l); ep_stats[d["episode_index"]] = d["stats"]
        eps = sorted(int(q.stem.split("_")[-1]) for q in (src / "data/chunk-000").glob("*.parquet"))
        n0 = new_i
        for old_i in eps:
            df = pd.read_parquet(src / f"data/chunk-000/episode_{old_i:06d}.parquet")
            old_t = int(df["task_index"].iloc[0]); t_str = src_tasks[old_t]
            if t_str not in tasks: tasks[t_str] = len(tasks)
            df["episode_index"] = np.int64(new_i); df["index"] = np.arange(running, running + len(df), dtype=np.int64); df["task_index"] = np.int64(tasks[t_str])
            running += len(df); df.to_parquet(dst / f"data/chunk-000/episode_{new_i:06d}.parquet", index=False)
            for c in CAMS: os.symlink((src / f"videos/chunk-000/{c}/episode_{old_i:06d}.mp4").resolve(), dst / f"videos/chunk-000/{c}/episode_{new_i:06d}.mp4")
            eps_meta.append({"episode_index": new_i, "tasks": [t_str], "length": int(len(df))})
            if old_i in ep_stats: stats_lines.append(json.dumps({"episode_index": new_i, "stats": ep_stats[old_i]}))
            new_i += 1
        per_src.append((name, new_i - n0)); print(f"{name}: {new_i - n0} episodes")
    (dst / "meta/episodes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eps_meta))
    (dst / "meta/tasks.jsonl").write_text("".join(json.dumps({"task_index": i, "task": t}) + "\n" for t, i in tasks.items()))
    if stats_lines: (dst / "meta/episodes_stats.jsonl").write_text("\n".join(stats_lines) + "\n")
    info = json.loads((ROOT / a.src[0] / "meta/info.json").read_text())
    info.update(total_episodes=new_i, total_frames=running, total_videos=new_i * len(CAMS), total_tasks=len(tasks), splits={"train": f"0:{new_i}"})
    (dst / "meta/info.json").write_text(json.dumps(info, indent=4))
    for f in ("modality.json", "stats.json", "relative_stats.json"):
        p = ROOT / a.src[0] / "meta" / f
        if p.exists(): shutil.copy2(p, dst / "meta" / f)
    (dst / "meta/SOURCES.json").write_text(json.dumps({"sources": per_src, "tasks": tasks}, indent=1))
    broken = [p for p in (dst / "videos").rglob("*.mp4") if not p.resolve().exists()]
    print(f"merged: {new_i} episodes, {running} frames, {len(tasks)} tasks, {len(stats_lines)} per-episode stats -> {dst}; broken links: {len(broken)}")


if __name__ == "__main__":
    main()
