# Pi05 Official LeRobot Async Test Plan

This document is the plan to test Pi05 using LeRobot's official async inference flow with the real SO-101 follower arm.

The goal is to stop relying on our custom first-action runner and test Pi05 closer to the way LeRobot expects action-chunking policies to run.

## 1. Why We Need This Test

Our earlier real-arm Pi05 tests proved that:

```text
local laptop can read cameras
local laptop can control SO-101 follower
L40S can load Pi05
local laptop can talk to L40S
Pi05 can return actions
SO-101 can move from those actions
```

But our custom runner often used only the first action from each returned Pi05 chunk.

Pi05 normally predicts an action chunk:

```text
action_0
action_1
action_2
...
action_49
```

Official LeRobot async inference is designed to queue these actions and execute them over time.

So this test checks:

```text
Does Pi05 work better when we use LeRobot's normal chunk queue behavior?
```

## 2. Target Architecture

The intended setup is:

```text
Local laptop
  - SO-101 follower connected by USB
  - top camera
  - front camera
  - wrist camera
  - LeRobot robot client

Remote L40S
  - Pi05 model
  - LeRobot policy server

Network
  - local laptop sends observations to L40S
  - L40S returns action chunks
  - local laptop queues actions and sends them to SO-101
```

Simple flow:

```text
camera images + robot state
        ↓
local LeRobot robot client
        ↓
remote L40S policy server
        ↓
Pi05 action chunk
        ↓
local action queue
        ↓
SO-101 follower
```

## 3. Current Known Hardware Setup

Robot:

```text
SO-101 follower
robot id: my_so101_follower
follower port: usually /dev/ttyACM1
```

Cameras:

```text
top   = /dev/video0, Logitech C270 RGB camera
front = /dev/video2, Acer RGB camera
wrist = normal /dev/videoX capture camera
```

Current wrist options:

```text
preferred: small USB UVC wrist camera that appears as /dev/videoX
fallback: /dev/video6 only after it reports Video Capture and OpenCV can read it
not accepted: current ESP32 serial/JTAG device
not accepted: direct Raspberry Pi TCP stream if official LeRobot rejects it
```

Policy:

```text
policy type: pi05
model: zz4321/so101_pi05
task: grasp the orange
```

## 3.1 Three-Camera Gate

The official Pi05 pick-orange evaluation requires:

```text
top image
front image
wrist image
SO-101 state
task text
```

Do not run top/front-only as a Pi05 success/failure test.

Reason:

```text
The current failure is close-range gripper/orange alignment, close, and lift.
The wrist camera is the camera most likely to show that close-range geometry.
Removing wrist would make the test weaker and could lead us to the wrong diagnosis.
```

Non-three-camera runs are allowed only as camera/infrastructure checks, not as Pi05 evaluation evidence.

## 4. Inspection Step A: Check Pi05 Expected Features

Before moving the robot, inspect what the model expects.

We need to know:

```text
camera feature names
state feature names
action feature names
image size
action dimension
```

Expected good result:

```text
cameras: top, front, wrist
state: shoulder_pan.pos, shoulder_lift.pos, elbow_flex.pos, wrist_flex.pos, wrist_roll.pos, gripper.pos
actions: shoulder_pan.pos, shoulder_lift.pos, elbow_flex.pos, wrist_flex.pos, wrist_roll.pos, gripper.pos
```

If names do not match, add the correct rename map before running motion.

## 5. Inspection Step B: Check Local Robot Observation

Check what the local robot client can produce.

We need:

```text
SO-101 state readable
top camera frame readable
front camera frame readable
wrist camera frame readable
all images correct shape
all image names match model features
```

This step should not move the robot.

Success means:

```text
we can build one complete observation for Pi05
```

## 6. Inspection Step C: Official Async Dry Run

Purpose:

Test official async communication without moving the arm.

Flow:

```text
start policy server on L40S
local laptop builds one observation
send observation to L40S
L40S returns action chunk
print action chunk shape and first few actions
do not send actions to motors
```

Expected success:

```text
policy server accepts pi05
policy server loads zz4321/so101_pi05
local observation is accepted
action chunk comes back
chunk shape is valid
```

Failure examples:

```text
camera names mismatch
model feature mismatch
network/tunnel failure
policy cannot load
wrong action dimension
```

## 7. Inspection Step D: Official Async Real-Arm Short Test

Only run this after the dry run succeeds.

Purpose:

Test whether official LeRobot queue execution moves the arm more naturally than our first-action custom runner.

Initial settings:

```text
actions_per_chunk = 50
chunk_size_threshold = 0.5
aggregate_fn_name = weighted_average
fps = 30
task = grasp the orange
```

What LeRobot should do:

```text
receive action chunk
put actions into queue
send action_0 to robot
send action_1 to robot
send action_2 to robot
ask for next chunk before queue is empty
continue smoothly
```

Record:

```text
video
action chunks
queue size
robot state
sent actions
server/client logs
```

## 8. Safety Rules For First Motion Test

The first official async motion test should be short.

Keep:

```text
orange away from dangerous collision zones
gripper clear of table
hand near power switch
camera recording enabled
terminal visible
```

Stop immediately if:

```text
arm moves violently
wrist rotates unexpectedly too far
gripper drives into table
motor overload appears
camera feed is wrong
network stalls while robot keeps moving badly
```

Safety is for hardware protection. It is not the final behavior design.

## 9. Decision Tree

If official async dry run fails:

```text
fix feature names, camera inputs, network, or model loading
```

If dry run works but motion is bad:

```text
analyze raw Pi05 chunk and camera observations
then decide whether camera setup or fine-tuning is needed
```

If motion is better than custom runner:

```text
continue with official async
run longer tests
record success/failure videos
```

If official async still cannot grasp:

```text
record demonstrations on our exact setup
fine-tune Pi05 or another compatible policy
evaluate again
```

## 10. Success Criteria

Dry-run success:

```text
Pi05 action chunk is returned from L40S using our real observation format
```

First motion success:

```text
arm moves smoothly
gripper approaches orange
movement looks like a coherent sequence
no unsafe jump
```

Real task success:

```text
orange is grasped and lifted
```

A near miss is useful information, but it is not task success.

## 11. Immediate Next Work

Next implementation steps:

```text
1. inspect zz4321/so101_pi05 feature names
2. inspect local SO-101 observation keys and camera names
3. build official async dry-run client config
4. run dry run without motor movement
5. if dry run works, run short official async motion test
```

This is the correct bridge from our debug scripts to a proper LeRobot Pi05 real-arm setup.

## 12. Missing Practical Details We Must Handle

The high-level plan is correct, but these details must be handled before a serious GPU test.

### 12.1 True 3-Camera Dry Run

Some of our earlier dry-run scripts duplicated one camera frame into all Pi05 camera inputs.

That is useful for network/model testing, but it is not enough for real policy testing.

For this official async test, the dry run must use real views:

```text
top   = Logitech C270 frame
front = laptop camera frame
wrist = Raspberry Pi camera frame
```

Dry-run success should mean:

```text
Pi05 received the same three camera roles that the real motion test will use
```

### 12.2 Camera Adapter Risk

The top and front cameras are local USB/OpenCV cameras, so they are straightforward.

The wrist camera is different because it comes from the Raspberry Pi.

Current wrist source:

```text
tcp://192.168.1.17:8554
```

That endpoint is a continuous MJPEG TCP stream from `rpicam-vid`.

Current official async result:

```text
OpenCV can read a frame from tcp://192.168.1.17:8554 in a plain manual test.
Official robot_client cannot use that direct TCP source today because robot cameras must specify width, height, and fps, and LeRobot's OpenCVCamera validation fails when OpenCV reports set(width/height/fps)=False for the TCP stream.
```

Current intended fix:

```text
OpenCVCamera("/dev/video0") OK as top.
OpenCVCamera("/dev/video2") OK as front.
Make /dev/video6 readable as Video Capture.
Feed the Pi MJPEG stream into /dev/video6.
Use OpenCVCamera("/dev/video6") as wrist.
```

The Pi `timelapse.service` must stay stopped while the wrist stream is active because it otherwise takes exclusive control of the CSI camera.

### 12.3 Exact Feature Name Report

Before motion, save a feature report.

The report should include:

```text
model image features
model state features
model action features
local robot observation keys
local robot action keys
camera names we send
rename map, if needed
```

Save it under:

```text
logs/pi05_async_feature_check/
```

This gives us proof that Pi05 and the robot client are speaking the same feature language.

### 12.4 Queue And Latency Logs

Official async is only useful if the action queue stays healthy.

For every real motion test, log:

```text
actions_per_chunk
chunk_size_threshold
queue size over time
server inference time
network latency
client FPS
robot control FPS
number of actions executed
number of chunks received
```

Why this matters:

```text
if queue becomes empty, robot may pause
if latency is high, movement may lag behind camera state
if FPS is unstable, policy behavior may look worse than it really is
```

### 12.5 Video And Log Artifact Folder

Each test should create one folder containing all evidence.

Example:

```text
/data/downloads/so101_pi05_official_async_tests/2026-06-23_1530_grasp_orange/
```

Inside:

```text
video.mp4
client.log
server.log
feature_report.json
action_chunks.jsonl
queue_size.csv
notes.md
```

This prevents us from losing track of which video belongs to which settings.

### 12.6 Stop And Recovery Plan

Before a real motion test, define the stop path.

Stop options:

```text
Ctrl+C in robot client terminal
turn off follower motor power
stop policy server
close tunnel
disconnect robot client
```

After stopping, verify:

```text
robot is no longer receiving actions
motors are not fighting
follower can reconnect
camera feeds still work
```

If a motor overload occurs:

```text
stop motion
power cycle follower
check wrist/gripper geometry
run position check before another policy test
```

### 12.7 GPU Cost Rule

Before starting L40S:

```text
local cameras must already be working
follower must already be connected
feature inspection script must be ready
test command must be ready
recording folder must be ready
```

During L40S:

```text
only run inference tests
do not debug local camera setup on paid GPU time
```

After test:

```text
copy logs/videos locally
stop the L40S if no more tests are ready
```

## 13. Updated Immediate Next Work

The next implementation work should be:

```text
1. make wrist camera available as a normal /dev/videoX capture camera
2. save top/front/wrist camera precheck images
3. verify official robot_client can connect all three cameras
4. start RunPod policy_server only after local camera gate passes
5. run one official async three-camera test with official defaults
6. save manifest, logs, and external video
7. update docs/pi05_active_work_tracker.md with evidence and outcome
```

This avoids wasting GPU time and keeps the test evidence clean.
