# Leader/Follower Workflow

This document describes the practical workflow after the arms are built.

## Daily Startup

1. Check cables.
2. Clear the workspace.
3. Power on the follower arm.
4. Connect the leader arm.
5. Start the robot control environment.
6. Verify both arms are detected.
7. Load calibration.
8. Move to home pose.
9. Test one small teleoperation movement.
10. Start recording only after the test passes.

## Teleoperation Session

Use this flow:

1. Reset object position.
2. Start recording.
3. Perform the task using the leader arm.
4. Stop recording.
5. Mark success or failure.
6. Reset the scene.
7. Repeat.

Keep each episode short and focused.

## Data Collection Rules

Good data is more important than lots of data.

Rules:

- Keep the camera fixed.
- Keep lighting fixed.
- Keep the task instruction fixed.
- Use the same object set.
- Reset objects consistently.
- Move smoothly.
- Avoid accidental bumps.
- Do not record while debugging hardware.

## First Dataset Plan

Dataset 1:

```text
Task: pick up block and place on marked target
Episodes: 30
Camera: one fixed camera
Policy: ACT
```

Dataset 2:

```text
Task: pick up block and place into bowl
Episodes: 50
Camera: one fixed camera
Policy: ACT
```

Dataset 3:

```text
Task: two object positions, same place target
Episodes: 100
Camera: one fixed camera
Policy: ACT or SmolVLA fine-tuning
```

## What To Log

For every dataset:

- Date
- Robot version
- Camera position
- Lighting condition
- Task description
- Number of episodes
- Number of successful demos
- Number of failed demos
- Notes about problems

Example:

```text
Date: 2026-05-28
Task: pick red block and place on blue tape
Episodes: 30
Successful demos: 26
Failed demos: 4
Camera: front third-person camera
Notes: gripper sometimes slips when closing too fast
```

## First Training Path

Train ACT first:

1. Record 20-50 clean demos.
2. Train ACT.
3. Evaluate 20 real robot trials.
4. Watch failure videos.
5. Add more demos for the failure cases.
6. Retrain ACT.

Move to SmolVLA only when:

- Teleoperation is smooth.
- Dataset recording is stable.
- ACT gets useful success.
- Camera and calibration are repeatable.

## Evaluation Template

Use this table for every policy:

| Policy | Dataset | Task | Trials | Success | Notes |
| --- | --- | --- | ---: | ---: | --- |
| ACT | block_place_v1 | place block on target | 20 | TBD | TBD |

## Common Problems

### Bad Calibration

Symptoms:

- Follower moves opposite direction.
- Home pose is different after restart.
- Policy actions look shifted.

Fix:

- Recalibrate both arms.
- Verify joint order.
- Verify joint signs.
- Save and reload calibration.

### Poor Camera View

Symptoms:

- Robot blocks the object.
- Gripper is not visible.
- Object leaves frame.

Fix:

- Move camera farther back.
- Raise camera slightly.
- Add lighting.
- Mark camera mount position.

### Weak Demonstrations

Symptoms:

- Robot learns jerky movement.
- Robot misses object often.
- Policy repeats human mistakes.

Fix:

- Record slower demos.
- Keep only clean successes for the first dataset.
- Make the task simpler.

### Too Hard A Task

Symptoms:

- ACT does not learn.
- Failures are inconsistent.
- Demos vary too much.

Fix:

- Use one object.
- Use one start position.
- Use one target position.
- Shorten the task.

## Next Decision

Before buying or assembling more hardware, define:

```text
First real robot task:
Camera count:
Arm type:
Motor type:
Controller:
Computer:
Power supply:
```

Once those are fixed, the next step is a hardware bill of materials and assembly checklist.

