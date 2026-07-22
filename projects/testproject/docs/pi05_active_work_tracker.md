# Pi05 Active Work Tracker

Last updated: 2026-07-22

This is the active tracker for the SO-101 Pi05 orange-pick work.

Use this file to answer:

```text
What are we working on now?
What is blocked?
What evidence do we have?
What is the next concrete action?
What should not be worked on yet?
```

This is different from the older progress documents. Older docs explain history. This tracker controls current work.

## 1. Current Objective

Main objective:

```text
Finish a staged Pi05 fine-tune, compare the new checkpoint offline, and only then run the real arm again.
```

Current execution rule:

```text
Use official LeRobot behavior first.
Use official defaults unless the user approves a change.
Do not create custom scripts or modify execution code until official LeRobot is checked and the user approves instrumentation.
```

Current deployment target:

```text
local laptop official robot_client -> RunPod official policy_server -> Pi05 checkpoint -> SO-101 follower
```

## 2. Current State Summary

### Working

```text
RunPod policy_server can run.
SSH tunnel to RunPod can work.
Top camera /dev/video0 reads normally.
Front camera /dev/video2 reads normally.
Wrist camera /dev/video6 reads through the Raspberry Pi -> ffmpeg -> v4l2loopback bridge.
SO-101 follower serial port is known.
Pi05 checkpoint 005000/pretrained_model is the complete base orange checkpoint we are keeping.
Pi05 Option A focused checkpoint 003000/pretrained_model is complete on RunPod and is the starting point for staged fine-tuning.
Pi05 batch-size probes on RTX 3090 passed for batch_size=2 and batch_size=4.
The staged batch_size=4 run from 003000 to 012000 was launched on RunPod, reached step 6000, then failed while saving because of disk quota.
Old base checkpoints 001000-004000 were deleted after user approval, freeing workspace usage from about 91 GB to about 48 GB.
Official async path previously moved the real arm with top/front camera setup.
Official async path connected top/front/wrist cameras together on 2026-07-19.
Official async path generated Pi05 action chunks with robot.max_relative_target=None.
Read-only trace instrumentation is approved and implemented.
Official async 3-camera trace run official_async_3cam_trace_20260720_010244 captured camera frames, robot state, Pi05 action chunks, executed actions, timestamps, and task text.
```

### Blocked

```text
No current P0 hardware/software blocker is known for another official 3-camera async run.
```

Current evidence gap:

```text
We need to restart staged fine-tuning from the complete focused `003000/pretrained_model` checkpoint.
```

### Not Proven Yet

```text
We now know the exact top/front/wrist images, Pi05 action chunks, executed actions, robot state, and timestamps for official_async_3cam_trace_20260720_010244.
We now know the existing 49-episode dataset contains many good full grasp-pick-move windows.
We now have a validated focused grasp/pick/move dataset built from 40 approved non-holdout windows.
We now have a validated Option A training dataset: original 49 full episodes plus the 40 focused windows once.
We now have a completed 3000-step Option A fine-tuned checkpoint on RunPod.
The 3000-step batch_size=1 checkpoint is likely undertrained relative to the 40,712-frame dataset.
The staged 12000-step batch_size=4 checkpoint does not exist yet.
The partial `006000` folder exists but is incomplete and unusable.
We do not yet know whether the staged checkpoint improves real-arm grasp/lift/move success.
```

## 3. Single Source Of Truth Docs

Use these documents together:

```text
docs/pi05_active_work_tracker.md
  Current tasks, blockers, evidence, and next actions.

docs/pi05_work_prioritization.md
  How to decide priority and what not to do yet.

docs/pi05_three_camera_requirement.md
  Decision that correct Pi05 evaluation requires top, front, and wrist cameras.

docs/repo_source_control_policy.md
  Source-control rule: testproject is a normal folder inside the parent LeRobot repo.

docs/pi05_evidence_investigation_master_plan.md
  Full evidence-based investigation strategy.

docs/pi05_async_trace_instrumentation_plan.md
  What trace data we may collect if official logs are not enough.

docs/pi05_grasp_focus_dataset_plan.md
  Plan for mining verified grasp/pick/move windows from the existing 49 episodes before recording more.

docs/pi05_staged_finetuning_execution_plan.md
  Current staged fine-tuning plan, checkpoint save policy, RunPod cleanup evidence, and restart gates.

docs/pi05_run_evidence_checklist.md
  Checklist for each real-arm run.

docs/official_lerobot_only_workflow.md
  Project rule: official LeRobot first.

docs/pi05_official_async_test_plan.md
  Official async testing plan.
```

## 4. Active Task Board

Statuses:

```text
todo
in_progress
blocked
done
deferred
```

Priorities:

```text
P0 = blocks all meaningful next work
P1 = needed for next evidence run
P2 = useful after current evidence exists
P3 = later improvement
```

| ID | Priority | Status | Task | Evidence Needed | Next Action |
| --- | --- | --- | --- | --- | --- |
| T01 | P0 | done | Make wrist camera usable by official LeRobot as a normal camera | Wrist appears as `/dev/video6`, reports Video Capture, and OpenCV reads frames | Keep bridge running before tests |
| T02 | P0 | done | Save fresh 3-camera precheck images | Top/front/wrist images saved by official camera discovery | Recheck only if cameras move or reboot |
| T03 | P1 | done | Run one clean official async 3-camera test | Run folder with logs, camera precheck, external video, official defaults | Latest run is labeled from IMG_9257 |
| T04 | P1 | done | Label official run outcome | Outcome score 0-5 and key timestamps | Outcome: reach/near-contact, no grasp/lift |
| T05 | P1 | done | Review official async logs | Model load, inference timing, queue behavior, errors | Record findings in evidence register |
| T06 | P2 | done | Add read-only async trace instrumentation | User approval and reason official logs are insufficient | Implemented as opt-in `--trace_dir`; default behavior unchanged |
| T07 | P2 | done | Run one instrumented official async trace test | Images, state, action chunks, executed actions, timing | Trace saved under `artifacts/traces/official_async_3cam_trace_20260720_010244/` |
| T08 | P2 | done | Compare failed trace against 49 training episodes | Reviewed grasp-pick-move windows with synchronized camera and action evidence | First pass found 45 good windows, 2 uncertain, 1 bad, 1 grasp_only |
| T09 | P2 | done | Decide whether grasp-pick-move correction episodes are justified | Evidence identifies which part of align-close-lift-move-place is missing or underrepresented | Do not record new episodes yet; mine focused dataset first |
| T10 | P2 | done | Ask approval and create offline focused-dataset builder | User-approved script plan, review CSV, output path, and no source overwrite | Script created; no robot movement |
| T11 | P2 | done | Build and validate focused grasp-pick-move dataset | LeRobotDataset loads, videos decode, metadata/action/state align | 40 good non-holdout windows validated |
| T12 | P2 | done | Build and validate Option A training dataset | Original 49 + focused windows once, LeRobotDataset load passes | Dataset and package tarball created |
| T13 | P1 | done | Upload Option A dataset to RunPod | Current RunPod direct TCP SSH host/port works and dataset extracts under `/workspace/lerobot_datasets` | Uploaded to active pod at `213.192.2.83:40161` using `~/.ssh/runpod_ed25519` |
| T14 | P1 | done | Fine-tune Option A | Smoke train passes, then expert train writes checkpoints | 3000-step expert run completed; checkpoint `003000/pretrained_model` exists |
| T15 | P1 | todo | Run staged longer Option A fine-tune | RTX 3090 batch_size=4 train reaches checkpoint `012000/pretrained_model` | Restart from complete `003000/pretrained_model` into fresh output folder after confirming no duplicate process |
| T16 | P1 | todo | Offline-compare staged checkpoint against 003000 | Same focus frames show improved close/lift predictions and fewer missed strong-close cases | Run comparison only after a complete staged checkpoint exists |
| T17 | P1 | todo | Evaluate staged checkpoint on real arm | Official 3-camera async run with trace, logs, and physical outcome | Only start after offline comparison improves |
| T18 | P1 | todo | Analyze staged real-arm evaluation | Trace shows camera frames, Pi05 action chunks, executed actions, state, timing, and task text | Compare against previous reach-without-grasp trace |

## 5. Current Highest Priority

Current highest priority:

```text
Restart the staged 12000-step batch_size=4 fine-tune from the complete focused 003000 checkpoint.
```

Why:

```text
The official traced run proved the software path, cameras, policy server, and action execution are working.
The trace showed Pi05 had clear 3-camera visual input and LeRobot sent the same actions Pi05 requested.
The Option A dataset was built and validated from original 49 full episodes plus the 40 focused windows once.
The 003000 run used only 3000 effective samples, about 0.074 epoch on the 40,712-frame dataset.
Batch_size=4 fits the RTX 3090, so the next evidence step is a longer staged checkpoint before another real-arm run.
The staged run reached 6000 steps but failed while writing the checkpoint because the RunPod volume quota was exceeded.
```

Acceptance criteria:

```text
Current RunPod endpoint is known.
Partial `006000` checkpoint is marked unusable.
At least the complete `005000` base checkpoint and complete focused `003000` checkpoint are kept.
Restarted run writes a complete checkpoint before offline comparison.
```

## 6. Current Known Commands And Paths

Project path:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject
```

Current complete checkpoint:

```text
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model
```

Current focused Option A checkpoint:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
```

Current staged fine-tune output:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000
```

Current staged fine-tune target checkpoint:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model
```

Known failed staged checkpoint:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_012000/checkpoints/006000
status: incomplete, do not use
reason: Disk quota exceeded while writing model.safetensors
```

Validated local training datasets:

```text
focused windows only:
  /data/lerobot_datasets/so101_orange_49_grasp_pick_move_focus
  repo_id: local/so101_orange_49_grasp_pick_move_focus
  40 episodes, 10,988 frames

Option A training mix:
  /data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
  repo_id: local/so101_orange_49_plus_grasp_pick_move_focus
  89 episodes, 40,712 frames

local package:
  /data/downloads/so101_orange_49_plus_grasp_pick_move_focus.tar.gz
```

RunPod training dataset:

```text
/workspace/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
```

Known local cameras:

```text
top   = /dev/video0
front = /dev/video2
wrist = /dev/video6
```

Accepted wrist paths:

```text
current: /dev/video6 through Raspberry Pi camera bridge
preferred long-term: small USB UVC wrist camera that appears as /dev/videoX
not accepted: current ESP32 serial/JTAG device
not accepted: direct Raspberry Pi TCP stream if official LeRobot rejects it
```

Known follower serial port:

```text
/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00
```

Current intended task text:

```text
pick up the orange and move it to another place
```

## 7. Evidence Register

Use this section to record important evidence files after each run.

| Date | Run ID | Evidence | What It Proves | Notes |
| --- | --- | --- | --- | --- |
| 2026-07-18 | camera_check_20260718_223923 | `artifacts/camera_check_20260718_223923/` | Top/front/wrist images existed, but front framing was weak and wrist adapter still needed work | Use only as pre-fix evidence |
| 2026-07-18 | IMG_9248 | `artifacts/IMG_9248.MOV` and extracted frames | Arm reached/touched/pushed orange but did not cleanly grasp/lift | External video, not exact Pi05 input trace |
| 2026-07-19 | official_async_3cam_20260719_1547_long | `projects/testproject/logs/official_async_3cam_20260719_1547_long/robot_client.log`; RunPod `/workspace/logs/policy_server_official_3cam_20260719_long.log` | Official LeRobot async connected top/front/wrist/follower, used `robot.max_relative_target=None`, loaded Pi05 on GPU, and generated action chunks | Physical outcome still needs external video/direct observation |
| 2026-07-19 | IMG_9257 | `artifacts/IMG_9257.MOV`; analysis frames under `artifacts/video_analysis_img_9257/` | Arm repeatedly reached the orange zone and got close, but the orange stayed outside the gripper center; no clean close/lift was visible | External video only; does not show exact Pi05 image/action trace |
| 2026-07-19 | official_async_3cam_20260719_1725_repeat | `projects/testproject/logs/official_async_3cam_20260719_1725_repeat/robot_client.log`; RunPod `/workspace/logs/policy_server_official_3cam_20260719_40003.log` | Official LeRobot async connected top/front/wrist/follower after RunPod migration, used `robot.max_relative_target=None`, loaded Pi05 on GPU, and generated action chunks without server errors | Physical outcome still needs external video/direct observation |
| 2026-07-19 | IMG_9258 | `artifacts/IMG_9258 (1).MOV`; analysis frames under `artifacts/video_analysis_img_9258_1/` | Repeat video shows reach and side/top contact with the orange, but no centered grasp and no lift | External video only; strengthens the reach-without-grasp finding |
| 2026-07-20 | official_async_3cam_trace_20260720_010244 | `artifacts/traces/official_async_3cam_trace_20260720_010244/`; `analysis_contact_sheet.jpg`; `analysis_action_state_timeline.png` | Official LeRobot async with top/front/wrist captured 130 observations, 390 images, 115 Pi05 action chunks, and 1,564 executed actions; no `robot.max_relative_target` clamp was used; requested and performed actions matched | Trace shows good visual input and no hidden command clamp; gripper close appears strongest early, then trends open near the object |
| 2026-07-21 | dataset_grasp_window_audit_20260720 | `artifacts/dataset_grasp_window_audit_20260720/grasp_pick_move_review.csv`; `contact_sheet_pages_v2/`; `codex_visual_review_notes.md`; `grasp_focus_execution_summary.txt` | Existing 49-episode dataset contains many usable full grasp-pick-move windows; gripper direction confirmed from visual/action evidence | First pass labels: 45 good, 2 uncertain, 1 bad, 1 grasp_only; 5 good windows held out; 40 good non-holdout windows available for the first focused dataset |
| 2026-07-21 | grasp_focus_dataset_validation_20260721 | `artifacts/grasp_focus_dataset_validation_20260721/validation_report.md`; `/data/lerobot_datasets/so101_orange_49_grasp_pick_move_focus` | Focused dataset built from 40 approved non-holdout windows; 10,988 frames; LeRobotDataset load/decode passed with top/front/wrist | Original source dataset was not modified |
| 2026-07-21 | orange49_plus_grasp_focus_validation_20260721 | `artifacts/orange49_plus_grasp_focus_validation_20260721/validation_report.md`; `/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus`; `/data/downloads/so101_orange_49_plus_grasp_pick_move_focus.tar.gz` | Option A dataset built and validated: original 49 episodes plus focused windows once; 89 episodes, 40,712 frames; LeRobotDataset load/decode passed | Package tarball is 764 MB |
| 2026-07-21 | runpod_option_a_upload_20260721 | `/workspace/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus` | Option A dataset uploaded and extracted on RunPod | Uploaded to `root@213.192.2.83:40161` using `~/.ssh/runpod_ed25519`; extracted size about 793 MB |
| 2026-07-21 | pi05_orange49_plus_grasp_focus_smoke_20260721 | `/workspace/logs/pi05_orange49_plus_grasp_focus_smoke_20260721.log` | Dataset, checkpoint loading, and training loop worked on RunPod | 200/200 steps completed; checkpoint save hit disk quota before cleanup, so it was treated as train-loop proof only |
| 2026-07-21 | pi05_orange49_plus_grasp_focus_expert_20260721 | `/workspace/logs/pi05_orange49_plus_grasp_focus_expert_20260721.log`; `/workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model` | Option A fine-tune completed from checkpoint 005000 and wrote a usable Pi05 checkpoint | 3000/3000 steps, final loss about 0.053, `model.safetensors` 8.8 GB, checkpoint directory 11 GB |
| 2026-07-22 | pi05_orange49_focus_bs4_from003000_012000_20260721_193801 | `/workspace/logs/pi05_orange49_focus_bs4_from003000_012000_20260721_193801.log`; partial `/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_012000/checkpoints/006000` | Batch_size=4 training ran successfully to step 6000, but checkpoint save failed because of disk quota | `006000` is incomplete: only `config.json`, no `model.safetensors`, no `train_config.json`, no `training_state`; do not use |
| 2026-07-22 | runpod_checkpoint_cleanup_20260722 | RunPod `/workspace/outputs/pi05_base_to_orange49_expert/checkpoints` | Deleted old base checkpoints `001000`-`004000` after user approval; kept complete `005000` base and complete focused `003000` | Workspace usage dropped from about 91 GB to about 48 GB |

Add every serious run here.

## 8. Decision Log

Use this format:

```text
Date:
Decision:
Evidence:
Reason:
Follow-up:
```

### 2026-07-19

Decision:

```text
Do not fine-tune or collect more episodes until the latest official 3-camera run outcome is labeled.
```

Evidence:

```text
Official 3-camera async now runs through the LeRobot robot_client and policy_server.
Default async logs prove model load, inference timing, action chunk shape, and client/camera/follower connection.
Default async logs do not prove the physical grasp outcome by themselves.
```

Reason:

```text
Fine-tuning now may solve the wrong problem if the latest official run already improves behavior or if the remaining failure is execution/timing rather than data coverage.
```

Follow-up:

```text
Inspect external video or repeat one official run with recording, then decide whether read-only trace is needed.
```

### 2026-07-19 Official 3-Camera Async Run

Decision:

```text
Treat the official 3-camera software path as working unless new evidence breaks it.
```

Evidence:

```text
top=/dev/video0, front=/dev/video2, wrist=/dev/video6 all connected through official OpenCVCamera.
SO-101 follower connected.
robot.max_relative_target=None, so the run used the official default of no robot-level relative movement clamp.
Policy server loaded Pi05 on RTX 3090 in 165.5578 seconds.
Server generated 108 logged action chunks, each shaped [1, 50, 6].
No policy_server ERROR or Traceback was found in the run log.
```

Reason:

```text
This clears the previous camera/setup blocker and moves the work to outcome analysis.
```

Follow-up:

```text
Attach or inspect the run video. If no video exists, repeat one official 3-camera run while recording.
```

### 2026-07-19 IMG_9257 Video Outcome

Decision:

```text
Treat the latest physical outcome as reach/near-contact success but grasp/lift failure.
```

Evidence:

```text
IMG_9257 duration is 159.838 seconds.
At about 00:02, the gripper contacts or nearly contacts the orange but is not centered.
At about 01:10-01:35, the gripper returns to the orange zone but remains offset.
At about 01:54, a human hand enters the scene, so later evidence must be treated carefully.
At about 02:08-02:20, the gripper makes the closest useful approach, but the orange remains outside the center of the gripper mouth and no squeeze/lift is visible.
At the end, the orange is still on the table.
```

Reason:

```text
Video is enough to show the task did not complete, but not enough to prove whether the failure is Pi05 action generation, action execution, timing, or data coverage.
```

Follow-up:

```text
Ask the user before adding read-only async tracing. Do not start more fine-tuning or data collection yet.
```

### 2026-07-19 Official 3-Camera Repeat Run

Decision:

```text
Treat the repeated official software path as healthy after RunPod migration.
```

Evidence:

```text
Run ID: official_async_3cam_20260719_1725_repeat.
RunPod port changed to 40003.
RunPod venv Python 3.12.13 had to be restored after migration.
top=/dev/video0, front=/dev/video2, wrist=/dev/video6 all connected through official OpenCVCamera.
SO-101 follower connected.
robot.max_relative_target=None.
Policy server loaded Pi05 on RTX 3090 in 180.2104 seconds.
Server generated 86 logged action chunks, each shaped [1, 50, 6].
No policy_server ERROR or Traceback was found in the run log.
The robot_client stopped at timeout and disconnected all cameras and the follower.
```

Reason:

```text
The repeated run confirms that the official LeRobot async infrastructure still works after the pod migration.
```

Follow-up:

```text
Use external video/direct observation from this run to label physical outcome.
If the outcome is again reach/near-contact without grasp/lift, the evidence gap remains exact Pi05 image/action trace.
```

### 2026-07-19 IMG_9258 Repeat Video Outcome

Decision:

```text
Treat the repeat physical outcome as reach/contact success but grasp/lift failure.
```

Evidence:

```text
IMG_9258 duration is 167.602 seconds.
At about 01:42, the gripper approaches the orange but remains in front/side of the object.
At about 01:46, the gripper/body contacts the orange area, but the orange is not enclosed between the two fingers.
At about 01:52-01:56, the gripper pulls away while the orange remains on the table.
At about 02:08-02:18, the arm makes another near-target approach, again offset from a clean grasp.
At about 02:46, the arm is still near/touching the orange from the side/top; the orange remains on the table.
```

Reason:

```text
Two external videos now show the same pattern: the policy reaches the orange zone but does not execute a centered close-and-lift grasp.
```

Follow-up:

```text
The next evidence gap is still exact Pi05 input/output trace, because video alone cannot prove whether Pi05 commanded close/lift or whether execution/mapping/timing caused the miss.
```

### 2026-07-19 Read-Only Async Trace Approved And Implemented

Decision:

```text
Use one opt-in official robot_client trace run before more fine-tuning or more dataset collection.
```

Evidence:

```text
The user approved read-only tracing after repeated video evidence showed reach/contact without grasp/lift.
The trace flag is disabled by default:
  trace_dir=None
The official robot_client CLI now exposes:
  --trace_dir [str]
The local testproject virtualenv was still importing LeRobot from /data/projects/lerobot/src.
That was corrected so it now imports from:
  /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/src
Dry-run trace verification created:
  events.jsonl
  observations.jsonl
  action_chunks.jsonl
  executed_actions.jsonl
  images/top/*.jpg
  images/front/*.jpg
```

Reason:

```text
External video proves the physical outcome, but not Pi05's exact visual input or numeric output.
The read-only trace should answer whether Pi05 commanded gripper close/lift and whether robot_client sent the same command to the arm.
```

Follow-up:

```text
Run one official 3-camera test with --trace_dir under artifacts/.
Keep external iPhone video for physical context, but use trace data for cause analysis.
Do not collect correction episodes or fine-tune more until the trace is reviewed.
```

### 2026-07-20 Official 3-Camera Trace Result

Decision:

```text
Treat the official async execution stack as working for the traced run.
Move the investigation from hardware/LeRobot plumbing to policy behavior and training-data coverage.
```

Evidence:

```text
Run ID: official_async_3cam_trace_20260720_010244.
Trace saved 130 observations, 390 camera images, 115 Pi05 action chunks, and 1,564 executed actions.
Cameras present in every observation: top, front, wrist.
Task text: pick up the orange and move it to another place.
robot.max_relative_target was None, so no robot-level relative target clamp was used.
The maximum absolute difference between requested and performed action values was 0.0.
Saved trace images show the orange and gripper clearly during close-range approach.
Gripper command range was 12.50 to 46.49.
Local project notes define gripper around +24 as partly open and around +40 as more open.
The strongest close-ish gripper commands happened around timesteps 148-297.
During later close-range frames around timesteps 520-994, gripper command was mostly 25-40 and trending open rather than committing to close/lift.
```

Reason:

```text
This evidence makes a hidden clamp or missing camera less likely as the primary explanation for this run.
The current failure pattern is timing/geometry: reach is present, but close/lift is not aligned with the close-range orange position.
```

Follow-up:

```text
Compare this traced timing against the 49 training episodes.
If training lacks enough close-range centered-close-lift examples, collect close-range correction episodes.
If training has good examples but the trace still opens near the object, inspect Pi05 config/checkpoint behavior before more data.
```

### 2026-07-21 Grasp-Pick-Move Dataset Review

Decision:

```text
Do not record new correction episodes yet.
Build and validate a focused dataset from approved good windows in the existing 49-episode dataset first.
```

Evidence:

```text
Dataset root /data/lerobot_datasets/so101_orange_49 has 49 episodes, 29,724 frames, 30 FPS, three camera streams, and 6D SO-101 state/action.
Contact sheets were generated for all 49 candidate windows.
Visual review labels: 45 good, 2 uncertain, 1 bad, 1 grasp_only.
Gripper direction was confirmed on representative episodes 00, 07, and 29:
  higher gripper.pos = more open
  lower gripper.pos = more closed
Five good windows are marked as holdout: 0, 11, 24, 37, 48.
That leaves 40 good non-holdout windows for the first focused dataset.
```

Reason:

```text
The plan threshold says 35 or more good windows is enough to try Option A first.
Because the existing dataset already contains many full grasp-pick-move examples, recording new episodes now is not the smallest evidence-based step.
```

Follow-up:

```text
Ask approval for an offline dataset-builder script.
Create a new focused dataset without modifying /data/lerobot_datasets/so101_orange_49.
Validate the new dataset through LeRobotDataset before any fine-tuning.
```

### 2026-07-21 Focus Dataset And Option A Dataset Built

Decision:

```text
Use Option A as the next fine-tuning dataset:
original 49 full episodes + 40 approved grasp/pick/move focused windows once.
```

Evidence:

```text
Focused dataset:
  /data/lerobot_datasets/so101_orange_49_grasp_pick_move_focus
  40 episodes, 10,988 frames
  no holdout windows included
  LeRobotDataset load/decode passed with top/front/wrist images

Option A dataset:
  /data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
  89 episodes, 40,712 frames
  focus windows are episodes 49-88
  LeRobotDataset load/decode passed with top/front/wrist images

Package:
  /data/downloads/so101_orange_49_plus_grasp_pick_move_focus.tar.gz
```

Reason:

```text
The failure trace showed reach behavior but weak close-range grasp posture.
Option A preserves full reach demonstrations while showing successful grasp/pick/move windows more often.
This is the smallest training change before collecting new correction episodes.
```

Follow-up:

```text
Upload the packaged dataset.
Run the 200-step smoke train first.
If smoke passes, run the 3000-step expert continuation from checkpoint 005000/pretrained_model.
```

### 2026-07-21 Option A RunPod Upload And Training

Decision:

```text
Use the new Option A checkpoint for the next real-arm evaluation.
Superseded on 2026-07-22 by the staged fine-tuning plan because the `003000` checkpoint was judged undertrained.
```

Evidence:

```text
RunPod endpoint:
  root@213.192.2.83 -p 40161

Working SSH key:
  ~/.ssh/runpod_ed25519

Dataset uploaded and extracted:
  /workspace/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
  extracted size about 793 MB

Smoke train:
  loaded dataset with 89 episodes and 40,712 frames
  loaded base checkpoint 005000/pretrained_model
  completed 200/200 train steps
  save failed due RunPod disk quota, so temporary outputs and tarballs were cleaned

Expert train:
  base policy: /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model
  output: /workspace/outputs/pi05_orange49_plus_grasp_focus_expert
  steps: 3000
  train_expert_only=true
  save_freq=3000
  completed 3000/3000 steps
  ended with PI05_ORANGE49_PLUS_GRASP_FOCUS_EXPERT_TRAIN_OK
  checkpoint exists at /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
  model.safetensors size is 8.8 GB
  checkpoint directory size is 11 GB
```

Reason:

```text
This completes the planned Option A fine-tune without recording new episodes.
The remaining question is not training infrastructure anymore; it is real-arm behavior.
```

Follow-up:

```text
Restart staged batch_size=4 fine-tuning from the complete focused 003000 checkpoint.
Run offline comparison before any real-arm evaluation.
```

### 2026-07-21 RunPod Upload Blocked By Stale Endpoint

Decision:

```text
Historical resolved block: do not attempt a large upload when the active RunPod direct TCP SSH endpoint is unknown.
```

Evidence:

```text
Last known endpoint checked:
  root@213.192.2.110 -p 40113

Result:
  ssh: connect to host 213.192.2.110 port 40113: Connection refused
```

Reason:

```text
The local dataset and package are ready, but the pod endpoint changed or the pod is not accepting SSH.
```

Follow-up:

```text
This was later resolved by the successful Option A upload.
The current known RunPod endpoint for staged training restart is:
  root@213.192.2.67 -p 40066
```

### 2026-07-19 Wrist Camera Hardware Timeout Blocks Trace Run

Decision:

```text
Do not run the official 3-camera robot trace until the wrist camera self-test passes.
```

Evidence:

```text
top=/dev/video0 and front=/dev/video2 streamed frames with v4l2-ctl.
/dev/video6 loopback was present as Pi_Wrist_Camera and reported Video Capture.
The local OpenCVCamera precheck hung while reading /dev/video6.
Restarting the local ffmpeg bridge did not restore valid wrist frames.
Raspberry Pi rpicam-vid detected the OV5647 camera, but direct 2-second self-test failed.
The first user self-test also showed the camera pipeline was in use by another process.
Investigation found timelapse.service running /home/raspi/timelapse_loop.sh.
That service launched repeated rpicam-still captures into /home/raspi/timelapse/.
Stopping timelapse.service removed the pipeline-busy failure.
After stopping timelapse.service, PipeWire, and WirePlumber, rpicam-still and low-FPS rpicam-vid still failed.
Pi log repeated:
  Camera frontend has timed out!
  Please check that your camera sensor connector is attached securely.
  Alternatively, try another cable and/or sensor.
No official robot_client motion run was started after this failure.
```

Reason:

```text
This proves the current blocker is the Raspberry Pi camera sensor/cable path, not Pi05, RunPod, or the official LeRobot robot_client.
A 3-camera trace run without a working wrist frame would be invalid.
timelapse.service is also incompatible with using the same Pi camera as the LeRobot wrist camera during tests.
```

Follow-up:

```text
Fix or replace the Raspberry Pi wrist camera connection.
Keep timelapse.service stopped during LeRobot wrist-camera tests.
Then rerun the Pi camera self-test before restarting the /dev/video6 bridge.
After /dev/video6 passes OpenCVCamera read, run the official 3-camera trace test.
```

### 2026-07-19 Three-Camera Gate

Decision:

```text
Do not use top/front-only as the main Pi05 evaluation path.
Correct Pi05 evaluation requires top, front, and wrist cameras.
```

Evidence:

```text
The current failure is close-range gripper/object alignment, close, and lift.
The wrist camera is the view most relevant to close-range grasp completion.
The connected ESP32 appears only as /dev/ttyACM1 serial/JTAG, not as /dev/videoX.
```

Reason:

```text
A two-camera run could fail because wrist information is missing, so it would not prove the policy or dataset is the true problem.
```

Follow-up:

```text
Use a USB UVC wrist camera or fix /dev/video6 so it behaves as a real Video Capture device.
```

### 2026-07-19 Source Control Cleanup

Decision:

```text
Use the parent Gitgai/lerobot repo as the only active source-control repo for projects/testproject.
```

Evidence:

```text
The nested projects/testproject repo caused Source Control confusion.
After committing and pushing the nested repo, the parent LeRobot repo could still show the same files as pending.
Both repos were checked before cleanup, and project files were not deleted.
```

Action:

```text
Moved only the nested .git metadata from:
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/.git

to backup:
/home/gaikwad-prakash/PrakashProjects/lerobot/git_metadata_backups/testproject_dotgit_20260719_133929
```

Reason:

```text
One active repo avoids duplicate pending changes and makes commit/push behavior clear.
```

Follow-up:

```text
Commit and push future project work only from /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot.
See docs/repo_source_control_policy.md.
```

## 9. Blocker Log

| Blocker | First Seen | Owner | Current Status | Unblocks |
| --- | --- | --- | --- | --- |
| `/dev/video6` is output-only, not capture | 2026-07-18 | local machine setup | resolved through v4l2loopback bridge | official 3-camera async test |
| Pi TCP stream exits after client disconnect | 2026-07-18 | Raspberry Pi camera setup | mitigated by running bridge before tests | stable wrist camera feed |
| Connected ESP32 is serial/JTAG, not `/dev/videoX` | 2026-07-19 | hardware choice | not usable for wrist unless flashed as UVC | wrist camera replacement |
| Exact Pi05 image/action trace missing from official async | 2026-07-18 | LeRobot async instrumentation decision | resolved for opt-in traced runs with `--trace_dir` | precise root-cause diagnosis |
| RunPod disk quota during Pi05 checkpoint save | 2026-07-21 | RunPod storage management | mitigated by deleting temporary outputs/tarballs and saving only final checkpoint | Option A expert fine-tune |

## 10. How To Update This Tracker

After every meaningful action:

```text
1. Update task status in the Active Task Board.
2. Add new evidence to the Evidence Register.
3. Add decisions to the Decision Log.
4. Add unresolved problems to the Blocker Log.
5. Keep the Current Highest Priority section accurate.
```

Do not let this tracker become a history dump.

Move long explanations to the relevant plan document and link them here.

## 11. What Not To Start Yet

Do not start these until prerequisites are met:

```text
New correction-episode recording before evaluating the Option A checkpoint
Option B repeated-window fine-tuning before Option A real-arm evidence
Changing actions_per_chunk
Changing chunk_size_threshold
Changing robot.max_relative_target
Custom eval scripts
Behavior-changing trace or execution code changes
2-camera Pi05 evaluation
ESP32 serial camera workaround
```

## 12. Next Concrete Action

Next concrete action:

```text
Restart the staged batch_size=4 fine-tune from the complete focused 003000 checkpoint into:

/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000
```

After that:

```text
Verify a complete checkpoint exists.
Run offline comparison against the old focused 003000 checkpoint.
Only if offline comparison improves, evaluate the staged checkpoint on the real arm through official LeRobot async with three cameras and read-only trace.
```
