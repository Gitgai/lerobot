# Pi05 Evidence-Based Investigation Master Plan

Date: 2026-07-18

This document defines how we will investigate the SO-101 Pi05 orange-pick problem without guessing.

The rule is simple:

```text
Do not guess the fix.
Collect evidence.
Use the evidence to locate the failure point.
Only then change cameras, data, fine-tuning, commands, or code.
```

This plan follows the current project decision:

```text
Use official LeRobot behavior first.
Use official defaults unless the user approves a change.
Do not create or modify scripts until we prove LeRobot does not expose the data we need.
Before adding instrumentation, explain the change and ask for permission.
```

## 1. Current System Under Investigation

The target evaluation path is:

```text
local laptop
  - SO-101 follower arm
  - top camera
  - front camera
  - wrist camera
  - official lerobot.async_inference.robot_client

RunPod GPU
  - official lerobot.async_inference.policy_server
  - Pi05 checkpoint

network
  - local SSH tunnel to RunPod policy server
```

The intended data flow is:

```text
camera frames + robot joint state + task text
        -> official robot_client
        -> official policy_server
        -> Pi05 action chunk
        -> official robot_client action queue
        -> robot.send_action()
        -> SO-101 motors
```

Our investigation must preserve this flow unless the user approves a change.

## 2. Known Current Facts

These are not guesses. These are current observed facts from the repo and recent tests.

```text
The RunPod policy_server can start and listen on port 8080.
The local SSH tunnel can connect to that server.
The complete usable checkpoint is:
  /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model
The later plus5k_from005000/001000 folder was incomplete because it did not contain model.safetensors.
The top camera /dev/video0 reads normally.
The front camera /dev/video2 reads normally.
The Pi wrist TCP stream can produce frames, but direct official OpenCV camera setup rejects it.
/dev/video6 currently appears as Video Output only, not Video Capture.
Official 3-camera async testing is blocked until the wrist camera is readable as a normal camera.
```

The current camera blocker must be resolved before a clean 3-camera policy test.

Current decision:

```text
The main Pi05 evaluation must use all three cameras.
Do not run top/front-only as a Pi05 success/failure test.
Do not use the connected ESP32 unless it becomes a real /dev/videoX UVC camera.
```

## 3. The Problem We Need To Explain

From the iPhone video analysis, the policy behavior looked meaningful:

```text
The arm moved toward the orange.
The gripper got close to the orange.
The gripper touched or pushed the orange.
The gripper did not consistently center around the orange.
The gripper did not close and lift successfully.
```

That means the problem is probably not "the robot is totally random."

But we cannot yet say which exact part is failing:

```text
camera view problem
policy output problem
action queue problem
action execution problem
timing/latency problem
training data coverage problem
start pose or object placement problem
```

We need evidence that separates these cases.

## 4. Failure Points To Test

### 4.1 Camera Evidence Failure

Question:

```text
Did Pi05 actually see the orange and gripper clearly from the camera inputs used for that action?
```

Evidence needed:

```text
top image at each policy observation
front image at each policy observation
wrist image at each policy observation
camera timestamp
policy observation timestep
camera mapping used in the command
```

Possible conclusions:

```text
orange visible and well framed -> camera is less likely the main problem
orange missing from one or more views -> camera setup is a real problem
gripper blocks orange at grasp time -> need more wrist/front correction data or better camera angle
front camera sees mostly room/person, not orange -> front view is weak evidence for Pi05
wrist missing or padded -> policy is not using the intended visual setup
```

### 4.2 Robot State Failure

Question:

```text
Was the robot state sent to Pi05 correct when the model decided what to do?
```

Evidence needed:

```text
observation.state at every policy observation
raw motor positions from SO-101
state feature order
policy expected state feature order
timestep and timestamp
```

Possible conclusions:

```text
state order matches policy -> state wiring is probably correct
state order mismatch -> Pi05 may be reasoning from wrong joint positions
state values jump or freeze -> robot read problem
state differs from visible pose -> calibration or feature mapping problem
```

### 4.3 Pi05 Output Failure

Question:

```text
Did Pi05 command a real grasp sequence?
```

Evidence needed:

```text
full action chunk from Pi05 for each processed observation
action feature names
action values after postprocessor
first action, middle actions, final actions in chunk
gripper action trend across chunk
shoulder/elbow/wrist action trend across chunk
```

A useful grasp sequence should usually show:

```text
approach toward orange
center gripper around orange
close gripper
lift or move after close
```

Possible conclusions:

```text
Pi05 outputs close/lift but robot does not do it -> execution or queue problem
Pi05 never outputs close/lift -> model/data problem
Pi05 outputs close too early or too late -> timing/chunking/data alignment problem
Pi05 outputs mostly hover/reorientation -> policy has weak grasp completion behavior
Pi05 outputs a large side push -> visual/action mapping is off
```

### 4.4 Action Queue Failure

Question:

```text
Did official LeRobot execute the Pi05 chunk in the intended queue behavior?
```

Evidence needed:

```text
actions_per_chunk
chunk_size_threshold
aggregate_fn_name
fps
incoming action timesteps
queue size over time
latest executed action timestep
which observations generated which chunks
```

Official async code already logs some of this to file-level DEBUG logs.

Possible conclusions:

```text
queue is healthy -> official chunk execution is probably not the main problem
queue repeatedly empties -> inference/network may be too slow
queue grows stale -> old actions may be executed after the scene changed
aggregation changes many actions -> queue overlap may be affecting behavior
```

### 4.5 Robot Execution Failure

Question:

```text
Did SO-101 receive the same action that the client selected?
```

Evidence needed:

```text
action selected from queue
action dict passed to robot.send_action()
action returned by robot.send_action()
robot state after the action
whether max_relative_target was active
whether disable_torque_on_disconnect or other robot config changed behavior
```

Important code fact:

```text
SOFollower.send_action() returns the action actually sent to the motors.
If max_relative_target is None, LeRobot does not clamp the target inside SOFollower.send_action().
If max_relative_target is set, the returned action may differ from the requested action.
```

Current rule:

```text
Do not set robot.max_relative_target unless the user explicitly approves it.
Use official default None.
```

Possible conclusions:

```text
requested action equals sent action -> robot execution is faithful
requested action differs from sent action -> some guard or processor changed the command
sent action changes but robot state does not -> hardware/motor/torque problem
robot state changes correctly but orange not grasped -> model/data/visual servoing problem
```

### 4.6 Timing And Latency Failure

Question:

```text
Was the robot acting on fresh observations or stale observations?
```

Evidence needed:

```text
client observation timestamp
server receive timestamp
policy inference start/end time
action chunk timestamp
client receive timestamp
action execution timestamp
camera FPS
control loop FPS
queue size
```

Official async logs already include some latency and FPS information.

Possible conclusions:

```text
low latency and stable FPS -> timing is less likely the main problem
long inference delay -> policy may act on stale visual data
camera read delay -> images may not be fresh enough
control loop slower than target FPS -> action timing may not match training
```

### 4.7 Training Data Coverage Failure

Question:

```text
Does the training dataset contain the behavior the robot failed to do?
```

Evidence needed:

```text
the 49 training episodes
episode videos
state/action Parquet data
gripper action timing
close-range approach frames
successful align-close-lift examples
camera viewpoints matching test setup
object position variation
start pose variation
```

Possible conclusions:

```text
dataset has many close-range align-close-lift examples -> model may need more fine-tuning or better eval setup
dataset mostly contains reach/push but few clean grasps -> data gap
dataset camera views differ from current cameras -> deployment camera mismatch
dataset gripper closes too late or not at all -> learned behavior will not pick
dataset does not include near-orange correction -> close-range correction episodes are justified
```

## 5. Evidence Levels

We will use three evidence levels.

### Level 1: Official Logs And External Video

This requires no code changes.

Data:

```text
robot_client log
policy_server log
RunPod GPU status
camera precheck images
iPhone video or external video
exact command/manifest
```

This can answer:

```text
Did the run start correctly?
Did policy_server load the model?
Did action chunks return?
Did the queue run?
Did the robot physically reach/touch/grasp/lift?
```

This cannot fully answer:

```text
Which exact camera image caused which exact action chunk?
What exact numeric actions did Pi05 output?
What exact action was sent at each frame?
```

Use Level 1 for infrastructure and quick sanity.

### Level 2: Official Dataset Recording

This uses official LeRobot rollout or recording modes where supported.

Data:

```text
camera videos
robot state
actions
timestamps
task text
LeRobot dataset metadata
```

This can answer:

```text
What did the robot see and do during a rollout?
Did the gripper close in the saved action stream?
Was the object visible in dataset video?
How do the rollout actions compare to training episodes?
```

Current limitation:

```text
Official rollout recording is not the same as the current laptop robot_client -> RunPod policy_server setup.
It can be useful if we can run the policy through lerobot-rollout on a suitable machine.
It is not currently our clean RunPod async path.
```

Use Level 2 when we can run official rollout without changing the deployment architecture too much.

### Level 3: Read-Only Async Trace Instrumentation

This requires a small diagnostic code change after user approval.

Data:

```text
raw camera images sent by robot_client
raw robot state sent by robot_client
task text sent by robot_client
policy_server processed observation metadata
full Pi05 action chunk
postprocessed action chunk
client queue events
executed action
action actually returned by robot.send_action()
timestamps tying all of these together
```

This can answer the key question:

```text
For observation N, these exact images and this exact state produced this exact Pi05 action chunk, and LeRobot executed these specific actions.
```

Use Level 3 only after:

```text
3-camera official run is possible
Level 1 evidence shows a failure worth diagnosing
the user approves read-only instrumentation
```

## 6. Investigation Workflow

### Phase 0: Fix Test Preconditions

Do not run a serious Pi05 test until:

```text
RunPod policy_server is listening
SSH tunnel is alive
top camera image is correct
front camera image is correct
wrist camera image is correct
SO-101 serial port is correct
arm starts from the agreed safe start pose
orange starts from the agreed test position
command uses official defaults unless approved otherwise
```

Current immediate blocker:

```text
The wrist camera must be a normal official-compatible capture camera.
Preferred: small USB UVC wrist camera that appears as /dev/videoX.
Fallback: /dev/video6 only after it reports Video Capture and OpenCV can read it.
```

### Phase 1: One Clean Official Async Run

Run one official async evaluation with:

```text
official robot_client
official policy_server
official defaults
all three cameras
external video recording
logs preserved
one run manifest
```

Goal:

```text
Prove whether the official async path can reproduce the strong reach behavior.
```

Do not change training data yet.
Do not change APQ manually.
Do not add guards unless approved.

### Phase 2: Label The Outcome From Video

After the run, label the physical behavior:

```text
0 = no meaningful reach
1 = reaches toward orange
2 = touches/pushes orange
3 = gripper surrounds orange
4 = gripper closes on orange
5 = lift or clear move happens
```

This gives a simple success/failure label.

### Phase 3: Read Official Logs

Extract:

```text
model loaded or not
inference time per chunk
action shape
incoming action timestep ranges
queue size behavior
observation FPS
client/server latency
exceptions or disconnects
```

If the run fails before action chunks:

```text
fix infrastructure, not training data
```

If the run gets action chunks and the arm reaches/touches:

```text
move to deeper trace only if grasp still fails
```

### Phase 4: Decide If Instrumentation Is Needed

Use this decision:

```text
If logs/video are enough to identify an infrastructure failure:
  fix infrastructure.

If logs/video show the policy reaches but does not grasp:
  add read-only trace instrumentation after user approval.

If logs/video show camera views are bad:
  fix camera views before model changes.

If trace shows Pi05 never commands close/lift:
  collect close-range correction episodes or fine-tune more.

If trace shows Pi05 commands close/lift but robot does not execute it:
  inspect action execution, robot state, and hardware.
```

### Phase 5: Compare Against Training Data

Only after test trace exists, compare failure frames to the 49 training episodes.

Questions:

```text
At similar gripper-orange distance, what did human demos do?
Did demos center the orange before closing?
How long after contact did demos close?
Did demos include side/top approaches like the failed run?
Were all three camera views similar to test views?
Did demos include recovery after pushing the orange?
```

This tells us whether more close-range episodes are justified.

## 7. Evidence Folder Standard

Every serious run should create one folder:

```text
artifacts/pi05_evidence_runs/YYYYMMDD_HHMMSS_<short_label>/
```

Expected contents:

```text
manifest.md
commands.txt
camera_precheck/
  top.jpg
  front.jpg
  wrist.jpg
logs/
  robot_client.log
  policy_server.log
  runpod_status.txt
external_video/
  iphone_video.mov
analysis/
  outcome_label.md
  key_frames/
```

If Level 3 instrumentation is approved:

```text
trace/
  observations.jsonl
  action_chunks.jsonl
  executed_actions.jsonl
  images/
    obs_000000_top.jpg
    obs_000000_front.jpg
    obs_000000_wrist.jpg
```

## 8. Minimum Evidence Before Claiming A Cause

Do not say "we need more data" unless we have at least one of:

```text
Pi05 action chunks do not contain close/lift behavior.
Training episodes do not contain close-range align-close-lift behavior.
Camera trace shows Pi05 did not see the needed visual information.
Execution trace shows the robot did not receive or perform the intended close/lift.
```

Do not say "camera mismatch" unless we have:

```text
saved camera frames from the actual policy observations
or a camera precheck showing the orange/gripper are missing or badly framed
```

Do not say "queue problem" unless we have:

```text
queue size/timestep logs showing empty, stale, or inconsistent execution
```

Do not say "robot hardware problem" unless we have:

```text
sent action values
actual returned action values
next robot state showing mismatch
```

## 9. What Counts As A Good Diagnosis

A good diagnosis must have this form:

```text
Claim:
  What failed.

Evidence:
  Which saved file/log/frame/action proves it.

Mechanism:
  Why that evidence explains the physical behavior.

Next action:
  Smallest change that directly addresses the proven failure.
```

Example:

```text
Claim:
  Pi05 is reaching but not learning the final close/lift.

Evidence:
  In action_chunks.jsonl, gripper.pos stays open across the final 20 actions
  while the video shows the gripper beside the orange.

Mechanism:
  The model plans approach/reorientation but does not issue grasp closure.

Next action:
  Collect 10-20 close-range correction episodes with align, close, lift.
```

## 10. What We Should Not Do

Do not:

```text
fine-tune again just because one video failed
change cameras without saved evidence showing the view is wrong
run top/front-only as a valid Pi05 evaluation
use the current ESP32 serial/JTAG device as a wrist camera
change actions_per_chunk or queue settings without queue evidence
add robot guards without explaining why and getting approval
remove official defaults silently
create custom scripts before official LeRobot paths are checked
claim the model cannot grasp without action chunk evidence
claim the model can grasp without lift evidence
```

## 11. Immediate Next Step

The next practical step is not more fine-tuning.

The next practical step is:

```text
Fix the wrist camera so official LeRobot sees all three cameras.
Preferred solution: mount a small USB UVC wrist camera that appears as /dev/videoX.
Run one clean official async test with logs and external video.
If it still fails to grasp, add approved read-only tracing.
Use trace evidence to decide whether the next fix is camera, execution, timing, or training data.
```
