# Pi05 Official Async Run Evidence Checklist

Date: 2026-07-18

Use this checklist for every serious Pi05 real-arm test.

The purpose is to make every run useful evidence. A run without enough saved evidence should not drive fine-tuning or hardware decisions.

## 1. Run Rule

Before every run:

```text
One run = one folder.
One run = one manifest.
One run = saved logs.
One run = saved camera precheck images.
One run = external video if the robot moves.
```

Folder format:

```text
artifacts/pi05_evidence_runs/YYYYMMDD_HHMMSS_<short_label>/
```

Example:

```text
artifacts/pi05_evidence_runs/20260718_231500_official_async_3cam_orange_pick/
```

## 2. Pre-Run Preconditions

Do not run the robot until every required item is checked.

### 2.1 Project Location

```text
cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject
```

Save:

```text
pwd
git status --short
git rev-parse HEAD
```

### 2.2 Policy Server

Check:

```text
RunPod reachable
policy_server process running
port 8080 listening
GPU visible
GPU has enough memory free
checkpoint folder complete
```

Evidence to save:

```text
logs/runpod_status.txt
logs/policy_server.log
```

Minimum checkpoint check:

```text
config files exist
model.safetensors exists
pretrained_model folder is complete
```

Current known complete checkpoint:

```text
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model
```

Do not use incomplete checkpoint folders.

### 2.3 SSH Tunnel

Check:

```text
local port 8080 is listening
TCP connection to localhost:8080 succeeds
tunnel points to the current RunPod host/port
```

Evidence to save:

```text
logs/tunnel_status.txt
```

### 2.4 Cameras

Required mapping for the intended 3-camera run:

```text
top   = /dev/video0
front = /dev/video2
wrist = a normal official-compatible /dev/videoX capture camera
```

Current important blocker:

```text
The wrist camera must report Video Capture.
If /dev/video6 reports only Video Output, official LeRobot/OpenCV cannot read it as a camera.
The connected ESP32 appears as serial/JTAG, not /dev/videoX, so it is not a usable wrist camera today.
Preferred solution is a small USB UVC wrist camera.
```

Save precheck images:

```text
camera_precheck/top.jpg
camera_precheck/front.jpg
camera_precheck/wrist.jpg
```

Each precheck image must show:

```text
top:
  orange visible
  gripper/arm visible
  table visible

front:
  orange visible or at least useful gripper/object geometry
  not mostly room/person
  robot not cut off

wrist:
  gripper visible
  orange visible when near grasp range
  image is normal RGB, not IR greyscale
```

If a camera is bad:

```text
fix camera before running
do not spend GPU time
do not blame the model
```

### 2.5 Robot

Check:

```text
SO-101 follower serial port exists
arm connects through official LeRobot robot class
robot starts from agreed pose
table area is clear
orange is in agreed start position
user is physically near emergency power
```

Current follower port:

```text
/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00
```

### 2.6 Official Defaults

Use official defaults unless approved otherwise.

For the current rule:

```text
do not pass --robot.max_relative_target unless user approves
do not pass --robot.disable_torque_on_disconnect unless user approves
do not silently change actions_per_chunk
do not silently change chunk_size_threshold
do not silently change aggregate_fn_name
```

If any non-default is used, manifest must include:

```text
the exact value
why it was changed
who approved it
what evidence justified it
```

## 3. Manifest Template

Create:

```text
manifest.md
```

Template:

```text
# Pi05 Run Manifest

run_id:
date:
operator:
repo_path:
git_commit:
git_status_short:

purpose:

policy:
  policy_type: pi05
  checkpoint:
  checkpoint_complete: yes/no

server:
  runpod_name:
  ssh_host:
  ssh_port:
  tunnel_local_port: 8080
  policy_server_command:

robot:
  type: so101_follower
  id: my_so101_follower
  port:
  max_relative_target: official default None
  disable_torque_on_disconnect: official default

cameras:
  top:
  front:
  wrist:

official_async:
  fps:
  actions_per_chunk:
  chunk_size_threshold:
  aggregate_fn_name:
  task:

environment:
  orange_position:
  robot_start_pose:
  lighting:
  camera_notes:

evidence:
  camera_precheck:
  robot_client_log:
  policy_server_log:
  external_video:
  trace_enabled: yes/no

approval_notes:
```

## 4. During-Run Evidence

For a Level 1 run, save:

```text
robot_client stdout/stderr log
policy_server log
RunPod GPU status before and after
external video
any camera precheck images
```

For a Level 3 instrumented run, also save:

```text
trace/observations.jsonl
trace/server_observations.jsonl
trace/policy_observation_features.jsonl
trace/action_chunks.jsonl
trace/queue_events.jsonl
trace/executed_actions.jsonl
images/obs_*_top.jpg
images/obs_*_front.jpg
images/obs_*_wrist.jpg
```

Do not analyze during robot motion. Save evidence first.

## 5. Stop Conditions

Stop the run if:

```text
robot moves outside expected workspace
camera freezes
policy_server errors
robot_client errors
queue appears stalled
serial disconnect occurs
user requests stop
```

If stopped, still save:

```text
logs
manifest
partial trace if any
short note explaining why it stopped
```

## 6. Post-Run Outcome Label

Create:

```text
analysis/outcome_label.md
```

Use this scale:

```text
0 = no meaningful reach
1 = reaches toward orange
2 = touches or pushes orange
3 = gripper surrounds orange
4 = gripper closes on orange
5 = lift or clear move happens
```

Record:

```text
final score:
best timestamp:
failure timestamp:
short physical description:
```

Example:

```text
final score: 2
best timestamp: 00:38
failure timestamp: 00:39
description:
  Gripper reached the orange and touched it from the side.
  Orange moved, but it stayed outside the center of the gripper.
  No clean close or lift happened.
```

## 7. Log Review Checklist

From `robot_client` log, extract:

```text
config printed at start
camera connection lines
robot connection line
server connection line
received actions lines
queue size/timestep lines if debug exists
errors or exceptions
disconnect reason
```

From `policy_server` log, extract:

```text
config printed at start
client connected
policy instructions received
model path
model load time
device
running inference for observation N
action chunk generated for observation N
action shape
inference time
errors or exceptions
```

From timing:

```text
observation FPS
policy inference time
network latency if logged
control loop timing if logged
queue empty/stale signs
```

## 8. Trace Review Checklist

If trace exists, answer these questions in order.

### 8.1 Did Pi05 See The Scene?

Check:

```text
observations.jsonl
images/
policy_observation_features.jsonl
```

Questions:

```text
Was the orange visible in top?
Was the orange visible in front?
Was the orange visible in wrist?
Was the gripper visible?
Were all expected image features present?
Were any camera features missing or padded?
Were image shapes correct?
```

Conclusion allowed:

```text
camera evidence good
camera evidence bad
camera evidence inconclusive
```

### 8.2 Did Pi05 Command Grasp?

Check:

```text
action_chunks.jsonl
```

Questions:

```text
Did shoulder/elbow/wrist actions move toward the orange?
Did gripper.pos show a close command?
Did the close happen when gripper was around the orange?
Did any later action lift or move after close?
Was the chunk mostly hover/reorientation?
```

Conclusion allowed:

```text
Pi05 commanded reach only
Pi05 commanded reach plus close
Pi05 commanded reach plus close plus lift
Pi05 commanded wrong direction
Pi05 output inconclusive
```

### 8.3 Did LeRobot Queue Execute Correctly?

Check:

```text
queue_events.jsonl
executed_actions.jsonl
robot_client log
```

Questions:

```text
Were action chunks received in order?
Was queue size stable?
Were old actions skipped?
Were overlapping actions aggregated?
Did the client execute fresh actions?
Did the queue empty repeatedly?
```

Conclusion allowed:

```text
queue healthy
queue stale
queue empty too often
queue behavior inconclusive
```

### 8.4 Did The Robot Execute The Action?

Check:

```text
executed_actions.jsonl
next observation state
external video
```

Questions:

```text
Did requested action equal performed action?
Did joint state change after performed action?
Did gripper state change when close was commanded?
Did physical video match the state/action trace?
```

Conclusion allowed:

```text
execution faithful
execution changed by config/processor
motor/hardware did not follow
execution evidence inconclusive
```

## 9. Decision Matrix

Use this table after each run.

```text
Evidence found                                Next action
-------------------------------------------   ------------------------------------------
camera images bad                             fix camera, rerun
wrist missing/padded                          fix 3-camera setup, rerun
policy did not load                           fix RunPod/checkpoint/env
no action chunks                              fix async connection/server
action chunks good, queue bad                 inspect official queue settings
Pi05 reaches but never closes                 inspect training data, collect close-range demos
Pi05 closes but robot does not                inspect execution/hardware
Pi05 closes before alignment                  add close-range correction data with alignment
Pi05 grasps but does not lift                 add lift-after-close correction data
good trace and successful pick                preserve command and repeat for reliability
```

## 10. Training Dataset Comparison Checklist

Only do this after test evidence exists.

Use the 49 training episodes.

Check:

```text
How many episodes show clean grasp?
How many show close-range correction?
How many start with gripper already near orange?
How many include side approach?
How many include top approach?
How many show gripper centered before close?
How many show close then lift?
How many show failed/pushed orange?
Are camera views similar to current test cameras?
Are action/state feature names and order identical?
```

Create a short table:

```text
episode | success | close_range | centered_before_close | close_frame | lift_frame | notes
```

This prevents blind fine-tuning.

## 11. When Close-Range Correction Episodes Are Justified

Record close-range correction episodes only if evidence shows:

```text
Pi05 reaches/touches but does not center/close/lift
or training data lacks close-range align-close-lift examples
or trace shows gripper close timing is wrong near the orange
```

Do not record them just because the model failed once.

Close-range correction demo should show:

```text
start near orange
small alignment correction
gripper centered around orange
close gripper
lift slightly
move orange to target
```

## 12. What To Report After Each Run

Final run report should include:

```text
Run ID:
Command:
Cameras:
Checkpoint:
Outcome score:
Best moment:
Main evidence files:
What failed:
What is proven:
What is not proven:
Next action:
```

Example:

```text
Run ID:
  20260718_231500_official_async_3cam_orange_pick

Outcome score:
  2, touched/pushed orange but did not grasp.

What is proven:
  The policy reached the object.
  All three camera observations were present.
  Action chunks returned normally.

What is not proven:
  Whether Pi05 commanded gripper close. No trace was enabled.

Next action:
  Enable approved read-only trace and rerun one short test.
```

## 13. Current Immediate Action

Before another serious 3-camera run:

```text
fix wrist camera so official LeRobot can read it as Video Capture
preferred: use a small USB UVC wrist camera that appears as /dev/videoX
fallback: fix /dev/video6 so it reports Video Capture and OpenCV can read it
save camera precheck images
start RunPod policy_server
verify tunnel
run official robot_client with official defaults
record external video
save logs
```

Do not run top/front-only as a Pi05 pick-orange evaluation.
