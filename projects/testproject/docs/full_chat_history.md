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
bin/so101
config/so101.json
scripts/so101_runner.py
docs/brev_l4_setup.md
docs/numbered_project_progress.md
docs/leader_follower_workflow.md
docs/libero_results.md
docs/robot_hardware_plan.md
docs/simulator_evaluation.md
docs/so101_commands.md
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
Laptop camera recording works.
Five local SO-101 demonstration episodes were recorded.
All five episodes replayed successfully on the follower arm.
```

## 26. SO-101 Runner Workflow

To avoid repeatedly copying long LeRobot commands, we created a project CLI:

```text
scripts/so101_runner.py
bin/so101
config/so101.json
```

The wrapper stores the important local settings:

```text
Leader port: /dev/ttyACM0
Follower port: /dev/ttyACM1
Leader id: my_so101_leader
Follower id: my_so101_follower
Dataset root: /data/lerobot_datasets/so101_pick_test
Dataset repo id: local/so101_pick_test
Camera: opencv index 0, 640x480, 30 FPS
```

Important commands:

```bash
./bin/so101 status
./bin/so101 positions
./bin/so101 teleop
./bin/so101 teleop --no-max-relative-target
./bin/so101 record --episodes 5 --delete --no-max-relative-target
./bin/so101 replay 0
./bin/so101 logs
./bin/so101 tail-log
```

The runner writes command logs to:

```text
logs/so101/
```

It was also improved so `positions` handles partial read failures cleanly. Instead of a raw traceback, it reports whether the leader or follower read failed and gives next checks.

## 27. Safety Limiter Discussion

The normal teleoperation command uses:

```bash
--robot.max_relative_target=5
```

This tells LeRobot to clamp large sudden target jumps. It is a software safety limiter. When the leader and follower poses differ a lot, LeRobot prevents a big instant movement and prints clamp warnings.

We tested both modes:

```bash
./bin/so101 teleop
./bin/so101 teleop --no-max-relative-target
```

With the limiter enabled, the robot is safer but clamp warnings can appear when the arm poses differ.

With the limiter removed, the follower follows the recorded/leader targets more directly, but sudden large differences can be riskier. We used it only after the arms were physically aligned and the position check looked good.

## 28. Arm Position Checks

We repeatedly used:

```bash
./bin/so101 positions
```

This compares the leader and follower joint readings:

```text
shoulder_pan
shoulder_lift
elbow_flex
wrist_flex
wrist_roll
gripper
```

Good aligned result after the no-limiter teleop test:

```text
shoulder_pan   GOOD
shoulder_lift  GOOD
elbow_flex     GOOD
wrist_flex     GOOD
wrist_roll     GOOD
gripper        GOOD
```

After replaying all episodes, most joints were still good, but wrist_roll and later gripper differed from the leader's current physical pose. We decided to leave that for later because replay only drives the follower; the leader is not involved during replay, so leader/follower mismatch after replay does not automatically mean replay failed.

## 29. Camera Recording Setup

The laptop camera was tested with LeRobot using:

```bash
--robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}"
--display_data=true
```

At first, display failed because `rerun-sdk` was missing:

```text
ImportError: 'rerun-sdk' is required but not installed.
```

The fix was:

```bash
cd /data/projects/lerobot
pip install -e ".[viz]"
```

After that, Rerun opened and showed:

```text
Camera image stream
Observation joint positions
Action joint positions
Timeline
```

The camera confirmed that laptop camera recording works.

## 30. Five Episode Dataset Recording

We recorded a fresh five-episode dataset with:

```bash
./bin/so101 record --episodes 5 --delete --no-max-relative-target
```

The first recording was stopped and deleted because we wanted a clean run. The fresh run completed successfully:

```text
Episodes: 5
Frames: 8948
FPS: 30
Size: 123 MB
Return code: 0
```

Dataset location:

```text
/data/lerobot_datasets/so101_pick_test
```

Important dataset files:

```text
data/chunk-000/file-000.parquet
meta/episodes/chunk-000/file-000.parquet
meta/info.json
meta/stats.json
meta/tasks.parquet
videos/observation.images.front/chunk-000/file-000.mp4
```

The combined camera video was split into easier-to-watch episode files:

```text
/data/downloads/so101_pick_test_episodes/episode_0.mp4
/data/downloads/so101_pick_test_episodes/episode_1.mp4
/data/downloads/so101_pick_test_episodes/episode_2.mp4
/data/downloads/so101_pick_test_episodes/episode_3.mp4
/data/downloads/so101_pick_test_episodes/episode_4.mp4
```

Episode timing from metadata:

```text
episode 0: 0.000000s   to 59.700000s
episode 1: 59.700000s  to 119.433333s
episode 2: 119.433333s to 179.133333s
episode 3: 179.133333s to 238.733333s
episode 4: 238.733333s to 298.266667s
```

## 31. Replay Of Episodes 0-4

We replayed all five episodes:

```bash
./bin/so101 replay 0
./bin/so101 replay 1
./bin/so101 replay 2
./bin/so101 replay 3
./bin/so101 replay 4
```

All five replay commands completed cleanly:

```text
Follower connected.
Episode replayed.
Follower disconnected.
No software crash.
No overload error.
No connection failure.
```

Replay logs:

```text
logs/so101/20260603_162654_replay_ep0.log
logs/so101/20260603_162810_replay_ep1.log
logs/so101/20260603_162926_replay_ep2.log
logs/so101/20260603_163041_replay_ep3.log
logs/so101/20260603_163203_replay_ep4.log
```

This proved the basic loop:

```text
teleoperate -> record dataset -> save video/data -> replay follower motion
```

## 32. Episode Video Review

We generated contact sheets from the five episode videos:

```text
/data/downloads/so101_pick_test_review/episode_0_contact.jpg
/data/downloads/so101_pick_test_review/episode_1_contact.jpg
/data/downloads/so101_pick_test_review/episode_2_contact.jpg
/data/downloads/so101_pick_test_review/episode_3_contact.jpg
/data/downloads/so101_pick_test_review/episode_4_contact.jpg
```

The review found:

```text
Good:
- Robot arm is visible.
- Object is visible in many frames.
- Target box is visible.
- The five episodes recorded correctly.

Needs improvement:
- Human hands/body appear in multiple episodes.
- Object and target are not always the center of the camera view.
- Workspace has some visual clutter.
- Laptop camera side angle is usable for testing but not ideal for final training.
```

Conclusion:

```text
This dataset is good as a smoke test.
It should not be treated as the final training dataset yet.
```

## 33. Public Data And Models Instead Of 50 Episodes

The user asked whether we can avoid recording 50 local episodes by using LeRobot/Hugging Face data.

The answer:

```text
Yes, public SO-101 datasets and pretrained SO-101 policies can help.
No, they do not fully replace local data unless the task, camera angle, object, target, and robot setup match closely.
```

Examples discussed:

```text
Public datasets:
- aswinkumar99/LeRobot-SO101-Pick-Place
- edge-inference/smolvla-so101-pick-orange-data

Pretrained/published policy examples:
- edge-inference/smolvla-so101-pick-orange
- SO-101 ACT/SmolVLA pick-place variants on Hugging Face
```

Best current plan:

```text
Use our 5 episodes to verify the pipeline.
Record 5-10 cleaner local episodes with a better camera view.
Then try a pretrained or fine-tuned SO-101 model path.
Only collect 30-50 episodes if the small-data/pretrained route fails.
```

The important practical point:

```text
For a reliable real-arm policy, at least some local data is still needed because our camera, table, object, lighting, and arm mechanics are unique.
```

## 34. Recommended Next Steps

Immediate next step:

```text
Record another small clean dataset, around 5-10 episodes.
```

Before recording:

```text
Move the camera closer or angle it toward the object, gripper, and target.
Keep human hands/body out of the view after recording starts.
Keep object and target in fixed positions.
Clean visual clutter from the table.
Make each episode a complete task attempt.
```

Then:

```text
Split videos into per-episode clips.
Review contact sheets.
Replay at least one or two episodes.
Compare quality against the first smoke-test dataset.
```

Training should start only after:

```text
Teleoperation remains smooth.
Camera view is stable and task-focused.
Recorded episodes are clean.
Replay works.
Dataset has enough good examples or is combined with a suitable public/pretrained model.
```

## 35. Pi05 On L4 Remote-Brain Plan

The user decided they may not want to continue with ACT and asked how to proceed with a pretrained Pi05 model on an L4 GPU.

We documented a new plan:

```text
docs/pi05_l4_remote_plan.md
```

The core idea:

```text
local laptop = SO-101 body controller
Brev L4 GPU  = Pi05 model brain
```

The control loop would be:

```text
1. Laptop reads camera image.
2. Laptop reads SO-101 joint state.
3. Laptop sends image + state + task text to the L4 server.
4. L4 runs Pi05.
5. L4 sends back a chunk of future actions.
6. Laptop checks safety limits.
7. Laptop sends safe actions to the follower arm.
```

Important safety decision:

```text
The L4 should not directly control the motor bus.
The local laptop must remain the final safety gate.
```

Candidate Pi05 models already inspected:

```text
zz4321/so101_pi05
nuffnuff/pi05-so101-finetuned_1
aswinkumar99/LeRobot-SO101-Pi05-universal-all_bs32_s20000
felixmayor/pi05_so101_orange_cube
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

Main blocker:

```text
our setup currently has one front camera
the strongest pretrained Pi05 candidates expect two or three cameras
```

Recommended next technical step:

```text
Add an inspect-policy command to the SO-101 runner.
Use it to compare policy camera/state/action requirements with our real setup.
Then load/test Pi05 on L4 without moving the robot.
```

## 36. Short Glossary

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

Dataset:
The saved camera observations, robot states, actions, timestamps, and task labels from demonstrations.

Replay:
Sending saved dataset actions back to the follower arm to verify that the recorded motion can be reproduced.

Rerun:
The visualization app used by LeRobot to show camera frames, robot observations, and action/state plots.
```
