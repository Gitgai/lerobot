"""PRE-FLIGHT: will the model actually RECEIVE every camera it expects?

Run BEFORE any long training job. Takes SECONDS. It would have caught the STEP 3g
failure, where --rename_map silently blanked the wrist camera for all 24,000
batches and cost 7 hours of GPU time.

THE RULE
--------
lerobot builds the policy's `input_features` FROM THE DATASET's feature names.
`--rename_map` is applied to the BATCH, *after* those features are fixed.

⇒ Renaming an image key therefore GUARANTEES a mismatch: the model still expects
  the dataset's original name, but the batch now carries the renamed one.

WHY IT IS INVISIBLE WITHOUT AN EXPLICIT CHECK
---------------------------------------------
pi05 does NOT error on a missing camera (modeling_pi05.py):

    missing_img_keys = [k for k in self.config.image_features if k not in batch]
    for _ in range(len(missing_img_keys)):
        img = torch.ones_like(img) * -1     # padded
        mask = torch.zeros_like(mask)       # masked out

The camera is padded and masked. Training runs, and LOSS GOES DOWN — fewer
inputs is a simpler function to fit. STEP 3g's broken run had loss 0.052 against
a healthy run's 0.062, ~18% *better* at every checkpoint, and scored 1-3% instead
of 64.5%. **The degraded run looked better by the metric being watched.**

Usage:
  python preflight_batch_check.py --dataset REPO [--rename-map JSON]
"""

import argparse
import json
import sys

p = argparse.ArgumentParser()
p.add_argument("--dataset", required=True)
p.add_argument("--rename-map", default="{}")
a = p.parse_args()

from lerobot.datasets.lerobot_dataset import LeRobotDatasetMetadata

rename = json.loads(a.rename_map)
meta = LeRobotDatasetMetadata(a.dataset)
ds_imgs = sorted(k for k in meta.features if k.startswith("observation.images"))

# lerobot derives input_features from the DATASET names...
expects = set(ds_imgs)
# ...but --rename_map rewrites the BATCH keys.
batch = {rename.get(k, k) for k in ds_imgs}

missing = sorted(expects - batch)
extra = sorted(batch - expects)

print("=" * 70)
print("PRE-FLIGHT BATCH CHECK")
print("=" * 70)
print(f"  dataset            {a.dataset}")
print(f"  rename_map         {rename if rename else '{} (none)'}")
print(f"  model will expect  {sorted(expects)}")
print(f"  batch will carry   {sorted(batch)}")
print("=" * 70)
if missing:
    print(f"  ⛔ FAIL — {len(missing)} camera(s) will be MISSING and silently padded:")
    for k in missing:
        print(f"        {k}")
    print("\n  pi05 pads these with -1 and masks them. Training will run, loss")
    print("  will look FINE or BETTER, and the model will NEVER see that input.")
    print("  ⇒ DO NOT LAUNCH. Your rename_map is wrong, or unnecessary.")
    if extra:
        print(f"  ⇒ the batch would instead carry: {extra}")
else:
    print("  ✅ PASS — every camera the model expects is present in the batch.")
print("=" * 70)
sys.exit(1 if missing else 0)
