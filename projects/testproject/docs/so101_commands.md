# SO-101 Commands

This document keeps the commands we use most often for the SO-101 leader/follower setup.

## 1. Activate LeRobot Environment

The easiest workflow uses the project launcher:

```bash
cd /home/prakash-gaikwad/PrakashProjects/testproject
./bin/so101 status
```

The launcher automatically activates:

```text
/data/conda-envs/lerobot
```

If you want to run the Python helper directly:

```bash
conda activate /data/conda-envs/lerobot
cd /home/prakash-gaikwad/PrakashProjects/testproject
```

## 2. Easy Python Runner

Use this helper so you do not need to copy long commands every time:

```bash
python scripts/so101_runner.py ports
```

Or with the shorter launcher:

```bash
./bin/so101 ports
```

Run teleoperation until you stop it:

```bash
./bin/so101 teleop
```

Run teleoperation for 60 seconds:

```bash
./bin/so101 teleop --seconds 60
```

Run teleoperation with laptop camera viewer:

```bash
./bin/so101 teleop --camera
```

Try faster movement limit:

```bash
./bin/so101 teleop --max-relative-target 10
```

Run without `max_relative_target`:

```bash
./bin/so101 teleop --no-max-relative-target
```

Record 5 fresh episodes:

```bash
./bin/so101 record --episodes 5 --delete
```

Replay one episode:

```bash
./bin/so101 replay 0
```

Calibrate:

```bash
./bin/so101 calibrate-follower
./bin/so101 calibrate-leader
```

Check current setup status:

```bash
./bin/so101 status
```

Check leader/follower joint positions:

```bash
./bin/so101 positions
```

List recent logs:

```bash
./bin/so101 logs
```

Show the end of the latest log:

```bash
./bin/so101 tail-log
```

Inspect a pretrained Hugging Face policy without moving the robot:

```bash
./bin/so101 inspect-policy zz4321/so101_pi05
```

The runner uses the current normal ports:

```text
Leader arm:   /dev/ttyACM0
Follower arm: /dev/ttyACM1
```

It also uses:

```text
Dataset: /data/lerobot_datasets/so101_pick_test
Camera: laptop camera index 0, 640x480, 30 FPS
Default max relative target: 5
Logs: /home/prakash-gaikwad/PrakashProjects/testproject/logs/so101
```

The settings live here:

```text
/home/prakash-gaikwad/PrakashProjects/testproject/config/so101.json
```

Edit that file if ports, camera index, dataset path, or task text changes.

## 3. Logging

The helper writes logs for robot sessions here:

```text
logs/so101/
```

Each log includes:

1. Timestamp.
2. Working directory.
3. Full command.
4. LeRobot output.
5. Return code.

Useful commands:

```bash
./bin/so101 logs
./bin/so101 tail-log
./bin/so101 tail-log --lines 150
```

Logging is useful because it lets us inspect:

```text
Clamp warnings
Overload errors
Connection errors
Replay failures
Recording problems
```

## 4. Position Check

Use this before and after teleoperation:

```bash
./bin/so101 positions
```

It prints:

```text
motor              leader     follower     diff(follower-leader)    status
shoulder_pan       ...
shoulder_lift      ...
elbow_flex         ...
wrist_flex         ...
wrist_roll         ...
gripper            ...
```

Status meaning:

```text
GOOD     = leader and follower are close
OK-ish   = small mismatch
MISMATCH = inspect alignment, calibration, or that joint
```

## 5. Check USB Ports

Current normal mapping:

```text
Leader arm:   /dev/ttyACM0
Follower arm: /dev/ttyACM1
```

Check connected boards:

```bash
ls -l /dev/ttyACM*
ls -l /dev/serial/by-id/
```

## 6. Teleoperate Without Timer

Use this for normal leader-to-follower testing. It runs until you press `Ctrl+C`.

```bash
cd /data/projects/lerobot

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

## 7. Teleoperate For 60 Seconds

```bash
cd /data/projects/lerobot

lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower \
  --robot.disable_torque_on_disconnect=false \
  --robot.max_relative_target=5 \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=my_so101_leader \
  --teleop_time_s=60
```

## 8. Teleoperate With Laptop Camera Viewer

This opens Rerun visualization and shows the camera plus joint/action plots.

```bash
cd /data/projects/lerobot

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

## 9. Record 5 Clean Episodes

This deletes the previous `so101_pick_test` dataset and records a fresh 5-episode dataset.

```bash
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

## 10. Replay One Episode

Change `--dataset.episode=0` to replay another episode.

```bash
cd /data/projects/lerobot

lerobot-replay \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower \
  --robot.disable_torque_on_disconnect=false \
  --dataset.repo_id=local/so101_pick_test \
  --dataset.root=/data/lerobot_datasets/so101_pick_test \
  --dataset.episode=0
```

## 11. Calibrate Follower

Type `c` when prompted if you want to run a fresh calibration.

```bash
cd /data/projects/lerobot

lerobot-calibrate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower
```

## 12. Calibrate Leader

Type `c` when prompted if you want to run a fresh calibration.

```bash
cd /data/projects/lerobot

lerobot-calibrate \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=my_so101_leader
```

## 13. Safety Notes

Keep this option while testing:

```bash
--robot.max_relative_target=5
```

It prevents large sudden joint jumps.

After the arm is moving reliably, you can test a slightly faster limit:

```bash
--robot.max_relative_target=10
```

Use `10` only when:

1. Leader and follower start in similar poses.
2. All joints are tracking smoothly.
3. There are no overload errors.
4. Clamp warnings are not constant.

If the arm jerks, overloads, or feels stressed, go back to:

```bash
--robot.max_relative_target=5
```

To remove this limit completely:

```bash
./bin/so101 teleop --no-max-relative-target
```

Use this only when:

1. Leader and follower positions are already `GOOD`.
2. The workspace is clear.
3. You are ready to stop immediately.
4. You move the leader slowly at first.

Without this limit, the follower may receive large target jumps if the arms become misaligned.

Before running teleoperation or recording:

1. Put leader and follower in similar starting poses.
2. Start the command.
3. Move slowly for the first 5-10 seconds.
4. Stop if clamp warnings continue constantly.

## 14. Inspect Pretrained Pi05 Policies

This command only reads small Hugging Face config files. It does not load full model weights and does not connect to the robot arm.

```bash
./bin/so101 inspect-policy zz4321/so101_pi05
./bin/so101 inspect-policy nuffnuff/pi05-so101-finetuned_1
./bin/so101 inspect-policy aswinkumar99/LeRobot-SO101-Pi05-universal-all_bs32_s20000
```

Use it before trying any pretrained Pi05 model.

It reports:

```text
policy type
model size
state shape
action shape
expected camera names
compatibility with our current SO-101 config
```
