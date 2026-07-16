# Official LeRobot Only Workflow

Date: 2026-07-16

This document records the decision we made for the Pi05 SO-101 orange-pick work going forward.

## Decision

We will test and use the LeRobot library as-is before adding any project customizations.

Going forward:

```text
Default path: official LeRobot commands and library behavior.
No new custom scripts.
No edits to custom scripts for evaluation.
No custom execution loops unless official LeRobot does not provide the needed feature.
Before creating or changing any script, Codex must explain why it is needed and ask for permission.
```

## Why We Changed Direction

Earlier, we used project-local scripts to investigate Pi05 behavior on the real SO-101:

```text
scripts/pi05_closed_loop_eval.py
scripts/pi05_faithful_chunk_test.py
scripts/record_3cam_demos.py
```

Those scripts helped diagnose action chunks, APQ, camera mosaics, action CSV logs, and robot guard behavior. That was useful for debugging, but it is not the final direction.

The new direction is:

```text
First verify official LeRobot works correctly.
Only customize after proving LeRobot is missing something we need.
```

## What Official LeRobot Provides

We inspected the installed LeRobot source and confirmed these official entry points exist:

```text
python -m lerobot.async_inference.policy_server
python -m lerobot.async_inference.robot_client
python -m lerobot.scripts.lerobot_find_cameras opencv
```

The official async client provides:

```text
LeRobot SO-101 follower robot class
LeRobot camera configuration
LeRobot policy server connection
LeRobot action execution through robot.send_action()
Pi05 policy type support
action chunks
action queue
chunk_size_threshold
action aggregation
fps control
```

## Important Difference From Our Custom APQ Tests

Our custom Pi05 eval script used an explicit APQ setting:

```text
actions-per-query = 5, 10, or 25
```

That meant:

```text
Ask Pi05 for a chunk.
Execute exactly K actions.
Ask Pi05 again.
```

Official LeRobot does not expose the same APQ knob in that form. Instead, it uses:

```text
actions_per_chunk
chunk_size_threshold
aggregate_fn_name
fps
```

Official behavior is queue-based:

```text
1. Robot client sends observations to policy server.
2. Policy server returns an action chunk.
3. Robot client places actions into a queue.
4. Robot client executes queued actions at the target fps.
5. When the queue gets low, robot client sends a new observation.
6. If new and old chunks overlap, LeRobot aggregates overlapping actions.
```

This is the behavior we want to test now.

## Verified So Far

We tested official LeRobot only, without custom scripts:

```text
.venv/bin/python -m lerobot.scripts.lerobot_find_cameras opencv
```

Result:

```text
Official camera finder works.
It detected OpenCV Camera @ /dev/video4.
```

We also tested official robot client with an unreachable policy server so the robot could not receive actions:

```text
.venv/bin/python -m lerobot.async_inference.robot_client ...
```

Result:

```text
Official robot_client parsed the SO-101 config.
OpenCVCamera(/dev/video4) connected.
my_so101_follower SOFollower connected.
Robot connected and ready.
Policy server connection failed intentionally because server_address was 127.0.0.1:1.
No robot motion occurred.
```

This means official LeRobot works for the available robot and camera path.

## Current Non-Code Blockers

The remaining blockers are hardware/device availability, not custom-code problems:

```text
/dev/video2 was busy by Chrome.
The Logitech top camera was not visible at that moment.
The user will fix the cameras.
```

We will not work around these by writing custom code. We will wait for the cameras to be fixed, then use official LeRobot commands.

## Official Test Path Going Forward

### 1. Check Cameras

Use official LeRobot camera discovery:

```bash
cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject

.venv/bin/python -m lerobot.scripts.lerobot_find_cameras opencv
```

Expected:

```text
front camera visible
top camera visible
any direct USB cameras visible as OpenCV cameras
```

### 2. Check Robot Client Without Actions

Use official robot_client with an unreachable server address only for connection testing.

Purpose:

```text
Validate robot and cameras connect through official LeRobot.
Avoid real robot movement because no policy server is available.
```

### 3. Start Official Policy Server

On the GPU machine:

```bash
python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8080 \
  --fps=30
```

### 4. Run Official Robot Client

On the robot laptop:

```bash
.venv/bin/python -m lerobot.async_inference.robot_client \
  --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00 \
  --robot.id=my_so101_follower \
  --robot.disable_torque_on_disconnect=false \
  --robot.max_relative_target=12 \
  --robot.cameras='{ front: {type: opencv, index_or_path: "/dev/videoX", width: 640, height: 480, fps: 30} }' \
  --policy_type=pi05 \
  --pretrained_name_or_path=/path/to/pi05/checkpoint \
  --actions_per_chunk=50 \
  --task="pick up the orange and move it to another place" \
  --server_address=127.0.0.1:8080 \
  --policy_device=cuda \
  --client_device=cpu \
  --fps=30 \
  --chunk_size_threshold=0.5 \
  --aggregate_fn_name=weighted_average
```

Replace `/dev/videoX` and the checkpoint path with the real values after camera and model setup are confirmed.

## Permission Rule For Future Customization

Codex must not create or edit custom scripts unless all of the following are true:

```text
1. Official LeRobot does not provide the needed behavior.
2. Codex explains exactly what is missing.
3. Codex explains the smallest proposed customization.
4. The user gives permission.
```

Until then, the operating rule is:

```text
Use LeRobot as-is.
Verify official behavior first.
Treat custom code as a last resort.
```
