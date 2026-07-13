# Real SO-101 Working Robot Plan

This document is the plan for the actual goal:

Make the real SO-101 arm reliably pick up the orange using cameras and a learned policy.

The goal is not only to make the arm move. The goal is a repeatable, useful robot behavior.

## 1. Current Status

We have already proven the main system pieces work:

1. The local laptop can control the SO-101 follower arm.
2. The follower arm motors are connected and calibrated.
3. The local laptop can read camera views.
4. The Raspberry Pi wrist camera is working.
5. The Logitech C270 top camera is working.
6. The laptop/front camera is working.
7. The remote L40S GPU can run the Pi05 model.
8. The local laptop can send observations to the remote GPU.
9. The remote GPU can return Pi05 actions.
10. The SO-101 arm can move from those returned actions.

Current working camera setup:

```text
top camera   = Logitech C270
front camera = laptop camera
wrist camera = Raspberry Pi camera
```

Current model:

```text
zz4321/so101_pi05
```

Current task prompt:

```text
grasp the orange
```

## 2. What We Know For Sure

The system is not completely broken.

We know this because Pi05 actions have moved the arm, and the movement is not always random. In several tests the arm moved toward the orange area.

We also know the orange is not being picked because the final gripper geometry is wrong:

```text
the gripper does not center around the orange
the gripper does not close around the orange
the orange stays on the table
```

So the current failure is not simply:

```text
no camera
no GPU
no robot connection
no model output
```

The current failure is:

```text
the policy/control path is not yet producing a successful grasp trajectory on our real setup
```

## 3. What The Current Script Changes

Our current test script does not send Pi05 output to the arm completely unchanged.

The current path is closer to this:

```text
camera images + robot state
        ↓
Pi05 on L40S
        ↓
Pi05 action chunk
        ↓
we often use only the first action
        ↓
our script may limit the action
        ↓
LeRobot may also limit large relative motor jumps
        ↓
SO-101 motors move
```

This was useful while testing because it protected the arm from sudden large movements.

But it is not the final behavior we want.

For a real working robot, we should not hide Pi05 behavior behind too many restrictions. We need to know whether the model itself can solve the task, and if it cannot, we should improve the model or data instead of relying on band-aids.

## 4. What We Do Not Know Yet

We do not yet know the single root cause with 100 percent certainty.

The possible causes are:

1. We are not executing the Pi05 action chunk correctly.
2. The camera views do not match what the model expects.
3. The start pose is too different from what the model expects.
4. The orange placement is too difficult or ambiguous.
5. The pretrained Pi05 checkpoint is not adapted enough to our exact SO-101 setup.
6. More than one of these is happening at the same time.

This matters because each cause has a different fix.

If chunk execution is wrong, we fix the execution code.

If the camera setup is wrong, we fix the camera layout.

If the model is not adapted to our setup, we collect demonstrations and fine-tune.

## 5. Engineering Principle

We should not build the final system from band-aid fixes.

Temporary safety limits are allowed for investigation and hardware protection.

But the real solution should be:

```text
test Pi05 honestly
understand exactly where it fails
collect data on our own setup
fine-tune if needed
evaluate the fine-tuned policy
```

That matches the actual goal: a real working robot, not just a script that forces movement.

## 6. Milestone 1: Faithful Pi05 Execution Test

Purpose:

Find out whether Pi05 is failing because we are editing its actions too much.

Current concern:

Pi05 returns an action chunk, but our current test often uses only the first action from that chunk. A chunked policy usually expects several actions to be executed as a short sequence.

Better test:

```text
ask Pi05 for an action chunk
execute more of that chunk
record the video
record the raw actions
compare what Pi05 requested with what the arm actually did
```

Suggested progression:

```text
first test: execute 3 actions from the chunk
second test: execute 5 actions from the chunk
third test: execute 10 actions from the chunk only if stable
```

Success signs:

```text
motion becomes smoother
the gripper approaches the orange more directly
the gripper starts closing near the orange
the wrist does not suddenly rotate into a strange pose
```

Failure signs:

```text
the arm still misses the orange
the wrist makes large confusing rotations
the gripper closes away from the orange
the motion is unsafe or inconsistent
```

Decision after this milestone:

If chunk execution helps, improve the Pi05 execution code.

If chunk execution does not help, move to demonstration data and fine-tuning.

## 7. Milestone 2: Controlled Scene Test

Purpose:

Remove confusion from the visual scene.

We should keep these fixed during each test:

```text
same table
same lighting
same orange
same camera positions
same prompt
same start pose style
same orange placement
```

Then we change only one thing at a time.

Example controlled test variables:

```text
prompt: "grasp the orange"
orange: centered in front of gripper
top camera: sees whole arm and orange
front camera: sees gripper and orange from the side/front
wrist camera: sees the object area
```

The goal is not to make the task artificially fake. The goal is to remove unnecessary uncertainty while debugging.

## 8. Milestone 3: Demonstration Dataset

If pretrained Pi05 does not reliably pick the orange, the next serious fix is our own data.

We should record successful demonstrations on our exact setup.

Dataset requirements:

```text
robot: our SO-101 follower
cameras: top, front, wrist
task: grasp the orange
actions: real follower actions from leader teleoperation
state: robot joint positions
video: clear view of the orange and gripper
```

Recommended dataset sizes:

```text
5 episodes     = pipeline check only
20 episodes    = first small fine-tune experiment
50 episodes    = useful first real attempt
100+ episodes  = better reliability target
```

For early fine-tuning, record mostly successful examples.

Bad episodes can be useful later, but first we need to teach the desired behavior clearly.

## 9. Milestone 4: Fine-Tune Pi05

If the pretrained model is not enough, we fine-tune instead of adding more movement hacks.

Fine-tuning means:

```text
start from a pretrained Pi05 model
show it our robot's camera views
show it our successful actions
train it to imitate our demonstrations
save a new checkpoint
test that checkpoint on the real arm
```

Why fine-tuning is the right fix:

```text
our cameras are unique
our table is unique
our orange placement is unique
our calibration is unique
our wrist camera is unique
```

A pretrained model may understand the idea of grasping, but still fail on the exact geometry of our real setup.

Fine-tuning teaches it our setup.

## 10. Milestone 5: Real Evaluation

A real success test should not be one lucky run.

We should evaluate like this:

```text
10 attempts from the same easy setup
record every attempt
count success only if the orange is grasped and lifted
```

Track:

```text
success count
failed approach
failed grasp
unsafe movement
gripper closed too early
gripper closed too late
camera issue
network/model issue
```

First target:

```text
3 successful picks out of 10
```

Better target:

```text
7 successful picks out of 10
```

Strong target:

```text
9 successful picks out of 10
```

## 11. What Not To Do

Avoid these patterns:

```text
randomly changing many things at once
running many tests without saving video and logs
assuming more steps automatically means better behavior
using clamps as the final solution
testing raw long runs without an emergency stop plan
training before checking that the dataset is clean
```

Those make the project slower because we cannot tell what caused an improvement or failure.

## 12. Recommended Immediate Next Step

The next best step is:

```text
run a chunk-direct Pi05 test
```

Meaning:

```text
do not only use the first Pi05 action
execute a short sequence from the returned Pi05 action chunk
record video
record raw actions
compare result
```

This answers the most important current question:

```text
Is Pi05 failing because the model is not adapted,
or because our current script is not executing Pi05 actions faithfully?
```

If chunk-direct improves the behavior, we fix the execution path.

If chunk-direct still fails, we move to recording demonstrations and fine-tuning.

## 13. Final Direction

For the actual goal, the path is:

```text
faithful Pi05 test
        ↓
controlled repeatable setup
        ↓
record successful demonstrations
        ↓
fine-tune Pi05 or another compatible policy
        ↓
evaluate on the real SO-101 arm
```

That is the clean path from experiment to working robot.
