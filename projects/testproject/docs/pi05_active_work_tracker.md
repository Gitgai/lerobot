# Pi05 Active Work Tracker

Last updated: 2026-07-19

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
SO-101 follower serial port is known.
Pi05 checkpoint 005000/pretrained_model is the current complete checkpoint.
Official async path previously moved the real arm with top/front camera setup.
```

### Blocked

```text
Official 3-camera LeRobot async test is blocked by the wrist camera path.
```

Current wrist problem:

```text
Pi TCP stream can produce frames.
Direct tcp://192.168.1.17:8554 is rejected by official LeRobot OpenCV setup.
/dev/video6 currently reports Video Output only, not Video Capture.
OpenCV cannot read /dev/video6 as a normal camera yet.
```

### Not Proven Yet

```text
We do not yet know the exact images Pi05 saw during the strongest reaching run.
We do not yet know the exact full Pi05 action chunks from that run.
We do not yet know whether Pi05 commanded gripper close/lift and the robot failed to execute it.
We do not yet know whether Pi05 never commanded close/lift.
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
| T01 | P0 | blocked | Make wrist camera usable by official LeRobot as a normal camera | Wrist appears as `/dev/videoX`, reports Video Capture, and OpenCV reads frames | Prefer a small USB UVC wrist camera; fallback is fixing `/dev/video6` capture |
| T02 | P0 | todo | Save fresh 3-camera precheck images | `top.jpg`, `front.jpg`, `wrist.jpg` show useful views | Run camera check after T01 |
| T03 | P1 | todo | Run one clean official async 3-camera test | Run folder with manifest, logs, camera precheck, external video | Run only after T01 and T02 pass |
| T04 | P1 | todo | Label official run outcome | Outcome score 0-5 and key timestamps | Inspect video and logs after T03 |
| T05 | P1 | todo | Review official async logs | Model load, inference timing, queue behavior, errors | Extract findings from robot_client and policy_server logs |
| T06 | P2 | deferred | Add read-only async trace instrumentation | User approval and reason official logs are insufficient | Only after T03-T05 show a grasp failure that logs cannot explain |
| T07 | P2 | deferred | Run one instrumented official async trace test | Images, state, action chunks, executed actions, timing | Only after T06 approval |
| T08 | P2 | deferred | Compare failed trace against 49 training episodes | Table of similar close-range cases and gripper/lift timing | Only after T07 or enough official evidence |
| T09 | P2 | deferred | Decide whether close-range correction episodes are justified | Evidence Pi05 lacks close/lift or dataset lacks close-range examples | Do not record until evidence says why |
| T10 | P3 | deferred | Fine-tune more | Verified dataset gap and selected complete checkpoint | Do not fine-tune until T08/T09 justify it |

## 5. Current Highest Priority

Current highest priority:

```text
T01: Make wrist camera usable by official LeRobot as a normal camera.
```

Why:

```text
Without a working wrist camera, the intended 3-camera official LeRobot test is not clean.
Top/front-only is not an accepted Pi05 evaluation path for this project.
If we continue without wrist evidence, we may blame Pi05 for a camera setup problem.
```

Acceptance criteria:

```text
Wrist camera appears as a normal /dev/videoX device.
v4l2-ctl -D -d /dev/videoX shows Video Capture.
OpenCV can open /dev/videoX.
OpenCV can read a 640x480 RGB frame.
Saved wrist precheck image shows the gripper and useful wrist view.
Official robot_client can connect top, front, and wrist cameras without failing before motion.
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
wrist = a normal /dev/videoX capture camera
```

Accepted wrist paths:

```text
preferred: small USB UVC wrist camera that appears as /dev/videoX
fallback: /dev/video6 only after it reports Video Capture and OpenCV can read it
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
Do not fine-tune or collect more episodes until we get stronger evidence from official LeRobot testing.
```

Evidence:

```text
Current official 3-camera eval is blocked by wrist camera.
Default async logs do not save exact camera images and action chunks.
External video shows reach/touch but not the full cause of failed grasp.
```

Reason:

```text
Fine-tuning now may solve the wrong problem if the actual issue is camera, action queue, execution, or timing.
```

Follow-up:

```text
Fix wrist camera, run official async, then decide whether read-only trace is needed.
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

## 9. Blocker Log

| Blocker | First Seen | Owner | Current Status | Unblocks |
| --- | --- | --- | --- | --- |
| `/dev/video6` is output-only, not capture | 2026-07-18 | local machine setup | open | official 3-camera async test |
| Pi TCP stream exits after client disconnect | 2026-07-18 | Raspberry Pi camera setup | open | stable wrist camera feed |
| Connected ESP32 is serial/JTAG, not `/dev/videoX` | 2026-07-19 | hardware choice | not usable for wrist unless flashed as UVC | wrist camera replacement |
| Exact Pi05 image/action trace missing from official async | 2026-07-18 | LeRobot async instrumentation decision | deferred | precise root-cause diagnosis |

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
Trace instrumentation code changes
2-camera Pi05 evaluation
ESP32 serial camera workaround
```

## 12. Next Concrete Action

Next concrete action:

```text
Fix or replace the wrist camera path so official LeRobot can read all three cameras.
Preferred solution: small USB UVC wrist camera that appears as /dev/videoX.
```

After that:

```text
Save fresh camera precheck images.
Run one official async 3-camera test with official defaults.
Record external video.
Save logs and manifest.
Update this tracker with outcome and evidence.
```
