# THE PLAN — get the real arm working, via GR00T

Date: 2026-08-06. Supersedes `finetune_plan_sim_pick_place_20260805.md` as the
active plan. That document's Phase 1 is explicitly **dropped** — see section 5.

---

## 1. The goal, restated

```text
GET THE PHYSICAL SO-101 ARM PICKING AND PLACING.

Everything else - the simulator, the scoring harness, the public checkpoints,
the fine-tuning - is INSTRUMENTAL. A simulator score is not the product.
```

This needs restating because two full days of work produced excellent simulation
results and **zero** hardware results.

---

## 2. Where we honestly stand

```text
SIMULATION: SOLVED
  Isaac Sim 5.1 + Isaac Lab 2.3.0 + LeIsaac 0.4.0 running, driver pinned 580.173.02
  scoring harness VERIFIED against a known-good actor (positive control)
  a public checkpoint does the task 100%: 12e21/gr00t_n1d6_leisaac_pick_orange,
    5/5 runs, 15/15 oranges placed, stdev 0.00, every grasp real (lift >0.10 m)

REAL ARM: UNTOUCHED FOR TWO DAYS
  and before that, 0 successful places in the ENTIRE project history

PI05 FAILS IN BOTH PLACES
  real arm: 145 empty squeezes, 0 places, ever
  sim:      tracks the orange to 0.073 m, 0 grasps, in EVERY run
  => two INDEPENDENT failures of the same checkpoint, on the same task
```

### The finding that drives this plan

```text
TRAINING DOMAIN DOMINATES MODEL SIZE AND BREADTH.

  GR00T N1.6, 1.09B DiT, trained IN this simulator   -> 15/15 oranges placed
  Pi05 012000, 4.14B, trained on REAL frames of this task -> 0 grasps
  GR00T N1.7, broad community mix (2,242 eps/39 repos)    -> 0 grasps

A quarter the parameters beat both, because it was in-domain.
```

**The actionable reading: GR00T's architecture solves this task class where Pi05
does not.** Pi05 has now failed on our data repeatedly, in two environments. The
sensible move is to change the ARCHITECTURE, not to keep tuning the one that
does not work.

---

## 3. THE PLAN

### Step 1 — Fine-tune GR00T N1.6 on OUR 89 REAL episodes

This is the main line. Rationale:

```text
GR00T demonstrably works for this task class (proven above)
our real data is the ONLY asset describing our actual table, arm and calibration
Pi05 - a different architecture on that same data - has failed twice
```

Two concrete blockers, both solvable:

```text
BLOCKER A - MEMORY CEILING (32 GB)
  The fine-tune needs more than 31.35 GB as configured. It OOMs at batch 16,
  at batch 8, with gradient checkpointing, and with bf16 weights - ALWAYS inside
  _multi_tensor_adam. Batch-independence proves it is OPTIMIZER STATE, not
  activations:
      trained params   weights + grads + Adam(2 fp32 moments)
      DiT only 1.09B   2.2 + 4.4 + 8.7 = 15.3 GB   fits
      ALL params ~3B   6.0 + 12.0 + 24.0 = 42.0 GB  does NOT fit
  FIX: 8-bit Adam (adamw_bnb_8bit) - cuts optimizer state ~4x, 24 GB -> ~6 GB.
       One config change plus bitsandbytes. Alternative: adafactor.
  NOTE: NVIDIA's recipe presumably targets 80 GB cards.

BLOCKER B - DATASET FORMAT
  ours   v3.0, data/chunk-000/file-000.parquet (consolidated),
         cameras front + TOP + wrist, 89 eps / 40,712 frames
  needed v2 layout, data/chunk-000/episode_NNNNNN.parquet (per-episode),
         cameras front + wrist ONLY, plus GR00T-flavored meta:
         modality.json + stats.json + relative_stats.json
  Only a FORWARD v2.1->v3.0 converter ships in LeRobot. There is no backward
  path, so this needs writing.
  Dropping `top` is REQUIRED, not optional - GR00T declares front+wrist, and S2
  proved a view the model never trained on is actively harmful.
```

### Step 2 — Serve it on the REAL ARM and measure properly

```text
NOT in the simulator. This is the step that has never happened.
Score with analyze_grasp_from_trace.py's FINGER-STALL test - fingers cannot pass
through an object - which is the real-world twin of the object-displacement
check that exposed a convincing false "grasp" in sim.
NEVER accept "gripper closed" as evidence of a grasp, in either environment.
```

### Step 3 — Keep the simulator as a REGRESSION HARNESS

```text
Its real value is validating a SERVING PATH before hardware touches it. The
Era-1 class of bug - right checkpoint, wrong-era code, silently wrong numbers -
has burned this project repeatedly, and sim catches it for free.
Use it to answer "is my serving stack correct", not "is my policy good".
```

### Free, do anytime — MATCH THE FRONT CAMERA

```text
The sim's front camera is rigidly mounted on the ROBOT BASE:
    prim_path  {ENV}/Robot/base/front_camera
    pos        (0.0, -0.5, 0.6)      relative to the base
    focal      28.7
Physically matching this costs nothing, is reversible, and makes every future
sim/real mixing experiment cheaper. Do NOT invent a pose - S2 showed an invented
camera pose cut Pi05's near-object time from 86% to 23%.
```

---

## 4. Order of work

```text
1. 8-bit Adam / adafactor -> unblock fine-tuning         (needed by everything)
2. v3.0 -> GR00T v2 converter for our 89 real episodes   (drop `top`)
3. fine-tune GR00T N1.6 on our real data
4. serve on the REAL ARM, score with the finger-stall test
5. sim regression check of the serving path before step 4 touches hardware
```

---

## 5. What we are DROPPING, and why

```text
PHASE 1 of the previous plan (reproduce their fine-tune on their dataset)
  It answers "could we train one if we needed to". We already HAVE a working sim
  checkpoint, and the thing blocking the user is HARDWARE, not sim capability.
  The memory fix it needs is the SAME one step 1 needs, so nothing is wasted.
  Its data-prep work is already done and committed if we ever want it back:
  the dataset is GR00T-flavored and the modality config exists.

HUNTING MORE PUBLIC CHECKPOINTS
  Three have now failed this scene. The ONE that works, works because it was
  trained IN-DOMAIN - which is exactly why it will not help the real arm.
  Every remaining candidate costs an era-matched environment build.

FURTHER SIM TUNING FOR ITS OWN SAKE
  The sim is solved. More sim numbers do not move the goal.
```

---

## 6. The honest risks

```text
1. 89 EPISODES MAY NOT BE ENOUGH. Pi05 had 40,712 frames and still failed. If
   GR00T also fails on the real arm, the answer is probably MORE AND BETTER REAL
   DATA - and that is where the sim's state machine genuinely helps, by showing
   what a good demonstration looks like (12 clean place operations, which the
   real rig has never produced).

2. SIM-TRAINED DATA WILL NOT TRANSFER ALONE. Today proved domain mismatch
   dominates, in one direction. Sim-data -> real-arm is the same bet reversed.
   If we use sim data at all, CO-TRAIN it with the real episodes; do not train
   on sim alone and expect hardware to work.

3. GR00T MAY FAIL TOO. It is a different architecture, not a guarantee. The
   value of trying it is that it is the ONE architecture we have watched succeed
   at this exact task, and Pi05 is the one we have watched fail twice.
```

---

## 7. What "done" looks like

```text
The real SO-101 arm picks up an orange and places it, and the finger-stall trace
confirms the object was actually held - not the gripper closing on air.

That has never happened in this project. Every metric in every other document is
a proxy for it.
```
