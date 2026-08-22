# Pi05 Policy/Inference Debug - 2026-07-01

## Question

Why does replay of our recorded episodes pick/move the orange, but the fine-tuned Pi05 policy does not reliably pick the orange on the real arm?

## What We Can Prove

1. Replay proves the robot/action side works.

   We replayed several cleaned dataset episodes on the real follower arm. The user confirmed the replay actually picked/moved the orange. Replay does not use Pi05 or cameras; it only sends the recorded action trajectory to the follower. This proves:
   - the follower can physically execute the dataset actions
   - calibration/action units are good enough for these recorded trajectories
   - the cleaned dataset actions are not impossible for the robot

2. The fine-tuned checkpoint format matches the cleaned dataset.

   Model:

   ```text
   /data/models/pi05_so101_orange_move_cleaned_3000/pretrained_model
   ```

   It expects:

   ```text
   observation.state: 6 joints
   observation.images.front: 3 x 480 x 640
   observation.images.top:   3 x 480 x 640
   observation.images.wrist: 3 x 480 x 640
   action: 6 joints
   ```

   Cleaned dataset:

   ```text
   /data/lerobot_datasets/so101_pick_orange_move_cleaned
   ```

   It contains the same camera names and the same action/state joint names:

   ```text
   shoulder_pan.pos
   shoulder_lift.pos
   elbow_flex.pos
   wrist_flex.pos
   wrist_roll.pos
   gripper.pos
   ```

3. The camera JPEG path is not using the wrong RGB/BGR color order.

   Both inference and recording HTTP camera paths decode JPEG with OpenCV and convert BGR to RGB:

   ```python
   cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
   ```

   So the obvious "orange becomes blue" bug is not present.

4. The current cleaned dataset still has start idle.

   I measured when each cleaned episode first moves meaningfully from the starting state. Result:

   ```text
   median first meaningful movement: about 2.9 s
   28 / 30 episodes first move after 2 s
   24 / 30 episodes have almost zero arm movement in the first 50 frames
   ```

   Pi05 action chunks are 50 actions. At 30 FPS, 50 actions is about 1.67 seconds. That means many training examples start with a whole first chunk that looks like "do almost nothing".

5. The fine-tuned task text and eval default were mismatched.

   The cleaned dataset task is:

   ```text
   pick up the orange and move it to another place
   ```

   But the old eval scripts defaulted to:

   ```text
   grasp the orange
   ```

   I changed the defaults in:

   ```text
   scripts/pi05_closed_loop_eval.py
   scripts/pi05_faithful_chunk_test.py
   ```

   to match the cleaned dataset task.

## What This Means

The most concrete policy-side problem is not the robot motor path. It is that the policy was trained on demonstrations where the beginning often says:

```text
image/state: start pose, orange visible
action: hold still or tiny motion
```

At inference, the policy sees the real start pose and can reasonably output tiny/holding motion or unclear motion. Because it has `n_obs_steps=1`, it does not know "we are now 3 seconds into the episode". It only sees the current image/state. If the same kind of image/state was paired with idle actions during training, the policy can learn the wrong first move.

This also explains why simply increasing steps to 100, 300, or 600 did not solve it. More time does not force the model to enter the reach phase if the current observation keeps mapping to weak/idle/incorrect actions.

## Correct Next Fix

Build a second cleaned dataset that removes the idle beginning of each episode, not only the idle/rest tail.

For each episode:

```text
old cleaned episode:
idle start -> reach -> grasp -> lift -> move/drop

better training episode:
reach -> grasp -> lift -> move/drop
```

Then fine-tune again from the same base:

```text
zz4321/so101_pi05
```

using the corrected dataset and the exact task:

```text
pick up the orange and move it to another place
```

## What Is Still Not 100% Proven

We cannot prove the neural network's internal "reason" with 100% certainty. What we can prove is:

```text
replay works
model/dataset feature names match
RGB/BGR conversion is correct
dataset contains start-idle behavior
eval prompt default was mismatched
longer 100/300/600-step policy runs still did not pick
```

So the next scientifically correct test is:

1. remove start idle from the training dataset
2. retrain/fine-tune
3. test with the exact matching task string
4. compare against the current 3000-step checkpoint

## Completed Fix - Action-Start-Cleaned Dataset

We created the corrected dataset:

```text
/data/lerobot_datasets/so101_pick_orange_move_action_start_view
```

Repo id:

```text
local/so101_pick_orange_move_action_start_view
```

This dataset is a fast video-backed view. It keeps the corrected trimmed parquet rows and points the episode video timestamps into the original cleaned videos. This avoids rebuilding thousands of image files while still giving LeRobot the same three camera observations:

```text
observation.images.front
observation.images.top
observation.images.wrist
```

Verified facts:

```text
episodes: 30
frames: 15,905
fps: 30
task: pick up the orange and move it to another place
camera feature dtype: image
video-backed dataset: yes
```

The start-idle problem is now removed:

```text
median first meaningful movement: 0.37 s
episodes first move after 2 s: 0 / 30
```

For comparison, the older cleaned dataset had:

```text
median first meaningful movement: about 2.9 s
episodes first move after 2 s: 28 / 30
```

The packaged tarball for RunPod is:

```text
/data/downloads/so101_pick_orange_move_action_start_view.tar.gz
```

Next fine-tune should use this corrected dataset, not the older `so101_pick_orange_move_cleaned` dataset.
