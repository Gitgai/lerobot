"""E1 v2 — WHICH CAMERAS WILL THE MODEL ACTUALLY RECEIVE?

Supersedes preflight_batch_check.py, WHICH GAVE A FALSE PASS on 2026-08-14.

WHY v1 WAS WRONG
----------------
v1 encoded one universal rule: "lerobot builds input_features FROM THE DATASET,
therefore renaming an image key GUARANTEES a mismatch." That rule is real but it
only holds for FRESH policies. lerobot says so itself (configs/train.py:249):

    "`rename_map` requires a pretrained policy checkpoint. Fresh initialization
     derives feature names from the current dataset, so no rename is applied."

  fresh   (--policy.type=pi05)  features come from the DATASET; rename_map is REJECTED
  pretrained (--policy.path=…)  features come from the CHECKPOINT; rename_map is how
                                dataset names are mapped ONTO them — often REQUIRED

Every real run here is pretrained, so v1 had the rule exactly backwards and
passed a config that lerobot then refused to start.

WHY A CHECK IS NEEDED AT ALL — lerobot's own validation is opt-out
-----------------------------------------------------------------
policies/factory.py:382

    if not rename_map:
        validate_visual_features_consistency(cfg, features)

⇒ **Supplying a rename_map DISABLES visual validation entirely.** Exactly the
runs that remap cameras — the ones most able to get it wrong — are the ones
lerobot stops checking. And pi05 does not error on a missing camera; it pads it
with -1 and masks it (modeling_pi05.py), so a blanked camera trains happily and
LOSS GOES DOWN, because fewer inputs is a simpler function to fit.

This script therefore reports what the model RECEIVES, empirically, from the
same config objects lerobot itself builds. It does not encode a rule.

Usage:
  python preflight_features.py --dataset REPO --policy-path lerobot/pi05_base \
      [--rename-map '{"observation.images.wrist_image": "..."}']
"""

import argparse
import json
import sys

p = argparse.ArgumentParser()
p.add_argument("--dataset", required=True)
p.add_argument("--policy-path", default=None, help="omit for a FRESH policy")
p.add_argument("--rename-map", default="{}")
p.add_argument("--expect-padded", type=int, default=0,
               help="how many policy cameras you INTEND to be padded (e.g. pi05_base "
                    "has 3 camera slots but LIBERO is a 2-camera setup)")
a = p.parse_args()

from lerobot.configs.policies import PreTrainedConfig
from lerobot.configs.types import FeatureType
from lerobot.datasets.lerobot_dataset import LeRobotDatasetMetadata
from lerobot.utils.feature_utils import dataset_to_policy_features

rename = json.loads(a.rename_map)
meta = LeRobotDatasetMetadata(a.dataset)
ds_feats = dataset_to_policy_features(meta.features)
provided = {rename.get(k, k) for k, v in ds_feats.items() if v.type == FeatureType.VISUAL}

print("=" * 74)
print("PRE-FLIGHT — CAMERAS THE MODEL WILL RECEIVE")
print("=" * 74)
print(f"  dataset       {a.dataset}")
print(f"  policy        {a.policy_path or 'FRESH (features derived from the dataset)'}")
print(f"  rename_map    {rename if rename else '{} (none)'}")

if a.policy_path is None:
    if rename:
        print("\n  ⛔ FAIL — rename_map with a fresh policy: lerobot rejects this outright.")
        sys.exit(1)
    print("\n  ✅ PASS — fresh policy takes its feature names from the dataset.")
    print("=" * 74)
    sys.exit(0)

# lerobot registers policy configs lazily, so PreTrainedConfig.from_pretrained
# raises "not registered ... Available policy types: {}" until the matching
# module is imported. Mirror what policies/factory.py does.
import importlib

from huggingface_hub import hf_hub_download

_ptype = json.load(open(hf_hub_download(a.policy_path, "config.json")))["type"]
importlib.import_module(f"lerobot.policies.{_ptype}.configuration_{_ptype}")

cfg = PreTrainedConfig.from_pretrained(a.policy_path)
expected = {k for k, v in cfg.input_features.items() if v.type == FeatureType.VISUAL}

padded = sorted(expected - provided)
ignored = sorted(provided - expected)
print(f"\n  policy expects   {sorted(expected)}")
print(f"  batch will carry {sorted(provided)}")
print("=" * 74)

fail = False
if ignored:
    print(f"  ⛔ {len(ignored)} dataset camera(s) the policy will NEVER SEE (silently dropped):")
    for k in ignored:
        print(f"        {k}")
    fail = True
if padded:
    verdict = "EXPECTED" if len(padded) <= a.expect_padded and not ignored else "⛔ UNEXPECTED"
    print(f"  {verdict}: {len(padded)} policy camera(s) will be PADDED with -1 and masked:")
    for k in padded:
        print(f"        {k}")
    if len(padded) > a.expect_padded:
        print(f"\n  You declared --expect-padded={a.expect_padded}. pi05 will train happily")
        print("  on this and LOSS WILL LOOK FINE OR BETTER. Do not launch until the")
        print("  count is intentional.")
        fail = True

if not fail and not padded:
    print("  ✅ PASS — every policy camera is fed, every dataset camera is used.")
elif not fail:
    print("  ✅ PASS — padding is as declared.")
print("=" * 74)
sys.exit(1 if fail else 0)
