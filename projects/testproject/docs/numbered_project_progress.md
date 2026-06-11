# Numbered Project Progress

This document is the short numbered record of what we did from the start of the project until the current SO-101 leader/follower testing stage.

## 1. Project Goal

We started with this goal:

```text
Use LeRobot to evaluate robot policies in simulation, then build a real SO-101 leader/follower arm setup, collect demonstrations, and eventually train/evaluate a policy on the real robot.
```

The practical path became:

1. Test pretrained policies in simulators.
2. Learn which simulators and policies work.
3. Build the SO-101 leader and follower arms.
4. Calibrate both arms.
5. Test leader-to-follower teleoperation.
6. Add laptop camera recording.
7. Record and replay demonstration episodes.
8. Prepare for clean dataset collection and ACT training.

## 2. VLABench SmolVLA Evaluation

We first investigated:

```text
lerobot/smolvla_vlabench
```

We confirmed it is a pretrained/fine-tuned SmolVLA checkpoint for VLABench, not an empty model.

Important conclusion:

```text
Good target: VLABench simulator
Bad target: direct SO-101 hardware use
Reason: VLABench policy expects VLABench observations/actions, not SO-101 motor commands
```

We set up VLABench on a Brev L4 GPU instance and ran:

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
Smoke test ran successfully
Task: select_fruit
Episodes: 1
Success rate: 0%
```

Then we ran 10 episodes:

```text
Episodes: 10
Success rate: 0%
```

Lesson:

```text
The VLABench checkpoint could run, but it was not useful enough for our next goal.
```

## 3. LIBERO Policy Evaluation

After VLABench was not giving useful success, we switched to LIBERO.

We tested:

```text
lerobot/smolvla_libero
lerobot/pi05_libero_finetuned
```

The stronger result came from:

```text
lerobot/pi05_libero_finetuned
```

Results recorded in this project:

```text
LIBERO Object:  99/100 = 99%
LIBERO Spatial: 97/100 = 97%
LIBERO Goal:    96/100 = 96%
```

Videos were copied locally under:

```text
/data/downloads/pi05_libero_object_tasks_0to9_10eps/
/data/downloads/pi05_libero_spatial_tasks_0to9_10eps/
/data/downloads/pi05_libero_goal_tasks_0to9_10eps/
```

Lesson:

```text
LIBERO + pi0.5 was the best simulator result we got.
```

## 4. RoboCasa And Jetson/Orin Notes

We also tried RoboCasa on the Orin Nano.

What worked:

1. Installed RoboCasa in a separate conda environment.
2. Downloaded lightweight RoboCasa assets.
3. Created a `CloseFridge` environment.
4. Reset the environment.
5. Rendered a smoke-test frame.

Important limitation:

```text
RoboCasa simulator smoke test worked on Orin.
Full LeRobot SmolVLA RoboCasa policy evaluation was blocked by Python/CUDA/PyTorch compatibility on Jetson.
```

Decision:

```text
Use L4/L40S GPU machines for heavy simulator policy evaluation.
Use Jetson/Orin for smaller simulator tests or future robot-side inference experiments.
```

## 5. LeIsaac Simulator Work

We investigated LeIsaac for SO-101 PickOrange simulation.

The working setup required:

1. Brev GPU instance.
2. Isaac launchable containers.
3. Browser VS Code on port 80.
4. LeIsaac installed inside the container.
5. Required USD assets downloaded.
6. Web viewer fixed to use WebRTC signaling on port `49100`.

Working command:

```bash
python scripts/environments/teleoperation/teleop_se3_agent.py \
  --task=LeIsaac-SO101-PickOrange-v0 \
  --teleop_device=keyboard \
  --num_envs=1 \
  --device=cuda \
  --enable_cameras \
  --kit_args="--no-window --enable omni.kit.livestream.webrtc"
```

Lesson:

```text
LeIsaac can run the SO-101 PickOrange simulator in the browser, but we paused that path to focus on the real follower arm first.
```

## 6. Local LeRobot Installation For SO-101

We installed LeRobot locally for the SO-101 hardware.

Main local environment:

```text
Conda env: /data/conda-envs/lerobot
LeRobot repo: /data/projects/lerobot
```

Activation:

```bash
conda activate /data/conda-envs/lerobot
cd /data/projects/lerobot
```

We installed the Feetech support needed for SO-101:

```bash
pip install -e ".[feetech]"
```

Later, for camera visualization, we installed:

```bash
pip install -e ".[viz]"
```

This added `rerun-sdk`, which is needed for:

```bash
--display_data=true
```

## 7. Leader Arm Motor Setup

We set up motor IDs on the leader arm.

Command:

```bash
lerobot-setup-motors \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0
```

Motor IDs assigned:

```text
shoulder_pan   id 1
shoulder_lift  id 2
elbow_flex     id 3
wrist_flex     id 4
wrist_roll     id 5
gripper        id 6
```

## 8. Follower Arm Motor Setup

We set up motor IDs on the follower arm.

Command:

```bash
lerobot-setup-motors \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0
```

There were temporary connection failures during setup:

```text
Motor 'wrist_roll' was not found
Motor 'wrist_flex' was not found
```

After reseating/checking and retrying, all follower motors were assigned:

```text
shoulder_pan   id 1
shoulder_lift  id 2
elbow_flex     id 3
wrist_flex     id 4
wrist_roll     id 5
gripper        id 6
```

Lesson:

```text
During setup-motors, only one motor should be connected at a time.
If a motor is not found, check power, cable direction, connector seating, and retry.
```

## 9. Current USB Port Mapping

The current normal mapping is:

```text
Leader arm:   /dev/ttyACM0
Follower arm: /dev/ttyACM1
```

The stable serial paths are:

```text
Leader:
/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14029688-if00

Follower:
/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00
```

## 10. Leader And Follower Calibration

Leader calibration command:

```bash
lerobot-calibrate \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=my_so101_leader
```

Follower calibration command:

```bash
lerobot-calibrate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower
```

Calibration files:

```text
Leader:
/home/prakash-gaikwad/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/my_so101_leader.json

Follower:
/home/prakash-gaikwad/.cache/huggingface/lerobot/calibration/robots/so_follower/my_so101_follower.json
```

Important calibration rule:

```text
Move all joints except wrist_roll during calibration.
```

Meaning:

```text
wrist_roll zero is taken from the initial middle pose.
So both wrists must be physically straight/aligned before pressing Enter at the first calibration prompt.
```

## 11. First Successful Leader/Follower Teleoperation

Command:

```bash
lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_so101_follower \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM1 \
  --teleop.id=my_so101_leader
```

This connected both arms and ran around 60 Hz.

Later, after port mapping settled, the main command became:

```bash
lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower \
  --robot.disable_torque_on_disconnect=false \
  --robot.max_relative_target=5 \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=my_so101_leader
```

## 12. Why We Added `max_relative_target`

We added:

```bash
--robot.max_relative_target=5
```

Meaning:

```text
Do not command any follower joint to jump more than 5 degrees from its current position in one control step.
```

Why:

1. The arms had mismatch problems during early testing.
2. Wrist motor ID 5 had intermittent overload/missing status behavior.
3. Sudden jumps can damage hardware or cause unsafe movement.

Current recommendation:

```text
Keep max_relative_target=5 while testing and recording first datasets.
Later try 10 only after the arm behaves reliably.
Do not remove it yet.
```

## 13. Wrist Roll / Motor ID 5 Issue

We saw intermittent problems around motor ID 5:

```text
wrist_roll
id 5
```

Symptoms included:

```text
Missing motor ID 5
Overload error when disabling torque
Large wrist_roll mismatch between leader and follower
```

After physical checking and retesting, motor 5 came back and later position checks showed the wrist was aligned.

Important lesson:

```text
The old issue was not purely software.
It was likely physical alignment, joint stress, or intermittent connector/position stress.
```

## 14. Latest Position Check

The latest live position check showed all joints matching well:

```text
shoulder_pan   GOOD
shoulder_lift  GOOD
elbow_flex     GOOD
wrist_flex     GOOD
wrist_roll     GOOD
gripper        GOOD
```

Measured mismatch was less than 1 degree for every joint.

Conclusion:

```text
The leader and follower are currently aligned well.
```

## 15. Safety Clamping Warning

We investigated this warning:

```text
Relative goal position magnitude had to be clamped to be safe
```

Meaning:

```text
The leader requested a target too far from the follower's current joint position.
LeRobot reduced the command to a smaller safe movement.
```

The latest pasted log showed:

```text
Traceback: 0
Overload: 0
ConnectionError: 0
Clamp warnings: 1628
```

Most warnings were for:

```text
shoulder_lift
```

Conclusion:

```text
That run did not crash.
It was mostly safety limiting because the starting poses were probably not aligned.
```

Fix before each teleop run:

1. Put leader and follower in similar starting poses.
2. Start teleop.
3. Move slowly for the first 5-10 seconds.
4. If clamping continues constantly, stop and inspect that joint.

## 16. Laptop Camera Test

We tested the laptop camera with LeRobot.

Camera config:

```bash
--robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}"
```

Camera visualization command:

```bash
lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower \
  --robot.disable_torque_on_disconnect=false \
  --robot.max_relative_target=5 \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=my_so101_leader \
  --display_data=true
```

This opened Rerun visualization showing:

```text
action.*       = leader commands
observation.*  = follower measured state
observation.front = camera video
```

## 17. First Local Dataset Recording

We recorded a local dataset:

```text
Dataset root:
/data/lerobot_datasets/so101_camera_test

Repo id:
local/so101_camera_test
```

Dataset summary:

```text
Episodes: 5
Frames: 8956
FPS: 30
Video duration: about 298.5 seconds
Video size: about 121 MB
Camera: observation.images.front
Action shape: 6
State shape: 6
```

Split episode videos were created at:

```text
/data/downloads/so101_camera_test_episodes/episode_0.mp4
/data/downloads/so101_camera_test_episodes/episode_1.mp4
/data/downloads/so101_camera_test_episodes/episode_2.mp4
/data/downloads/so101_camera_test_episodes/episode_3.mp4
/data/downloads/so101_camera_test_episodes/episode_4.mp4
```

## 18. Dataset Replay

Replay command:

```bash
lerobot-replay \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower \
  --robot.disable_torque_on_disconnect=false \
  --dataset.repo_id=local/so101_camera_test \
  --dataset.root=/data/lerobot_datasets/so101_camera_test \
  --dataset.episode=0
```

Replay results:

```text
Episode 0: replayed successfully
Episode 1: replayed successfully
Episode 2: replayed successfully
Episode 3: replayed successfully after motor 5 recovered
Episode 4: earlier failed when motor ID 5 was missing
```

Lesson:

```text
Replay is the best check that recorded actions are usable by the follower arm.
```

## 19. GitHub Project Archive

We created and pushed project documentation to:

```text
git@github.com:Gitgai/lerobot.git
```

Project docs live in:

```text
/home/prakash-gaikwad/PrakashProjects/testproject/docs
```

The project was also synced into:

```text
/data/projects/lerobot/projects/testproject
```

## 20. Current Status

Current status:

```text
LeRobot installed locally
Leader arm motor IDs set
Follower arm motor IDs set
Leader calibrated
Follower calibrated
Teleoperation works
Laptop camera works
Rerun visualization works
First 5-episode local dataset recorded
Replay mostly verified
Current leader/follower joint positions match well
```

Main remaining concern:

```text
Watch motor ID 5 / wrist_roll for intermittent overload or missing status.
```

## 21. What We Should Do Next

Next recommended step:

```text
Record a clean 5-episode dataset again, with both arms aligned before starting.
```

Use:

```bash
conda activate /data/conda-envs/lerobot
cd /data/projects/lerobot

rm -rf /data/lerobot_datasets/so101_pick_test

lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower \
  --robot.disable_torque_on_disconnect=false \
  --robot.max_relative_target=5 \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=my_so101_leader \
  --display_data=true \
  --dataset.repo_id=local/so101_pick_test \
  --dataset.root=/data/lerobot_datasets/so101_pick_test \
  --dataset.num_episodes=5 \
  --dataset.single_task="Pick up the object and place it in the target area" \
  --dataset.push_to_hub=false
```

After recording:

1. Watch the episode videos.
2. Replay all 5 episodes.
3. Keep only clean successful demonstrations.
4. If 5 episodes replay cleanly, record 30-50 episodes for ACT training.

## 22. Operating Rule Going Forward

Before any teleoperation or recording:

1. Check USB ports.
2. Check power.
3. Put leader and follower in the same starting pose.
4. Keep `max_relative_target=5`.
5. Move slowly for the first 5-10 seconds.
6. Stop if warnings continue constantly or a joint feels stressed.

This keeps the hardware safe while we collect useful data.
