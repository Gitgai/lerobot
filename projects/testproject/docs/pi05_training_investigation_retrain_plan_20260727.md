# Pi05 Training Investigation And Retrain Plan

Last updated: 2026-07-28

> **ON HOLD 2026-07-28.** Phase 1 (pod verification) produced a decisive
> reversal: a recovered 2026-07-22 pod comparison shows 012000 learned the
> grasp (gripper corr 0.83 on focus frames, better than 003000). The local
> probes that motivated this plan were a broken harness. No retraining is
> currently justified. The active investigation is live deployment mismatch.
> See: `pi05_012000_pod_evidence_correction_20260728.md`.

This plan follows the 2026-07-26 saved-pipeline offline probe, which settled the
model-vs-harness question. It defines the full path: verify on RunPod, retrain,
gate offline, and only then return to the real arm.

Evidence basis:

```text
projects/testproject/docs/pi05_012000_saved_pipeline_probe_20260726.md
```

## 1. Current State (what is already decided)

Ruled out by evidence:

```text
broken measurement pipeline (saved processors used end-to-end; saved stats ==
  dataset stats; live RunPod path showed the same behavior)
delta/absolute action confusion (relative step disabled at training)
normalization squashing the gripper (close=-0.24 vs median=+0.37 in [-1,1])
bad training config (lr 2.5e-5, warmup 1000, cosine decay 30k, restart
  correctly pointed at 003000 weights)
"no close examples" (focus windows are 40.49% strong-close frames)
```

Confirmed failure signature:

```text
012000 collapses to the dataset-median action. Predicted first gripper was
39.9-43.4 on ALL 32 probe predictions regardless of input (dataset median
40.48). Zero close or near-close anywhere in any predicted 50-step chunk.
Arm joints (wrist_flex, shoulder_lift) also far from demonstrated trajectories
on the model's own training frames.
```

Prime suspect:

```text
Under-training. 12,000 steps x batch 4 = ~1.18 passes over 40,712 frames.
The LR schedule (30k decay steps) was built for a 30k run that stopped at 12k.
```

Key training facts (from the checkpoint's train_config.json):

```text
wandb: DISABLED -> loss history only exists in log files on the pod, if any
dataset root on pod: /workspace/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
output dir on pod:   /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000
baseline on pod:     /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
training dtype: bfloat16 on cuda | log_freq: 200 | save_freq: 3000
```

## 2. Phase 1 - RunPod Verification (blocked on user: current Connect info)

### 2.0 Reconnect checklist

```text
get current SSH endpoint from RunPod Connect tab (endpoints migrate)
verify: nvidia-smi, df -h /workspace
verify paths exist:
  /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/
  /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
  /workspace/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
```

### 2.1 Find the training loss history

wandb was disabled, so:

```bash
ls -la /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/
find /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000 -name "*.log" -o -name "*.jsonl" -o -name "events*"
# also check shell history / nohup files / tmux scrollback for the training console output
grep -h "loss" <logfile> | tail -80
```

Interpretation:

```text
loss still clearly decreasing at step 12000 -> supports under-training ->
  Phase 2 Branch A (continue training)
loss flat since early steps                -> under-training alone unlikely ->
  Phase 2 Branch B (deeper investigation)
no log found -> use 2.2 fallback below
```

### 2.2 Fallback / stronger check: measure training loss directly

If no logs survive, measure the actual training objective on the pod
(read-only, ~minutes on GPU): compute the Pi05 flow-matching loss of BOTH
checkpoints on ~50 fixed training batches (same seed, same frames).

```text
012000 loss noticeably < 003000 loss -> training was working, just unfinished
  -> Branch A
012000 loss ~= 003000 loss           -> 9000 extra steps changed nothing ->
  something is wrong beyond duration -> Branch B
```

### 2.3 The 003000 control probe

Run the saved-pipeline probe against 003000 on the pod. Script is ready at:

```text
projects/testproject/artifacts/offline_compare_012000_focus_20260726_cpu_probe2_v2/probe2_012000.py
```

Edits needed on the pod: CKPT -> 003000 path, DATA_ROOT ->
/workspace/lerobot_datasets/..., device overrides "cuda", OUT_DIR -> a
003000-labeled folder. Same 16-frame selection logic, 2 seeds.

Interpretation:

```text
003000 also collapses to ~40-41 -> both checkpoints under-trained; nothing
  regressed; Branch A with confidence
003000 closes on close frames   -> 012000 REGRESSED vs its own init ->
  Branch B; compare the two runs' configs and the restart procedure first
```

## 3. Phase 2 - Retrain

### Branch A (expected): continue training to 30k steps

```text
Continue FROM the existing 012000 run so optimizer/scheduler state resumes.
Requires the run's training_state to exist on the pod (check
checkpoints/012000/ for training_state/ next to pretrained_model/).
```

```bash
# on the pod, verify resume state exists first:
ls /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/last/

# resume and extend to 30k steps (matches the LR schedule's design):
lerobot-train \
  --config_path=/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/last/pretrained_model/train_config.json \
  --resume=true \
  --steps=30000
```

If training_state was pruned and resume is impossible, start a fresh run
initialized from 012000 weights (policy.pretrained_path = 012000
pretrained_model) with steps=18000-30000 and a fresh warmup.

Run hygiene (learned the hard way):

```text
disk: save_freq=3000 is fine ONLY with pruning; delete older checkpoints as
  new ones land (keep last + one milestone); previous run died at step 6000
  on disk quota
logging: enable wandb if possible, or tee the console to
  <output_dir>/train_console.log so the loss curve survives this time
measure steps/hour in the first 30 min and report ETA
batch size: keep bs4 unless GPU headroom allows more; gradient accumulation
  is an acceptable alternative; do NOT change other hyperparameters in
  Branch A (one variable at a time)
```

### Branch B (if evidence demands): deeper investigation before more compute

In priority order:

```text
1. Verify the restart actually loaded 003000 weights (compare a few tensors
   of 003000 vs an early-step checkpoint of the restart run, if any survive).
2. train_expert_only=true: confirm gradients flow to the action expert and
   projections; consider a short run with the VLM unfrozen for comparison.
3. Loss weighting over the 50-step chunk: close moments are a small fraction
   of chunk targets; consider focus-window oversampling or gripper-dimension
   loss weighting.
4. Sanity overfit: train on ONE focus episode for ~2k steps. A healthy
   pipeline must overfit it (probe should then predict close on that
   episode's frames). If it cannot, the training loop itself is broken.
```

## 4. Phase 3 - Offline Gate (local, no robot, ~10 min per checkpoint)

Re-run the local probe on every new checkpoint (3000-step intervals as they
land, pulled to the laptop, or run on the pod directly):

```text
script: probe2_012000.py (point CKPT at the new checkpoint)
```

PASS criteria (all required):

```text
close frames:    mean predicted first gripper <= 32; strong close (<=25)
                 appears in the predicted chunk on >= 8 of 12 rows
open frames:     mean predicted first gripper >= 44; no strong close in the
                 first 10 predicted actions
preclose frames: near-close (<=35) appears in the chunk on >= 6 of 8 rows,
                 with onset within +/-15 steps of the recorded onset
posture:         wrist_flex chunk MAE <= 20 on close frames (recorded grasp
                 posture must be reproduced, not just the gripper number)
predictions must VARY with input: close-frame and open-frame predicted first
                 grippers must differ by >= 10 (anti-collapse check)
```

FAIL -> keep training / go to Branch B. Do not touch the robot.

## 5. Phase 4 - Real-Arm Test (only after Phase 3 passes)

Unchanged from the existing gate (offline comparison plan doc section 7):

```text
official LeRobot async, three cameras (top /dev/video0, front /dev/video2,
wrist /dev/video6 via Pi bridge), robot.max_relative_target=null, read-only
trace enabled, start in the normal original-episode start pose, gripper
visibly open (first observed gripper state ~40-55, not 20-30)
```

Compare the live trace against the offline probe of the same checkpoint: if
offline passes but live fails, the deployment-mismatch investigation (camera
geometry, start pose, timing) becomes the active track - with the model now
excluded as the cause.

## 6. Bookkeeping

```text
docs updates after each phase land in projects/testproject/docs/
generated artifacts under projects/testproject/artifacts/ - never committed
no HF tokens anywhere; PaliGemma tokenizer needs runtime auth on the pod
prefer uv run / the project venv for local python
```

## 7. Blocked On User

```text
1. Current RunPod Connect info (SSH endpoint) - Phase 1 cannot start without it.
2. Approval of the 30k-step continuation budget (GPU-hours; measure steps/hour
   at run start and report before committing the full extension).
```
