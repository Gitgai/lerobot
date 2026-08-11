"""Compute q01/q99 quantile stats for a LeRobot dataset — LOCAL ONLY, no upload.

lerobot's own scripts/augment_dataset_quantile_stats.py does the right computation
but then calls dataset.push_to_hub() and creates a tag on the repo. For
lerobot/libero_spatial_image that is someone else's public dataset, so this
variant stops after write_stats() and never touches the Hub.

Why it is needed: pi05 normalizes STATE and ACTION with NormalizationMode.QUANTILES
(configuration_pi05.py), and libero_spatial_image predates the quantile feature:

    ValueError: QUANTILES normalization mode requires q01 and q99 stats
"""

import sys

from lerobot.datasets import LeRobotDataset, write_stats
from lerobot.scripts.augment_dataset_quantile_stats import (
    compute_quantile_stats_for_dataset,
    has_quantile_stats,
)
from lerobot.utils.utils import init_logging

REPO_ID = "lerobot/libero_spatial_image"

init_logging()
print(f"loading {REPO_ID} ...")
ds = LeRobotDataset(repo_id=REPO_ID)
print(f"  {ds.meta.total_episodes} episodes / {ds.meta.total_frames} frames")
print(f"  local root: {ds.meta.root}")

if has_quantile_stats(ds.meta.stats):
    print("already has quantile stats — nothing to do")
    sys.exit(0)

print("computing quantile stats (image/video frames sub-sampled per episode) ...")
new_stats = compute_quantile_stats_for_dataset(ds, use_sampling=True)

ds.meta.stats = new_stats
write_stats(new_stats, ds.meta.root)
print(f"wrote stats to {ds.meta.root}")

# Verify what the training run will actually look for.
missing = []
for key in ("observation.state", "action"):
    s = new_stats.get(key, {})
    for q in ("q01", "q99"):
        if q not in s:
            missing.append(f"{key}.{q}")
print(f"\nq01/q99 present for observation.state and action: {'YES' if not missing else 'NO ' + str(missing)}")
print("NOT pushed to the Hub — local only, by design.")
sys.exit(0 if not missing else 1)
