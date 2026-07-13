# Pi05 Cleaned Dataset Fine-Tune Plan

## 1. What We Are Fine-Tuning

We are fine-tuning this SO-101 Pi05 checkpoint:

```text
zz4321/so101_pi05
```

This checkpoint is not the same as `lerobot/pi05_base`.

The relationship is:

```text
lerobot/pi05_base
  -> fine-tuned by zz4321 on SO-101 cube data
  -> zz4321/so101_pi05
  -> fine-tune by us on SO-101 orange move data
  -> our orange-move checkpoint
```

We use `zz4321/so101_pi05` because it already matches the SO-101 style:

```text
state:  6 joints
action: 6 joints
cameras: top, front, wrist
policy: pi05
chunk size: 50
```

## 2. What Dataset We Are Using

Use the cleaned dataset:

```text
/data/lerobot_datasets/so101_pick_orange_move_action_start_view
```

Dataset facts already verified:

```text
episodes: 30
frames: 15,905
fps: 30
cameras: front, top, wrist
task: pick up the orange and move it to another place
camera storage: video-backed image observations
median first meaningful movement: 0.37 s
episodes first move after 2 s: 0 / 30
```

Do not use the old combined dataset for the next training run:

```text
/data/lerobot_datasets/so101_pick_orange_30eps
```

Reason: the old dataset contains confusing late/rest tails and/or idle starts. The action-start view dataset removes the idle beginning from each episode.

## 3. Why We Need A Smoke Test First

The smoke test is not meant to make a good robot.

It only proves:

```text
RunPod environment works
LeRobot imports correctly
dataset loads correctly
zz4321/so101_pi05 downloads correctly
training starts
checkpoint saves
```

This should be a small run, for example:

```text
200 steps
batch size 1
```

If that fails, we fix the setup before spending money on a long run.

## 4. Why Expert-Only Fine-Tuning First

Pi05 is a very large model. Full fine-tuning can need a lot of VRAM.

For the first useful RunPod A40 run, use:

```text
--policy.train_expert_only=true
```

This trains the action expert/projection parts while keeping the large vision-language part mostly fixed.

This is not a movement bandaid. It is an official model fine-tuning strategy for large policies when GPU memory is limited.

If expert-only improves behavior but is still weak, then we can try a more expensive full fine-tune later.

## 5. RunPod Folder Layout

Use this layout on the RunPod machine:

```text
/workspace/lerobot
/workspace/lerobot_datasets/so101_pick_orange_move_action_start_view
/workspace/outputs/pi05_so101_orange_move_action_start_view_smoke
/workspace/outputs/pi05_so101_orange_move_action_start_view_expert
```

## 6. Local Dataset Packaging

Package the cleaned dataset locally:

```bash
./scripts/runpod/package_cleaned_dataset.sh
```

This creates:

```text
/data/downloads/so101_pick_orange_move_action_start_view.tar.gz
```

Upload that tarball to RunPod, then extract it to:

```text
/workspace/lerobot_datasets/so101_pick_orange_move_action_start_view
```

## 7. RunPod Setup

On RunPod:

```bash
cd /workspace
git clone https://github.com/huggingface/lerobot.git
cd /workspace/lerobot
pip install -e ".[pi]"
pip install -e ".[feetech]"
```

Then copy this project folder or at least the run scripts to RunPod.

## 8. Smoke Fine-Tune

Run:

```bash
bash scripts/runpod/pi05_cleaned_smoke_train.sh
```

Expected output folder:

```text
/workspace/outputs/pi05_so101_orange_move_action_start_view_smoke
```

Success means a checkpoint appears under:

```text
/workspace/outputs/pi05_so101_orange_move_action_start_view_smoke/checkpoints/
```

## 9. Real First Fine-Tune

After smoke test passes, run:

```bash
bash scripts/runpod/pi05_cleaned_expert_train.sh
```

Default:

```text
steps: 3000
batch size: 2
train_expert_only: true
```

Override example:

```bash
STEPS=5000 BATCH_SIZE=2 bash scripts/runpod/pi05_cleaned_expert_train.sh
```

Expected output folder:

```text
/workspace/outputs/pi05_so101_orange_move_action_start_view_expert
```

## 10. What We Must Download After Training

Download the final checkpoint folder:

```text
/workspace/outputs/pi05_so101_orange_move_action_start_view_expert/checkpoints/last/pretrained_model
```

or the latest numbered checkpoint:

```text
/workspace/outputs/pi05_so101_orange_move_action_start_view_expert/checkpoints/<STEP>/pretrained_model
```

The important files are:

```text
config.json
train_config.json
model weights
normalization stats
```

## 11. Real-Arm Test After Fine-Tune

Test with the same task text:

```text
pick up the orange and move it to another place
```

Use the same camera setup:

```text
top: Logitech C270
front: laptop/front camera
wrist: Raspberry Pi wrist camera
```

The first test should be closed-loop and logged:

```text
30 steps
no behavior-shaping clamp
record video
save action CSV
```

## 12. Current Verification Status

Verified locally on the action-start view dataset:

```text
dataset root: /data/lerobot_datasets/so101_pick_orange_move_action_start_view
repo id:      local/so101_pick_orange_move_action_start_view
episodes:     30
frames:       15,905
fps:          30
state shape:  6
action shape: 6
front image:  3 x 480 x 640
top image:    3 x 480 x 640
wrist image:  3 x 480 x 640
task:         pick up the orange and move it to another place
```

The RunPod package has also been created:

```text
/data/downloads/so101_pick_orange_move_action_start_view.tar.gz
```

The tarball includes the parquet files and real MP4 files for all three cameras.

## 12. Success Criteria

The fine-tuned policy is useful only if:

```text
gripper command changes meaningfully
arm moves toward the orange
orange is picked or clearly attempted
orange is moved away after pickup
video matches the task text
```

If it still does not command a grasp, then the issue is not our control script. The next fix is better/more demonstrations or a different starting checkpoint.
