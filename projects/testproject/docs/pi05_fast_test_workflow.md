# Pi05 Fast Test Workflow

This document is the practical, cost-aware workflow for Pi05 real-arm testing.

The goal is:

```text
Do all cheap work first.
Use GPU time only for inference.
Keep each run short and informative.
```

This is different from the full repeatable protocol.

Use this document for normal day-to-day testing when we want to move fast.

Related reference:

```text
docs/pi05_session_checklist.md
docs/pi05_pick_orange_repeatable_protocol.md
```

## 1. Why We Need This

The expensive part of the project is:

```text
remote GPU time
```

The cheaper part is:

```text
local robot checks
camera checks
orange placement
deciding the next test
watching videos afterward
```

So the correct order is:

```text
Before GPU:
do all local checks

During GPU:
only run inference tests

After GPU:
review video locally and decide next action
```

That is the main idea.

## 2. Two Testing Modes

We should use two modes, not one.

### Quick Test Mode

Use this for most runs.

Purpose:

```text
Try one idea quickly.
See if the motion is promising.
Avoid wasting GPU time.
```

Rules:

```text
1. Keep the run short.
2. Record video every time.
3. Change only one thing at a time.
4. Stop early if the setup is clearly bad.
```

Typical run:

```text
prompt = grasp the orange
steps = 10 to 15
same cameras
same easy orange placement
```

### Proper Comparison Mode

Use this only when a run looks promising.

Purpose:

```text
Verify whether one setup is really better than another.
```

Rules:

```text
fixed pose
fixed orange placement
same prompt
same cameras
same steps
```

My recommendation:

```text
80% quick test mode
20% proper comparison mode
```

## 3. Before GPU Checklist

Do all of this before starting the L40S.

### Robot

```text
Follower controller connected
Follower arm powered
Arm in acceptable start pose
Workspace clear
Orange placed in easy spot
```

### Cameras

```text
Top camera working
Front camera working
Wrist camera working
All views show arm + orange clearly enough
```

### Test Decision

Decide these before starting GPU:

```text
prompt
step count
video filename
what one variable we are testing
```

If these are not decided yet, do not start the GPU.

## 4. During GPU Workflow

Once the GPU is running, do only inference work.

### Step 1

Start the remote Pi05 policy server.

### Step 2

Bring up the local tunnel / connection.

### Step 3

Run one short test first.

Recommended default:

```text
prompt = grasp the orange
steps = 15
```

### Step 4

Save the video with a clear name.

### Step 5

Decide immediately:

```text
promising -> continue
clearly bad -> stop GPU and fix local setup first
```

## 5. After GPU Workflow

After the inference run, do the review locally.

Ask only these questions:

```text
1. Did the arm move toward the orange?
2. Did alignment get better or worse?
3. Did the gripper close meaningfully?
4. Did it touch or trap the orange?
5. Was failure caused by pose, cameras, prompt, or too few steps?
```

Then choose exactly one next change.

Good examples:

```text
same setup, more steps
same setup, shorter prompt
same setup, orange slightly closer
same setup, better start pose
```

Bad example:

```text
change prompt + pose + cameras + orange placement all together
```

## 6. What Counts As A Good Quick Test

A quick test does not need a perfect grasp.

A quick test is useful if it tells us one of these:

```text
Pi05 is clearly confused
Pi05 is approaching correctly
Pi05 closes the gripper at the right time
Pi05 gets closer but still misses alignment
```

That is enough to decide the next step.

## 7. Stop Rules

Stop the GPU session if:

```text
1. A camera is not working.
2. The arm start pose is clearly bad.
3. The first short run is obviously nonsense.
4. The issue is local geometry, not policy inference.
```

Do not keep spending GPU time on a setup that is already clearly wrong.

## 8. Recommended Default Test

For now, this is the default fast run:

```text
3 cameras
prompt = grasp the orange
easy orange placement
15 steps
record video
```

Only move to 30 steps if the 15-step run already looks meaningful.

## 9. What We Should Keep Stable Most Of The Time

To go faster, keep these stable unless there is a good reason to change them:

```text
camera layout
basic orange placement
default prompt
video folder
test command template
```

That way we spend less time rebuilding the test each session.

## 10. My Recommendation

Use this workflow for normal testing:

```text
Before GPU:
prepare everything locally

During GPU:
run only short Pi05 tests

After GPU:
review video and choose one next change
```

This is the fastest and cheapest workflow for where the project is right now.
