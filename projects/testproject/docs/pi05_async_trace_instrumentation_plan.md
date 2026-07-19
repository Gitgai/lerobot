# Pi05 Official Async Trace Instrumentation Plan

Date: 2026-07-18

This document describes the exact diagnostic instrumentation we may need for the current official async setup:

```text
local robot_client -> RunPod policy_server
```

This is a plan only. It is not approval to change code.

The user rule remains:

```text
Do not create or modify scripts/code until Codex explains why and the user approves.
Use official LeRobot as-is first.
If instrumentation is needed, make it read-only and behavior-neutral.
```

## 1. Why Instrumentation May Be Needed

Official async LeRobot already gives useful logs:

```text
robot_client config
policy_server config
model load status
observation send timing
inference timing
action chunk shape
queue size/timestep debug logs
client/server latency
exceptions
```

But official async does not save this by default:

```text
the exact top/front/wrist images sent to Pi05
the exact robot state sent with those images
the exact task string attached to the observation
the exact full numeric Pi05 action chunk
the exact action selected from the queue on each control tick
the exact action returned by robot.send_action()
```

Without those, we cannot prove the full cause of a failed grasp.

Example question we cannot fully answer with default async logs:

```text
At 00:39, when the gripper touched the orange, what did Pi05 see and what did it command for gripper.pos over the next 50 actions?
```

Instrumentation would answer that exactly.

## 2. Scope

Instrumentation must be:

```text
read-only
off by default
enabled by one explicit flag or environment variable
stored under one run folder
compatible with official async behavior
not changing action values
not changing timing except for unavoidable logging overhead
not changing camera mappings
not changing robot safety config
not changing policy outputs
```

Instrumentation must not:

```text
replace robot_client
replace policy_server
create a new evaluation loop
alter action chunks
alter action queue behavior
alter postprocessing
add clamps or guards
hide model behavior
```

## 3. What To Instrument

### 3.1 Run Manifest

Location:

```text
local laptop
artifacts/pi05_evidence_runs/<run_id>/manifest.json
```

Fields:

```json
{
  "run_id": "20260718_231500_official_async_3cam",
  "created_at_local": "2026-07-18T23:15:00+05:30",
  "git_commit": "<commit>",
  "git_status_short": "<status>",
  "policy_type": "pi05",
  "checkpoint": "/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model",
  "task": "pick up the orange and move it to another place",
  "server_address": "localhost:8080",
  "fps": 30,
  "actions_per_chunk": 50,
  "chunk_size_threshold": 0.5,
  "aggregate_fn_name": "weighted_average",
  "robot_type": "so101_follower",
  "robot_port": "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00",
  "robot_max_relative_target": null,
  "cameras": {
    "top": "/dev/video0",
    "front": "/dev/video2",
    "wrist": "/dev/video6"
  }
}
```

Why needed:

```text
This proves exactly what we ran.
It prevents confusion between old guarded tests, official async tests, and camera experiments.
```

### 3.2 Raw Observation Trace

Capture point:

```text
src/lerobot/async_inference/robot_client.py
RobotClient.control_loop_observation()
right after:
  raw_observation = self.robot.get_observation()
  raw_observation["task"] = task
before:
  self.send_observation(observation)
```

Data:

```text
observation timestep
client timestamp
task text
all scalar robot state values
camera names present
camera frame shapes
image file paths saved for this observation
queue size at observation time
must_go flag
latest executed action timestep
```

Suggested file:

```text
trace/observations.jsonl
```

Suggested record:

```json
{
  "kind": "observation",
  "timestep": 37,
  "client_timestamp": 1784396000.123,
  "must_go": true,
  "latest_action": 37,
  "queue_size": 0,
  "task": "pick up the orange and move it to another place",
  "state": {
    "shoulder_pan.pos": 1.2,
    "shoulder_lift.pos": -33.4,
    "elbow_flex.pos": 55.6,
    "wrist_flex.pos": -12.1,
    "wrist_roll.pos": 4.3,
    "gripper.pos": 18.0
  },
  "images": {
    "top": "images/obs_000037_top.jpg",
    "front": "images/obs_000037_front.jpg",
    "wrist": "images/obs_000037_wrist.jpg"
  },
  "image_shapes": {
    "top": [480, 640, 3],
    "front": [480, 640, 3],
    "wrist": [480, 640, 3]
  }
}
```

Why needed:

```text
This proves what Pi05 was about to see.
It lets us inspect whether the orange and gripper were visible before each action chunk.
```

### 3.3 Server Observation Metadata Trace

Capture point:

```text
src/lerobot/async_inference/policy_server.py
PolicyServer.SendObservations()
after deserializing TimedObservation
```

Data:

```text
observation timestep
client timestamp
server receive timestamp
one-way latency
whether observation was enqueued
whether observation was filtered out
```

Suggested file:

```text
trace/server_observations.jsonl
```

Why needed:

```text
This proves whether the server received fresh observations and whether they were actually queued for inference.
```

### 3.4 Processed Observation Feature Trace

Capture point:

```text
src/lerobot/async_inference/policy_server.py
PolicyServer._predict_action_chunk()
after raw_observation_to_observation()
after preprocessor()
```

Data:

```text
timestep
raw observation keys
policy observation keys
policy image feature keys expected
which images were present
which images were missing or padded
observation.state shape
image tensor shapes
preprocess time
```

Suggested file:

```text
trace/policy_observation_features.jsonl
```

Suggested record:

```json
{
  "kind": "policy_observation_features",
  "timestep": 37,
  "expected_image_features": [
    "observation.images.top",
    "observation.images.front",
    "observation.images.wrist"
  ],
  "present_image_features": [
    "observation.images.top",
    "observation.images.front",
    "observation.images.wrist"
  ],
  "missing_image_features": [],
  "state_shape": [1, 6],
  "image_shapes": {
    "observation.images.top": [1, 3, 224, 224],
    "observation.images.front": [1, 3, 224, 224],
    "observation.images.wrist": [1, 3, 224, 224]
  }
}
```

Why needed:

```text
This proves feature compatibility.
It catches hidden camera-name or feature-name problems.
```

### 3.5 Pi05 Action Chunk Trace

Capture point:

```text
src/lerobot/async_inference/policy_server.py
PolicyServer._predict_action_chunk()
after:
  action_tensor = self._get_action_chunk(observation)
after:
  action_tensor = torch.stack(processed_actions, dim=1).squeeze(0)
```

Data:

```text
observation timestep
action chunk length
action feature names
raw model action tensor summary before postprocessor
postprocessed action values after unnormalization
timed action timesteps
timed action timestamps
inference time
postprocess time
```

Suggested file:

```text
trace/action_chunks.jsonl
```

Suggested record:

```json
{
  "kind": "action_chunk",
  "observation_timestep": 37,
  "chunk_start_timestep": 37,
  "chunk_end_timestep": 86,
  "action_names": [
    "shoulder_pan.pos",
    "shoulder_lift.pos",
    "elbow_flex.pos",
    "wrist_flex.pos",
    "wrist_roll.pos",
    "gripper.pos"
  ],
  "actions": [
    [1.0, -32.0, 55.0, -10.0, 3.0, 18.0],
    [1.4, -31.6, 54.7, -9.6, 3.2, 18.5]
  ],
  "summary": {
    "gripper_min": 18.0,
    "gripper_max": 42.0,
    "gripper_first": 18.0,
    "gripper_last": 42.0
  },
  "timing_ms": {
    "inference": 120.5,
    "postprocess": 4.1
  }
}
```

Why needed:

```text
This directly answers whether Pi05 planned reach, close, and lift.
```

### 3.6 Client Receive And Queue Trace

Capture point:

```text
src/lerobot/async_inference/robot_client.py
RobotClient.receive_actions()
after deserializing timed_actions
before and after _aggregate_action_queues()
```

Data:

```text
received chunk start/end timesteps
server-to-client latency
old queue size and timestep range
new queue size and timestep range
latest executed action timestep
deserialize time
aggregate function used
```

Suggested file:

```text
trace/queue_events.jsonl
```

Why needed:

```text
This proves whether official queueing is healthy or stale.
```

### 3.7 Executed Action Trace

Capture point:

```text
src/lerobot/async_inference/robot_client.py
RobotClient.control_loop_action()
around:
  _performed_action = self.robot.send_action(...)
```

Data:

```text
control tick timestamp
action timestep popped from queue
requested action dict
action returned by robot.send_action()
queue size after pop
latest action after update
```

Suggested file:

```text
trace/executed_actions.jsonl
```

Suggested record:

```json
{
  "kind": "executed_action",
  "action_timestep": 37,
  "client_timestamp": 1784396000.456,
  "requested_action": {
    "shoulder_pan.pos": 1.0,
    "shoulder_lift.pos": -32.0,
    "elbow_flex.pos": 55.0,
    "wrist_flex.pos": -10.0,
    "wrist_roll.pos": 3.0,
    "gripper.pos": 18.0
  },
  "performed_action": {
    "shoulder_pan.pos": 1.0,
    "shoulder_lift.pos": -32.0,
    "elbow_flex.pos": 55.0,
    "wrist_flex.pos": -10.0,
    "wrist_roll.pos": 3.0,
    "gripper.pos": 18.0
  },
  "queue_size_after_pop": 42
}
```

Why needed:

```text
This proves whether the robot got what Pi05 requested.
```

### 3.8 Post-Action State Trace

Capture point:

```text
next RobotClient.control_loop_observation()
```

Data:

```text
robot state after previous action
delta from previous state
image after previous action
```

Why needed:

```text
This proves whether the motor command caused the expected state change.
```

## 4. Storage Layout

All trace data should live in one run folder:

```text
artifacts/pi05_evidence_runs/<run_id>/
```

Folder layout:

```text
manifest.json
commands.txt
logs/
  robot_client.log
  policy_server.log
  runpod_status.txt
camera_precheck/
  top.jpg
  front.jpg
  wrist.jpg
trace/
  observations.jsonl
  server_observations.jsonl
  policy_observation_features.jsonl
  action_chunks.jsonl
  queue_events.jsonl
  executed_actions.jsonl
  timing_summary.jsonl
images/
  obs_000000_top.jpg
  obs_000000_front.jpg
  obs_000000_wrist.jpg
external_video/
  iphone_video.mov
analysis/
  outcome_label.md
  key_frames/
```

JSONL is preferred because:

```text
it is append-only
it survives crashes better than one giant JSON file
it is easy to inspect with jq, pandas, or Python
it does not require a database
```

Images should be saved as JPEG unless a lossless image is needed for a specific inspection.

## 5. Synchronization Keys

Every saved record should include:

```text
run_id
kind
timestep
client_timestamp where available
server_timestamp where available
wall_time_iso where available
```

For linking observations and actions:

```text
observation_timestep
chunk_start_timestep
chunk_end_timestep
action_timestep
```

This lets us answer:

```text
Observation 37 generated action chunk 37-86.
Client received that chunk at time X.
Client executed action 42 at time Y.
Next observation after action 42 showed state Z.
```

## 6. Performance Limits

Instrumentation can slow the loop if it saves every full-resolution image synchronously.

Mitigation:

```text
save images only for observations sent to policy, not every control tick
write JSONL line-by-line
flush periodically
use JPEG quality around 85
avoid expensive analysis during robot motion
do not compute object detection during the run
```

If the run becomes slower than target FPS, record that in the timing evidence.

## 7. Privacy And Size

Images and videos may contain the user, room, and equipment.

Default:

```text
store locally under artifacts/
do not push videos/images to GitHub
do not upload to Hugging Face unless the user asks
keep artifact paths out of committed docs unless needed
```

Git rule:

```text
trace docs can be committed
large trace outputs should not be committed
```

## 8. Minimal Implementation Approach If Approved

If the user approves instrumentation, the smallest clean approach is:

```text
add an optional trace output directory to robot_client
add an optional trace output directory to policy_server
write small helper functions inside the existing async modules
guard all trace writes behind config/env flag
leave default behavior unchanged
```

Possible enable method:

```text
LEROBOT_ASYNC_TRACE_DIR=artifacts/pi05_evidence_runs/<run_id>/trace
```

or CLI flags if we choose to extend config:

```text
--trace_dir=artifacts/pi05_evidence_runs/<run_id>/trace
--trace_images=true
```

Environment variable is less invasive to CLI config.
CLI flag is easier to discover.

Do not implement either until approved.

## 9. Verification For Instrumentation

Before running the real robot with instrumentation:

```text
run import checks
run robot_client help
start policy_server
run a no-motion or short connection test where possible
confirm trace files are created
confirm default behavior still works with tracing disabled
```

During a real run:

```text
watch for FPS slowdowns
watch RunPod GPU usage
keep external video recording active
stop if robot behavior becomes unsafe
```

After a run:

```text
count observations
count action chunks
count executed actions
verify all expected camera names appear
verify action feature names are correct
verify gripper values are readable
verify images match the external video timing roughly
```

## 10. Analysis Questions The Trace Must Answer

The trace must let us answer these without guessing:

```text
Was the orange visible when Pi05 decided?
Was the gripper visible when Pi05 decided?
Was the wrist camera present or missing?
Did Pi05 output a gripper close?
Did Pi05 output a lift after close?
Did official queueing execute the intended chunk order?
Did the action sent to robot equal the action selected from the queue?
Did the robot state change after that action?
Was the run limited by network or inference latency?
```

If the trace cannot answer those questions, instrumentation is incomplete.

## 11. Decision Rules After Trace

### Case A: Bad Visual Input

Evidence:

```text
saved observation images show orange/gripper missing, blocked, or badly framed
```

Next action:

```text
fix camera placement or camera source
rerun before changing model/data
```

### Case B: Good Visual Input, No Grasp In Pi05 Output

Evidence:

```text
images show orange and gripper clearly
action_chunks.jsonl shows gripper does not close or lift action does not appear
```

Next action:

```text
collect close-range correction episodes
or fine-tune more on verified grasp-completion examples
```

### Case C: Pi05 Outputs Grasp, Robot Does Not Execute

Evidence:

```text
action_chunks.jsonl shows close/lift
executed_actions.jsonl differs from requested action
or robot state does not follow executed action
```

Next action:

```text
inspect robot action postprocessing, robot config, motor state, torque, serial stability
```

### Case D: Queue Or Timing Failure

Evidence:

```text
queue_events.jsonl shows stale chunks, empty queue, or high latency
timing logs show low control FPS or slow inference
```

Next action:

```text
adjust official queue/inference settings only after explaining why and getting approval
```

### Case E: Training Data Gap

Evidence:

```text
trace shows missing close/lift behavior
training dataset lacks similar close-range align-close-lift examples
```

Next action:

```text
record 10-20 close-range correction episodes
verify dataset videos/actions
fine-tune from the last good complete checkpoint
```

## 12. Approval Gate

Before implementing instrumentation, Codex must tell the user:

```text
what code file will change
what data will be saved
where it will be saved
why official logs are not enough
why this does not change robot behavior
how to disable it
how we will verify it
```

Only after approval should code be changed.
