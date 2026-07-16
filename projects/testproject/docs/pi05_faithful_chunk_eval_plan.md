# Pi05 Faithful Chunk Evaluation Plan

## 1. Purpose

Test the trained Pi05 orange policy in a way that matches how Pi0/Pi0.5 action-chunk policies are intended to be executed.

The previous 20-step tests were useful hardware checks, but they were not a fair policy evaluation because they re-queried the policy every step and executed only the first action from each returned 50-action chunk.

This plan tests whether the policy's planned action trajectory actually moves the SO-101 toward the orange when sequential actions from the same chunk are executed.

## 2. Key Correction

Pi05 returns an action chunk:

```text
action_0
action_1
...
action_49
```

The earlier runner mostly did this:

```text
observe
request 50 actions
execute only action_0
observe again
request 50 new actions
execute only action_0
...
```

That can destroy the policy's intended reach trajectory.

The corrected test should do this:

```text
observe
request 50 actions
execute action_0..action_9
observe again
request next 50 actions
execute action_0..action_9
...
```

## 3. Safety Position

Do not use the outer behavior clamp:

```text
--max-step-deg
--gripper-max-step
```

Those clamps are not part of the faithful test.

Keep only the LeRobot robot-level movement guard:

```text
--robot-max-relative-target 8
```

This guard does not steer the policy toward the orange. It only limits a single unsafe joint jump sent to the motors.

## 4. Pre-Run Setup

1. Place the orange in the same position as the training/eval setup.
2. Put the robot in the same start pose used in the previous tests.
3. Confirm the workspace is clear.
4. Keep hand near power/off switch.
5. Stop the Pi timelapse service:

```bash
ssh raspi@192.168.1.17 'sudo systemctl stop timelapse.service'
```

6. Start the wrist proxy:

```bash
.venv/bin/python tools/pi_wrist_proxy.py --pi-host raspi@192.168.1.17 --pi-ip 192.168.1.17
```

7. Start the RunPod tunnel:

```bash
ssh -N -L 8080:127.0.0.1:8080 -i ~/.ssh/runpod_ed25519 -p 40120 root@213.192.2.123
```

8. Confirm the wrist stream is fresh:

```bash
curl -fsS --max-time 3 http://127.0.0.1:8092/status
```

Expected:

```text
"ok": true
```

9. Confirm the local robot and cameras are free:

```bash
id
ls -l /dev/serial/by-id /dev/ttyACM* 2>/dev/null
fuser -v /dev/video0 /dev/video2 2>&1 || true
```

Expected:

```text
user is in dialout
follower serial exists
front/top cameras are not held by another process
```

10. Confirm the RunPod policy server is already loaded with the intended checkpoint.

Only use `--skip-policy-setup` when the server is already running this exact policy:

```text
/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model
```

If unsure, remove `--skip-policy-setup` from the dry run and main run so the client explicitly sends setup instructions.

## 5. Dry Chunk Inspection

Before moving, request one full chunk and log all 50 actions.

```bash
.venv/bin/python scripts/pi05_faithful_chunk_test.py \
  --server-address 127.0.0.1:8080 \
  --policy /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model \
  --policy-type pi05 \
  --policy-device cuda \
  --actions-per-chunk 50 \
  --task "pick up the orange and move it to another place" \
  --timeout-s 600 \
  --skip-policy-setup \
  --camera-fill-mode top-front-wrist \
  --wrist-camera-url http://127.0.0.1:8092/frame \
  --dry-run \
  --action-log logs/so101/pi05_faithful_chunk_dry_run.actions.csv
```

Success criteria:

```text
DRY_RUN_OK actions_logged=50
```

Review:

```text
logs/so101/pi05_faithful_chunk_dry_run.actions.csv
```

Look for obvious impossible jumps or nonsensical gripper behavior.

Also compute basic chunk deltas before moving:

```text
max absolute difference from current state for each joint
max difference between consecutive actions for each joint
whether the 50-action chunk trends toward the orange or only oscillates
```

If the first chunk contains huge discontinuities, do not run the motion test yet.

## 6. Main Faithful Chunk Evaluation

Run the real test with sequential chunk execution:

```bash
mkdir -p logs/so101

.venv/bin/python scripts/pi05_closed_loop_eval.py \
  --server-address 127.0.0.1:8080 \
  --policy /workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model \
  --policy-type pi05 \
  --policy-device cuda \
  --actions-per-chunk 50 \
  --task "pick up the orange and move it to another place" \
  --timeout-s 600 \
  --skip-policy-setup \
  --camera-fill-mode top-front-wrist \
  --wrist-camera-url http://127.0.0.1:8092/frame \
  --actions-per-query 25 \
  --max-steps 300 \
  --robot-max-relative-target 8 \
  --settle-s 0.15 \
  --record-layout mosaic \
  --record-video logs/so101/pi05_faithful_chunk_eval_300step.mp4 \
  --action-log logs/so101/pi05_faithful_chunk_eval_300step.actions.csv \
  --i-understand-this-moves-robot
```

Use timestamped filenames when running more than once to avoid overwriting results:

```text
logs/so101/pi05_faithful_chunk_eval_300step_YYYYMMDD_HHMMSS.mp4
logs/so101/pi05_faithful_chunk_eval_300step_YYYYMMDD_HHMMSS.actions.csv
```

## 7. Why These Settings

`actions-per-query=25`:

Executes half of each 50-action Pi05 trajectory before re-observing. This lets the policy follow more of its planned reach motion than the 10-step test, while still giving the cameras a chance to correct before the full chunk is exhausted.

`max-steps=300`:

Gives about 12 policy queries at 25 actions per query. This is a longer horizon for observing whether the arm reaches toward the orange, approaches the gripper, closes, and begins lift/move behavior.

`robot-max-relative-target=8`:

Keeps the script's default robot-level jump guard. Do not raise this to 12 for this plan. This guard does not steer the policy; it only limits a single unexpectedly large motor command.

`record-layout=mosaic`:

Records top, front, and wrist together so failure analysis can distinguish policy failure from camera/view mismatch.

Important limitation:

This script is more faithful than the first-action runner, but it is still not full official LeRobot RTC. It executes a fixed number of actions from each chunk, then re-observes. It does not asynchronously generate the next chunk while executing the current one, and it does not use RTC inpainting/guidance.

So the result answers:

```text
Does sequential chunk execution work better than first-action-only execution?
```

It does not fully answer:

```text
How would this policy behave under official LeRobot RTC deployment?
```

## 8. Stop Conditions

Stop immediately if:

```text
arm drives toward table
arm moves away from workspace
wrist twists aggressively
gripper jams into orange/table
camera feed freezes or goes black
network/tunnel stalls while motion continues badly
motor overload or abnormal sound appears
```

## 9. Result Categories

Good:

```text
gripper moves toward orange
approach direction is coherent
gripper closes near orange
orange is touched, grasped, or moved
```

Partial:

```text
arm approaches orange but misses height/angle
gripper closes too early or too late
arm reaches nearby but does not grasp
```

Bad:

```text
arm oscillates around start pose
arm moves away from orange
gripper behavior is unrelated to object
no progress after 150 steps
```

## 10. Decision After The Run

If Good:

Run 2-3 more eval episodes with the same setup and measure repeatability.

If Partial:

Collect 10-20 focused correction demos from the same starting pose and orange position, then continue fine-tuning from the current checkpoint.

If Bad:

Do not remove all restrictions and keep pushing. Instead inspect:

```text
camera role mismatch
start pose mismatch
orange position mismatch
action chunk trajectory
training data coverage
whether current checkpoint overfit/underfit
```

Then collect more demonstrations or adjust preprocessing before further motion tests.

## 10.1 Post-Run Analysis Checklist

After every run, inspect:

```text
1. mosaic video start/middle/end frames
2. action CSV commanded vs sent rows
3. how often robot-max-relative-target changed the commanded action
4. whether gripper distance to orange decreased over time
5. whether gripper closed near the orange or away from it
6. whether top/front/wrist views were correct throughout the run
```

If the robot-level guard clamps many actions, treat the run as partially constrained and do not call it fully faithful.

If the video shows no progress but the action log shows coherent reach commands, investigate robot calibration or action/state scaling.

If the action log itself is incoherent, investigate model/data/training.

## 11. Artifacts To Save

Save these for every run:

```text
video: logs/so101/*.mp4
actions: logs/so101/*.actions.csv
terminal output
wrist status output
policy checkpoint path
exact command
```

## 12. Final Evaluation Question

This run answers:

```text
Does the trained Pi05 policy move through its planned chunk trajectory toward the orange when executed faithfully?
```

It does not answer:

```text
Can an unrestricted raw target command move the arm quickly?
```

The first question is the correct policy evaluation question.

## 13. Next Test If This Works

If the faithful chunk run is promising, the next engineering target is official LeRobot deployment:

```text
lerobot-rollout with inference.type=rtc
or a Pi05-specific async client using the official action queue
```

Do not use `scripts/async_client_3cam.py` as-is for Pi05 because it is currently hardcoded to:

```text
--policy_type=act
```

Before official RTC, fix or replace that script so it uses:

```text
--policy_type=pi05
--pretrained_name_or_path=/workspace/outputs/pi05_base_to_orange49_expert/checkpoints/005000/pretrained_model
```
