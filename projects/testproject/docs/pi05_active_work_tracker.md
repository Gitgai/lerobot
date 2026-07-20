# Pi05 Active Work Tracker

Last updated: 2026-07-20

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
Make an evidence-based decision about why Pi05 reaches/touches the orange but does not reliably grasp/lift it.
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
Pi05 checkpoint 005000/pretrained_model is the current complete checkpoint.
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
We need either user physical-outcome notes or external video for the latest traced run.
The trace proves what Pi05 saw and what LeRobot sent to the robot, but an external view still helps label exact contact/grasp/lift outcome.
```

### Not Proven Yet

```text
We now know the exact top/front/wrist images, Pi05 action chunks, executed actions, robot state, and timestamps for official_async_3cam_trace_20260720_010244.
We do not yet have an external physical-outcome label for that traced run.
We do not yet know whether the same mistimed close/open pattern appears in the training demonstrations.
We do not yet know whether more fine-tuning is the correct next fix.
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
| T08 | P2 | todo | Compare failed trace against 49 training episodes | Table of similar close-range cases and gripper/lift timing | Check whether demos contain enough centered-close-lift examples from wrist view |
| T09 | P2 | todo | Decide whether close-range correction episodes are justified | Evidence Pi05 lacks close/lift or dataset lacks close-range examples | Use trace plus training comparison; do not record blindly |
| T10 | P3 | deferred | Fine-tune more | Verified dataset gap and selected complete checkpoint | Do not fine-tune until T08/T09 justify it |

## 5. Current Highest Priority

Current highest priority:

```text
T08: Compare the traced failure pattern against the 49 training episodes before collecting more data.
```

Why:

```text
The official traced run proves the software path, cameras, policy server, and action execution are working.
The trace shows Pi05 had clear 3-camera visual input and LeRobot sent the same actions Pi05 requested.
The strongest gripper-close command happened early, while later close-range frames showed the orange near the gripper but the gripper command trended open.
Before collecting new episodes, compare this pattern against the 49 training episodes to see whether close-range centered-close-lift examples are missing or underrepresented.
```

Acceptance criteria:

```text
Identify whether the training data contains enough examples where the wrist camera sees:
  gripper centered around orange
  gripper closes while centered
  arm lifts after close
Decide with evidence whether to record close-range correction episodes.
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
More fine-tuning
More data collection
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
Compare official_async_3cam_trace_20260720_010244 against the 49 training episodes.
Focus on close-range wrist/top/front frames where the gripper centers around the orange, closes, and lifts.
```

After that:

```text
If the dataset is weak in close-range correction examples, record a small batch of correction episodes.
If the dataset already has strong close-range examples, inspect Pi05 config/checkpoint behavior before collecting more data.
```
