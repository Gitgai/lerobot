# LeIsaac environments, datasets and checkpoints — what we can actually run

Date: 2026-08-05. Source: https://lightwheelai.github.io/leisaac/resources/available_env/
cross-checked against the LOCAL install and the Hugging Face APIs.

---

## 1. The five environments, and what each needs

```text
TASK              ENV ID                              SCENE NEEDED        HAVE IT?
Pick Orange       LeIsaac-SO101-PickOrange-v0         kitchen_with_orange   YES
Lift Cube         LeIsaac-SO101-LiftCube-v0           table_with_cube       no (9 files)
Clean Toy Table   LeIsaac-SO101-CleanToyTable-v0      lightwheel_toyroom    no (80 files)
Fold Cloth        LeIsaac-SO101-FoldCloth-BiArm-v0    lightwheel_bedroom    no (100 files)
Cleanup Trash     LeIsaac-LeKiwi-CleanupTrash-v0      (LeKiwi, not SO-101)  no

15 task IDs are registered locally (Direct/Mimic/BiArm variants of the above).
WE HAVE EXACTLY ONE SCENE: kitchen_with_orange (127 MB).

Scenes downloadable from HF `LightwheelAI/leisaac_env`:
    kitchen_with_orange, table_with_cube, lightwheel_toyroom, lightwheel_bedroom
NOT in that repo (referenced in code, source unknown):
    kitchen_with_hamburger (AssembleHamburger), lightwheel_loft
```

**Cheapest expansion by far: `table_with_cube` is 9 files.** LiftCube is
single-arm SO-101, front+wrist, and is Mimic-capable — the natural second scene.
FoldCloth and CleanToyTable-BiArm need TWO arms, which we do not have even in
principle for the real transfer.

---

## 2. Can we generate data? Three paths, very different costs

```text
1. SCRIPTED STATE MACHINE   ***ONLY PickOrange***
   leisaac ships exactly one: datagen/state_machine/pick_orange.py
   Fully automatic, no human, no hardware. This produced our 12 place ops and
   the harness positive control.
   -> Any OTHER task would need us to WRITE a state machine.

2. ISAAC LAB MIMIC          PickOrange AND LiftCube
   scripts/mimic/{annotate_demos,generate_dataset}.py
   Take a few source demos -> annotate subtask boundaries -> generate MANY
   augmented episodes. This is the scalable path and it is NOT limited by
   teleoperation time. LightwheelAI shipped a mimic dataset themselves
   (leisaac-pick-orange-mimic-v0, 60 eps / 41,891 frames).

3. TELEOPERATION            any task
   Needs the leader arm plugged in. The only route for CleanToyTable, FoldCloth
   and CleanupTrash today.
```

So: **for the two tasks we can realistically pursue (PickOrange, LiftCube) we
can generate as much data as we want without touching hardware.** That is the
answer to "can we generate datasets for fine-tuning" — yes, and by two
independent methods for PickOrange.

---

## 3. Public datasets — yes, and one is a perfect match

```text
LightwheelAI/leisaac-pick-orange            *** THE REFERENCE ***  465 downloads
    v2.1 | 60 episodes | 36,293 frames | 30 fps | robot so101_follower
    cameras: front + wrist          <- EXACTLY our scene's two cameras
    task string: "Grab orange and place into plate"

LightwheelAI/leisaac-pick-orange-mimic-v0   v2.1 | 60 eps | 41,891 frames
    the Mimic-generated counterpart of the above

The11One/isaac_sim_so101_lift_cube          v3.0 | 50 eps | 8,800 frames | 10 fps
    cameras: side + top, robot "unknown"  <- a DIFFERENT rig, not drop-in

community pick-orange copies: alizaidi, ASBJ021, khb2439, shuni52 (x2), Toby0614
also: aaronsu11/so101_fruit_leisaac (40 dl)
```

`LightwheelAI/leisaac-pick-orange` matches our scene, robot, camera set and
resolution. It is the obvious fine-tuning corpus for either Pi05 or GR00T, and
it is **v2.1** — which is what GR00T's loader wants, and which our own LeRobot
does not write (we write v3.0; only a forward v2.1->v3.0 converter ships).

---

## 4. *** THE TASK STRING, SETTLED ***

```text
meta/tasks.jsonl of the official dataset:
    {"task_index": 0, "task": "Grab orange and place into plate"}
```

This closes the instruction question that has been open all day:

```text
THE ENV declares    "Pick three oranges and put them into the plate, then reset
                     the arm to rest state."      (cfg.task_description)
THE DATASET uses    "Grab orange and place into plate"

THEY ARE DIFFERENT, AND THE DATASET STRING IS THE ONE A TRAINED MODEL SAW.
```

It also confirms the phrasing-pattern hypothesis: the canonical form really is
`Grab <object> and place into <container>`, which is why the accidental
"Grab pens and place into pen holder" outperformed the invented
"pick up the orange and move it to another place".

### GR00T N1.7 across all three instructions (900 steps each, same scene)

```text
instruction                              d_min  d_grasp  pickTRUE  objLift
invented   "pick up the orange..."       0.164      -         0    0.0000
wrong-obj  "Grab pens and place..."      0.110    0.039      80    0.0029
CANONICAL  "Grab orange and place..."    0.100    0.047       3    0.0234
------------------------------------------------------------------------
state machine (known-good reference)     0.111    0.021     842    0.1959
```

The canonical string gets the **closest approach** and is the **only one that
actually moves the orange** (2.3 cm, 8x the pens run) — but it holds for 3 steps
and lifts 8x less than a real grasp. **The instruction is worth real
performance, and it is not enough.** This checkpoint still cannot pick in this
scene.

> Practical rule: read `meta/tasks.jsonl` of the dataset a checkpoint was
> trained on. Do not use the env's `task_description`, and never invent one.

---

## 5. Checkpoints for these environments

```text
PickOrange   LightwheelAI/leisaac-pick-orange-v0     GR00T N1.5  (LeIsaac authors)
             12e21/gr00t_n1d6_leisaac_pick_orange    GR00T N1.6
             omkarmayekar555/act_leisaac_orange      LeRobot ACT, 51.6M
pick-block   tshiamor/groot-n1.6-leisaac-pick-block  GR00T N1.6
LiftCube     none found
CleanToyTable / FoldCloth / CleanupTrash   none found
```

### Which of these can actually be served on a 5090 — CHECKED, not assumed

An earlier draft said flatly that "old checkpoint eras pin old torch with no
sm_120, so Era 1 and Blackwell conflict". **That is true for N1.5 and FALSE for
N1.6.** The actual pins, read from the NVIDIA/Isaac-GR00T release tags:

```text
release          torch pin    sm_120 (Blackwell / RTX 5090)?
n1.5-release     2.5.1        NO  - predates Blackwell support entirely
n1.6-release     2.7.1        YES - 2.7.x+cu128 is the first Blackwell-capable
n1.7-release     2.9.0        YES - what we run today (verified, arch list
                                    includes sm_120)
```

```text
=> LightwheelAI/leisaac-pick-orange-v0 (N1.5) IS genuinely blocked: its era
   wants torch 2.5.1, which has no sm_120 at all.

=> THE N1.6 CHECKPOINTS ARE NOT BLOCKED:
       12e21/gr00t_n1d6_leisaac_pick_orange     (LeIsaac PickOrange!)
       tshiamor/groot-n1.6-leisaac-pick-block
   n1.6-release pins torch 2.7.1, and 2.7.x+cu128 is exactly the version this
   project already verified on sm_120. LeIsaac ALSO ships a native n1.6 client,
   so none of our adapter code would sit in the path.
   Remaining risk is flash-attn==2.7.4.post1 building for Blackwell, not torch.

=> the ACT checkpoint is blocked for a DIFFERENT reason: it silently drops its
   normalization on our LeRobot 0.6.1 (old embedded norm buffers), which would
   have produced garbage that looked like a harness failure.
```

**So a matched, sim-trained comparison IS reachable** — via N1.6, not N1.5, and
it costs one era-matched venv rather than "impossible". See
`public_so101_datasets_and_checkpoints_20260805.md` for the per-checkpoint
detail.

---

## 6. What this implies

```text
FINE-TUNING IS NOW THE STRONGEST PLAY, not more public-checkpoint hunting.
  - a perfectly matched 60-episode v2.1 dataset exists and is ungated
  - we can generate unlimited more (state machine AND Mimic) with no hardware
  - the harness is proven to detect grasp, place and lift
  - and three public checkpoints in a row have failed this scene

The remaining public-checkpoint options all cost an era-matched, Blackwell-
capable environment build EACH. Fine-tuning on our own verified stack costs one
GPU run and reuses everything already validated today.
```

Suggested order:

1. Download `LightwheelAI/leisaac-pick-orange` (v2.1, 60 eps) and fine-tune
   GR00T N1.7 on it — same version we can already serve, so no era problem.
2. Add `table_with_cube` (9 files) and bring LiftCube up as a second task.
3. Use Mimic to multiply episodes rather than recording more by hand.

**Unchanged:** nothing has been tested on the real arm.
