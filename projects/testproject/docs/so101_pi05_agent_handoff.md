# SO-101 Pi05 Agent Handoff

Last updated: 2026-06-25

This document is for the next agent working on Prakash's SO-101 robot project. It summarizes what has been built, what has been tested, what is known from evidence, and what should happen next.

## 1. Project Goal

The real goal is:

```text
Make the real SO-101 follower arm reliably pick up an orange using cameras and a learned policy.
```

This is not just a simulator project anymore. The user has a real SO-101 follower arm, a leader arm, multiple cameras, and access to cloud GPUs.

The desired final path is:

```text
real cameras + real SO-101 state
        -> policy
        -> SO-101 actions
        -> successful grasp and lift of orange
```

The user does not want band-aid control tricks as the final answer. Temporary safety guards are acceptable for investigation, but the correct long-term solution should be model/data based.

## 2. Local Project Location

Main project folder:

```text
/home/prakash-gaikwad/PrakashProjects/testproject
```

Important files:

```text
config/so101.json
scripts/so101_runner.py
scripts/pi05_guarded_real_action_test.py
scripts/pi05_faithful_chunk_test.py
docs/so101_commands.md
docs/pi05_official_async_test_plan.md
docs/real_so101_working_robot_plan.md
docs/raspberry_pi_lerobot_camera_plan.md
docs/full_chat_history.md
```

Launcher:

```bash
./bin/so101
```

LeRobot local environment:

```text
/data/conda-envs/lerobot
```

LeRobot repo:

```text
/data/projects/lerobot
```

## 3. Current Hardware Setup

Robot:

```text
SO-101 follower arm connected to local laptop
Leader arm exists and has been used for teleoperation/recording
Pi05 real-arm inference only needs the follower arm
```

Known follower serial path:

```text
/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00
```

Config currently maps:

```json
"follower_serial": "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00"
```

Follower ID:

```text
my_so101_follower
```

Leader ID:

```text
my_so101_leader
```

## 4. Camera Setup

The current intended three-camera setup is:

```text
top camera   = Logitech C270 USB camera
front camera = laptop integrated camera
wrist camera = Raspberry Pi Zero 2W camera on SO-101 wrist
```

Current camera config in `config/so101.json`:

```json
"top_camera_index": "/dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0",
"top_camera_fourcc": "MJPG",
"top_camera_warmup_s": 3,
"top_camera_url": "http://127.0.0.1:8094/frame",

"front_camera_index": "/dev/v4l/by-id/usb-CKFNF16U42542009AA90_Integrated_Webcam_FHD_200901010001-video-index0",
"front_camera_warmup_s": 3,

"wrist_camera_url": "http://127.0.0.1:8092/frame"
```

The Logitech C270 had a direct-capture black-frame issue when grabbed too early. The browser/proxy path worked better:

```text
http://127.0.0.1:8094/
http://127.0.0.1:8094/frame
```

The Raspberry Pi wrist stream used a live camera path, proxied locally:

```text
http://127.0.0.1:8092/frame
```

Use the front laptop camera's default/auto exposure first. That is the preferred default because it is simpler and survives fewer assumptions about the room lighting.

If the front view is washed out, then use manual exposure as a troubleshooting fix. One useful manual setting from earlier testing was:

```bash
v4l2-ctl -d /dev/v4l/by-id/usb-CKFNF16U42542009AA90_Integrated_Webcam_FHD_200901010001-video-index0 \
  --set-ctrl=auto_exposure=1 \
  --set-ctrl=exposure_time_absolute=700 \
  --set-ctrl=gain=1 \
  --set-ctrl=backlight_compensation=0
```

Before Pi05 tests, always verify camera images manually. Do not spend GPU time until all three camera views are good.

If manual exposure was used and the user wants to return to the camera default behavior, switch auto exposure back on:

```bash
v4l2-ctl -d /dev/v4l/by-id/usb-CKFNF16U42542009AA90_Integrated_Webcam_FHD_200901010001-video-index0 \
  --set-ctrl=auto_exposure=3
```

## 5. Pi05 Model Tested

Main model tested:

```text
zz4321/so101_pi05
```

Hugging Face model page:

```text
https://huggingface.co/zz4321/so101_pi05
```

Important model facts:

```text
policy type: pi05
base model: lerobot/pi05_base
training dataset shown on model page: zz4321/so101_cube
model size: about 4B params
```

Local cached config:

```text
/home/prakash-gaikwad/.cache/huggingface/hub/models--zz4321--so101_pi05/snapshots/dbd6d5754bbf78318808aea1706ff23beeb8b663/config.json
```

Expected features from config:

```text
observation.state shape: [6]
observation.images.top shape: [3, 480, 640]
observation.images.front shape: [3, 480, 640]
observation.images.wrist shape: [3, 480, 640]
action shape: [6]
chunk_size: 50
n_action_steps: 50
```

This matches the SO-101 follower action/state dimension and the intended three-camera names.

## 6. Remote GPU Setup

The user has used NVIDIA Brev L40S instances to run Pi05. L40S works for loading/running Pi05 inference but is expensive.

Policy server command used on L40S:

```bash
source /home/ubuntu/miniforge3/etc/profile.d/conda.sh
conda activate pi05
cd /home/ubuntu/lerobot

nohup env TORCHDYNAMO_DISABLE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8080 \
  --fps=30 \
  --inference_latency=0.033 \
  --obs_queue_timeout=5 \
  > logs/pi05_policy_server_8080.log 2>&1 < /dev/null &
```

Local SSH tunnel example:

```bash
ssh -f \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=3 \
  -N \
  -L 8080:127.0.0.1:8080 \
  <BREV_INSTANCE_NAME>
```

The server can run out of memory if multiple policy setups/load attempts accumulate in one process. If behavior gets strange or OOM appears, restart the policy server cleanly before the next test.

## 7. Important Tests Already Done

### 7.1 Guarded 15-step Pi05 tests

Script:

```text
scripts/pi05_guarded_real_action_test.py
```

Behavior:

```text
ask Pi05 for a chunk
use mostly the first action
apply safety limits/clamps
repeat
```

These tests proved:

```text
local laptop can send observations to L40S
L40S can return Pi05 actions
SO-101 can move from returned actions
```

But they did not produce a successful orange grasp.

### 7.2 Faithful Pi05 chunk test

Script:

```text
scripts/pi05_faithful_chunk_test.py
```

Purpose:

```text
ask Pi05 once
receive one 50-action chunk
execute action[0], action[1], action[2] from the same chunk
do not apply outer clamps
```

Result:

```text
FAITHFUL_CHUNK_TEST_OK
chunk actions executed: 3
outer clamp: none
robot max_relative_target: none
```

Files:

```text
Video:
/data/downloads/3cam tests/so101_pi05_faithful_chunk_3actions_20260624_132259.mp4

Action log:
/data/downloads/3cam tests/so101_pi05_faithful_chunk_3actions_20260624_132259.actions.csv
```

Important evidence from the action log:

```text
before wrist_roll: -116.35
Pi05 action 0:      -6.63
after wrist_roll:   -7.43
```

This is about a 109 degree wrist-roll change.

Action 0 delta from before:

```text
shoulder_pan:    +1.10 deg
shoulder_lift:   +6.74 deg
elbow_flex:     -22.82 deg
wrist_flex:      -6.20 deg
wrist_roll:    +109.73 deg
gripper:         +1.37 deg
```

Actual after minus before:

```text
shoulder_pan:    +0.62 deg
shoulder_lift:   +4.31 deg
elbow_flex:     -20.04 deg
wrist_flex:      -4.13 deg
wrist_roll:    +108.92 deg
gripper:         +0.54 deg
```

Interpretation:

```text
The robot accepted the raw Pi05 action.
Pi05 mostly commanded wrist/arm reorientation.
It did not command a clear reach-close-lift orange grasp trajectory.
```

This is the strongest evidence so far.

## 8. Current Root-Cause Understanding

Known facts:

```text
Robot connection works.
Camera capture works when prechecked.
Remote Pi05 inference works.
Action feature shape matches the robot.
Faithful chunk execution works for at least the first 3 raw actions.
The orange is not picked.
The raw Pi05 chunk starts with major wrist reorientation, not a useful grasp.
```

Most likely cause:

```text
The pretrained zz4321/so101_pi05 checkpoint is not adapted to this exact real setup.
```

Why:

```text
The checkpoint is associated with zz4321/so101_cube, not this user's orange-pick setup.
The camera layout, scene, object, lighting, start pose, and wrist view differ from training.
The model's raw actions do not produce a grasp trajectory in our scene.
```

Do not overclaim:

```text
We do not know Pi05's internal intent.
We do know the actions it produced and the motion that happened.
```

## 9. What Not To Repeat

Avoid spending more L40S time on:

```text
random 15-step prompt tweaks
more guarded first-action tests
long raw uncontrolled runs
changing many variables at once
```

Those have already consumed time and did not solve the task.

Avoid saying:

```text
"It just needs more steps"
```

The faithful chunk test showed the first raw actions were not a clean grasp approach.

## 10. Correct Next Technical Direction

There are two valid next paths.

### Option A: Validate pretrained checkpoint on an easier/training-like setup

Purpose:

```text
Check whether zz4321/so101_pi05 can do the kind of task it was trained for.
```

Use:

```text
cube-like object instead of orange
scene closer to the dataset
camera layout stable
start pose closer to the apparent model distribution
```

This tells us whether the checkpoint is usable at all.

### Option B: Correct solution for the real goal

Purpose:

```text
Make the real robot pick the orange in this user's setup.
```

Do:

```text
record successful orange-pick demonstrations
fine-tune Pi05 or another suitable policy on those demos
evaluate the fine-tuned model
```

Recommended dataset sizes:

```text
5 episodes: pipeline smoke test only
20 successful episodes: first fine-tune test
50 successful episodes: better first real attempt
100+ successful episodes: more reliable behavior
```

Each successful episode should include:

```text
start with visible orange
open gripper
move to orange
align gripper
close gripper around orange
lift orange slightly
end after clear success
```

## 11. Recommended Immediate Next Step

Do not start cloud GPU first.

First, locally:

```text
1. Check follower arm status.
2. Check leader arm status if recording demonstrations.
3. Check top/front/wrist camera images.
4. Fix exposure/lighting if needed.
5. Record 5 clean orange-pick episodes by teleoperation.
6. Replay those episodes.
```

Only after local demonstrations look good:

```text
start cheaper training GPU
copy/upload dataset
fine-tune
evaluate
stop GPU immediately
```

## 12. Useful Local Commands

From project root:

```bash
cd /home/prakash-gaikwad/PrakashProjects/testproject
```

Status:

```bash
./bin/so101 status
```

Positions:

```bash
./bin/so101 positions
```

Teleoperate:

```bash
./bin/so101 teleop
```

Record 5 fresh episodes:

```bash
./bin/so101 record --episodes 5 --delete
```

Replay:

```bash
./bin/so101 replay 0
```

Inspect model:

```bash
./bin/so101 inspect-policy zz4321/so101_pi05
```

## 13. User Preferences

The user wants:

```text
clear explanation
real evidence
no vague guessing
correct solutions over band-aids
execution help, not just commands
cost awareness because L40S is expensive
```

When explaining uncertainty, separate:

```text
facts we measured
likely interpretation
what test would prove/disprove it
```

The user dislikes repeating random tests. Keep experiments purposeful and documented.

## 14. Cost Guidance

The user asked about cheaper GPUs than Brev L40S.

For Pi05 fine-tuning, likely better options:

```text
RunPod A100 80GB
Vast.ai A100 80GB
```

Avoid assuming 24GB GPUs are enough for Pi05 fine-tuning.

Suggested strategy:

```text
record and verify data locally first
rent GPU only for training
stop GPU immediately after training/evaluation
```

## 15. Final Summary For Next Agent

The system pipeline works, but the pretrained checkpoint does not currently solve the real orange-pick task.

The most important evidence is the faithful chunk test:

```text
Pi05 returned a valid 50-action chunk.
The robot executed raw actions from that chunk.
The first actions mostly reoriented wrist/arm.
They did not approach, grasp, and lift the orange.
```

The correct next serious step is not more prompt/clamp tuning. It is:

```text
collect successful demonstrations on the exact real setup
fine-tune/evaluate a policy on that data
```
