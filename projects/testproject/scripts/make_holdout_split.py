"""Split the 89-episode dataset into 79 train / 10 held-out.

Why: the A/B between the two camera variants is only meaningful if both are
scored on episodes neither of them trained on. Scoring on training data measures
memorisation, and would crown whichever variant memorises more easily.

The SAME 10 episodes are held out from both variants, so the comparison is like
for like. The held-out episodes stay in the original 89-episode directories,
which is where the probe reads them from - nothing is deleted.

Videos are symlinked (they are the bulk of the bytes and are never modified).
Parquet files are rewritten because `episode_index` and the global `index`
column must be renumbered to stay contiguous after removing episodes.

Usage: make_holdout_split.py
"""

import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/kiran/lerobot_assets/datasets")
VARIANTS = ["so101_orange_89_v21", "so101_orange_89_v21_topfront"]
N_HOLDOUT = 10
SEED = 20260817


def split_one(name: str, holdout: list[int]) -> None:
    src = ROOT / name
    dst = ROOT / f"{name}_train79"
    if dst.exists():
        shutil.rmtree(dst)

    eps_meta = [
        json.loads(line) for line in (src / "meta/episodes.jsonl").read_text().splitlines() if line.strip()
    ]
    stats_meta = [
        json.loads(line)
        for line in (src / "meta/episodes_stats.jsonl").read_text().splitlines()
        if line.strip()
    ]
    by_idx = {e["episode_index"]: e for e in eps_meta}
    stats_by_idx = {e["episode_index"]: e for e in stats_meta}

    keep = [e for e in sorted(by_idx) if e not in holdout]
    cams = sorted(p.name for p in (src / "videos/chunk-000").iterdir())

    (dst / "data/chunk-000").mkdir(parents=True)
    (dst / "meta").mkdir(parents=True)
    for c in cams:
        (dst / "videos/chunk-000" / c).mkdir(parents=True)

    new_eps, new_stats, running, total_frames = [], [], 0, 0
    for new_i, old_i in enumerate(keep):
        df = pd.read_parquet(src / f"data/chunk-000/episode_{old_i:06d}.parquet")
        df["episode_index"] = np.int64(new_i)
        df["index"] = np.arange(running, running + len(df), dtype=np.int64)
        running += len(df)
        total_frames += len(df)
        df.to_parquet(dst / f"data/chunk-000/episode_{new_i:06d}.parquet", index=False)

        for c in cams:
            os.symlink(
                src / f"videos/chunk-000/{c}/episode_{old_i:06d}.mp4",
                dst / f"videos/chunk-000/{c}/episode_{new_i:06d}.mp4",
            )

        e = dict(by_idx[old_i])
        e["episode_index"] = new_i
        new_eps.append(e)
        s = dict(stats_by_idx[old_i])
        s["episode_index"] = new_i
        new_stats.append(s)

    (dst / "meta/episodes.jsonl").write_text("".join(json.dumps(e) + "\n" for e in new_eps))
    (dst / "meta/episodes_stats.jsonl").write_text("".join(json.dumps(e) + "\n" for e in new_stats))

    info = json.loads((src / "meta/info.json").read_text())
    info["total_episodes"] = len(keep)
    info["total_frames"] = total_frames
    info["total_videos"] = len(keep) * len(cams)
    info["splits"] = {"train": f"0:{len(keep)}"}
    (dst / "meta/info.json").write_text(json.dumps(info, indent=4))

    for f in ("tasks.jsonl", "modality.json", "stats.json", "relative_stats.json"):
        if (src / "meta" / f).exists():
            shutil.copy2(src / "meta" / f, dst / "meta" / f)

    print(f"  {dst.name}: {len(keep)} episodes, {total_frames} frames, {len(keep) * len(cams)} videos")


rng = np.random.default_rng(SEED)
all_eps = sorted(
    int(p.stem.split("_")[-1]) for p in (ROOT / VARIANTS[0] / "data/chunk-000").glob("*.parquet")
)
holdout = sorted(rng.choice(all_eps, N_HOLDOUT, replace=False).tolist())
print(f"held-out episodes (identical for both variants): {holdout}")

for v in VARIANTS:
    split_one(v, holdout)

(ROOT / "holdout_episodes.json").write_text(json.dumps({"seed": SEED, "holdout": holdout}, indent=2))
print(f"\nheld-out list written to {ROOT / 'holdout_episodes.json'}")
