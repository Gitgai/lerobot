# Pi05 Staged Fine-Tuning Execution Plan

Last updated: 2026-07-25

This document is the active fine-tuning plan for the SO-101 orange pick task.

The purpose is not to keep training blindly. The purpose is to train in measured stages, check evidence after each stage, and only then decide whether to test the real arm or continue training.

## 1. Goal

Improve the Pi05 policy on the exact behavior that failed during real-arm tests:

```text
reach orange
center orange between gripper fingers
close gripper while centered
lift orange
move orange to another place
```

The current evidence says the 3000-step focused checkpoint learned reach/contact better than reliable grasp/lift/move.

The later 012000 checkpoint was tested twice on the real arm. It still did not
pick/lift the orange.

The next goal is:

```text
run the full offline audit of 012000 against successful focus-window demonstrations
then decide whether to train more, fix action/gripper handling, adjust focused-window weighting, correct deployment/start state, or collect new correction episodes
```

## 2. Evidence Behind This Plan

### Dataset size

The current focused training dataset on RunPod is:

```text
/workspace/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
```

Known facts:

```text
episodes: 89
frames: 40,712
fps: 30
cameras: top, front, wrist
state/action: 6D SO-101
```

This dataset is:

```text
original 49 full episodes
+ 40 verified grasp/pick/move focused windows once
```

### Why 3000 steps was not enough

The completed `003000` checkpoint used:

```text
steps: 3000
batch_size: 1
effective samples seen: 3000
```

Compared with the dataset:

```text
3000 samples / 40712 frames = 0.074 epoch
```

Plain meaning:

```text
The model saw only about 7.4 percent of one full dataset pass.
```

That was useful to prove the pipeline worked, but it was not enough evidence that the model had learned the full close/lift/move behavior.

### Gripper-close examples are rare

Earlier dataset mining found strong close actions are a small fraction of all frames.

If strong close actions are around 5.89 percent of frames, then a 3000-sample batch-1 run sees roughly:

```text
3000 * 0.0589 = about 177 strong-close samples
```

That is very little exposure for the exact skill that failed.

## 3. GPU Findings

RunPod GPU:

```text
GPU: RTX 3090
VRAM: 24 GB
```

Batch-size probes:

```text
batch_size=2: passed
batch_size=4: passed
```

Observed during real `batch_size=4` training:

```text
GPU memory from nvidia-smi: about 14.5 GB / 24.6 GB
trainer memory report: about 12.89 GB
GPU utilization: about 90-100 percent
speed: about 1.40 seconds per step
```

Decision:

```text
Use batch_size=4 for the next staged fine-tune.
```

Reason:

```text
It fits the RTX 3090 and gives 4 training samples per step instead of 1.
```

## 4. Current Training Stage

Input checkpoint:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
```

Do not reuse the failed output directory:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_012000
```

Reason:

```text
It contains a broken partial 006000 checkpoint from the disk-quota failure.
Keeping it untouched preserves the failure evidence.
Using a fresh folder avoids mixing good and bad checkpoints.
```

Restart output directory:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000
```

Restart command shape:

```bash
source /workspace/venv312/bin/activate
cd /workspace/lerobot

lerobot-train \
  --dataset.repo_id=local/so101_orange_49_plus_grasp_pick_move_focus \
  --dataset.root=/workspace/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus \
  --dataset.video_backend=pyav \
  --policy.type=pi05 \
  --policy.pretrained_path=/workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model \
  --output_dir=/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000 \
  --job_name=pi05_orange49_focus_bs4_from003000_restart_012000 \
  --policy.repo_id=local/pi05_orange49_focus_bs4_from003000_restart_012000 \
  --policy.push_to_hub=false \
  --wandb.enable=false \
  --policy.device=cuda \
  --policy.dtype=bfloat16 \
  --policy.gradient_checkpointing=true \
  --policy.compile_model=false \
  --policy.train_expert_only=true \
  --steps=12000 \
  --batch_size=4 \
  --save_freq=3000
```

Expected training exposure:

```text
12000 steps * batch_size 4 = 48000 samples
48000 / 40712 = about 1.18 epochs
```

Plain meaning:

```text
This run gives the model about one full pass over the mixed dataset.
```

## 5. Checkpoint Save Frequency

LeRobot behavior from local source:

```text
save_freq controls how often a checkpoint is written.
LeRobot also saves at the final step.
```

The saved checkpoint contains:

```text
pretrained_model/
  model weights
  policy config
  train config
  processor config if present

training_state/
  optimizer state
  scheduler state
  random state
  training step
```

This matters because Pi05 checkpoints are large.

Observed size from the previous completed focused checkpoint:

```text
003000 checkpoint directory: about 11 GB
model.safetensors alone: about 8.8 GB
```

### Restart setting: save_freq=3000

For a 12000-step run:

```text
checkpoints saved:
  003000
  006000
  009000
  012000

estimated checkpoint storage:
  about 44 GB
```

Why this was chosen:

```text
Storage cleanup freed about 43 GB.
This gives recovery points every 3000 steps without the 132 GB cost of save_freq=1000.
It allows earlier offline comparison if the pod stops before 12000.
```

If storage gets tight again, use `save_freq=6000` instead.

### What if we save at 1000?

If we set:

```text
--save_freq=1000
```

then a 12000-step run saves:

```text
001000
002000
003000
004000
005000
006000
007000
008000
009000
010000
011000
012000
```

Storage estimate:

```text
12 checkpoints * about 11 GB each = about 132 GB
```

Advantages:

```text
If RunPod stops or migrates, we lose at most 1000 steps.
We can inspect early checkpoints like 001000, 002000, 003000.
We get more evidence about when offline action predictions start improving.
```

Disadvantages:

```text
It can use about 132 GB for one 12000-step run.
Each checkpoint save pauses training while files are written.
It can hit RunPod storage limits.
It creates many checkpoint folders to manage.
It does not make the model learn better by itself.
```

Important conclusion:

```text
save_freq=1000 improves recovery and evidence granularity.
save_freq=1000 does not improve training quality directly.
```

Recommendation:

```text
Use save_freq=3000 after the 2026-07-22 cleanup.
Use save_freq=6000 if storage becomes tight again.
Use save_freq=1000 only if we explicitly want frequent recovery points and have enough storage.
```

If using `save_freq=1000`, also use a retention rule:

```text
Keep:
  latest checkpoint
  complete 003000 or complete 006000 if needed for comparison
  final checkpoint

Delete:
  old intermediate checkpoints after offline comparison
```

Do not delete any checkpoint until:

```text
the final checkpoint is verified
the log shows training ended cleanly
offline comparison artifacts are saved
the user approves cleanup
```

## 6. Current Run Status Rule

### Historical RunPod Check: 2026-07-22

Fresh RunPod endpoint:

```text
root@213.192.2.67 -p 40066
key used successfully: ~/.ssh/runpod_ed25519
```

Current GPU state:

```text
RTX 3090 idle
no lerobot-train process running
```

The staged run did start and train, but it failed at checkpoint save:

```text
latest completed training step before failure: 6000 / 12000
latest metric: loss about 0.035, epoch about 0.59
failure point: Checkpoint policy after step 6000
error: Disk quota exceeded
```

Evidence from the log:

```text
INFO 2026-07-21 22:02:58 ot_train.py:651 Checkpoint policy after step 6000
safetensors._safetensors_rust.SafetensorError: Error while serializing: I/O error: Disk quota exceeded (os error 122)
```

The `006000` checkpoint is not usable:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_012000/checkpoints/006000
size: about 2 MB
missing: model.safetensors
missing: train_config.json
missing: training_state/training_step.json
missing: training_state/optimizer_state.safetensors
```

Required conclusion:

```text
Do not use 006000 for offline comparison or real-arm evaluation.
Do not resume from 006000.
Historical note: this was superseded by a later successful restarted 012000 run.
```

Storage pressure found:

```text
/workspace/outputs: about 65 GB
/workspace/outputs/pi05_base_to_orange49_expert: about 54 GB
/workspace/outputs/pi05_orange49_plus_grasp_focus_expert: about 11 GB
/workspace/hf_cache: about 14 GB
/workspace/venv312: about 11 GB
```

Large checkpoint folders:

```text
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/001000: about 11 GB
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/002000: about 11 GB
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/003000: about 11 GB
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/004000: about 11 GB
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000: about 11 GB
/workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000: about 11 GB
```

Safe cleanup candidate identified before deletion:

```text
Delete old intermediate base checkpoints:
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/001000
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/002000
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/003000
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/004000

Keep:
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000
  /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000
```

This would free about:

```text
44 GB
```

Cleanup performed on 2026-07-22 after user approval:

```text
deleted:
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/001000
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/002000
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/003000
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/004000

kept and re-verified:
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000
  /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000

workspace size before cleanup: about 91 GB
workspace size after cleanup: about 48 GB
```

The broken partial staged checkpoint was not deleted during this cleanup:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_012000/checkpoints/006000
```

It is still marked unusable and should not be used for comparison or resume.

Before starting or restarting any training run:

```text
check whether the previous run is still alive
check whether a new checkpoint already exists
check the current RunPod Connect tab endpoint
do not launch duplicate training into the same output directory
use a fresh output directory after the failed partial 006000 save
```

The old endpoint may become invalid after RunPod migration:

```text
old direct endpoint example:
  root@213.192.2.83 -p 40161
```

If direct SSH says `Connection refused`, get the new direct TCP SSH line from RunPod before making decisions.

### Current 012000 Status: 2026-07-25

Complete checkpoint:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model
```

Local checkpoint copy used for the sampled CPU probe:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/artifacts/checkpoints/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/012000/pretrained_model
```

Real-arm evidence:

```text
official_async_3cam_012000_trace_20260722_230756:
  reach/contact: yes
  strong close <=25: 0 frames
  pick/lift: no

official_async_3cam_012000_trace_20260722_233341:
  reach/contact: yes
  strong close <=25: 85 frames
  strong close timing: timesteps 0-84, before correct grasp
  final near-orange gripper: open
  pick/lift: no
```

Sampled offline CPU-probe evidence:

```text
selected successful close/hold focus frames: 6
recorded first gripper mean: 21.80
012000 predicted first gripper mean: 40.35
predicted strong close in next 10 actions: 0/6
predicted near close in next 10 actions: 0/6
```

Detailed report:

```text
projects/testproject/docs/pi05_012000_cpu_probe_close_frames_20260725.md
```

Current conclusion:

```text
Do not treat 012000 as solved.
Do not repeat the same ordinary physical test as the next step.
Run the full GPU offline audit on all successful focus-window phases first.
If the audit confirms the sampled failure, fix training/action handling before more ordinary real-arm tests.
```

## 7. Monitoring Commands

Use the current RunPod SSH endpoint from the Connect tab.

Replace `<pod-ip>` and `<pod-port>`:

```bash
ssh -i ~/.ssh/runpod_ed25519 -p <pod-port> root@<pod-ip>
```

Clean status command:

```bash
python3 - <<'PY'
from pathlib import Path

logs = sorted(Path("/workspace/logs").glob("pi05_orange49_focus_bs4_from003000_restart_012000_*.log"))
log = logs[-1] if logs else Path("/workspace/logs/pi05_orange49_focus_bs4_from003000_restart_012000.log")
text = log.read_text(errors="replace").replace("\r", "\n") if log.exists() else ""
progress = [line for line in text.splitlines() if "Training:" in line and "/12000" in line]
metrics = [line for line in text.splitlines() if " ot_train.py:606 step:" in line]
print("log:", log)
print("latest progress:", progress[-1] if progress else "none")
print("latest metric:", metrics[-1] if metrics else "none")
PY

nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits
ps -eo pid,etime,pcpu,pmem,rss,stat,cmd | grep -E "lerobot-train|python" | grep -v grep
find /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints -maxdepth 2 -type d 2>/dev/null | sort
```

Checkpoint size command:

```bash
du -sh /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/* 2>/dev/null
```

## 8. Offline Audit Before More Real-Robot Testing

Do not run another ordinary real-arm test immediately.

First compare the 012000 checkpoint against recorded demonstration frames across
the full focused-window set.

Current sampled result:

```text
The 2026-07-25 CPU probe tested six successful close/hold frames.
All six recorded frames asked for strong close.
012000 predicted no near-close action in the next 10 actions for any of them.
```

Minimum comparison:

```text
old checkpoint:
  /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model

current checkpoint:
  /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model
```

Compare on the same selected focus frames:

```text
camera inputs
robot state
task text
predicted Pi05 action chunks
recorded demonstration actions
```

Metrics to check:

```text
first-action action MAE
full-chunk action MAE
gripper action MAE
missed strong-close count
missed lift/move pattern count
examples where recorded gripper closes but Pi05 predicts open
examples where recorded lift starts but Pi05 predicts hover
```

Evidence target:

```text
The 012000 checkpoint should reduce missed close/lift cases compared with 003000.
It must predict close/hold on known-good close/hold focus frames before another ordinary physical test.
```

If it does not improve offline:

```text
do not run the real arm
inspect training mix, action normalization, gripper labels, gripper-dimension loss, frame/action timing, focused-window weighting, and visual/state alignment
```

## 9. Real-Arm Evaluation Gate

Only after the full offline audit improves, or after explicit user approval for
a start-state diagnostic run despite offline failure:

```text
start official LeRobot policy_server from the new checkpoint
run official LeRobot robot_client
use top/front/wrist cameras
use official defaults
do not set robot.max_relative_target unless user approves
enable read-only trace
record external video if possible
start with gripper visibly open
confirm first observed gripper state is close to the training open range, ideally 40-55
```

Required real-arm evidence:

```text
camera precheck images
policy_server log
robot_client log
read-only trace with images/state/action chunks/executed actions
external video if available
manual outcome label
```

Outcome labels:

```text
0: no reach
1: reaches wrong area
2: reaches orange but no useful contact
3: contacts/pushes orange but no grasp
4: grasps/lifts but does not move/place
5: grasp, lift, and move to another place
```

## 10. Decision After 12000

If offline comparison improves and real-arm score is `4` or `5`:

```text
repeat official evaluation 3-5 times
measure reliability
do not change training until reliability is known
```

If offline comparison improves but real-arm score is still `3`:

```text
inspect trace timing and gripper geometry
compare Pi05 output against executed action
look for camera viewpoint mismatch or start-pose mismatch
```

If offline comparison does not improve:

```text
stop training this exact setup
inspect dataset labels and action distributions
consider repeated focus windows or additional close-range correction episodes
```

If a complete checkpoint `006000` exists but `012000` does not:

```text
offline-compare 006000 before restarting
```

If checkpoint `006000` exists but is incomplete:

```text
do not compare it
do not resume from it
restart from the last complete checkpoint
```

## 11. Next Concrete Action

Restart the staged batch-size-4 fine-tune from the complete focused `003000` checkpoint into a fresh output folder.

Current known RunPod endpoint:

```text
ssh -i ~/.ssh/runpod_ed25519 -p 40066 root@213.192.2.67
```

Preflight:

```text
1. Confirm no `lerobot-train` process is already running.
2. Confirm GPU is idle.
3. Confirm complete input checkpoint exists:
   /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model/model.safetensors
4. Confirm workspace is still about 48 GB after cleanup.
5. Confirm fresh output folder is empty or does not exist:
   /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000
```

Restart settings:

```text
batch_size=4
steps=12000
save_freq=3000
output_dir=/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000
```

After restart:

```text
1. Monitor until training reaches step 3000 and writes a complete checkpoint.
2. Verify every checkpoint has `pretrained_model/model.safetensors`.
3. If training reaches `012000`, run full offline audit before real-arm testing.
4. If training stops after a complete `003000`, `006000`, or `009000`, offline-compare the latest complete checkpoint before restarting.
5. If checkpoint save fails again, stop and inspect storage before any new run.
```

Do not:

```text
do not reuse the old failed output folder
do not use the incomplete old `006000`
do not set save_freq=1000 unless storage is expanded or old checkpoints are actively pruned
do not run the real arm until offline comparison improves, unless the user explicitly approves a diagnostic physical run
```
