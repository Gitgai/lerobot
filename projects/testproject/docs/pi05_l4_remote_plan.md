# Pi05 On L4 With Local SO-101 Arm

This document explains the plan for using a pretrained Pi05 model on a Brev/NVIDIA L4 GPU while the real SO-101 arm stays connected to the local Ubuntu laptop.

## 1. Why This Is Needed

Pi05 is a large vision-language-action policy. It is much heavier than ACT.

The local laptop is good for:

```text
SO-101 USB motor control
camera capture
local safety checks
dataset recording
```

The L4 GPU is better for:

```text
loading Pi05
running CUDA inference
testing large pretrained checkpoints
```

So the system becomes:

```text
local laptop = robot body controller
Brev L4 GPU  = Pi05 model brain
```

## 2. High-Level Flow

The full control loop would be:

```text
1. Laptop reads camera image.
2. Laptop reads SO-101 follower joint state.
3. Laptop sends image + state + task text to the L4 server.
4. L4 runs Pi05.
5. L4 returns a chunk of future robot actions.
6. Laptop checks safety limits.
7. Laptop sends safe actions to the follower arm.
8. Repeat.
```

Simple picture:

```text
Local Ubuntu laptop                         Brev L4 GPU
-------------------                         -----------
camera frame  --------------------------->  Pi05 model
robot state   --------------------------->  action chunk
                                             |
SO-101 arm    <---------------------------  safe actions
```

## 3. Why Action Chunks Matter

Pi05 predicts a chunk of future actions, not just one tiny action.

That helps because remote inference has latency:

```text
laptop -> internet -> L4 -> internet -> laptop
```

Instead of waiting for the cloud every single motor step, the laptop can execute part of the returned action chunk while the L4 prepares the next chunk.

This is the right shape for remote inference, but it still needs careful safety handling.

## 4. Process Structure In Simple Words

Think of the system as two computers sharing one robot job.

```text
Local laptop:
- owns the real robot
- owns the real camera
- talks to USB motors
- decides whether an action is safe

Brev L4:
- owns the big Pi05 model
- receives observations from the laptop
- predicts what the robot should do next
- sends actions back
```

The L4 is not physically connected to the SO-101 arm.

The laptop is physically connected to the SO-101 arm.

That means:

```text
the L4 suggests actions
the laptop approves and executes actions
```

This is important for safety.

### One Control Cycle

One robot control cycle looks like this:

```text
1. Laptop captures a camera frame.
2. Laptop reads follower joint positions.
3. Laptop creates an observation packet:
   - image
   - joint state
   - task text, for example "pick up the cube"
4. Laptop sends the packet to the L4.
5. L4 runs Pi05 inference.
6. L4 returns an action chunk.
7. Laptop checks the action chunk:
   - is it 6D?
   - are values inside safe range?
   - are jumps too large?
   - did the reply arrive in time?
8. Laptop sends safe actions to the follower arm.
9. Laptop asks the L4 for the next action chunk.
```

### Why The Laptop Must Stay In Control

The robot can move only because the laptop talks to the servo controller board over USB.

So even if Pi05 runs on L4, the local laptop should always be the final controller:

```text
Pi05: "I think the next actions should be these."
Laptop: "I checked them. They are safe. I will send them to the arm."
```

If something goes wrong:

```text
network delay
bad model output
wrong action shape
camera frame missing
user presses Ctrl+C
```

the laptop stops sending actions.

### What Data Moves Over The Network

From laptop to L4:

```text
camera image(s)
current joint state
task instruction text
timestamp/session id
```

From L4 to laptop:

```text
action chunk
confidence/debug info if available
timing information
```

The L4 should not receive direct USB access. It only receives robot observations.

### Why This Is More Complex Than Local ACT

With local ACT:

```text
laptop camera -> local model -> local arm
```

With L4 Pi05:

```text
laptop camera -> internet -> L4 model -> internet -> local arm
```

So Pi05 has more power, but also more moving pieces:

```text
network latency
server process
client process
model loading
camera name matching
safety checks
timeouts
```

That is why we start with inspection and offline inference before moving the arm.

## 5. Current Compatibility Issue

Our current robot setup:

```text
Robot: SO-101 follower
State: 6 joint positions
Action: 6 motor actions
Camera: one laptop camera
Camera name: observation.images.front
```

The strongest Pi05 SO-101 candidates we inspected expect more cameras:

```text
zz4321/so101_pi05:
- observation.images.top
- observation.images.front
- observation.images.wrist
- observation.state shape: 6
- action shape: 6

nuffnuff/pi05-so101-finetuned_1:
- observation.images.top
- observation.images.wrist
- observation.state shape: 6
- action shape: 6
```

The action and state shapes are promising because they match SO-101.

The camera setup is the main blocker:

```text
we have 1 front camera
models expect 2-3 cameras
```

We should not let a pretrained Pi05 model move the real arm until we solve or deliberately test this camera mismatch.

## 6. Candidate Models

Initial order to inspect/test:

```text
1. zz4321/so101_pi05
2. nuffnuff/pi05-so101-finetuned_1
3. aswinkumar99/LeRobot-SO101-Pi05-universal-all_bs32_s20000
4. felixmayor/pi05_so101_orange_cube
```

Best first candidate:

```text
zz4321/so101_pi05
```

Reason:

```text
LeRobot Pi05 format
SO-101 dataset
state shape 6
action shape 6
```

Problem:

```text
expects top + front + wrist cameras
```

## 7. Start Here: Step 1 Local Policy Inspection

The first step is not to start the L4 and not to move the robot.

The first step is:

```text
inspect pretrained policy configs locally
```

Goal:

```text
compare each pretrained Pi05 model with our real SO-101 setup before any robot movement
```

Command we want to add to our local runner:

```bash
./bin/so101 inspect-policy zz4321/so101_pi05
```

Expected report:

```text
Policy repo: zz4321/so101_pi05
Policy type: pi05
State shape expected: 6
Action shape expected: 6
Action chunk size: 50
Cameras expected:
- observation.images.top
- observation.images.front
- observation.images.wrist

Our current config:
- observation.images.front
- observation.state shape: 6
- action shape: 6

Compatibility:
- state: OK
- action: OK
- cameras: MISMATCH, missing top and wrist
```

Why this matters:

```text
If state/action shape does not match, do not use the model.
If camera names do not match, decide whether to add cameras, rename cameras, or only do offline testing.
```

This step is safe because it only reads Hugging Face model config files:

```text
config.json
train_config.json
policy_preprocessor.json
policy_postprocessor.json
README.md
```

It does not load the full model weights and it does not connect to the arm.

## 8. Safe Development Phases

### Phase 1: Local Policy Inspection

Goal:

```text
prove which pretrained Pi05 models are compatible enough to test
```

No robot movement.

No L4 required.

Checks:

```text
policy type is pi05
action shape is 6
state shape is compatible
camera names are known
chunk size is known
missing camera inputs are clearly reported
```

Output:

```text
candidate model ranking
camera mismatch report
safe next action
```

### Phase 2: L4 Model Load Test

Goal:

```text
prove the selected Pi05 checkpoint can download and load on the L4 GPU
```

No robot movement.

Checks:

```text
model downloads
dependencies install
CUDA sees L4
policy config loads
VRAM is enough
```

### Phase 3: Offline Inference Test

Goal:

```text
run Pi05 on saved observations without connecting to the robot
```

Use our saved dataset:

```text
/data/lerobot_datasets/so101_pick_test
```

Checks:

```text
observation format can be built
policy returns action
action shape is 6
action chunk length is expected
inference latency is measured
```

### Phase 4: Remote Inference Server

Goal:

```text
run Pi05 on the L4 as a small HTTP/WebSocket service
```

Server idea:

```text
POST /predict
input:
- camera image(s)
- robot state
- task text

output:
- action chunk
```

The L4 should only predict actions. It should not directly talk to the motor bus.

### Phase 5: Local Robot Client

Goal:

```text
local laptop controls the real SO-101 and treats the L4 as a model service
```

Laptop responsibilities:

```text
read camera
read robot state
send request to L4
receive action chunk
validate action shape
limit maximum movement
stop on timeout
send safe actions to follower
```

The local laptop remains the safety gate.

### Phase 6: Very Short Real Test

Goal:

```text
verify real robot movement under strict limits
```

First test:

```text
duration: 5-10 seconds
robot in open space
no object
hand near power switch
small motion limit
log everything
```

Only after that:

```text
30 second test
single task attempt
longer task attempt
```

## 9. Safety Rules

Do not start with direct real-arm policy execution.

Before actions touch the follower arm, verify:

```text
action shape is 6
joint values are within safe calibrated ranges
per-step joint change is small
network timeout stops motion
Ctrl+C works
power switch is reachable
logs are saved
```

If any check fails:

```text
do not move the arm
```

## 10. Camera Plan

Current one-camera setup is enough for our own ACT-style dataset tests, but not ideal for pretrained Pi05 models.

For Pi05, the practical camera plan is:

```text
minimum useful setup:
- front camera
- top camera

better setup:
- front camera
- top camera
- wrist camera
```

Possible sources:

```text
USB webcam for front/top
small Pi/ESP32 camera for secondary view
wrist-mounted USB or small network camera later
```

Avoid relying on WiFi cameras for the main safety-critical view until latency is tested.

## 11. Why We Are Not Using ACT Here

ACT is still the simpler and safer local-training path.

But if the goal is:

```text
avoid training from scratch
try pretrained policies
use a stronger VLA model
```

then Pi05 on L4 is the right direction.

Tradeoff:

```text
ACT:
- local
- smaller
- simpler
- needs our demonstrations

Pi05 + L4:
- pretrained
- more powerful
- remote GPU needed
- more complex
- camera compatibility matters more
```

## 12. Recommended Next Step

Do not move the real arm yet.

Immediate technical step:

```text
Use zz4321/so101_pi05 for the first L4 load/offline inference test.
```

The local inspection command now exists and reports:

```text
policy type
input camera names
state shape
action shape
chunk size
model size
compatibility with our current config
```

Then test:

```bash
./bin/so101 inspect-policy zz4321/so101_pi05
./bin/so101 inspect-policy nuffnuff/pi05-so101-finetuned_1
./bin/so101 inspect-policy aswinkumar99/LeRobot-SO101-Pi05-universal-all_bs32_s20000
```

After that:

```text
choose the best candidate
start an L4 instance only after inspection passes
install LeRobot with Pi05 dependencies on L4
download/load the selected model
run offline inference only, still without moving the arm
```

## 13. Concrete Workflow From Today

Do this in order:

```text
1. Implement ./bin/so101 inspect-policy. DONE
2. Inspect zz4321/so101_pi05. DONE
3. Inspect nuffnuff/pi05-so101-finetuned_1. DONE
4. Inspect aswinkumar99/LeRobot-SO101-Pi05-universal-all_bs32_s20000. DONE
5. Pick the least mismatched model. DONE: zz4321/so101_pi05
6. Decide camera plan:
   - add top/wrist cameras, or
   - do offline-only testing with duplicated front images.
7. Start L4.
8. Install LeRobot [pi].
9. Load the selected model.
10. Run offline inference on saved observations.
11. Build L4 /predict server.
12. Build local safety client.
13. Run 5-10 second real-arm test only after all previous steps pass.
```

Current next action:

```text
start L4 and load/test zz4321/so101_pi05 offline, without moving the robot
```

## 14. Step 1 Result: Local Policy Inspection

The `inspect-policy` command was added to:

```text
scripts/so101_runner.py
```

Command format:

```bash
./bin/so101 inspect-policy <hugging-face-policy-repo>
```

It reads small config files only:

```text
config.json
train_config.json
policy_preprocessor.json
policy_postprocessor.json
```

It does not load full model weights and does not connect to the robot.

### zz4321/so101_pi05

Command:

```bash
./bin/so101 inspect-policy zz4321/so101_pi05
```

Result:

```text
Policy type: pi05
Model size: 6.96 GiB
State shape: [6]
Action shape: [6]
Chunk size: 50
Action steps: 50

Expected cameras:
- observation.images.front
- observation.images.top
- observation.images.wrist

Our camera:
- observation.images.front

Compatibility:
- policy: OK
- state: OK
- action: OK
- cameras: MISMATCH, missing top and wrist
```

Interpretation:

```text
This is the best current candidate.
The robot action/state format matches SO-101.
The blocker is camera setup.
```

### nuffnuff/pi05-so101-finetuned_1

Command:

```bash
./bin/so101 inspect-policy nuffnuff/pi05-so101-finetuned_1
```

Result:

```text
Policy type: pi05
Model size: 6.96 GiB
State shape: [6]
Action shape: [6]
Chunk size: 50
Action steps: 50

Expected cameras:
- observation.images.top
- observation.images.wrist

Our camera:
- observation.images.front

Compatibility:
- policy: OK
- state: OK
- action: OK
- cameras: MISMATCH, front camera not expected
```

Interpretation:

```text
Action/state are compatible.
Camera setup is a bigger mismatch than zz4321 because our current front camera is not one of its expected cameras.
```

### aswinkumar99/LeRobot-SO101-Pi05-universal-all_bs32_s20000

Command:

```bash
./bin/so101 inspect-policy aswinkumar99/LeRobot-SO101-Pi05-universal-all_bs32_s20000
```

Result:

```text
Policy type: pi05
Model size: 10.76 GiB
State shape: [32]
Action shape: [6]
Chunk size: 50
Action steps: 50

Expected cameras:
- observation.images.base_0_rgb
- observation.images.empty_camera_0
- observation.images.left_wrist_0_rgb
- observation.images.right_wrist_0_rgb

Our camera:
- observation.images.front

Compatibility:
- policy: OK
- state: MISMATCH
- action: OK
- cameras: MISMATCH
```

Interpretation:

```text
Do not use this first.
It needs more adaptation because both state and camera inputs differ from our current setup.
```

## 15. Updated Candidate Ranking

After local inspection:

```text
1. zz4321/so101_pi05
   Best candidate. State/action match. Needs top and wrist cameras.

2. nuffnuff/pi05-so101-finetuned_1
   State/action match. Needs top and wrist cameras, and does not expect our front camera.

3. aswinkumar99/LeRobot-SO101-Pi05-universal-all_bs32_s20000
   More complex. Action matches, but state and cameras mismatch.
```

Next recommended step:

```text
Use zz4321/so101_pi05 for the first L4 load/offline inference test.
Do not move the real arm yet.
```

## 16. L4 Load Test Attempt: usual-coffee-starfish

Instance:

```text
Brev name: usual-coffee-starfish
GPU: NVIDIA L4
VRAM: about 22 GiB
RAM: 16 GiB
Machine: g6.xlarge
```

What worked:

```text
Brev login worked.
SSH shell worked.
NVIDIA L4 was visible with nvidia-smi.
Python 3.12.13 was available through uv.
LeRobot repo cloned.
Python venv created at /home/ubuntu/pi05-venv.
LeRobot installed with pip install -e ".[pi]".
Torch CUDA worked:
- torch 2.11.0+cu130
- cuda_available True
- gpu NVIDIA L4
Small zz4321/so101_pi05 config files downloaded.
```

The model config loaded and confirmed:

```text
policy type: pi05
dtype: bfloat16
state shape: [6]
action shape: [6]
cameras:
- observation.images.top
- observation.images.front
- observation.images.wrist
```

What failed:

```text
Full policy weight loading for zz4321/so101_pi05 caused the Brev instance to become UNHEALTHY.
SSH connection dropped during policy weight load.
brev ls reported:
STATUS: UNHEALTHY
BUILD: COMPLETED
SHELL: READY
```

Reset attempt:

```bash
brev reset usual-coffee-starfish
```

Result:

```text
The instance still reported UNHEALTHY after reset/wait.
SSH did not become available again.
```

Likely reason:

```text
The L4 VRAM may be enough for bfloat16 Pi05, but the 16 GiB system RAM g6.xlarge instance may be too small or unstable during full checkpoint load.
```

Important conclusion:

```text
The software environment setup is mostly solved.
The blocker is full model loading stability on this small L4 instance.
No robot movement was attempted.
No local SO-101 arm was connected to this test.
```

Recommended next step:

```text
Retry Pi05 load on an instance with more system RAM, ideally 32 GiB or more.
Keep using L4 or a larger GPU, but avoid 16 GiB RAM if possible.
```
