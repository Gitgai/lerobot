# What The Simulator Can Actually Give Us, And The Camera Question

Last updated: 2026-08-05
Answers three questions raised after the first Pi05 sim runs:
  1. should we test Pi05 with two cameras?
  2. can the sim provide a THIRD camera, as Pi05 expects?
  3. do we need NVIDIA's dataset, or can the sim generate our data?

Prerequisites: the working stack in `new_machine_local_serving_20260804.md`.
Related: `sim_place_data_generation_20260805.md`, `groot_vs_pi05_comparison_plan_20260804.md`.

---

## 1. Pi05 On Two Cameras - ALREADY DONE, and it is what we measured

```text
Every Pi05 sim run so far WAS a two-camera test.
The LeIsaac kitchen scene exposes ONLY front + wrist. Our policy declares
front/top/wrist, so `top` was padded with -1 and MASKED on every step
(modeling_pi05.py:1150, per-batch masking - verified 2026-08-04).

So "test Pi05 with 2 cameras" is not a NEW experiment. It is the experiment we
ran, and the three-run result stands:
    approaches 5-9 cm, gripper range 1.0-1.4, 0/3 grasps, 0/3 places.
```

What is NOT yet separated: how much of that degradation is the MISSING CAMERA
versus the DOMAIN GAP (rendered kitchen vs our table). Adding a third camera
(Section 2) is what separates them:

```text
2 cameras -> reaches but never grasps        (measured)
3 cameras -> ?                               (would isolate the camera variable)
```

---

## 2. Giving The Sim A Third (`top`) Camera - FEASIBLE, and not hard

Cameras are ordinary config objects in the single-arm template, not baked into
the scene asset:

```text
source/leisaac/leisaac/tasks/template/single_arm_env_cfg.py
  wrist: TiledCameraCfg  prim_path "{ENV_REGEX_NS}/Robot/gripper/wrist_camera"
                         focal_length 36.5
  front: TiledCameraCfg  prim_path "{ENV_REGEX_NS}/Robot/base/front_camera"
                         focal_length 28.7
  plus a matching ObsTerm using mdp.image(sensor_cfg=..., data_type="rgb")
```

Both are attached to the ROBOT. Adding `top` means a third `TiledCameraCfg`
mounted in the SCENE looking down at the table, plus one more `ObsTerm`.
LeIsaac is EDITABLE-INSTALLED (`~/sim/leisaac-src`), so this is a local edit -
no fork, no upstream dependency.

```text
DIRECTION CORRECTED 2026-08-05 - SIM IS THE REFERENCE, NOT THE REAL RIG.
This section originally said to match the sim camera to our real C270. That is
backwards: if we train on sim data, SIM IS THE TRAINING DISTRIBUTION and the
real rig must be built to match IT. Choose the sim pose deliberately; that
choice becomes the spec the physical camera is mounted to.
See sim_first_strategy_20260805.md.

STILL TRUE EITHER WAY: it is not enough to merely HAVE a third camera. Sim and
real must AGREE. A mismatched pair is worse than two matched cameras, because
the model gets a view at deployment that does not correspond to anything it
trained on.

BONUS FINDING: TiledCamera works fine here. GitHub IsaacLab #4951 reports
TiledCamera HANGING on RTX 5090 - LeIsaac uses TiledCameraCfg throughout and we
have rendered thousands of frames with no hang. That concern is empirically
CLOSED on this machine (driver 580.173.02 + Isaac Sim 5.1).
```

---

## 3. Do We Need NVIDIA's Dataset? What Can The Sim Generate?

### The honest answer: the sim can generate ONE task automatically

```text
15 SO-101 tasks are REGISTERED. Only ONE has a scripted state machine:
  source/leisaac/leisaac/datagen/state_machine/  ->  base.py, pick_orange.py

  PickOrange      state machine  YES  -> fully automated, no human, no hardware
  LiftCube        state machine  no   -> teleop only
  CleanToyTable   state machine  no   -> teleop only
  AssembleHamburger              no   -> teleop only
  FoldCloth (bi-arm)             no   -> teleop only
  LeKiwi-CleanupTrash            no   -> teleop only (different robot)
```

So "the sim can generate unlimited data" is true for **pick-and-place-oranges
only**. Everything else needs a human driving the leader arm - which needs the
physical leader on USB, though not the follower, cameras or the Pi.

### Registered tasks (all 15)

```text
LeIsaac-SO101-PickOrange-v0 / -Direct-v0 / -Mimic-v0
LeIsaac-SO101-LiftCube-v0 / -Direct-v0 / -Mimic-v0 / -DigitalTwin-v0
LeIsaac-SO101-CleanToyTable-v0 / -BiArm-v0 / -BiArm-Direct-v0
LeIsaac-SO101-AssembleHamburger-v0 / -BiArm-v0
LeIsaac-SO101-FoldCloth-BiArm-v0 / -BiArm-Direct-v0
LeIsaac-LeKiwi-CleanupTrash-v0
```

`-Mimic-` variants AUGMENT recorded demos (MimicGen); they still need seed demos.

### Scenes available

```text
DECLARED in code: kitchen_with_orange, kitchen_with_hamburger, table_with_cube,
                  lightwheel_bedroom, lightwheel_loft, lightwheel_toyroom
DOWNLOADED so far: kitchen_with_orange (v0.1.0 release, 70 MB)
ALSO on releases:  table_with_cube (v0.1.2). Other scenes are referenced in code
                   but their assets are not in the releases we checked - the
                   docs point at lightwheel.ai for more.

=> MULTIPLE SCENES IS THE INTERESTING PART. PI's ablation (handoff Section 6)
   ranks ENVIRONMENT DIVERSITY as the single most damaging thing to remove
   (OOD success -> 31%). Different scenes is the one variable our single real
   table structurally cannot provide. Downloading more scenes is cheap.
```

### Can we WRITE state machines for the other tasks? Yes - and it is tractable

```text
source/leisaac/leisaac/datagen/state_machine/
  base.py         100 lines  - StateMachineBase, 5 abstract methods:
                               setup(env), check_success(env), get_action(env),
                               advance(), (+1)
  pick_orange.py  312 lines  - the full working reference implementation

=> ~300 lines per new task. They get PRIVILEGED STATE (exact object poses from
   the simulator, e.g. env.scene["Plate"].data.root_pos_w), so NO PERCEPTION is
   needed - that is why they are short.
```

**But question whether it is the best use of that effort.** Judged against our
actual gaps (place - now covered; position/scene generalization - not):

```text
CleanToyTable      places into a BOX - different target, different objects.
                   The only one that clearly earns its 300 lines.
LiftCube           no place phase. We already have place. Low value.
AssembleHamburger  complex multi-object sequencing, far from our task.
FoldCloth          BI-ARM and deformable. We have ONE arm. Not applicable.

CHEAPER ROUTE TO THE SAME BENEFIT:
  Our remaining verified gap is POSITION / SCENE generalization. That can be
  attacked with the state machine we ALREADY have, by varying orange positions
  and swapping scenes - NO NEW CODE, since LeIsaac is editable-installed and
  six scenes are declared.

  Varying PickOrange costs nothing. Writing CleanToyTable costs ~300 lines for
  one more task family. EXHAUST THE FIRST BEFORE STARTING THE SECOND.
```

### So: do we need NVIDIA's `finish_sandwich` / `so101-table-cleanup` dataset?

```text
NOT for data value - we can generate our own place demos, and ours are in OUR
task domain (oranges), not sandwiches.

YES for PIPELINE VALIDATION, and that is worth doing first:
  it is KNOWN-GOOD data in the format GR00T expects. Fine-tuning on it proves
  the GR00T pipeline works BEFORE we debug our own conversion on top of an
  unproven pipeline. That is Stage 3b-0 in the GR00T plan and it is the Era 1
  rule again: validate the harness against a known-good answer first.

Our own sim data needs TWO conversions to reach GR00T:
  LeIsaac HDF5 --isaaclab2lerobotv3.py--> LeRobot v3
               --convert_v3_to_v2.py-->    LeRobot v2  (GR00T wants v2)
Both scripts ship upstream. Neither is yet tested by us.
```

---

## 4. Recommended Order

```text
1. GR00T pipeline validation on NVIDIA's own dataset (izuluaga/finish_sandwich).
   Known-good, proves the fine-tune path. No robot, no conversion of ours.
2. Vary the ORANGE POSITION in sim and re-run Pi05.
   Separates "reaches for the orange" from "reaches toward the table centre".
   Until this is done, only "it reaches" is established. CHEAP AND HIGH VALUE.
3. Add a `top` camera matched to our real rig, re-run Pi05.
   Separates the missing-camera penalty from the domain gap.
4. Convert our 4 sim place episodes to LeRobot v2 and fine-tune GR00T on them.
5. Download more scenes; generate PickOrange demos across several environments.
   This is the environment diversity our real table cannot produce.
```

Steps 2 and 3 are experiments on a model we already have, cost only GPU time,
and each isolates ONE variable - which is this project's hard rule #8.

---

## 5. Open Questions

```text
Is Pi05's sim reach ORANGE-DIRECTED or a positional prior?      -> step 2
How much of the 2-camera penalty is the missing top view?       -> step 3
Can a top camera be posed closely enough to our real C270 for
  the model to actually use it?
Do sim demos transfer to the real arm at all?                   -> unproven,
  the load-bearing unknown behind all of this
Would writing state machines for other tasks be worth it?
  (only pick_orange has one; the base class is small)
```
