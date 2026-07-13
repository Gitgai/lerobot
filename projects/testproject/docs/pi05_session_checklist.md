# Pi05 Session Checklist

Use this during a real Pi05 test session.

This is the short version.

If you want the full explanation, see:

```text
docs/pi05_fast_test_workflow.md
docs/pi05_pick_orange_repeatable_protocol.md
```

## 1. Before GPU

Do all of this first.

### Robot

```text
[ ] Follower controller connected
[ ] Follower arm powered
[ ] Arm in acceptable start pose
[ ] Workspace clear
[ ] Orange placed in easy reachable spot
```

### Cameras

```text
[ ] Top camera working
[ ] Front camera working
[ ] Wrist camera working
[ ] All cameras show arm + orange clearly enough
```

### Test Plan

Decide before starting GPU:

```text
[ ] Prompt chosen
[ ] Step count chosen
[ ] Video filename chosen
[ ] Only one variable being tested
```

Default quick test:

```text
prompt = grasp the orange
steps = 15
```

If all boxes are not checked, do not start the GPU yet.

## 2. Start GPU

Once local setup is ready:

```text
[ ] Start L40S
[ ] Wait until instance is fully ready
```

## 3. During GPU

Only do inference work here.

```text
[ ] Start remote Pi05 policy server
[ ] Start local tunnel / connection
[ ] Run one short test
[ ] Save video
```

## 4. Immediate Decision After Run

Ask:

```text
[ ] Did the arm move toward the orange?
[ ] Did alignment improve?
[ ] Did the gripper close meaningfully?
[ ] Did it touch or trap the orange?
```

Then decide only one of these:

```text
[ ] Continue with same setup and more steps
[ ] Keep setup and change one small thing
[ ] Stop GPU because the setup is clearly bad
```

## 5. Stop GPU If Any Of These Are True

```text
[ ] A camera is broken
[ ] Start pose is clearly wrong
[ ] First short run is obviously nonsense
[ ] Problem is local geometry, not model inference
```

If yes:

```text
stop GPU
fix local setup
try again later
```

## 6. Session Rule

Keep this rule for every session:

```text
Before GPU:
do all local checks

During GPU:
only run inference tests

After GPU:
review video locally and decide next action
```
