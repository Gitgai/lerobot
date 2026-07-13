# Pi05 Fine-Tuned Checkpoint Failure Investigation - 2026-06-30

## 1. Download Status

Requested checkpoint:

```text
/workspace/outputs/pi05_so101_orange_ft1000_continue_1000steps/checkpoints/001000/pretrained_model
```

This is the final fine-tuned Pi05 `pretrained_model` folder from the RunPod A40 session.

Current blocker:

```text
ssh root@194.68.245.38 -p 22147 -i ~/.ssh/id_ed25519
```

returned:

```text
ssh: connect to host 194.68.245.38 port 22147: Connection refused
```

So the model cannot be downloaded from that endpoint right now. The RunPod pod is probably stopped, rebuilt, or using a new SSH endpoint.

## 2. Local Evidence Available

Combined training dataset:

```text
/data/lerobot_datasets/so101_pick_orange_30eps
```

Dataset facts:

```text
episodes: 30
frames: 20929
fps: 30
task: grasp the orange
camera views: top, front, wrist
action/state dimension: 6 SO-101 joints
```

Final ft2500 real-arm test:

```text
/data/downloads/3cam tests/so101_pi05_ft2500_grasp_orange_closed_loop_30steps_20260630_025314.mp4
/data/downloads/3cam tests/so101_pi05_ft2500_grasp_orange_closed_loop_30steps_20260630_025314.actions.csv
```

Comparison sheet:

```text
/data/downloads/pi05_failure_investigation_20260630/front_comparison.jpg
```

## 3. What Is Proven

### 3.1 The Robot Received The Pi05 Commands Exactly

For both ft500 and ft2500 tests:

```text
max_abs_sent_minus_commanded = 0.0
```

That means the logged `sent` actions exactly matched the Pi05 `commanded` actions.

So this failure was not caused by our script clamping, rewriting, or smoothing the actions in those logs.

### 3.2 The ft2500 Policy Did Not Command A Grasp Trajectory

ft2500 test start:

```text
shoulder_pan:   -9.05
shoulder_lift: -103.12
elbow_flex:     96.79
wrist_flex:     80.53
wrist_roll:      3.12
gripper:        41.40
```

ft2500 test end:

```text
shoulder_pan:  -13.36
shoulder_lift: -104.62
elbow_flex:     96.70
wrist_flex:     68.22
wrist_roll:      3.03
gripper:        41.61
```

Actual movement over 30 steps:

```text
shoulder_pan:   -4.31
shoulder_lift:  -1.49
elbow_flex:     -0.09
wrist_flex:    -12.31
wrist_roll:     -0.09
gripper:        +0.21
```

The important part is the gripper:

```text
gripper changed only +0.21
```

So Pi05 did not command a meaningful close/open grasp sequence.

### 3.3 The ft2500 Policy Stayed In A Narrow Action Range

During the ft2500 30-step test:

```text
gripper min:   40.90
gripper max:   42.04
gripper range:  1.13
```

In the training dataset:

```text
gripper action min:  0.80
gripper action max: 59.28
```

Training demonstrations contain much larger gripper changes. The ft2500 test did not.

### 3.4 The Test Start Pose Was Closest To A Late Training Frame

The ft2500 test start state was closest to:

```text
episode: 27
frame: 561
time: 18.70s
episode duration: 19.90s
```

That is near the end of a demonstration, not near the beginning.

Nearest training state:

```text
shoulder_pan:  -10.46
shoulder_lift: -103.12
elbow_flex:     96.79
wrist_flex:     78.95
wrist_roll:      3.38
gripper:        39.79
```

Nearest training action:

```text
shoulder_pan:  -10.20
shoulder_lift: -102.86
elbow_flex:     96.62
wrist_flex:     79.21
wrist_roll:      5.32
gripper:        39.68
```

That nearest training action is also a small/holding action, not a new reach-to-object action.

This is a strong explanation for the behavior: the model was started from a state that resembles a late/end demonstration state, so the next learned action is not a fresh pick trajectory.

## 4. What Is Not Proven

We cannot honestly claim with 100% certainty what the neural network "understood" internally.

What we can prove:

```text
The model output did not contain a successful reach-close-lift command sequence.
The robot executed those model outputs exactly.
The test state was close to late training states.
The gripper command stayed nearly constant.
```

What still needs a controlled experiment:

```text
Whether the same checkpoint works from the true demonstration start pose.
Whether the camera views in the test match the training views closely enough.
Whether more data or more fine-tuning fixes the policy output.
```

## 5. Exact Problem Statement

The real-arm pick failed because the fine-tuned Pi05 checkpoint did not output the action sequence needed to pick the orange.

Specifically, in the ft2500 closed-loop test it mostly adjusted shoulder pan and wrist flex, while the gripper stayed almost unchanged and the arm did not reach the orange.

The robot-control script sent the model outputs exactly, so the failure is not from a remaining software clamp in that test.

The strongest verified reason is that the evaluation started from a pose/state that matches late demonstration frames, where the correct next action in the dataset is mostly holding/finishing rather than beginning a reach-grasp-lift.

## 6. Correct Next Debug Test

Run one evaluation from the actual dataset-style start condition:

```text
1. Put the arm in the same start pose used at the beginning of the clean training episodes.
2. Put the orange in the same visible starting area as those episodes.
3. Confirm top/front/wrist camera views match the training views.
4. Run the same ft2500 checkpoint.
5. Compare the action log:
   - gripper should move across a meaningful range
   - shoulder/elbow/wrist should move toward the orange
   - video should show reach-close-lift
```

If it still does not command a grasp from the correct start condition, then the answer is:

```text
the checkpoint is under-trained or the dataset is insufficient/inconsistent
```

Then the correct fix is not clamps; it is better training data and/or longer fine-tuning.
