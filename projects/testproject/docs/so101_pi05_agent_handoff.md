# SO-101 Pi05 Agent Handoff

Last updated: 2026-07-23

This document is the fast handoff for the next agent. It summarizes the
current SO-101 Pi05 orange-pick project state, the evidence we have, the rules
the user wants followed, and the next concrete work.

## 1. Current Goal

Make the real SO-101 follower arm reliably:

```text
see orange -> reach orange -> center gripper -> close -> lift -> move orange
```

The project is now evidence-driven. Do not guess at fixes. Use traces,
training data, logs, and controlled tests to decide what to do next.

## 2. User Rules

Follow these rules unless the user explicitly changes them:

```text
Use official LeRobot execution first.
Use official LeRobot defaults unless the user approves a change.
Use the three intended cameras for valid Pi05 evaluation: top, front, wrist.
Do not create or edit robot execution scripts unless official LeRobot lacks the needed feature, and explain/ask first.
Read-only trace instrumentation is allowed because it does not change robot behavior.
Do not put videos, images, traces, datasets, checkpoints, or generated artifacts in git.
Commit/push only from the parent LeRobot repo.
```

The user cares about clear evidence. When explaining anything, separate:

```text
measured fact
interpretation
what would prove or disprove it
```

## 3. Repo And Source Control

Active repo:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
remote: https://github.com/Gitgai/lerobot.git
```

Project folder:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject
```

Important source-control fact:

```text
projects/testproject used to be a nested git repo.
That nested .git metadata was moved to a backup on 2026-07-19.
Now projects/testproject is a normal folder inside the parent LeRobot repo.
```

Backup path for the old nested git metadata:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/git_metadata_backups/testproject_dotgit_20260719_133929
```

Always commit from:

```bash
cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
git status
git add projects/testproject/...
git commit -m "..."
git push origin main
```

Details are in:

```text
projects/testproject/docs/repo_source_control_policy.md
```

## 4. Local Python Environment

Local project venv:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/.venv
```

Expected LeRobot import path:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/src/lerobot/__init__.py
```

Verify:

```bash
cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
projects/testproject/.venv/bin/python -c "import lerobot; print(lerobot.__file__)"
```

This matters because the venv previously imported an old checkout from:

```text
/data/projects/lerobot/src
```

That was fixed.

## 5. Hardware

Robot:

```text
SO-101 follower arm
SO-101 leader arm for teleoperation/recording
```

Known follower serial port:

```text
/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00
```

Expected robot id:

```text
my_so101_follower
```

Known camera mapping for official Pi05 runs:

```text
top   -> /dev/video0  Logitech top camera
front -> /dev/video2  Acer RGB front camera
wrist -> /dev/video6  Raspberry Pi camera bridged through v4l2loopback
```

Do not use:

```text
/dev/video4 as a normal policy camera
```

Reason:

```text
/dev/video4 was identified as the Acer IR greyscale camera, not the normal RGB camera.
```

The Raspberry Pi wrist camera is reachable at:

```text
ssh raspi@192.168.1.17
```

The Pi camera may fail with:

```text
failed to acquire camera ... Pipeline handler in use by another process
```

That means another process on the Raspberry Pi is holding the camera. Stop the
conflicting Pi camera process/service before starting the wrist stream.

## 6. Official Execution Path

Use this mental model:

```text
top/front/wrist cameras
        +
SO-101 joint state
        +
task text
        |
        v
laptop official robot_client
        |
        | observation sent over network
        v
RunPod official policy_server + Pi05
        |
        | action chunk returned
        v
laptop official robot_client
        |
        | robot.send_action(...)
        v
SO-101 follower arm moves
```

Official async behavior is queue-based:

```text
robot_client sends an observation
policy_server returns an action chunk
robot_client queues and executes actions at fps
when queue becomes low, robot_client sends another observation
overlapping actions are aggregated by LeRobot
```

Current intended task text:

```text
pick up the orange and move it to another place
```

Current official/default control facts from latest runs:

```text
actions_per_chunk: 50
chunk_size_threshold: 0.5
aggregate_fn_name: weighted_average
fps: 30
robot.max_relative_target: None
```

Do not silently change these values.

## 7. RunPod

RunPod pods migrate often, so host/port must be re-read from the RunPod UI each
time. Do not assume the last SSH endpoint is still current.

Recent endpoints seen in chat included:

```text
root@213.192.2.83 -p 40161
root@213.192.2.107 -p 40109
root@213.192.2.67 -p 40066
```

Treat these as history only. Verify the current active pod before connecting.

SSH key commonly used:

```text
~/.ssh/runpod_ed25519
```

Example connection shape:

```bash
ssh -i ~/.ssh/runpod_ed25519 -p <PORT> root@<RUNPOD_IP>
```

Never write the user's Hugging Face token into docs, scripts, or git.

## 8. Models And Checkpoints

Original reference from another user:

```text
zz4321/so101_pi05
base model: lerobot/pi05_base
trained for SO-101 cube
```

Our project moved to orange-pick fine-tuning.

Complete checkpoint kept from earlier orange training:

```text
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model
```

Complete Option A focused checkpoint:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
```

Current staged checkpoint to analyze/test:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model
```

Do not use this incomplete checkpoint:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_012000/checkpoints/006000
```

Why not:

```text
It was created during a failed save with "Disk quota exceeded".
It is missing the complete model/training-state files.
```

## 9. Datasets

Original useful dataset:

```text
49 SO-101 orange episodes
```

Focused grasp/pick/move dataset:

```text
/data/lerobot_datasets/so101_orange_49_grasp_pick_move_focus
40 episodes
10,988 frames
```

Option A mixed training dataset:

```text
/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
89 episodes
40,712 frames
```

Option A means:

```text
original 49 full episodes
+
40 verified focused grasp/pick/move windows once
```

RunPod copy:

```text
/workspace/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
```

Local package:

```text
/data/downloads/so101_orange_49_plus_grasp_pick_move_focus.tar.gz
```

Do not commit datasets/packages/artifacts to git.

## 10. Latest Real-Arm Evidence

The 012000 checkpoint was tested twice with official LeRobot async execution,
three cameras, official defaults, and read-only trace.

Trace 1:

```text
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_230756
37 observations
29 Pi05 chunks
422 executed actions
robot.max_relative_target: null
```

Key result:

```text
reached/contacted orange
no pick/lift
strong close <=25: 0 executed frames
final 100 gripper range: 32.56 to 47.48
```

Interpretation:

```text
Pi05 did not command a strong close during this run.
The gripper got near/contacted the orange, but the orange was offset instead of centered between fingers.
```

Trace 2:

```text
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_233341
21 observations
16 Pi05 chunks
220 executed actions
robot.max_relative_target: null
```

Key result:

```text
reached/contacted orange
no pick/lift
strong close <=25: 85 executed frames
strong close happened early: timesteps 0-84
final 100 gripper range: 54.33 to 58.88
```

Interpretation:

```text
Pi05 can command close, but in this run it closed too early and later opened near the orange.
```

Current evidence-backed conclusion:

```text
The problem is not a basic camera connection failure.
The problem is not a robot.max_relative_target clamp.
The problem is not LeRobot obviously rewriting a close command into an open command.
The unresolved failure is conditional grasp timing/geometry:
  orange centered between fingers -> close strongly -> keep closed -> lift/move
```

Detailed report:

```text
projects/testproject/docs/pi05_012000_trace_vs_training_analysis_20260723.md
```

## 11. Training Data Evidence

The Option A mix has many close examples, especially in focused windows.

Measured gripper distribution:

```text
Original 49 full episodes:
  29,724 frames
  strong close <=25: 5,660 frames, 19.04%
  near close <=35: 10,728 frames, 36.09%
  open >=45: 11,809 frames, 39.73%

Focused 40 windows:
  10,988 frames
  strong close <=25: 4,449 frames, 40.49%
  near close <=35: 6,832 frames, 62.18%
  open >=45: 2,506 frames, 22.81%

Full Option A mix:
  40,712 frames
  strong close <=25: 10,109 frames, 24.83%
  near close <=35: 17,560 frames, 43.13%
  open >=45: 14,315 frames, 35.16%
```

Gripper direction:

```text
higher gripper value = more open
lower gripper value = more closed
```

Successful reviewed training windows show:

```text
orange in gripper mouth
gripper closes
orange lifts
orange moves away
```

That is why the next question is not "do we have any grasp frames?" We do.
The next question is:

```text
Does checkpoint 012000 reproduce the correct action when shown those successful frames?
```

## 12. Current Highest Priority

Do not repeat another ordinary physical 012000 run yet.

Next priority:

```text
Run offline 012000 checkpoint comparison on successful focus-window frames.
```

Purpose:

```text
If 012000 fails on known-good training/focus frames, the issue is model/training.
If 012000 succeeds on known-good training/focus frames, the live failure is more likely deployment mismatch:
  start gripper state
  camera geometry
  orange placement
  timing/latency
```

Detailed plan:

```text
projects/testproject/docs/pi05_012000_offline_comparison_plan.md
```

Expected output folder:

```text
projects/testproject/artifacts/offline_compare_012000_focus_YYYYMMDD/
```

Do not commit generated outputs unless the user explicitly asks.

## 13. Next-Agent Work Plan

Step 1: verify local repo and import path.

```bash
cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
git status --short --untracked-files=all
projects/testproject/.venv/bin/python -c "import lerobot; print(lerobot.__file__)"
```

Step 2: verify current RunPod endpoint from the UI or user message.

```text
RunPod IP/port changes after migration.
Do not assume an old endpoint works.
```

Step 3: verify 012000 checkpoint exists on RunPod.

```bash
ssh -i ~/.ssh/runpod_ed25519 -p <PORT> root@<RUNPOD_IP> \
  'ls -lh /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model'
```

Step 4: run the offline comparison from the plan.

```text
Compare 003000 vs 012000 on selected successful focus-window frames.
Save predictions, comparison CSV, failure examples, and notes under artifacts/.
```

If a new diagnostic script is needed:

```text
It must be offline-only.
It must not move the robot.
It should be explained to the user before creating it if it adds source code.
```

Step 5: decide from evidence.

```text
Case A: 012000 misses close/lift on training frames
  -> do not run real arm again yet
  -> inspect training depth, gripper/action normalization, frame timing, and dataset balance

Case B: 012000 predicts close/lift correctly on training frames
  -> next physical test should control start state and camera geometry
  -> use official LeRobot, three cameras, official defaults, trace_dir enabled

Case C: offline results are mixed
  -> identify exactly which frame types fail:
     before-close, centered-close, held-close, lift/move
  -> use that to choose more training vs correction data
```

## 14. Next Physical Run Gate

Only run another real-arm evaluation after the offline comparison or explicit
user approval.

Before the next physical 012000 run:

```text
top/front/wrist cameras connected and visually checked
arm starts in normal original-episode start pose
gripper is visibly open
first observed gripper state is closer to 40-55, not 20-30
task text unchanged
official LeRobot async execution
robot.max_relative_target remains None
read-only trace enabled
external video is still useful as human-visible outcome evidence
```

Why external video is still useful:

```text
Trace tells what Pi05 saw and commanded.
External video tells whether the physical orange actually moved/lifted.
Use both when possible.
```

## 15. Important Docs To Read First

Read in this order:

```text
projects/testproject/docs/pi05_active_work_tracker.md
projects/testproject/docs/pi05_012000_trace_vs_training_analysis_20260723.md
projects/testproject/docs/pi05_012000_offline_comparison_plan.md
projects/testproject/docs/pi05_work_prioritization.md
projects/testproject/docs/pi05_run_evidence_checklist.md
projects/testproject/docs/official_lerobot_only_workflow.md
projects/testproject/docs/repo_source_control_policy.md
```

Older docs are historical and may contain stale paths or older strategy.
Prefer the active tracker and this handoff.

## 16. Do Not Do These Next

Do not:

```text
repeat ordinary real-arm 012000 tests without new evidence/control
change camera mapping silently
change task text silently
set robot.max_relative_target silently
change actions_per_chunk or chunk_size_threshold silently
use /dev/video4 as wrist/front RGB
use the incomplete 006000 checkpoint
push videos/images/traces/checkpoints/datasets to git
recommend more episodes before proving the existing focused windows are insufficient
```

## 17. Current Short Summary

Where we are:

```text
The official LeRobot 3-camera path works.
The 012000 checkpoint exists and was tested twice.
Both runs reached/contacted the orange but did not pick/lift it.
One run did not close strongly near the orange.
One run closed strongly too early, then opened near the orange.
Training data contains many verified close/lift examples.
The next evidence step is offline 012000-vs-training-frame comparison.
```

The next agent should start there.
