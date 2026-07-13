# Pi05 Base To Orange Fine-Tune Plan

## 1. Goal

This document describes the direct experiment:

```text
lerobot/pi05_base
  -> fine-tune on our SO-101 orange-pick dataset
  -> our orange Pi05 checkpoint
```

The direct-base path is useful because it answers a clean question:

```text
Can Pi05 base learn our SO-101 orange task from our small dataset directly?
```

It may need more GPU memory, more steps, or full fine-tuning to work well. The
first attempt should still be expert-only because that is the cheapest way to
verify the pipeline.

## 2. Dataset

Use the 49-episode orange dataset:

```text
/data/lerobot_datasets/so101_orange_49
```

Verified local facts:

```text
episodes: 49
frames: 29,724
fps: 30
cameras: observation.images.front, observation.images.top, observation.images.wrist
state: observation.state shape=[6]
action: action shape=[6]
task: pick up the orange and move it to another place
```

There is also a 30-episode cleaned action-start dataset:

```text
/data/lerobot_datasets/so101_pick_orange_move_action_start_view
```

That dataset is useful for a smaller/cleaner ablation. For this direct-base
experiment, use the dedicated orange49 scripts in `scripts/runpod/`.

## 3. Why Direct Base Is Harder

`lerobot/pi05_base` is a broad base model. Before fine-tuning it is not already
adapted to our exact SO-101 setup.

The fine-tune has to teach:

```text
SO-101 6D state/action format
front/top/wrist camera semantics
joint/action normalization statistics
the orange pick-and-move behavior
our camera angles, table, lighting, and object placement
```

The smoke test is mandatory because it proves LeRobot can instantiate a Pi05
checkpoint from raw base while using our dataset's SO-101 feature schema.

## 4. GPU Recommendation

Start with expert-only fine-tuning:

```text
--policy.train_expert_only=true
--policy.gradient_checkpointing=true
--policy.dtype=bfloat16
```

This may fit on an A40/L40S-class GPU depending on the LeRobot/Pi05 version and
batch size. Use `BATCH_SIZE=1` for the first direct-base run.

Full fine-tuning, where the large model body is also updated, may need an
A100 80GB-class GPU. Do not start with full fine-tuning until the expert-only
pipeline has passed a smoke test.

## 5. Package The Dataset Locally

Before packaging, validate the local dataset metadata:

```bash
python3 - <<'PY'
import json
from pathlib import Path

root = Path("/data/lerobot_datasets/so101_orange_49")
info = json.loads((root / "meta/info.json").read_text())
features = info["features"]
required = [
    "action",
    "observation.state",
    "observation.images.front",
    "observation.images.top",
    "observation.images.wrist",
]
missing = [name for name in required if name not in features]
print("episodes:", info.get("total_episodes"))
print("frames:", info.get("total_frames"))
print("fps:", info.get("fps"))
print("missing:", missing)
assert info.get("total_episodes") == 49
assert not missing
PY
```

Run on the laptop with the 49-episode dataset override:

```bash
cd /home/gaikwad-prakash/PrakashProjects/testproject

./scripts/runpod/package_orange49_dataset.sh
```

Expected output:

```text
/data/downloads/so101_orange_49.tar.gz
```

## 6. Upload To RunPod

If a previous copy exists on the pod, remove it before extracting a new tarball:

```bash
ssh -i ~/.ssh/runpod_ed25519 -p <ssh-port> root@<pod-ip> \
  'rm -rf /workspace/lerobot_datasets/so101_orange_49'
```

Then run on the laptop, replacing the host and port with the active pod SSH
details:

```bash
cd /home/gaikwad-prakash/PrakashProjects/testproject

RUNPOD_HOST=<pod-ip> \
RUNPOD_PORT=<ssh-port> \
SSH_KEY=~/.ssh/runpod_ed25519 \
./scripts/runpod/upload_orange49_dataset_to_runpod.sh
```

The upload script extracts the tarball to:

```text
/workspace/lerobot_datasets/so101_orange_49
```

Verify on the pod after upload:

```bash
test -f /workspace/lerobot_datasets/so101_orange_49/meta/info.json
```

## 7. Prepare The RunPod Environment

On the pod:

```bash
cd /workspace
git clone https://github.com/huggingface/lerobot.git
cd /workspace/lerobot
pip install -e ".[pi]"
```

Use persistent cache paths:

```bash
export HF_HOME=/workspace/hf_cache
export HF_DATASETS_CACHE=/workspace/hf_cache/datasets
export TRANSFORMERS_CACHE=/workspace/hf_cache/transformers
```

If available, set a Hugging Face token for faster and more reliable downloads:

```bash
export HF_TOKEN=<your-hf-token>
```

This is required for direct `lerobot/pi05_base` training because Pi05 loads the
gated Google PaliGemma tokenizer/config:

```text
google/paligemma-3b-pt-224
```

The Hugging Face account behind `HF_TOKEN` must have accepted access to that
model.

The base model download is large, so keep it on `/workspace`, not ephemeral
container storage.

## 8. Smoke Train From Base

Purpose:

```text
prove the pod, LeRobot install, dataset, base model download, and checkpoint
saving path all work
```

This smoke run is also the first check that `lerobot/pi05_base` can be adapted
to the dataset's 6D SO-101 state/action and front/top/wrist camera schema.

Run on the pod from the copied project folder:

```bash
cd /workspace/testproject

BASE_POLICY=lerobot/pi05_base \
STEPS=200 \
BATCH_SIZE=1 \
VIDEO_BACKEND=pyav \
bash scripts/runpod/pi05_base_orange49_smoke_train.sh
```

Expected checkpoint folder:

```text
/workspace/outputs/pi05_base_to_orange49_smoke/checkpoints
```

If this fails, fix the setup before starting a longer run.

After the smoke run, inspect the smoke checkpoint before any longer run:

```bash
python - <<'PY'
from pathlib import Path
root = Path("/workspace/outputs/pi05_base_to_orange49_smoke/checkpoints")
print("\n".join(str(p) for p in sorted(root.glob("**/pretrained_model"))))
PY
```

Download or inspect the newest `pretrained_model` and confirm it reports 6D
state/action and front/top/wrist cameras.

## 9. First Real Expert-Only Direct-Base Run

Run:

```bash
cd /workspace/testproject

BASE_POLICY=lerobot/pi05_base \
STEPS=5000 \
BATCH_SIZE=1 \
SAVE_FREQ=1000 \
VIDEO_BACKEND=pyav \
bash scripts/runpod/pi05_base_orange49_expert_train.sh
```

The script expands to a `lerobot-train` command with:

```text
--policy.type=pi05
--policy.pretrained_path=lerobot/pi05_base
--policy.device=cuda
--policy.dtype=bfloat16
--policy.gradient_checkpointing=true
--policy.compile_model=false
--policy.train_expert_only=true
--dataset.video_backend=pyav
```

Expected final checkpoint:

```text
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/last/pretrained_model
```

or a numbered checkpoint:

```text
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model
```

## 10. Optional Longer Runs

If the first 5k-step expert-only run trains successfully but underfits, try:

```bash
BASE_POLICY=lerobot/pi05_base \
OUTPUT_DIR=/workspace/outputs/pi05_base_to_orange49_expert_10k \
JOB_NAME=pi05_base_to_orange49_expert_10k \
POLICY_REPO_ID=local/pi05_base_to_orange49_expert_10k \
STEPS=10000 \
BATCH_SIZE=1 \
SAVE_FREQ=2500 \
bash scripts/runpod/pi05_base_orange49_expert_train.sh
```

If expert-only improves behavior but is still weak, consider a full fine-tune on
a larger GPU. That means making a separate script or command that removes:

```text
--policy.train_expert_only=true
```

Do this only after smoke and expert-only results are understood.

## 11. Download The Checkpoint

From the laptop:

```bash
mkdir -p /data/pi05_orange_checkpoints

scp -i ~/.ssh/runpod_ed25519 -P <ssh-port> -r \
  root@<pod-ip>:/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/last/pretrained_model \
  /data/pi05_orange_checkpoints/pi05_base_to_orange49_expert_last
```

## 12. Inspect Before Running The Arm

Run locally:

```bash
cd /home/gaikwad-prakash/PrakashProjects/testproject

./bin/so101 inspect-policy /data/pi05_orange_checkpoints/pi05_base_to_orange49_expert_last
```

The required result:

```text
policy: OK, expected pi05
state:  OK, expected [6], ours [6]
action: OK, expected [6], ours [6]
cameras: front/top/wrist match
```

Do not run the real arm if the checkpoint expects the wrong action shape or
camera names.

## 13. Evaluation Order

Use this order after training:

```text
1. Inspect policy compatibility.
2. Run offline/dry observation test without moving the arm.
3. Start the policy server on GPU.
4. Run one no-move action request and inspect action shape/range.
5. Run a very short guarded real-arm test with recording.
6. Review video before increasing duration.
```

Keep the first real-arm run short and guarded. This is a direct-base model, so
the outputs should be treated as untrusted until inspected.

## 14. Remaining Gaps To Close

Do these before spending on a long run:

```text
1. Use only the dedicated orange49 scripts for this experiment.
2. Remove any stale remote /workspace/lerobot_datasets/so101_orange_49 folder
   before uploading/extracting a new tarball.
3. Run the 200-step smoke train first and inspect the produced checkpoint.
4. Confirm the trained checkpoint has 6D state/action and front/top/wrist inputs.
5. Run offline/no-move action checks before any real-arm test.
```

Dedicated scripts:

```text
scripts/runpod/package_orange49_dataset.sh
scripts/runpod/upload_orange49_dataset_to_runpod.sh
scripts/runpod/pi05_base_orange49_smoke_train.sh
scripts/runpod/pi05_base_orange49_expert_train.sh
```

These remove the risk of accidentally training on the 30-episode default
dataset.

## 15. Success Criteria

Treat the direct-base run as successful only if all of these pass:

```text
smoke train completes
expert-only train completes
checkpoint inspection reports pi05 + 6D state/action + front/top/wrist cameras
offline action requests return finite 6D actions in a plausible range
first no-move live observation request succeeds
first short guarded real-arm run moves toward the orange without unsafe behavior
```
