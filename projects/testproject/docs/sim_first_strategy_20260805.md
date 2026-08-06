# Sim-First: The Simulator Is The Reference, The Real Rig Matches It

Last updated: 2026-08-05
Status: STRATEGY DECISION (user, 2026-08-05). Supersedes the implicit assumption
in earlier docs that the REAL rig is the reference and sim approximates it.
Related: `sim_capability_and_camera_plan_20260805.md`,
`sim_place_data_generation_20260805.md`, `groot_vs_pi05_comparison_plan_20260804.md`.

---

## 1. The Decision

```text
USER, 2026-08-05: "we are interested in sim to real transfer. so we should test
everything in sim first, and we will match hardware like camera settings etc to
match sim."
```

This **inverts** how earlier docs were written. They said things like "add a top
camera to sim **matched to our real C270**" - treating the physical rig as the
reference. That is backwards if sim is where training data comes from.

```text
IF WE TRAIN ON SIM DATA, SIM IS THE TRAINING DISTRIBUTION.
The real robot must see what the training data saw. There is no version of
sim-to-real where the two configurations differ and it still works.

=> SIM IS THE REFERENCE. The real rig gets built to match it.
```

---

## 2. Why This Is The Stronger Order

```text
THE REAL RIG IS OUR LEAST REPRODUCIBLE COMPONENT. Recorded failures, all ours:
  camera by-id path jumped to the IR SENSOR after a reboot and silently
    produced GREY 640x360 frames (hence the by-path rule)
  the front camera differs on a new laptop - the model's front view drifts
  the Pi wrist camera needs a network that does not exist on this machine
  "the laptop must physically FACE the robot" - has bitten three times
Sim camera poses are exact, versioned, and never drift.

COST ASYMMETRY. Changing sim is a config edit - free, reversible, exact.
Changing the real rig is mounting and measuring - but ONCE.

ITERATION SPEED. Sim runs cost GPU time and nothing else. We already ran three
scored Pi05 evaluations in an afternoon; the equivalent on the arm is three
sessions with a human present.
```

---

## 3. What This Changes In The Other Docs

```text
"BLOCKED ON HARDWARE" WAS THE WRONG FRAME.
The rig is not a blocker - it is the FINAL VALIDATION STEP. Everything before
it happens in sim. Re-read pi05_work_prioritization.md with that in mind: the
S1-S5 items are the main line of work, not a stopgap while we wait for hardware.

STAGE 2 (40-60 real teleop episodes) MAY SHRINK OR CHANGE SHAPE. Its job was to
supply place demos and position diversity. Sim now supplies both, in unlimited
quantity, in whatever scene we choose. What sim CANNOT supply is proof of
transfer - which is what the real rig is for.

THE TRUST EXAM IS NOT A REAL-ROBOT GATE. It validates the SERVING STACK, and
that same stack feeds 012000 to the simulator. If it is numerically wrong,
every sim result is wrong too. It remains worth doing FOR SIM REASONS.
Still blocked on the dataset transfer.
```

---

## 4. The Camera Decision This Forces

Sim currently exposes **`front` + `wrist`**. Our hard rule #4 is **three cameras
or it doesn't count**. Both cannot hold.

```text
OPTION A - DROP TO TWO on the real rig.
  Matches sim as-is. Removes the C270 and its MJPG/3-second-warmup quirks.
  Retires hard rule #4. Matches GR00T's shipped examples exactly.

OPTION B - ADD `top` TO SIM, keep three.   <- CHOSEN (user, 2026-08-05)
  Cameras are plain config objects in
  source/leisaac/leisaac/tasks/template/single_arm_env_cfg.py:
     wrist: TiledCameraCfg  Robot/gripper/wrist_camera   focal 36.5
     front: TiledCameraCfg  Robot/base/front_camera      focal 28.7
  Adding `top` = one more TiledCameraCfg mounted in the SCENE looking down,
  plus one ObsTerm. LeIsaac is editable-installed, so this is a local edit.
  THE POSE IS THEN DEFINED IN THE CONFIG FIRST, and the real top camera is
  mounted to match THAT - not the reverse.

WHAT IS NOT DEFENSIBLE: leaving sim and real mismatched.
```

### Does GR00T force us back to two? NO.

```text
CHECKED IN THE CODE 2026-08-05:
  every shipped modality.json uses 1 or 2 views (front+wrist, image+wrist_image,
  exterior_1_left+wrist_left) - but that is their EXAMPLES.
  NO max_views / num_views constant exists. `modality_keys` is a plain list and
  the loader iterates whatever is declared.
  getting_started/data_config.md shows adding cameras by extending the list.

=> Two cameras is GR00T's EXAMPLE, not a limit. Declare three and it should work.

HONEST UNCERTAINTY: absence of a config limit is not proof the MODEL handles
three views well. N1.7's vision backbone was pre-trained on some distribution of
view counts and every shipped example is 1-2. Three may work, may cost accuracy,
may blow the VRAM budget - the tutorial's ~25 GB figure is from a TWO-camera
setup and we have 32 GB. That is a margin question, not a config question.
```

### The toggle is free, so keep it - as an experiment, not a compromise

```text
`modality_keys` is per-config, so view selection is a CONFIG SWAP, not a
re-record. Record ONCE in sim with three cameras, then evaluate:

  GR00T  front + wrist            matches every shipped example; baseline
  GR00T  front + top + wrist      does the third view help, hurt, or OOM?
  Pi05   front + top + wrist      its NATIVE configuration, no masking

All three off the SAME episodes. That turns "GR00T might not take 3 cameras"
from a constraint into a measurable question.
```

---

## 5. Revised Order Of Work

```text
BASELINE EVERYTHING BELOW IS MEASURED AGAINST (4 runs, 2026-08-05)
  Pi05 012000 converges to a STABLE HOVER 13-18 cm from the nearest orange and
  holds there. 1500 steps: closest 0.130 m, 71% of steps within 0.20 m, 0/4
  grasps. 2.5x the time bought 1.5 cm - a consistent wrong distance, not a slow
  convergence. -> sim_place_data_generation_20260805.md

IN SIM (no hardware at all)
  1. MOVE THE ORANGE, re-run.   <- DO THIS FIRST, it is the cheapest and it
     decides what the baseline MEANS.
       follows the orange -> reach is OBJECT-DIRECTED; failure is final
                             positioning
       stays put          -> it is a POSITIONAL PRIOR and "reaches for the
                             orange" collapses to "reaches"
  2. ADD THE `top` CAMERA. Choose its pose DELIBERATELY - this becomes the spec
     the real rig is built to. Now diagnostic, because a stable OFFSET is what
     mismatched camera geometry would produce.
       hover distance changes    -> camera geometry implicated
       hover distance unchanged  -> look to appearance/lighting/physics
  3. RE-RUN PI05 with all three cameras against the 2-camera baseline.
  4. RE-RECORD place demos with three cameras.
  5. GR00T pipeline validation on NVIDIA's data, then fine-tune on ours.
  6. Multiple scenes for environment diversity (6 declared, we hold 1).

ON THE REAL RIG (last, and only then)
  7. Build the physical camera setup to match the sim config from step 2.
  8. Deploy and measure transfer. THIS is what the hardware is for.

NOTE steps 1 and 2 swapped order vs the first draft of this doc: moving the
orange is cheaper than adding a camera AND it gates the interpretation of
everything else, so it goes first.
```

---

## 5b. MATCH ONE SCENE, OR MAKE SIM DIVERSE? (raised 2026-08-05)

The strategy above says "build the real rig to match sim". S2 then showed that a
**mismatched** match is worse than none (an invented `top` camera pose cut time
near the object from 86% to 23%). That forces the question of what "match" means.

```text
STRATEGY A - one sim scene, real rig built to match it
  + exact correspondence, easy to reason about
  - brittle: lighting, texture, table height, object appearance are all silent
    gaps unless each is matched too
  - optimises for ONE environment

STRATEGY B - make sim DIVERSE enough that the real rig falls inside it
  vary scenes, lighting, camera poses, object positions; train on the spread;
  the real setup then needs only to be WITHIN range, not identical
  + PI's ablation: removing environment diversity hurt WORST (OOD -> 31%),
    worse than removing cross-embodiment (49%) or web data (80%)
  + LeIsaac declares SIX scenes and object positions are config values, so
    generating the diversity is cheap
  - more data and compute (both effectively free locally now)

THE ARGUMENT AGAINST A IS OUR OWN FAILURE: 012000 was trained on ONE table and
is welded to it - 145 empty squeezes when an onion moved a few inches. Building
a sim that matches one real setup risks reproducing that brittleness elsewhere.

RECOMMENDATION: aim at B; use A only where it is cheap. Do NOT try to replicate
the sim kitchen physically. Match what a model cannot easily be robust to
(camera COUNT and rough placement, task structure, object type) and RANDOMISE
the rest in sim rather than replicating it in the world.
```

---

## 6. The Honest Limit

```text
CAMERAS ARE ONE DIMENSION OF THE SIM2REAL GAP. Also unmatched: lighting,
textures, object appearance (a rendered orange vs a real one), physics, and
gripper contact dynamics. Matching camera poses REMOVES ONE KNOWN VARIABLE.
It does not close the gap.

AND THE LOAD-BEARING UNKNOWN IS UNCHANGED: whether ANY sim-trained behaviour
transfers to this arm is unproven. 012000 was fine-tuned entirely on real teleop.
This strategy is a bet that sim2real is achievable if the configurations match -
a reasonable bet, and the whole point of step 8, but still a bet.

Do not let the volume of sim work create the impression it is settled.
```
