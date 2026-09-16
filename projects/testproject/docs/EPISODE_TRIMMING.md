# Episode trimming and end-state verification

Written 2026-09-15 after measuring all 30 episodes recorded on the Acer through
the OV4689 wrist camera and C270 front camera.

Two separate jobs are described here:

1. **Trimming** — cutting the dead time off the end of each episode.
2. **Verification** — confirming from the front camera that the fruit actually
   reached the plate, without anyone having to watch the video.

---

## Why trimming is needed

Measured across all thirty episodes:

```text
                 length     idle      motion ends     dead tail
orange (20 eps)   59.8s     62%        26 - 38s       15 - 33s
tomato (10 eps)   29.9s     36%        18 - 30s        0 -  9s
```

**62% of the orange frames show an arm doing nothing.** Behaviour cloning copies
what it sees, and the most common thing in that data is stillness. The failure
mode is a policy that dawdles — already observed on 2026-09-14, in a test
episode where the gripper closed on empty air and the arm only began moving at
18 seconds.

The tomato episodes are already tight. **The orange ones are not** — and that
is why only the orange set is trimmed (see Scope, below). Within the orange set
the fix still has to be per-episode, because the dead tail varies from 15 to 33
seconds.

---

## Scope — WHICH episodes get trimmed

>>> DECISION (operator, 2026-09-15): trim the 20 orange episodes only.
>>> Leave the 10 tomato episodes exactly as recorded.

The tomato episodes are already tight and there is nothing worth taking:

```text
                 length    idle    dead tail      trimming would save
orange (20)       59.8s     62%     15 - 33s      15,004 frames (42%)
tomato (10)       29.9s     36%      0 -  9s         869 frames (3%)
```

**Trimming the tomato set would recover 29 seconds of video in total** — across
all ten episodes combined. That is not worth a re-encode, and it is not worth
the risk of a detector mistake on data that does not need touching. Four of the
ten have no dead tail at all.

The balance argument also disappears once the orange set is cut: orange comes
down to 34.8s against tomato's 29.9s, which is close enough.

**Do not run the rule below on the tomato datasets.**

---

## THE RULE (operator's wording, 2026-09-15)

```text
1. Never touch the front of the episode - it starts at rest already.
2. Find the moment the arm reaches its rest posture AT THE END and stays there.
3. Keep 3 more seconds after that moment.
4. Cut everything after.
```

**Step 2's "at the end" is load-bearing, not decoration.** The arm is at rest at
the *start* of every episode too. An earlier draft read "find the moment the arm
reaches its rest posture and stays there", which — scanned forward — matches
**frame zero** and deletes the entire episode. Always search backward from the
last frame.

**Step 1 is a boundary, not a step.** It comes first so nobody implements the
cut and only then discovers half the episode was off limits.

### Why anchor on rest, and not on "motion stopped"

An earlier proposal used a motion threshold plus a fixed 1-second tail. It was
worse for two reasons:

- A motion threshold is arbitrary; the rest posture is a **physical landmark**.
- The retreat to rest is real behaviour worth keeping, and a 1-second tail
  clipped into it.

### Why 3 seconds and not 2

Measured on the 20 orange episodes, the only ones being trimmed:

```text
2 seconds    20,327 frames kept
3 seconds    20,897 frames kept
difference      570 frames - 19 seconds of video across all twenty episodes
```

Under 3% more data for a full extra second of protection. The margin itself is
safe either way: the most active 3-second margin across the twenty contains
**1.98 degrees** of total movement, which is the arm settling on its springs.

The extra second is insurance against a rest-detector that fires slightly early
on some future recording — same cost, more protection.

---

## The rest pose, measured

All 30 episodes, final frame, degrees:

```text
joint            median     min      max    spread
shoulder_pan       -2.6    -11.9      4.6     16.4    varies - IGNORE
shoulder_lift    -104.3   -104.7   -103.7      1.0    ANCHOR
elbow_flex         96.7     96.7     96.7      0.1    ANCHOR
wrist_flex         78.4     76.1     79.5      3.3    ANCHOR
wrist_roll         -0.7    -10.7      9.0     19.7    varies - IGNORE
gripper            48.9     31.7     66.0     34.2    varies - IGNORE
```

**Detect rest on `shoulder_lift`, `elbow_flex`, `wrist_flex` only, at ±2°.**

The other three vary for good reasons and testing them would produce false
failures: the base ends wherever the plate is, the wrist wherever it was left,
and **the gripper at whatever opening released the fruit** — see the gripper
warning below.

The start-pose spread matches the final-pose spread almost exactly, which is the
evidence that the arm both begins at rest and returns to it.

---

## Safety checks before any cut

No episode is trimmed unless all of these pass. An episode that fails is **left
untrimmed and flagged**, never guessed at.

```text
1. The episode ends at the rest posture (all three anchor joints within 2 deg).
2. The discarded region contains no real motion.
3. The fruit is on the plate in the final frame (front camera - see below).
```

Measured on the current thirty: the discarded region's largest movement is
**0.09 degrees** — servo noise — in every single episode.

**If an episode does not end at rest, the detector has nothing to anchor on.**
That happens after a fumble, an abort, or a crash. Refuse to trim it.

---

## What the rule produces

Applied to the 20 orange episodes only:

```text
set                frames in   frames out   change
orange (20 eps)       35,901      20,897    -15,004  (42%)
tomato (10 eps)        8,980       8,980    untouched
TOTAL                 44,881      29,877    -15,004  (33%)

average episode      orange 59.8s -> 34.8s      tomato 29.9s (unchanged)
```

It adapts per episode, which was the whole point: orange ep1 keeps 40.9s while
ep5 keeps 29.0s. Everything removed is an arm sitting motionless.

**Originals are never modified.** The trimmed set is written to a new directory.
Fold the trim into the v3.0 → v2.1 conversion that GR00T training needs anyway,
so the videos are re-encoded once rather than twice.

---

## Verifying the fruit reached the plate

**The front camera can confirm this automatically. Do not rely on watching
video, and do not rely on the gripper trace.**

```text
judged 30/30    ON PLATE 30    edge 0    off 0    detector failures 0
margin range    +52 to +89 pixels inside the plate rim
```

### How it works

```text
PLATE   large blue-grey blob in the RIGHT of the frame, taller than wide,
        area > 15000 px. Take its CONVEX HULL.
FRUIT   saturated warm hue, round-ish: fill >= 0.55 of its bounding box,
        aspect >= 0.45, area > 800 px.
TEST    is the fruit's centroid inside the plate hull, and by how far.
```

### Three ways this detector failed first — do not repeat them

**1. Picking the plate by size.** The robot arm's white-and-grey plastic falls in
the same colour range and is *sometimes the larger blob*. Four episodes were
reported OFF PLATE because the fruit was being measured against the arm.

**2. Picking the plate by shape.** Requiring a smooth oval (solidity ≥ 0.88)
rejected the real plate in those same four: where the gripper overlaps the rim it
notches the outline and solidity drops from 0.99 to **0.76**.

**3. The fix is position plus convex hull.** The plate never moves — it sits at
roughly x=460, 175×250 px in every frame. Find it by position, then use its
convex hull so an overlapping gripper cannot break it.

### The gripper trace cannot score the task

An earlier check required the gripper to reopen by more than 30% of its travel
to count as "released". It failed two episodes that were perfectly good:

```text
ep0 (passed)   closes to 26.7, reopens to 53.2   51% of range
ep7 (failed)   closes to 29.0, reopens to 31.7   14% of range - fruit WAS on the plate
```

**A gentle release and a failed release look identical in the numbers.** The
fruit needs only a few millimetres of clearance to drop. Some operators open the
jaws wide; some open them just enough.

This generalises beyond trimming: **when scoring arm trials, the camera decides
whether the task succeeded, not the gripper.** This project has repeatedly tried
to score grasps from servo readings and been wrong each time.

---

## A caution on what these checks do and do not prove

They prove the arm moved, ended at rest, and left the fruit on the plate. They
**do not** prove the demonstration was good. An episode where the fruit was
fumbled, re-grasped, or dragged looks identical in this data to a clean one.

That question is answered by watching video, and is worth doing once for thirty
episodes before training on them.

---

## Related

```text
PLAN.md                            the project's direction
MODELS.md                          the model registry
MACHINES.md                        which machine holds what
agent_handoff_codex_20260915.md    the follower USB fault
```
