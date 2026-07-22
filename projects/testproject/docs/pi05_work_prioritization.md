# Pi05 Work Prioritization

Last updated: 2026-07-23

This document defines how we decide what to work on first for the SO-101 Pi05 orange-pick project.

It exists because the project has many possible next actions:

```text
fix cameras
run official LeRobot async
record more demos
fine-tune more
add instrumentation
change action chunk settings
inspect video
inspect logs
debug RunPod
```

Without prioritization, we can easily do busy work that does not answer the real question.

## 1. Main Principle

Priority is based on evidence value.

The highest priority task is the one that most directly answers:

```text
Where exactly is the failure happening?
```

The failure could be:

```text
camera input
robot state input
Pi05 output
LeRobot action queue
robot execution
timing/latency
training data coverage
hardware setup
```

We should work in that order only when evidence supports it.

## 2. Priority Levels

### P0: Blocks Meaningful Evidence

P0 means:

```text
We cannot run a valid test or collect useful evidence until this is fixed.
```

Examples:

```text
wrist camera not readable by official LeRobot
policy_server not running
SSH tunnel broken
SO-101 follower not connected
checkpoint incomplete
camera images stale or wrong
```

Rule:

```text
Do P0 before model/data changes.
```

### P1: Produces Required Evidence

P1 means:

```text
This produces evidence needed for the next decision.
```

Examples:

```text
one clean official async run
camera precheck images
saved logs
external video
outcome label
log review
```

Rule:

```text
Do P1 after P0 is cleared.
Do not skip P1 and jump to fine-tuning.
```

### P2: Explains A Specific Failure

P2 means:

```text
This is useful after a real failure is observed and basic logs/video are not enough.
```

Examples:

```text
read-only async trace instrumentation
action chunk analysis
executed action comparison
training dataset comparison
close-range correction demo decision
```

Rule:

```text
Do P2 only after the P1 run shows what needs deeper investigation.
```

### P3: Optimization Or Improvement

P3 means:

```text
This may improve performance but is not needed to identify the current failure.
```

Examples:

```text
more fine-tuning
more episodes
camera angle refinement after cameras already work
queue tuning
additional dashboards
cleanup docs
```

Rule:

```text
Do P3 only when evidence says it is the right fix.
```

## 3. Current Priority Order

Current priority order:

```text
P0. Keep the official three-camera gate: top, front, and wrist are required.
P1. Official async 3-camera run, video review, log review, and trace run are complete for the current failure.
P2. The 49-episode training dataset has been reviewed for full grasp-pick-move windows.
P2. Offline focused-dataset builder was approved, created, and validated.
P3. Option A 003000 fine-tune is complete: original 49 episodes plus focused grasp-pick-move windows once.
P1. Option A staged 012000 checkpoint is complete and has been tested twice on the real arm.
P1. Next: offline-compare 012000 on successful focus-window frames.
P1. Then: run a start-state-controlled official 3-camera trace only if needed and approved.
P2. Then: decide whether the issue is undertraining, start-state/camera deployment mismatch, or missing correction data.
P3. Record new correction episodes only if the evidence says existing focused windows are still insufficient.
```

## 4. What Always Comes Before Fine-Tuning

Fine-tuning is expensive and can hide the real problem.

Before fine-tuning more, we need evidence for at least one of:

```text
Pi05 did not command close/lift even with good camera inputs.
Training data lacks complete align-close-lift-move-place examples.
Training data camera views differ from deployment camera views.
Gripper close timing in training data does not match the needed behavior.
The current checkpoint is clearly undertrained and infrastructure is already proven good.
The current checkpoint fails to reproduce successful training/focus frames in offline comparison.
```

Fine-tuning should not be prioritized if:

```text
cameras are not working
official async run has not been tested cleanly
logs show infrastructure failure
we do not know what Pi05 actually output
we only have one external video and no action evidence
```

## 5. What Always Comes Before Changing LeRobot Settings

Do not change:

```text
actions_per_chunk
chunk_size_threshold
aggregate_fn_name
robot.max_relative_target
camera mapping
task text
```

until we know what problem the change is intended to solve.

Required evidence examples:

```text
queue empty often -> maybe inspect official queue settings
latency too high -> maybe adjust inference/timing setup
camera missing -> fix camera mapping/source
action too large and unsafe -> discuss robot safety setting
task text mismatch -> compare training task/instruction text
```

Every non-default must be recorded in the run manifest:

```text
value changed
reason
evidence
user approval
expected effect
```

## 6. What Always Comes Before Instrumentation

Instrumentation is allowed only when it is justified.

Before code instrumentation:

```text
official LeRobot path must be attempted
default official logs/video must be checked
we must identify the exact missing evidence
Codex must explain what code will change
user must approve
```

Instrumentation priority becomes P2 when:

```text
the robot reaches/touches but does not grasp
logs do not show exact action values
video alone cannot prove whether Pi05 commanded close/lift
we need to link exact camera images to exact action chunks
```

Instrumentation stays deferred when:

```text
the camera setup is still broken
policy_server cannot load
the robot does not connect
the run fails before Pi05 returns actions
```

## 7. Decision Tree

Use this tree after every test.

```text
Did all cameras work?
  no  -> P0 camera fix
  yes -> continue

Did policy_server load the model?
  no  -> P0 RunPod/checkpoint/env fix
  yes -> continue

Did robot_client receive action chunks?
  no  -> P0/P1 async connection/log review
  yes -> continue

Did the arm move meaningfully toward the orange?
  no  -> inspect camera/state/action trace need
  yes -> continue

Did the gripper center around the orange?
  no  -> inspect camera images and Pi05 action chunks
  yes -> continue

Did the gripper close?
  no  -> inspect Pi05 gripper action and training close examples
  yes -> continue

Did it lift/move the orange?
  no  -> inspect lift actions and training lift examples
  yes -> repeat for reliability
```

## 8. Evidence-To-Priority Matrix

| Evidence | Priority Result | Work To Do |
| --- | --- | --- |
| Wrist camera not readable | P0 | Fix camera before model tests |
| ESP32 appears only as serial/JTAG | P0 | Do not use it as wrist unless it becomes UVC `/dev/videoX` |
| Top/front/wrist precheck images bad | P0 | Fix camera placement/source |
| Checkpoint missing weights | P0 | Use complete checkpoint |
| Policy server not listening | P0 | Fix RunPod server |
| Robot client fails before motion | P0 | Fix config/hardware/camera |
| Action chunks return but queue is empty/stale | P2 | Inspect queue/timing, then consider setting changes |
| Video shows reach/touch but no grasp | P2 | Add trace or inspect actions before collecting data |
| Trace shows no gripper close | P3 after evidence | Collect close-range correction demos or fine-tune |
| Trace shows close command but robot does not close | P1/P2 hardware | Inspect gripper execution and robot state |
| Trace shows good grasp/lift once | P2 reliability | Repeat controlled runs and measure success rate |
| Dataset review finds 35+ good grasp-pick-move windows | P2 | Build focused dataset from existing approved windows before recording more demos |
| Dataset review finds fewer than 20 good grasp-pick-move windows | P3 data collection | Record new focused correction episodes |
| Option A fine-tune completes | P1 | Evaluate new checkpoint on real arm with official async, three cameras, trace, and video |
| Option A still reaches but does not lift/move | P2 | Compare new Pi05 action chunks to the previous traced failure before recording new episodes |

## 9. Work-In-Progress Limit

Only one active P0/P1 investigation should be open at a time.

Current WIP limit:

```text
1 hardware/camera blocker
1 official test run
1 analysis task
```

Do not start:

```text
fine-tuning
new dataset recording
setting experiments
instrumentation
```

while a P0 camera/server/robot blocker is still open.

## 10. How We Track Priority Changes

When a priority changes, update:

```text
docs/pi05_active_work_tracker.md
```

Add:

```text
date
task ID
old priority
new priority
evidence causing change
next action
```

Example:

```text
Date: 2026-07-19
Task: T06 read-only trace instrumentation
Old priority: deferred
New priority: P2
Evidence:
  Official async 3-camera run reached/touched but did not grasp.
  Logs did not include numeric Pi05 action chunks.
Next action:
  Ask user approval to add read-only trace instrumentation.
```

## 11. Current Do-Not-Do List

Do not do these now:

```text
Do not start the long expert fine-tune before the 200-step smoke train passes.
Do not record correction demos yet; use approved existing windows first.
Do not change APQ-style behavior manually.
Do not add robot.max_relative_target unless user approves.
Do not remove official defaults silently.
Do not create custom eval scripts.
Do not run top/front-only as Pi05 evaluation.
Do not use the connected ESP32 serial/JTAG device as a camera.
```

These can become valid later, but only when evidence makes them the smallest correct next step.

## 12. Current 012000 Evidence Rule

The 012000 checkpoint has already been tested twice through official LeRobot
async execution.

```text
trace 230756:
  reached/contacted orange
  strong close <=25 count: 0
  final 100 actions stayed partial/open-ish, gripper 32.56-47.48
  no pick/lift

trace 233341:
  reached/contacted orange
  strong close <=25 count: 85
  strong close happened at timesteps 0-84
  final near-orange window was open, gripper 54.33-58.88
  no pick/lift
```

Priority rule:

```text
Do not repeat the same ordinary 012000 real-arm run again as the next step.
First run offline 012000 comparison on successful focus-window frames.
Then control the real-arm start state before any next physical evaluation.
```

Reason:

```text
The current failure is not basic reach, camera connection, LeRobot execution, or action clamp.
The current failure is close timing and grasp geometry.
Repeating the same setup is lower evidence value than checking whether 012000 can imitate successful close/lift frames offline.
```
