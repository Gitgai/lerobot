# Pi05 012000 Trace vs Training Analysis

Last updated: 2026-07-23

This document records the evidence from the two complete official LeRobot
3-camera real-arm evaluations of the 012000 checkpoint.

The goal is to answer:

```text
Why did the arm reach the orange but not pick it?
What evidence do we have?
What should we do next?
```

## 1. Scope

This analysis used only saved data. No robot movement was performed during this
analysis.

Analyzed real-arm traces:

```text
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_230756
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_233341
```

Analyzed training dataset:

```text
/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
```

Generated analysis artifacts:

```text
projects/testproject/artifacts/trace_vs_training_analysis_20260723/
```

Important generated files:

```text
trace_summary.csv
trace_action_chunk_summary.csv
trace_per_window_summary.csv
trace_observations.csv
dataset_gripper_distribution.csv
training_focus_episode_action_summary.csv
training_review_window_action_summary.csv
training_window_aggregates.csv
live_start_pose_summary.csv
training_start_pose_distribution.csv
*_contact_sheet.jpg
```

## 2. Evaluation Setup

Both complete 012000 runs used:

```text
Official LeRobot async execution
Laptop robot_client -> RunPod policy_server -> Pi05 -> SO-101 follower
top camera /dev/video0
front camera /dev/video2
wrist camera /dev/video6
task text: "pick up the orange and move it to another place"
robot.max_relative_target: null
```

That means the latest evidence is not from a custom movement script and not from
a robot relative-target clamp.

## 3. Training Evidence

The Option A training mix contains:

```text
89 episodes
40,712 frames
original 49 full episodes
40 focused grasp/pick/move windows appended once
```

The focused 40 windows were built only from approved non-holdout windows. Their
visual review says:

```text
orange visible
gripper closes
orange lifts
orange moves away from original position
```

The review also records the gripper direction:

```text
higher gripper value = more open
lower gripper value = more closed
```

Frame-level gripper distribution:

| Dataset part | Frames | Strong close action <=25 | Near close action <=35 | Open action >=45 |
| --- | ---: | ---: | ---: | ---: |
| Original 49 full episodes | 29,724 | 5,660 frames, 19.04% | 10,728 frames, 36.09% | 11,809 frames, 39.73% |
| Focused 40 windows | 10,988 | 4,449 frames, 40.49% | 6,832 frames, 62.18% | 2,506 frames, 22.81% |
| Full Option A mix | 40,712 | 10,109 frames, 24.83% | 17,560 frames, 43.13% | 14,315 frames, 35.16% |

So the focused dataset does contain many grasp-close examples.

Successful training-window examples:

```text
episode 01 contact sheet:
projects/testproject/artifacts/dataset_grasp_window_audit_20260720/contact_sheets_v2/episode_01_grasp_pick_move_candidate.jpg

episode 07 contact sheet:
projects/testproject/artifacts/dataset_grasp_window_audit_20260720/contact_sheets_v2/episode_07_grasp_pick_move_candidate.jpg

episode 29 contact sheet:
projects/testproject/artifacts/dataset_grasp_window_audit_20260720/contact_sheets_v2/episode_29_grasp_pick_move_candidate.jpg
```

What those sheets show:

```text
orange is between/inside the gripper mouth
gripper closes while the orange is in the mouth
the arm lifts/moves after the close
```

## 4. Trace 230756 Evidence

Trace:

```text
official_async_3cam_012000_trace_20260722_230756
```

Counts:

```text
37 observations
29 Pi05 action chunks
422 executed actions
37 images from each camera
```

Final images:

```text
front:
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_230756/images/front/obs_000420_1784742115443020632_front.jpg

wrist:
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_230756/images/wrist/obs_000420_1784742115443020632_wrist.jpg
```

Generated contact sheets:

```text
projects/testproject/artifacts/trace_vs_training_analysis_20260723/official_async_3cam_012000_trace_20260722_230756_front_contact_sheet.jpg
projects/testproject/artifacts/trace_vs_training_analysis_20260723/official_async_3cam_012000_trace_20260722_230756_wrist_contact_sheet.jpg
```

Numerical gripper evidence:

```text
executed gripper min: 30.56
executed gripper max: 53.13
strong close <=25 count: 0 frames
near close <=35 count: 93 frames
open >=45 count: 245 frames
final 100 executed actions:
  gripper first: 46.67
  gripper min: 32.56
  gripper last: 36.16
```

Pi05 action chunk evidence near the end:

```text
chunk 345-394:
  gripper min 29.27, max 47.51

chunk 370-419:
  gripper min 30.54, max 34.16

chunk 396-445:
  gripper min 35.25, max 37.71
```

Interpretation:

```text
Pi05 did not command a strong close in this run.
It commanded a partial/near close while already near the orange.
The visual frames show the gripper reaches/contact-pushes the orange, but the orange is offset to the side/front rather than captured between both fingers.
The orange remains on the table at the final frame.
```

Evidence-backed result for trace 230756:

```text
reach: yes
near/contact: yes
strong close at the correct moment: no
lift/move: no
```

## 5. Trace 233341 Evidence

Trace:

```text
official_async_3cam_012000_trace_20260722_233341
```

Counts:

```text
21 observations
16 Pi05 action chunks
220 executed actions
21 images from each camera
```

Final images:

```text
front:
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_233341/images/front/obs_000200_1784743659708443050_front.jpg

wrist:
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_233341/images/wrist/obs_000200_1784743659708443050_wrist.jpg
```

Generated contact sheets:

```text
projects/testproject/artifacts/trace_vs_training_analysis_20260723/official_async_3cam_012000_trace_20260722_233341_front_contact_sheet.jpg
projects/testproject/artifacts/trace_vs_training_analysis_20260723/official_async_3cam_012000_trace_20260722_233341_wrist_contact_sheet.jpg
```

Numerical gripper evidence:

```text
executed gripper min: -6.85
executed gripper max: 58.88
strong close <=25 count: 85 frames
first strong close timestep: 0
last strong close timestep: 84
longest strong close run: 85 frames
final 100 executed actions:
  gripper first: 55.39
  gripper min: 54.33
  gripper last: 58.25
```

Pi05 action chunk evidence:

```text
chunk 0-49:
  gripper min -7.25, max -4.01

chunk 49-98:
  gripper min 4.99, max 13.80

chunk 99-148:
  gripper min 48.60, max 51.64

chunk 149-198:
  gripper min 54.64, max 56.51

chunk 174-223:
  gripper min 57.76, max 59.35
```

Interpretation:

```text
Pi05 did command a very strong close.
But it commanded that close at the beginning of the run, before the orange was in the gripper.
By the time the orange was visible close to the gripper, Pi05 was commanding open values around 50-59.
The final visual frames show the orange still on the table and the gripper open/offset.
```

Evidence-backed result for trace 233341:

```text
reach: yes
near/contact: yes
strong close exists: yes
strong close at the correct moment: no
lift/move: no
```

## 6. Start-State Evidence

The live start gripper state was lower/closed-ish than the focus-window start
distribution.

Live starts:

| Trace | Live first state gripper | Live first action gripper |
| --- | ---: | ---: |
| 230756 | 28.64 | 30.56 |
| 233341 | 21.19 | -4.01 |

Training start distributions:

| Training group | State gripper p10 | State gripper mean | State gripper p90 |
| --- | ---: | ---: | ---: |
| Original 49 episode starts | 28.38 | 39.14 | 49.73 |
| Focus 40 window starts | 41.91 | 50.27 | 55.84 |

Interpretation:

```text
The live arm shoulder/elbow/wrist start is similar to original full-episode starts.
The live gripper start, especially in trace 233341, is much more closed than the focused-window starts.
This may contribute to early-close/open timing confusion.
```

This does not fully explain trace 230756, because that run still reached the
orange and failed to strong-close near the object. But it is an evidence-backed
condition we should control before another real-arm run.

## 7. What This Proves

The current evidence supports these conclusions:

```text
The three-camera input path works.
The task text is correct.
The policy server returns Pi05 action chunks.
LeRobot executes actions from Pi05.
The real-arm runs used official defaults with robot.max_relative_target=null.
The failure is not caused by our old custom movement script.
The failure is not simply "Pi05 never learned to close", because trace 233341 has 85 strong-close executed frames.
The failure is close timing and grasp geometry: close does not happen when the orange is correctly centered between the fingers, and lift does not follow a captured grasp.
```

## 8. What This Does Not Prove Yet

Still-open evidence gaps:

```text
We have not yet run an offline 012000 checkpoint comparison on the successful training/focus frames.
So we do not yet know whether 012000 predicts correct close/lift actions when it sees the exact successful training images.

We have not yet run a start-state-controlled real-arm test.
So we do not yet know how much the low/closed-ish initial gripper state contributed to the early-close/open timing.

We have not yet compared camera geometry quantitatively between live final contact frames and successful training contact frames.
The visual evidence suggests live contact is offset, but this still needs side-by-side camera-pose review before changing camera placement.
```

## 9. Recommended Next Actions

Do not run another ordinary real-arm test immediately. We already have enough
evidence that repeating the same setup is unlikely to explain the problem.

Next action 1:

```text
Run offline 012000 checkpoint comparison on selected successful focus-window frames.
```

Why:

```text
If 012000 fails to predict the recorded close/lift actions on successful training frames, then it is still undertrained or the training mix is wrong.
If 012000 predicts the training frames correctly, then the live failure is more likely deployment-state/camera-geometry/start-pose mismatch.
```

Next action 2:

```text
Before the next real-arm evaluation, control the physical start state.
```

Target:

```text
Start with the SO-101 in the normal original-episode start arm pose.
Start with the gripper visibly open.
Confirm first observed gripper state is closer to the training open range, ideally around 40-55 rather than 20-30.
Use the same official LeRobot async command and trace recording.
Do not change actions_per_chunk, task text, camera mapping, or robot.max_relative_target.
```

Next action 3:

```text
If offline comparison is good but start-state-controlled run still fails, inspect camera/geometry mismatch and then decide whether to record new close-range correction episodes.
```

Correction episodes should only be recorded after the above evidence, because
the existing 40 focused windows already contain many successful close/lift
examples.

## 10. Current Working Conclusion

Evidence-based conclusion:

```text
The 012000 checkpoint can reach the orange and can command gripper close, but it has not reliably learned the conditional timing:

when orange is centered between the fingers -> close strongly -> keep closed -> lift/move.

The two latest runs fail in two different timing modes:

230756: no strong close near the orange, only partial close/contact.
233341: strong close happens early, then the gripper opens before/while reaching the orange.
```

Most useful next evidence:

```text
offline 012000 checkpoint comparison on successful focus frames
start-state-controlled official 3-camera trace run only after that comparison or with explicit user approval
```
