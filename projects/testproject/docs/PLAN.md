# SO-101 — the plan

Live document. Rewritten 2026-09-12 when the approach changed from "restore the
old camera" to "record through a new one". The previous version is kept as
`PLAN_superseded_20260912.md` for the reasoning it contains.

---

## The pivot, and why

For three weeks every arm trial failed while we tried to make a replacement
camera imitate the one the model learned from. Measured across ALL 1,145 wrist
frames of a working run and a failing one:

```text
                        orange in the wrist view
20 Aug, grasped         27% of frame (median), BELOW the fingers, 68/68 frames
5 Sep, failed            2% of frame,          ABOVE the fingers, 34/34 frames
                        the two sets do not overlap on a single frame
```

The model learned "a big orange under my fingers means descend and close". No
substitute camera produced that picture, so the descent was never commanded.

>>> DECISION (operator, 2026-09-10): stop matching new cameras to old pictures.
>>> Record fresh demonstrations through the camera we intend to keep.

That is this plan.

---

## The rig as it now stands

```text
WRIST    OV4689 USB, /dev/video4        32 ms/frame, 60 fps available at 640x480
         SunplusIT bridge, 92 deg FOV   sharp; orange reads 5-13% of frame
FRONT    Logitech C270, /dev/video6     aimed across the table at the arm
         (the Acer built-in on video0 now faces the room, not the workspace)
ARM      follower on USB 3-2            all 6 motors respond
LEADER   NOT CONNECTED                  required to record
```

### Two problems to clear before recording

```text
1  USB PORT 3-2 dropped the follower TWICE mid-recording, 2 s each time, exactly
   as port 3-1 did in August. The device renumbers and the recorder dies with
   "Input/output error". MOVE THE FOLLOWER to another socket.

2  USB BANDWIDTH. Two cameras at 640x480 MJPEG plus two serial devices sit on
   one controller. The OV4689 already returned no frames once when the C270 was
   added. If the laptop has ports on both sides they are often separate
   controllers - put the cameras on one side, the arms on the other. This may
   turn out to be what the "faulty port" actually is.
```

### Also noted, not yet chased

Motor supply reads **5.2-5.6 V**. The STS3215 is usually run nearer 7.4 V. Low
supply fits the pattern of servos that answer at rest and drop out under load.
Worth checking the supply before blaming anything else for a dropout.

---

## Step 1 — record (operator time, the expensive step)

```text
esp_orange   20 episodes   "pick up the orange and place it on the plate"
esp_apple    10 episodes   "pick up the apple and place it on the plate"
```

Script: `~/rec_esp.sh N dataset "instruction"` on the arm laptop. It resolves
both arms by SERIAL and refuses to start if the wrist camera is not live - a
frozen camera during recording poisons the dataset permanently, and unlike a
bad trial you cannot simply rerun it.

**Position spread, from the August session:**

```text
~8  middle band       where it already works
~8  operator-right    the region it fails in
~4  operator-left
```

**Two rules:**

1. **HOLD 5 OF THE 20 OUT OF TRAINING.** With all of them in, "did it improve?"
   has no offline answer at all. That is the wall plate_v2 hit and the single
   most valuable change available.
2. **One attempt per go.** No auto-retry. In August a retry recorded a poisoned
   episode while the operator was still resetting the scene.

### On the apple set

Recorded with the apple ALONE (operator's choice, 2026-09-10). This teaches the
apple as an object. It will NOT teach the model to read the instruction: with
one fruit in view the picture already says which to pick, so the words stay
redundant - the same mechanism measured on 2026-08-26, where the wrong sentence
cost -0.04. A language-grounding set needs BOTH fruits present with the command
choosing between them. That remains a separate, later job.

---

## Step 2 — train

```text
from     orange_pick_baseline_v1 (the frozen 9/10 model)
data     the new demos + the 79 old orange demos MIXED IN (anti-forgetting)
steps    6000
```

6000 is measured, not assumed: doubling to 12000 moved held-out error 2.50 ->
2.37 then back to 2.46, a spread of 1.1 standard errors on a paired test -
indistinguishable from chance.

**Caveat on mixing:** the old 79 demos carry the OV5647 wrist view; the new ones
carry the OV4689. Mixing two camera geometries may act as useful augmentation or
may dilute the signal. This has never been tested. If the result disappoints,
training on the new demos alone is the obvious next variant.

---

## Step 3 — test

The 5 held-out demos give an offline read first, then the arm. Score GRASP and
PLACE separately, never blended.

**A grasp requires all three**, each added after a scoring bug produced a false
positive:

```text
1  a SUSTAINED finger block >= 10 cycles     (chatter is not a hold)
2  the orange MOVED in the front camera      (a stall proves nothing on its own)
3  the arm actually TRAVERSED >= 30 deg      (a hold at the wrong height is not
                                              a grasp - c1/c2 held 21 and 31
                                              cycles at lift +72, a hundred
                                              degrees from the table)
```

---

## What we have, for the record

### Two models, differing ONLY in the front camera

```text
n16_real79_side/checkpoint-10000   = orange_pick_baseline_v1, the 9/10 model
                                     trained on so101_orange_89_v21_train79
n16_real79_top/checkpoint-10000    trained on so101_orange_89_v21_topfront_train79
```

Both declare the same keys, `front` and `wrist`. The 89 demonstrations were
captured with three cameras at once; two datasets were built by choosing which
second camera to call "front". **The wrist footage is identical in both.**

- SIDE "front" = a camera across the table, arm side-on
- TOP "front" = a camera looking down over the arm

**Brain B is marked retired on a verdict its own document calls into question.**
`n16_brainB_rtc_check_20260821.md` records A 10/10 vs B 7/10, then asks whether
that measured camera quality or tempo tolerance, since RTC alone took A from
4/10 to 9/10. Three RTC runs of B were planned to settle it and never run.

### The old model does not transfer to the new rig

Offline, at the pose from which the working model descended:

```text
new rig   C270 + OV4689     asks lift  -2.8   grip 33.8   no descent
reference r6's own cameras  asks lift -11.6   grip 27.7   descends and closes
```

CAVEAT: the deliberately-mismatched control in that test ALSO descended and
closed, so the test does not discriminate as cleanly as it should. What it
supports is narrow: the new rig produces a response unlike anything else tested,
and not the one a grasp needs. It does not prove the model "rejects" the
cameras.

---

## Standing rules earned the hard way

```text
CAMERA     ENFORCED IN CODE since 2026-09-03. The client refuses to start unless
           the wrist frame is < 1.5 s old AND two fetches a second apart DIFFER,
           and aborts mid-run after three stale frames. HTTP 200 is not proof -
           a frozen proxy returns 200 forever. Five trials lost before this.
USB        Arms NEVER on port 3-1, and now not 3-2 either. Resolve by SERIAL,
           never by device name - a 2 s dropout renumbers them.
GRASP      Requires all three checks above. Four separate scoring bugs produced
           false positives before they were all in place.
SCENE      Photograph the scene before a control run and CHECK it. A plate was
           present during a "no plate" control on 2026-09-02, invalidating it.
FRAMES     Verify frames by md5 against the source before analysing them. On
           2026-09-05 a cp bug nested today's frames under August ones and an
           entire analysis ran on the wrong day's pictures.
DETECTION  The orange detector must require ROUNDNESS and a saturation floor
           suited to the camera in use. Wood grain has outscored the fruit, and
           a washed-out frame has read 0.5% when the fruit filled a third.
SHARPNESS  Laplacian variance measures EDGES IN THE SCENE, not focus. Do not
           compare it across frames of different content - it produced a false
           "the lens is degrading" trend on 2026-09-09.
MACHINE    The GPU box also runs the DYNUS flight campaign. EXIT=143 with a clean
           log is systemd-oomd, not a bug. Checkpoint often; flights are the
           priority and training gives way.
PREMISE    Test the premise before building the fix. A 15-minute probe killed a
           geometric-augmentation plan that would have cost 2 h of GPU.
```

---

## Open questions, honestly labelled

```text
Does the new rig work at all?
  UNTESTED on the arm. The offline read is unfavourable but its control was
  faulty. The demonstrations are what settle it.

Does mixing two camera geometries in one training set help or hurt?
  NEVER TESTED. Step 2 does it. If the result disappoints, train on the new
  demos alone.

Was Brain B really worse, or just less tempo-tolerant?
  UNRESOLVED since 2026-08-21. Three RTC runs would answer it. Not a priority
  while the rig cannot deliver three uninterrupted runs.

Would full fine-tuning help?
  NEVER TESTED. 50% of the model is trained today (action head, top 4 language
  layers, projector); the vision encoder is frozen. Unfreezing needs ~7.5 GB
  more than the card has spare, and 99 episodes is thin for 1.87 B parameters -
  but "we inherited NVIDIA's default" is an admission, not a justification.

Why does the Pune rig drop out so often?
  Both machines have vanished together repeatedly, which points at the site
  network rather than either machine. Availability has been roughly one third.
  This now costs more time than any technical problem in this document.
```

---

## Data preparation — see `EPISODE_TRIMMING.md`

The 20 orange episodes recorded 2026-09-15 are 62% idle and are trimmed before
training. The 10 tomato episodes are already tight and are left untouched
(operator decision, 2026-09-15). The rule, the measured rest pose, and the
front-camera check that confirms the fruit reached the plate are all in
`EPISODE_TRIMMING.md`. All 30 episodes verified good; none excluded.
