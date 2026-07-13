# Pi05 Pick-Orange Repeatable Protocol

This document turns our Pi05 real-arm testing into a repeatable procedure.

The goal is simple:

```text
Stop changing many things at once.
Keep the setup repeatable.
Make each test easier to compare.
```

## 1. What We Learned So Far

From our recent tests:

```text
1. Pi05 is not random anymore.
2. The 3-camera setup helped a lot.
3. The arm can move toward the orange in a meaningful way.
4. The prompt "grasp the orange" is better than the longer prompt.
5. Start pose matters a lot.
```

That last point is the big one.

The same prompt can behave differently depending on where the arm starts.

So our next step is not "try more random runs".

Our next step is:

```text
Fix the start pose.
Fix the orange position.
Run the same test again.
```

## 2. Why We Need A Repeatable Start

Pi05 does not only look at the cameras.

It also looks at the robot state:

```text
joint positions
gripper opening
current arm pose
```

So if the arm starts from a very different pose, Pi05 may choose a very different action path.

That means:

```text
same prompt
same cameras
different start pose
= different behavior
```

This is why some runs looked more like approach behavior, while another run showed much stronger close-the-gripper behavior.

## 3. Best Current Prompt

Use this as the main prompt for now:

```text
grasp the orange
```

Why:

```text
It gave stronger grasp intent.
It closed the gripper more decisively.
It looked better than the longer sentence.
```

## 4. Best Current Camera Layout

Current working 3-camera layout:

```text
Top   = Logitech C270
Front = laptop camera
Wrist = Raspberry Pi camera
```

This is our current best real-arm Pi05 setup.

## 5. Good Start Pose vs Bad Start Pose

### Good Pre-Grasp Start Pose

This is close to the state from the stronger run, where Pi05 showed better grasp intent:

```text
shoulder_pan   about  -3
shoulder_lift  about +13
elbow_flex     about +31
wrist_flex     about +93
wrist_roll     about +101
gripper        about +24
```

Interpretation in simple words:

```text
arm is already somewhat lowered
arm is already somewhat bent toward the object
gripper is partly open
wrist is already in a more useful pre-grasp shape
```

This is not a perfect final grasp pose.

It is just a better starting pose for Pi05.

### Bad / Harder Start Pose

This is closer to the more open pose where Pi05 mostly approached but did not commit as strongly:

```text
shoulder_pan   about   0
shoulder_lift  about -105
elbow_flex     about  +96
wrist_flex     about  +67
wrist_roll     about +100
gripper        about  +40
```

Interpretation:

```text
arm starts farther back
arm is more open
gripper is more open
Pi05 has to do more work before it can actually grasp
```

So this is a harder start condition.

## 6. Orange Placement Rule

For now, do not place the orange randomly.

Use this rule:

```text
1. Put the orange very close to the gripper work area.
2. Keep it centered under the arm's approach path.
3. Keep it in the same table location every run.
4. Keep the table uncluttered around it.
```

Best practical trick:

```text
mark the orange position on the table with tape
mark the arm base position too if needed
```

That way we can repeat the test instead of guessing every time.

## 7. What A Good Demo Means

Right now we are not trying to prove:

```text
Pi05 can robustly solve every orange placement
```

Right now we are trying to prove:

```text
Pi05 can do one clean pick in a controlled setup
```

That is a good first milestone.

## 8. Exact Next Test Procedure

### Step 1

Put the arm into the better pre-grasp start pose.

Use the joint numbers as a guide, not as a religious rule:

```text
shoulder_pan   around  -3
shoulder_lift  around +13
elbow_flex     around +31
wrist_flex     around +93
wrist_roll     around +101
gripper        around +24
```

### Step 2

Place the orange:

```text
close to the gripper path
centered
not too far away
not touching the gripper
```

### Step 3

Check all three cameras:

```text
top camera sees arm + orange
front camera sees arm + orange
wrist camera sees gripper area
```

### Step 4

Run this exact task:

```text
grasp the orange
```

### Step 5

Run 15 steps first.

Why only 15 first:

```text
If the start pose is good, we should see whether Pi05 commits properly.
If it still misses, then we adjust placement or start pose.
```

### Step 6

Only after that:

```text
try 30 steps
```

## 9. What We Should Measure After Each Run

After each run, write down:

```text
1. Did it move toward the orange?
2. Did the gripper close at the right time?
3. Did the gripper touch the orange?
4. Did it trap the orange?
5. Did it lift the orange?
6. Did it lose alignment near the end?
```

This helps us separate:

```text
approach problem
alignment problem
gripper timing problem
lift problem
```

## 10. My Current Opinion

I think we should go ahead like this:

```text
1. Use the 3-camera setup.
2. Use the short prompt "grasp the orange".
3. Start from the better pre-grasp pose.
4. Put the orange in an easy repeatable spot.
5. Run 15 steps.
6. Record video.
7. Compare to earlier runs.
```

This is the most sensible next move.

Why:

```text
We already proved connectivity works.
We already proved Pi05 can produce meaningful motion.
Now the main issue is repeatability and geometry.
```

## 11. What I Think Success Looks Like Next

The next good result does not need to be a perfect lift yet.

A very meaningful success would be:

```text
Pi05 approaches the orange cleanly
gripper closes around it
orange shifts or gets trapped clearly
```

If we get that consistently, then we are very close to a real pick demo.

## 12. Related Video Folder

Saved videos:

```text
/data/downloads/so101_pi05_3cam_tests
```

Use this folder as the baseline comparison set.
