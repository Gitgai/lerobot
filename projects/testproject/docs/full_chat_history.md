# Full Project Chat History

This document summarizes the full project conversation from the first simulator question through the current GitHub archive work.

It is not a raw transcript. It is a readable project log: what we tried, what worked, what failed, what we learned, and what the next steps are.

## 1. Starting Point

The first question was about this model:

```text
lerobot/smolvla_vlabench
```

We clarified that it is not an empty model. It is a pretrained/fine-tuned SmolVLA checkpoint for VLABench:

```text
lerobot/smolvla_base
        -> fine-tuned on VLABench data
        -> lerobot/smolvla_vlabench
```

The important point was:

```text
Evaluate in VLABench simulator: yes
Run directly on SO-101 hardware: no
Use as starting point for robot fine-tuning: yes
```

The model expected VLABench-style inputs and outputs:

```text
Inputs:
- 3 camera images
- robot state

Output:
- 7D continuous action
```

## 2. First VLABench Setup On Brev L4

The first target machine was a Brev NVIDIA L4 instance.

The user connected with:

```bash
brev refresh
brev shell lightwheel-leisaac-f58019
```

At first, LeRobot install failed because the default Python was too old:

```text
Python 3.10.12 was installed
LeRobot required Python >= 3.12
```

The instance did not have `conda`, and Ubuntu apt did not provide `python3.12` because the remote machine was on Ubuntu Jammy repositories.

The fix was to install Miniforge and create a Python 3.12 conda environment:

```text
Miniforge: /home/ubuntu/miniforge3
Conda env: smolvla-vlabench312
Python: 3.12
```

Then LeRobot and VLABench were installed:

```text
LeRobot: /home/ubuntu/lerobot
VLABench: /home/ubuntu/VLABench
MuJoCo: 3.2.2
dm_control: working
Torch CUDA: working
GPU: NVIDIA L4 visible
VLABench assets: downloaded
```

## 3. First VLABench Smoke Test

We ran a one-episode VLABench smoke test:

```bash
lerobot-eval \
  --policy.path=lerobot/smolvla_vlabench \
  --env.type=vlabench \
  --env.task=select_fruit \
  --eval.batch_size=1 \
  --eval.n_episodes=1 \
  --eval.use_async_envs=false \
  --policy.device=cuda \
  '--rename_map={"observation.images.image": "observation.images.camera1", "observation.images.second_image": "observation.images.camera2", "observation.images.wrist_image": "observation.images.camera3"}'
```

Result:

```text
Task: select_fruit
Episodes: 1
Success rate: 0%
Runtime: about 202 seconds
```

The video was saved on the Brev instance:

```text
/home/ubuntu/lerobot/outputs/eval/2026-05-20/04-04-17_vlabench_smolvla/videos/select_fruit_0/eval_episode_0.mp4
```

Important lesson:

```text
Typing an .mp4 path directly tries to execute it as a program.
That gives "Permission denied".
Use xdg-open, vlc, a file manager, or copy the file locally.
```

## 4. Copying Videos From Brev

We clarified the difference between local terminal and Brev terminal:

```text
prakash-gaikwad@pg-ubuntu = local machine
ubuntu@brev-...           = Brev cloud machine
```

`brev copy` must be run from the local machine, not inside the Brev machine.

Example:

```bash
brev copy \
  lightwheel-leisaac-f58019:/home/ubuntu/lerobot/outputs/eval/2026-05-20/04-04-17_vlabench_smolvla/videos/select_fruit_0/eval_episode_0.mp4 \
  ~/Downloads/select_fruit_eval_episode_0.mp4
```

Later, a Brev copy attempt failed because the account ran out of credits:

```text
there was issues with your credits You have run out of credits
```

That was a billing/credit issue, not a LeRobot issue.

## 5. VLABench 10 Episode Run

We ran 10 episodes for `select_fruit`.

Result:

```text
avg_sum_reward: 0.0
avg_max_reward: 0.0
pc_success: 0.0
n_episodes: 10
eval_s: 1782.51
eval_ep_s: 178.25
```

The output videos were under:

```text
/home/ubuntu/lerobot/outputs/eval/2026-05-20/19-35-55_vlabench_smolvla/videos/select_fruit_0/
```

We discussed storing downloaded videos in:

```text
/data/downloads
```

instead of:

```text
/home/prakash-gaikwad/Downloads
```

## 6. Debugging VLABench 6D/7D Mismatch

After watching the VLABench episodes, the behavior looked wrong. We suspected a mismatch between what the policy outputs and what the environment expects.

The key issue was:

```text
Policy/action config suggests 7D action.
Some VLABench control path appeared to behave like 6D end-effector control.
```

Because the model achieved 0% and the behavior did not look meaningful, we decided not to spend too much more time forcing this checkpoint.

Decision:

```text
Move to a better-supported simulator/model pair.
Try LIBERO first.
Try RoboCasa second.
```

## 7. What LIBERO Is

We clarified:

```text
LIBERO is a simulator benchmark and task suite, not a model.
```

It provides robot manipulation tasks in simulation. A model such as SmolVLA, ACT, or pi0.5 can be evaluated on LIBERO tasks.

Simple version:

```text
LIBERO = simulated robot tasks
Policy/model = robot brain being tested
```

## 8. What RoboCasa Is

We clarified:

```text
RoboCasa is another robot simulation benchmark.
```

It focuses more on household/kitchen-style manipulation tasks. It is useful for testing robot policies in more realistic home-like scenes.

Simple version:

```text
RoboCasa = simulated kitchen/home manipulation world
LIBERO = simpler standardized manipulation benchmark
```

## 9. LIBERO Evaluation With SmolVLA

We switched to LIBERO.

We ran:

```text
Policy: lerobot/smolvla_libero
Suite: LIBERO Object
Task: 0
Episodes: 10
```

Result:

```text
Success rate: 70%
Successful episodes: 0, 1, 3, 4, 5, 7, 9
Failed episodes: 2, 6, 8
```

Videos were copied locally to:

```text
/data/downloads/libero_smolvla_object0_10eps/
```

This showed that LIBERO was a much better practical path than VLABench for immediate pretrained policy evaluation.

## 10. RoboCasa On Orin Nano

We also tested RoboCasa on the Orin Nano.

What worked:

```text
Conda env: robocasa310
RoboCasa installed
Lightweight RoboCasa assets downloaded
CloseFridge environment created
Environment reset succeeded
Rendered one frame successfully
```

Smoke frame:

```text
/home/kiran/projects/git/prakashprojects/roboarm/downloads/robocasa_smoke/robocasa_smoke_frame.png
```

But full SmolVLA RoboCasa policy evaluation on Orin was blocked by Python/CUDA compatibility:

```text
Jetson/Orin CUDA PyTorch works well in Python 3.10.
New LeRobot RoboCasa eval code wanted Python 3.12.
Python 3.12 CUDA PyTorch for Jetson was the blocker.
```

Decision:

```text
Use Orin for simulator smoke tests.
Use L4 GPU for full policy evaluation.
```

## 11. Hugging Face Auth And pi0.5 LIBERO

We then tried:

```text
lerobot/pi05_libero_finetuned
```

This model was gated, so Hugging Face authentication was required.

The user pasted a Hugging Face token during the chat. The token is intentionally not saved in this document.

After access was granted, we ran pi0.5 LIBERO evaluations.

## 12. pi0.5 LIBERO Results

The strongest results came from:

```text
Policy: lerobot/pi05_libero_finetuned
```

Completed suites:

| Suite | Tasks | Episodes | Success |
| --- | --- | ---: | ---: |
| LIBERO Object | 0-9 | 100 | 99% |
| LIBERO Spatial | 0-9 | 100 | 97% |
| LIBERO Goal | 0-9 | 100 | 96% |

Videos were organized locally:

```text
/data/downloads/pi05_libero_object_tasks_0to9_10eps/
/data/downloads/pi05_libero_spatial_tasks_0to9_10eps/
/data/downloads/pi05_libero_goal_tasks_0to9_10eps/
```

Combined result across these three suites:

```text
Total episodes: 300
Successful episodes: 292
Combined success rate: 97.33%
```

LIBERO 10 was attempted, but the 16 GB RAM L4 instance became unhealthy during startup/loading.

Recommendation:

```text
Run LIBERO 10 on a larger VM with at least 32 GB system RAM.
```

## 13. LeIsaac Simulator On NVIDIA Brev

We also worked on LeIsaac, a simulator path for SO-101 PickOrange.

Goal command:

```bash
python scripts/environments/teleoperation/teleop_se3_agent.py \
  --task=LeIsaac-SO101-PickOrange-v0 \
  --teleop_device=keyboard \
  --num_envs=1 \
  --device=cuda \
  --enable_cameras \
  --kit_args="--no-window --enable omni.kit.livestream.webrtc"
```

Expected result:

```text
Browser VS Code opens on port 80
Viewer opens at /viewer
LeIsaac PickOrange environment loads
Keyboard teleoperation works
```

Important ports:

```text
80
49100
```

Containers:

```text
isaac-lab-nginx-1
vscode
web-viewer
```

Key fix:

```yaml
web-viewer:
  environment:
    FORCE_WSS: "false"
    SIGNALING_PORT: "49100"
```

The reason was that Isaac/LeIsaac was listening on `49100`, while the viewer was trying to connect using `443` with WSS.

## 14. LeIsaac Session Failed Issue

When the viewer said `session failed`, we suspected WebRTC networking.

Important lesson:

```text
WebRTC can be picky with tunneled ports.
Direct Brev port exposure is better than SSH tunneling for the viewer.
```

The intended route became:

```text
Brev launchable/container setup
Open browser VS Code on port 80
Run LeIsaac inside VS Code terminal
Open /viewer from the same port 80 host
```

## 15. Leader Arm Setup

We then shifted from simulator work to real SO-101 hardware.

The leader arm motor IDs were configured successfully:

```bash
lerobot-setup-motors \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0
```

Motor ID mapping:

```text
gripper       -> 6
wrist_roll    -> 5
wrist_flex    -> 4
elbow_flex    -> 3
shoulder_lift -> 2
shoulder_pan  -> 1
```

Leader calibration:

```bash
lerobot-calibrate \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=my_so101_leader
```

Calibration saved:

```text
/home/prakash-gaikwad/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/my_so101_leader.json
```

During calibration, LeRobot said:

```text
Move all joints except 'wrist_roll'
```

Meaning:

```text
Do not manually spin wrist_roll through its range during calibration.
Move the other joints through their full ranges.
```

## 16. Follower Arm Setup

The follower controller board was connected with USB and power.

First attempts failed because individual motors were not detected:

```text
Motor 'wrist_roll' was not found.
Motor 'wrist_flex' was not found.
```

Those were physical connection / timing / single-motor setup issues.

After reconnecting carefully, follower motor setup succeeded:

```bash
lerobot-setup-motors \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0
```

Follower motor ID mapping:

```text
gripper       -> 6
wrist_roll    -> 5
wrist_flex    -> 4
elbow_flex    -> 3
shoulder_lift -> 2
shoulder_pan  -> 1
```

Follower calibration:

```bash
lerobot-calibrate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_so101_follower
```

Calibration saved:

```text
/home/prakash-gaikwad/.cache/huggingface/lerobot/calibration/robots/so_follower/my_so101_follower.json
```

## 17. First Leader/Follower Teleoperation

At first, trying to run follower alone failed:

```text
Missing required field(s) `teleop` for TeleoperateConfig
```

Reason:

```text
lerobot-teleoperate expects both robot and teleop configs.
```

Once both leader and follower were connected, teleoperation worked:

```bash
lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_so101_follower \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM1 \
  --teleop.id=my_so101_leader
```

Good sign:

```text
SOLeader connected
SOFollower connected
Teleop loop time: about 16.8 ms
60 Hz
```

This meant the leader and follower arms were communicating correctly through LeRobot.

## 18. Overload Error During Disconnect

One teleoperation run ended with:

```text
Failed to write 'Torque_Enable' on id_=4 with '0'
[RxPacketError] Overload error!
```

Meaning:

```text
Motor ID 4, wrist_flex, reported overload while LeRobot was trying to disable torque.
```

This could happen if:

```text
The joint was physically stressed.
The arm was near a hard limit.
The cable or power was unstable.
The joint was resisting load.
```

We then ran teleoperation with:

```bash
--robot.disable_torque_on_disconnect=false
```

That avoided the disconnect-time torque disable error:

```bash
lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_so101_follower \
  --robot.disable_torque_on_disconnect=false \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM1 \
  --teleop.id=my_so101_leader
```

## 19. Later Connection Error On Follower ID 5

A later one-minute test failed during connection:

```text
Failed to write 'Lock' on id_=5 with '1'
There is no status packet!
```

Meaning:

```text
Motor ID 5, wrist_roll, did not respond when LeRobot tried to configure it.
```

Most likely causes:

```text
Loose cable in the motor chain
Power issue
Motor board reset
Wrong port after reconnect
Servo temporarily stuck/unresponsive
```

Recommended checks:

```text
1. Power cycle the follower arm.
2. Reseat the 3-pin cable around wrist_roll.
3. Confirm the follower is still on /dev/ttyACM0.
4. Run a short teleop test again.
5. If the same ID fails repeatedly, inspect that motor/cable more closely.
```

## 20. One-Minute Test Plan

We decided the right way to analyze whether the arms are working neatly is:

```text
Run teleoperation for 60 seconds.
Move only one joint at a time.
Watch whether follower motion matches leader motion.
Check for lag, jitter, wrong direction, hard-limit hits, and gripper behavior.
```

Command:

```bash
lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_so101_follower \
  --robot.disable_torque_on_disconnect=false \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM1 \
  --teleop.id=my_so101_leader \
  --teleop_time_s=60
```

What to check:

```text
shoulder_pan: left/right base movement
shoulder_lift: arm up/down
elbow_flex: elbow bend/extend
wrist_flex: wrist pitch
wrist_roll: wrist rotation
gripper: open/close
```

If one joint is wrong:

```text
Stop testing.
Do not train or record data yet.
Fix calibration, wiring, or mechanical alignment first.
```

## 21. SO-101 Installation Path

We also documented the SO-101 Linux setup:

```text
Install Miniforge/Conda
Create Python 3.12 env
Clone LeRobot
Install Feetech support
Fix USB permissions
Find ports
Set motor IDs
Calibrate leader and follower
Teleoperate
Add camera
Record dataset later
```

Important install command:

```bash
pip install -e ".[feetech]"
```

This is needed because SO-101 uses Feetech serial bus servos.

## 22. SSH And Remote Access

We also discussed setting up SSH public key authentication for:

```bash
ssh kiran@192.168.194.17
```

The goal was to make file copying and remote work easier without typing a password every time.

Common flow:

```bash
ssh-keygen
ssh-copy-id kiran@192.168.194.17
ssh kiran@192.168.194.17
```

## 23. GitHub Repository Work

The user wanted this project stored in:

```text
https://github.com/Gitgai/lerobot
git@github.com:Gitgai/lerobot.git
```

The local LeRobot repo was:

```text
/data/projects/lerobot
```

The project folder was:

```text
/home/prakash-gaikwad/PrakashProjects/testproject
```

We copied the project into the LeRobot repo under:

```text
/data/projects/lerobot/projects/testproject/
```

Then committed and pushed:

```text
Commit: b115e2f2 Add testproject documentation
Remote: git@github.com:Gitgai/lerobot.git
Branch: main
```

We used a dedicated SSH key because HTTPS/OAuth push had permission issues for workflow files:

```text
~/.ssh/gitgai_lerobot_ed25519
```

Unrelated local experiment files in `/data/projects/lerobot` were intentionally not committed.

## 24. Current Project Files

Current project folder:

```text
/home/prakash-gaikwad/PrakashProjects/testproject
```

Current repo copy:

```text
/data/projects/lerobot/projects/testproject
```

Important docs:

```text
README.md
docs/brev_l4_setup.md
docs/leader_follower_workflow.md
docs/libero_results.md
docs/robot_hardware_plan.md
docs/simulator_evaluation.md
docs/full_chat_history.md
setup_smolvla_vlabench_brev.sh
```

## 25. Best Current Understanding

The project has two tracks.

Simulator track:

```text
VLABench was tested but gave 0% and possible action mismatch.
LIBERO worked very well.
pi0.5 LIBERO is the best simulation result so far.
LeIsaac is useful for SO-101-style browser simulation, but WebRTC setup needs careful port handling.
```

Hardware track:

```text
Leader motor setup completed.
Leader calibration completed.
Follower motor setup completed.
Follower calibration completed.
Leader/follower teleoperation connected and ran at about 60 Hz.
Some follower joint communication/overload issues still need careful mechanical and wiring checks.
```

## 26. Recommended Next Steps

Immediate hardware next step:

```text
Run a controlled 60-second leader/follower test.
Move one joint at a time.
Write down which joints behave correctly and which do not.
```

If all joints behave well:

```text
Add camera.
Test camera display.
Record 5 very simple episodes.
Replay one episode.
```

If a joint fails:

```text
Stop.
Power cycle.
Reseat cables.
Check the failing motor ID.
Redo calibration only if the mechanical movement is correct.
```

Do not train yet.

Training should start only after:

```text
Teleoperation is smooth.
Both arms reconnect reliably.
Calibration is repeatable.
Camera view is stable.
Short replay works.
```

## 27. Short Glossary

```text
Policy:
The model/controller that decides robot actions.

Simulator:
The virtual robot environment used for testing.

LIBERO:
A simulator benchmark for robot manipulation tasks.

RoboCasa:
A simulator benchmark for kitchen/home manipulation tasks.

VLABench:
A language-conditioned robot manipulation simulator benchmark.

LeIsaac:
Lightwheel/Isaac-based simulator path for SO-101-style tasks.

Leader arm:
The arm moved by hand by the human.

Follower arm:
The powered robot arm that follows the leader.

Calibration:
The process of teaching LeRobot each joint's range and center.

Teleoperation:
Controlling the follower arm using the leader arm.
```

