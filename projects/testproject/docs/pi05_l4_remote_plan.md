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

## 17. L40S Offline Pi05 Test: hidden-yellow-weasel

Instance:

```text
Brev name: hidden-yellow-weasel
GPU: NVIDIA L40S
VRAM: about 44.39 GiB usable
RAM: 32 GiB
Machine: g6e.xlarge
Public IP shown in Brev UI: 3.15.137.69
```

What worked:

```text
Brev SSH worked.
NVIDIA L40S was visible with nvidia-smi.
Python 3.12.13 was available.
uv was available.
LeRobot repo cloned to /home/ubuntu/lerobot.
Python venv created at /home/ubuntu/pi05-venv.
LeRobot installed with pip install -e ".[pi]".
Torch CUDA worked:
- torch 2.11.0+cu130
- cuda_available True
- gpu NVIDIA L40S
```

Model tested:

```text
zz4321/so101_pi05
```

Model load result:

```text
model.safetensors downloaded: 7.47 GB
policy type: pi05
state shape: [6]
action shape: [6]
cameras expected:
- observation.images.top
- observation.images.front
- observation.images.wrist
chunk size: 50
action steps: 50
loaded successfully on CUDA
VRAM allocated after load: about 8.71 GiB
VRAM reserved after load: about 8.94 GiB
```

This is important because the same full model load made the smaller L4 instance unhealthy.

Offline dummy inference result:

```text
input:
- fake front camera image: [1, 3, 480, 640]
- fake robot state: [1, 6]
- dummy language tokens: [1, 200]

output:
- action chunk shape: [1, 50, 6]
- dtype: torch.float32
- device: cuda:0
- first inference time: about 9.223 seconds
```

Result:

```text
OFFLINE_INFERENCE_SHAPE_OK
```

Meaning:

```text
The L40S can load Pi05.
The policy can run on CUDA.
The policy returns the correct SO-101 action chunk shape.
No real robot movement was attempted.
```

Remaining issue:

```text
The real PaliGemma tokenizer is gated:
google/paligemma-3b-pt-224
```

When we tried to download the tokenizer without Hugging Face authentication, Hugging Face returned:

```text
401 Unauthorized
Access to model google/paligemma-3b-pt-224 is restricted.
```

So before real instruction-based inference, we need Hugging Face auth on the GPU machine and access to:

```text
google/paligemma-3b-pt-224
```

Next recommended step:

```text
Authenticate Hugging Face on the L40S.
Confirm access to google/paligemma-3b-pt-224.
Run the same offline inference test with real task text tokenization.
Then inspect LeRobot async inference server/client commands.
Do not move the real SO-101 arm yet.
```

## 18. L40S Real-Text Offline Pi05 Test

Hugging Face authentication:

```text
HF token copied to /home/ubuntu/.huggingface.env on the L40S.
hf auth login succeeded.
hf auth whoami returned user: prakashgaikwad.
```

Tokenizer access:

```text
google/paligemma-3b-pt-224 tokenizer downloaded successfully.
Tokenizer class: GemmaTokenizer
```

Real task prompt used:

```text
Task: pick up the object, State: 128 128 128 128 128 128;
Action:
```

Why the state uses `128`:

```text
Pi05 stores the robot state in the text prompt as discretized bins.
For this offline test, 128 means a neutral/middle state value.
This is only a runtime test, not a real robot observation yet.
```

Input:

```text
fake front camera image: [1, 3, 480, 640]
fake robot state: [1, 6]
real tokenized task text: [1, 200]
```

Output:

```text
action chunk shape: [1, 50, 6]
dtype: torch.float32
device: cuda:0
inference time after model load: about 0.496 seconds
```

Result:

```text
REAL_TEXT_OFFLINE_INFERENCE_OK
```

Meaning:

```text
Pi05 now works with real instruction text on the L40S.
The gated tokenizer issue is solved on this instance.
The policy returns valid SO-101-shaped action chunks.
No real robot movement was attempted.
```

Updated next recommended step:

```text
Inspect LeRobot async inference server/client commands.
Decide whether to use the official async PolicyServer/RobotClient first.
Build a dry-run local client that receives action chunks but does not move the arm.
Only after dry-run logs look safe, test with very strict movement limits.
```

## 19. LeRobot Async Inference Commands

LeRobot already provides two official async inference entry points:

```text
PolicyServer:
python -m lerobot.async_inference.policy_server

RobotClient:
python -m lerobot.async_inference.robot_client
```

The server is started first on the GPU machine:

```bash
python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8080 \
  --fps=30 \
  --inference_latency=0.033 \
  --obs_queue_timeout=1
```

Why `0.0.0.0`:

```text
The PolicyServer runs on the L40S.
The laptop connects from outside that machine.
So the server must listen on all network interfaces, not only localhost.
```

Then the laptop-side client would normally be:

```bash
python -m lerobot.async_inference.robot_client \
  --server_address=<L40S_HOST>:8080 \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" \
  --task="pick up the object" \
  --policy_type=pi05 \
  --pretrained_name_or_path=zz4321/so101_pi05 \
  --policy_device=cuda \
  --client_device=cpu \
  --actions_per_chunk=50 \
  --chunk_size_threshold=0.5 \
  --aggregate_fn_name=weighted_average \
  --debug_visualize_queue_size=True
```

Important warning:

```text
Do not run this normal RobotClient on the real SO-101 yet.
The stock RobotClient sends received actions directly to robot.send_action().
It does not have a built-in dry-run flag.
```

So our first network test should be a custom dry-run client.

## 20. Why We Need A Dry-Run Client

The official client control loop does two things:

```text
1. Capture observation from the real robot and camera.
2. When actions arrive, call robot.send_action(...).
```

That is too early for us.

Our first network test should only do this:

```text
1. Connect to the L40S PolicyServer.
2. Send policy instructions:
   - policy_type=pi05
   - pretrained_name_or_path=zz4321/so101_pi05
   - policy_device=cuda
   - actions_per_chunk=50
3. Send a fake or saved observation.
4. Receive an action chunk.
5. Print/log:
   - action shape
   - min/max action values
   - first action
   - inference latency
6. Do not call robot.send_action().
```

Expected dry-run result:

```text
Server receives observation.
Server runs Pi05.
Laptop receives [50, 6] actions.
No arm movement happens.
```

This gives us a safe bridge test:

```text
Laptop <-> L40S network works
LeRobot async gRPC works
Pi05 server works
Action chunks return to laptop
Robot motors stay idle
```

## 21. Camera And Rename Caveat

`zz4321/so101_pi05` expects:

```text
observation.images.top
observation.images.front
observation.images.wrist
```

Our current laptop camera is:

```text
observation.images.front
```

Pi05 can pad missing cameras during direct offline inference, but the async preprocessing path expects camera keys to match known policy image features.

For first dry-run, we have three possible approaches:

```text
Option A:
Send only front if async preprocessing accepts missing top/wrist.

Option B:
Duplicate the same laptop image into top/front/wrist in a custom dry-run client.

Option C:
Add real top and wrist cameras before any real-arm policy execution.
```

Recommendation:

```text
Use Option B for dry-run.
Use Option C before serious real-arm testing.
```

## 22. Next Concrete Step

Next we should:

```text
1. Install LeRobot async dependencies on L40S.
2. Start PolicyServer on L40S port 8080.
3. Expose/forward port 8080 from Brev.
4. Run a custom dry-run client from the laptop.
5. Confirm [50, 6] action chunks arrive over gRPC.
6. Only then think about a real RobotClient test.
```

## 23. L40S Async Dependency Setup

On the L40S instance `hidden-yellow-weasel`, the same Pi05 virtual environment now also has LeRobot async dependencies installed:

```bash
cd /home/ubuntu/lerobot
source /home/ubuntu/pi05-venv/bin/activate
pip install -e ".[async]"
```

Verification:

```text
grpc import: OK
grpc version: 1.81.1
lerobot.async_inference.policy_server import: OK
```

This means the L40S is ready to start the official LeRobot PolicyServer:

```bash
cd /home/ubuntu/lerobot
source /home/ubuntu/pi05-venv/bin/activate
python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8080 \
  --fps=30 \
  --inference_latency=0.033 \
  --obs_queue_timeout=1
```

Do not start the real RobotClient yet.

Next task:

```text
Create/run a dry-run async client that logs returned Pi05 action chunks without moving the SO-101 arm.
```

## 24. Dry-Run Async Client Result

Created local script:

```text
scripts/pi05_async_dry_run_client.py
```

Purpose:

```text
Talk to a LeRobot async PolicyServer.
Send a synthetic SO-101 observation.
Receive a Pi05 action chunk.
Print action statistics.
Never instantiate the real robot.
Never open /dev/ttyACM*.
Never call robot.send_action().
```

First attempt with the stock PolicyServer:

```text
PolicyServer loaded Pi05 successfully.
PolicyServer received the synthetic observation.
PolicyServer then stalled inside policy.predict_action_chunk().
Client timed out after 300 seconds.
No robot movement happened.
```

Debug result:

```text
The stall was caused by TorchDynamo/TorchInductor compilation.
The traceback showed torch.compile / torch._dynamo / torch._inductor work inside predict_action_chunk().
```

Fix:

```text
Start PolicyServer with TORCHDYNAMO_DISABLE=1.
```

Working server command:

```bash
cd /home/ubuntu/lerobot
source /home/ubuntu/pi05-venv/bin/activate

TORCHDYNAMO_DISABLE=1 python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8080 \
  --fps=30 \
  --inference_latency=0.033 \
  --obs_queue_timeout=5
```

Working dry-run client command on the L40S, with the server already loaded:

```bash
/home/ubuntu/pi05-venv/bin/python /home/ubuntu/pi05_async_dry_run_client.py \
  --server-address=127.0.0.1:8080 \
  --task="pick up the object" \
  --timeout-s=120 \
  --skip-policy-setup
```

Dry-run result:

```text
server_ready_ms: 2.39
policy_setup_s: skipped
send_observation_ms: 5.23
get_actions_s: 0.699
received_actions: 50
action_tensor_shape: [50, 6]
action_dtype: torch.float32
action_min: -33.827065
action_max: 103.115753
first_timestep: 0
last_timestep: 49
```

First action returned:

```text
[-0.9545364379882812,
 -18.055564880371094,
 3.9836578369140625,
 22.778053283691406,
 19.201927185058594,
 11.647117614746094]
```

Result:

```text
ASYNC_DRY_RUN_OK
```

Meaning:

```text
LeRobot async gRPC works with Pi05 when TorchDynamo is disabled.
The L40S PolicyServer can return SO-101-shaped action chunks.
The dry-run client can receive those actions.
No real arm movement was attempted.
```

Known issue:

```text
The local Brev port-forward dropped during one laptop-to-L40S attempt.
The successful dry-run was executed on the L40S against localhost.
```

## 9. Laptop-to-L40S SSH Tunnel Dry Run

We then tested the same async path from the local laptop to the L40S using a normal SSH tunnel instead of Brev port-forward.

L40S instance:

```text
name: hidden-yellow-weasel
gpu: NVIDIA L40S
ssh alias: hidden-yellow-weasel
remote policy port: 8080
local tunnel port: 8080
```

Remote PolicyServer command:

```bash
ssh hidden-yellow-weasel

cd /home/ubuntu/lerobot
source /home/ubuntu/pi05-venv/bin/activate

TORCHDYNAMO_DISABLE=1 python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8080 \
  --fps=30 \
  --inference_latency=0.033 \
  --obs_queue_timeout=5
```

Local SSH tunnel command:

```bash
ssh -o RequestTTY=no -o ExitOnForwardFailure=yes \
  -N -L 8080:127.0.0.1:8080 hidden-yellow-weasel
```

Local dry-run client command:

```bash
cd /home/prakash-gaikwad/PrakashProjects/testproject

/data/conda-envs/lerobot/bin/python scripts/pi05_async_dry_run_client.py \
  --server-address=127.0.0.1:8080 \
  --task="pick up the object" \
  --timeout-s=300
```

Result:

```text
server_ready_ms: 594.72
policy_setup_s: 107.630
send_observation_ms: 2555.40
get_actions_s: 2.970
received_actions: 50
action_tensor_shape: [50, 6]
action_dtype: torch.float32
action_min: -25.745178
action_max: 113.192764
first_timestep: 0
last_timestep: 49
```

First action returned:

```text
[-3.4612903594970703,
 -22.69786834716797,
 9.39739990234375,
 25.910369873046875,
 21.046714782714844,
 16.252225875854492]
```

Final result:

```text
ASYNC_DRY_RUN_OK
```

What this proves:

```text
The laptop can talk to the L40S Pi05 PolicyServer through SSH.
The L40S can load zz4321/so101_pi05.
The L40S returns SO-101-shaped 6D action chunks.
The local dry-run client receives the action chunk successfully.
No real arm movement was attempted.
```

## 10. Live-Observation Dry Run

After the laptop-to-L40S fake-observation dry run worked, we ran a safer live-observation dry run.

This test did:

```text
Read real follower joint positions from the local SO-101 follower.
Read one real laptop camera frame from OpenCV camera index 0.
Duplicate that one camera frame into the Pi05 model's expected top/front/wrist camera inputs.
Send the real observation to the L40S Pi05 PolicyServer.
Receive an action chunk back.
Print the returned actions.
Never call robot.send_action().
Never write actions to the motors.
```

Local script:

```text
scripts/pi05_live_observation_dry_run.py
```

Important implementation detail:

```text
The script prefers the follower serial path when it exists:
/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00

This avoids problems when /dev/ttyACM0 and /dev/ttyACM1 swap.
```

Command used:

```bash
cd /home/prakash-gaikwad/PrakashProjects/testproject

/data/conda-envs/lerobot/bin/python scripts/pi05_live_observation_dry_run.py \
  --server-address=127.0.0.1:8080 \
  --task="pick up the object" \
  --timeout-s=300
```

Live follower state read:

```text
shoulder_pan.pos: -3.648
shoulder_lift.pos: -103.209
elbow_flex.pos: 96.396
wrist_flex.pos: 68.659
wrist_roll.pos: -176.396
gripper.pos: 16.343
camera_shape: [480, 640, 3]
```

Result:

```text
policy_setup_s: 109.671
send_observation_ms: 2147.43
get_actions_s: 3.277
received_actions: 50
action_tensor_shape: [50, 6]
action_dtype: torch.float32
action_min: -99.142235
action_max: 104.946198
first_timestep: 0
last_timestep: 49
```

First action returned:

```text
[-8.54312801361084,
 -88.47808074951172,
 73.2452621459961,
 48.10401916503906,
 1.6679189205169678,
 5.532790184020996]
```

Final result:

```text
LIVE_OBSERVATION_DRY_RUN_OK
```

What this proves:

```text
The local laptop can read the real SO-101 follower state.
The local laptop camera works as the front camera source.
The laptop can send real observations to the L40S.
The L40S Pi05 server can return 6D SO-101 actions from those observations.
We still have not moved the arm with Pi05.
```

Known limitation:

```text
The Pi05 checkpoint expects three camera views: top, front, and wrist.
For this dry run we only used one laptop camera and duplicated it into all three inputs.
That is acceptable for network/model testing, but it is not ideal for real autonomous behavior.
```

Next recommended step:

```text
Add a guarded real-action test script.
It should receive Pi05 actions, clamp/smooth them heavily,
send only one tiny action step at a time,
and require an explicit confirmation flag before any motor write.
```

## 11. Guarded One-Step Real-Action Test Script

We added a guarded script:

```text
scripts/pi05_guarded_real_action_test.py
```

Default behavior:

```text
Read local follower state.
Read local camera.
Ask the L40S Pi05 server for actions.
Print the raw first Pi05 action.
Clamp the first action to a tiny safe target.
Print what would be sent.
Do not move the robot.
```

Motor movement requires both explicit flags:

```text
--move-one-step
--i-understand-this-moves-robot
```

The default clamp is:

```text
max body joint step: 1 degree
max gripper step: 1 unit
```

Observation-only command:

```bash
cd /home/prakash-gaikwad/PrakashProjects/testproject

/data/conda-envs/lerobot/bin/python scripts/pi05_guarded_real_action_test.py \
  --server-address=127.0.0.1:8080 \
  --task="pick up the object" \
  --timeout-s=300
```

One tiny movement command:

```bash
cd /home/prakash-gaikwad/PrakashProjects/testproject

/data/conda-envs/lerobot/bin/python scripts/pi05_guarded_real_action_test.py \
  --server-address=127.0.0.1:8080 \
  --task="pick up the object" \
  --timeout-s=300 \
  --max-step-deg=1 \
  --gripper-max-step=1 \
  --move-one-step \
  --i-understand-this-moves-robot
```

Extra cautious option:

```bash
--disable-motor wrist_roll
```

Use that if wrist roll still feels mechanically suspicious.
