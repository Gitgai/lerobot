# SO-101 plate round — the plan

Live document. Supersedes the runbook's ordering where they disagree.
Last updated 2026-09-03.

---

## Where we actually are

```text
DONE AND BANKED
  orange_pick_baseline_v1   9/10 full task completions on the arm (2026-08-20)
                            FROZEN, write-protected, never overwrite
  20 plate demonstrations   recorded and verified (2026-08-25)
  plate_v1                  trained; passed its offline regression gate
  plate_v2                  trained to global ~12000; NO gain (within noise)

MEASURED, ONE TRIAL ONLY
  plate_v1 on the arm       grasped in 9 s, grip +5.3, DID NOT CARRY to the plate

BLOCKED
  the OV5647 wrist ribbon is dead. Everything below waits on it.
```

---

## THE BLOCKER, and why nothing else matters first

The wrist camera has failed twice by freezing mid-session and is now
electrically dead. It has cost five arm trials directly, and the attempt to
work around it with an ESP32 produced three more failures we still cannot
explain.

**We have had no positive control since 2026-08-20.** We cannot demonstrate the
rig grasps at all today, with any camera. Since that date the laptop has moved,
the arm has been unplugged and replugged across USB ports, and hardware has been
added to the wrist. Every model question this week has run aground on this.

> **Buy a replacement OV5647 ribbon. Same sensor - so the robot sees the world
> it learned. Nothing else unblocks the project.**

---

## Step 1 — restore the positive control (30 min at the bench)

```text
1  fit the replacement ribbon, confirm the Pi enumerates the camera:
     rpicam-hello --list-cameras   ->  ov5647 listed
     /dev/video0                   ->  present
2  start the proxy, verify LIVE (not merely HTTP 200):
     three fetches 2 s apart must have DIFFERENT md5 and age < 1 s
3  ONE trial: orange_pick_baseline_v1, plain orange, NO plate, mid-table
```

**Decision:**
- grasps -> the rig is healthy. Proceed to step 2.
- does not grasp -> something other than the camera broke since 2026-08-20.
  Stop and diagnose. Do NOT run model comparisons on a rig that cannot grasp.

---

## Step 2 — the ten trials plate_v1 has been waiting for

```text
model        plate_v1  (checkpoints/n16_plate_v1/checkpoint-6000)
instruction  "pick up the orange and place it on the plate"  (byte-exact)
scene        plate in position, one orange, nothing else
runtime      --rtc=true, jpeg 92, ports by SERIAL, arms NEVER on USB 3-1
vary         orange position across the three bands, plate position too
```

**TWO SEPARATE SCORES, never blended** - the demos taught two things at once
(a target, and a wider pickup zone), so one number would be uninterpretable:

```text
A) GRASP  did the orange leave its starting position? which band was it in?
B) PLACE  did the orange end ON the plate, or get carried toward it at all?
```

Scoring is automated and now requires BOTH a sustained >=10-cycle finger block
AND confirmed movement of the orange (see "scoring" below).

**Decision after ten trials:**

```text
carries sometimes (>=3/10)   -> the design works, it needs more data.
                                Record 40-60 more demos as in step 3.
grasps but NEVER carries     -> the demos may need to differ in KIND, not
                                number. Inspect what the wrist sees at the
                                moment of release before recording more.
does not grasp reliably      -> plate_v1 has cost the picking skill in a way
                                the offline gate missed. Fall back to the
                                frozen baseline and re-plan.
```

---

## Step 3 — expand the dataset (only if step 2 says so)

```text
target       60-80 plate demos total
proportions  ~40% familiar band, ~40% operator-right, ~20% operator-left
```

**Two changes from last time, both non-negotiable:**

1. **HOLD 5-10 PLATE DEMOS OUT OF TRAINING.** With all 20 in training, "did the
   plate skill improve?" cannot be answered offline at all. This is the wall
   plate_v2 hit and the single most valuable change available.
2. **Switch to the ESP32 wrist camera AT this session, not before.** The demos
   and the camera then match from the start, and the ribbon failure retires
   permanently. Switching at any other time means re-recording everything.

---

## Step 4 — train, and stop at 6000 steps

```text
from     orange_pick_baseline_v1  (NOT plate_v1 - start clean from the frozen
         baseline so the result is attributable)
data     new plate demos + the 79 orange demos MIXED IN (anti-forgetting)
steps    6000. MEASURED: doubling to 12000 gained 2.50 -> 2.37 then worsened
         to 2.46, a spread within noise (paired test, 1.1 standard errors).
gate     held-out orange error must stay near 2.41, AND the held-out PLATE
         demos give the first real offline read on the plate skill
```

---

## Standing rules earned the hard way

```text
CAMERA     ENFORCED IN CODE since 2026-09-03. The client refuses to start
           unless the wrist frame is < 1.5 s old AND two fetches a second
           apart DIFFER, and aborts mid-run after three stale frames.
           Verified against the frozen Pi proxy and a powered-off ESP32.
           HTTP 200 is NOT proof - a frozen proxy returns 200 forever.
           Five trials were lost to this before the guard existed.
USB        arms NEVER on port 3-1. Resolve ports by SERIAL, never by name.
GRASP      a grasp requires a SUSTAINED >=10-cycle finger block AND the orange
           moving in the front camera. Total blocked cycles is NOT enough -
           207 cycles of servo chatter once outscored a real 20-cycle hold.
SCENE      photograph the scene before a control run and CHECK it. A plate was
           present during a "no plate" control on 2026-09-02, invalidating it.
MACHINE    the GPU box also runs the DYNUS flight campaign. EXIT=143 with a
           clean log is systemd-oomd, not a bug. Checkpoint often; the flights
           are the priority and training gives way.
PREMISE    test the premise before building the fix. The viewpoint-augmentation
           plan was killed by a 15-minute probe that would otherwise have cost
           2 h of GPU and a wrong conclusion.
```

---

## Open questions, honestly stated

```text
Why did all three ESP32 runs fail to grasp?
  UNEXPLAINED. Two hypotheses tested and rejected: "different sensor images"
  (never isolated - the first control had a plate in the scene) and "viewpoint
  brittleness" (rejected: a 40 px shift costs +0.13 against +3.3 for a wrong
  image). No positive control exists. Do not theorise further - measure.

Does plate_v1 carry to the plate?
  ONE trial says no. That is an anecdote, not a measurement. Step 2 settles it.

Would full fine-tuning help?
  NEVER TESTED. The vision encoder (1.87 B params, 57% of the model) has been
  frozen in every run, inherited from NVIDIA's default recipe. Unfreezing needs
  ~7.5 GB more than the card has spare, and 99 episodes is thin for 1.87 B
  parameters - but the experiment has not been run, and "we never questioned
  the default" is an admission, not a justification.
```

---

## Model registry

See `MODELS.md`. Stable names only - `orange_pick_baseline_v1`, `plate_v1`.
`checkpoint-N` is a per-run step counter, NOT a version; a newer model can carry
a smaller number. Every checkpoint now writes `LINEAGE.json` at training time
recording its parent, dataset and settings.
