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

### Sharpened by the user (2026-08-06): domain match is NECESSARY, NOT SUFFICIENT

Pi05 was trained on 40,712 frames of OUR real table and still fails ON that
table. So the grid is:

```text
                     in-domain data          out-of-domain
GR00T architecture   WORKS (N1.6 in sim)     fails (N1.7 in sim)
Pi05  architecture   FAILS (our real arm)    fails (sim)
```

Every cell is measured except one: **GR00T + our real data + our real arm.**
GR00T-with-in-domain-data is the only combination that has ever worked anywhere
in this project — and Pi05 failing WITH the domain advantage is the strongest
evidence the problem is Pi05's architecture/recipe, not deployment.

Two implications, honestly:

- the as-is hardware test (step 1 below) starts from further back than domain
  logic alone suggests — in-domain training didn't save Pi05 on hardware
- if our 89 episodes are themselves flawed, GR00T inherits the flaw. Counter-
  point: sim N1.6 succeeded off ~60 episodes, fewer than our 89, so quantity
  alone is not the problem. A GR00T failure on our data would finally isolate
  DATA QUALITY as the variable — an answer Pi05's failures could never give.

---

## 3. THE PLAN (revised 2026-08-06 — user's correction)

### Step 0 — ROBUSTNESS CAMPAIGN IN SIM — **_ DONE 2026-08-06, GATE LIFTED _**

```text
17/18 runs scored (twoPlates crashed on a known script bug). Full results:
-> n16_robustness_campaign_20260806.md

THE THREE FINDINGS
  1. APPEARANCE IS FREE. Blue plate, GREEN ROBOT, 35% light, warm light, small
     oranges - all essentially unaffected. dimLight was the campaign's cleanest
     run (3/3, zero drops).
  2. GEOMETRY COSTS ~ONE ORANGE. Everything-moved is reliably 2/3. Perception
     is object-directed; precision suffers. Camera mount: 2 cm FREE, 5 cm
     fumbling-but-functional.
  3. DECOYS ARE FATAL. Two orange-colored spheres -> 1/3. [SUPERSEDED at
     n>=3, 08-07: decoys recovered to 6/9 = 67% - moderate, not fatal. The
     TRUE worst condition is the MOVED PLATE at 3/9 = 33%. Geometry, not
     lookalikes, is the weak axis. -> n16_robustness_campaign doc section 5]

WHAT IT DECIDED (per the rules agreed before the results)
  camera mounting   has slack - careful, not obsessive
  TABLE CLEANLINESS THE hard requirement: nothing orange-ish near the workspace
  room lighting     ignore
  expectations      "purposeful reach" is the realistic as-is goal on real
                    pixels; completion would be a pleasant surprise

WHY THIS MILDLY RAISES THE AS-IS TEST'S ODDS
  The sim->real gap is largely an APPEARANCE gap, and appearance is exactly
  where this policy proved robust. Bounded encouragement only: tints and
  lighting are still the SAME renderer - real optics, noise and textures are a
  bigger step than any variation we could synthesize.
```

### Step 1 — TRY THE SIM-TRAINED N1.6 CHECKPOINT AS-IS ON THE REAL ARM

Added on the user's standing rule: _"instead of guessing we could just test,
because testing doesn't cost us much."_ The prediction is that it fails (visual
domain gap, and Pi05 failed even in-domain) — but a prediction is not a
measurement, this is literally the project's original use-others'-work-as-is
strategy, and **nothing is wasted either way**: the serving path built for this
test is the SAME one the fine-tuned model needs later, and a failure MEASURES
the sim-to-real gap on the exact architecture we intend to use.

#### Scoped 2026-08-06 — what the as-is test actually needs

```text
ALREADY IN PLACE
  checkpoint     12e21/gr00t_n1d6_leisaac_pick_orange, local, serves in 8.2 GB
  server         gr00t.eval.run_gr00t_server on :5556 - the exact stack that
                 scored 15/15 in sim
  real-arm client SHIPS WITH THE REPO: gr00t/eval/real_robot/SO100/eval_so100.py
                 - drives an SO-101 via LeRobot robot classes, packages
                 front+wrist frames + state, queries the server, streams actions.
                 Its camera_keys are hardcoded ["front","wrist"] - exactly what
                 the checkpoint wants.
  calibration    ~/.cache/huggingface/lerobot/calibration/robots/so_follower/
                 my_so101_follower.json (transferred + verified day 1)
  units          NO conversion layer needed on real hardware - the arm speaks
                 LeRobot motor units natively, which is what the checkpoint was
                 trained on. The sim needed rad<->motor conversion; the real arm
                 does not. One less place to be wrong.

NEEDED - SOFTWARE (me)
  1. pip install lerobot into the n1.6 venv (it is NOT there - eval_so100.py
     imports lerobot.robots). RISK: must not disturb torch 2.7.1+cu128/sm_120.
     Verify torch after install; use --no-deps if it tries.
  2. Smoke-test eval_so100.py end-to-end with the server, no robot attached
     (it should fail at hardware discovery, proving imports and wiring).
  3. Only TWO cameras needed: front + wrist. The top camera - required for
     Pi05's 3-camera gate - is NOT used by GR00T. Simpler rig than every
     previous real-arm session.

NEEDED - HARDWARE (the user)  [rig spec UPDATED by the step-0 campaign]
  4. Plug in the arm (currently NO /dev/ttyACM*) and the front + wrist cameras
     (currently NO /dev/video*). Wrist previously came via the RPi bridge as
     /dev/video6 - needs re-checking on this machine.
  5. MOUNT THE FRONT CAMERA TO MATCH THE SIM: rigidly attached to the ROBOT
     BASE at pos=(0.0, -0.5, 0.6) relative to base, focal 28.7 (sim spec).
     Campaign result: there is SLACK - 2 cm off was free, 5 cm off fumbled but
     worked. Mount carefully; do not obsess over millimetres.
  6. Scene: orange(s) + a plate, roughly the sim layout. Geometry has slack too
     (moved objects cost ~one orange, not the task).
  6b. *** HARD REQUIREMENT 0 - LAYOUT MATCH (n=3 finding, 08-07). *** Plate
     left, oranges clustered 10-15 cm right, matching the sim's canonical
     arrangement. The displaced GOAL is the measured worst condition (33%);
     match the layout before worrying about anything visual.
  7. *** HARD REQUIREMENT 1 - A CLEAN TABLE. *** Nothing orange-ish anywhere
     near the workspace. Two orange decoy spheres was the ONE scene variation
     that broke the policy (1/3, two oranges never touched). No clutter.
  8. *** HARD REQUIREMENT 2 - LOCK THE CAMERAS' WHITE BALANCE (preflight
     finding). *** gamma/white-balance shift was the ONE observation-pipeline
     defect that broke it: 0/3, the worst run of the entire preflight, while
     even a full BGR channel swap was invisible. Webcams auto-white-balance
     continuously by default. Disable it (cv2 CAP_PROP_AUTO_WB=0 or v4l2-ctl)
     and lock exposure BEFORE the first episode.
  9. Room lighting: intensity/warmth do not matter (proven twice). What
     matters is that the CAMERA's rendering of it stays CONSTANT - see 8.
 10. Scene may use 1 or 3 oranges - the single-orange run passed (1/1).

RUN PROTOCOL
  instruction "Grab orange and place into plate"  (the string that worked in sim)
  workspace clear, hand on the kill switch, start from rest pose
  RECORD the episode (video + trace)
  score with analyze_grasp_from_trace.py's finger-stall test - NEVER
  "gripper closed" alone. Sim twin of the object-displacement rule.

VERDICT RULES
  works at all      -> enormous result, the original bet pays; iterate in place
  reaches wrong     -> visual gap dominates; fine-tune (step 2) attacks exactly this
  freezes / erratic -> check the SERVING path first (sim regression run on :5556)
                       before blaming the model - Era 1's lesson.
```

### Step 2 — Fine-tune GR00T N1.6 on OUR 89 REAL episodes

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

### Step 3 — Serve the FINE-TUNE on the real arm, same protocol as step 1

```text
NOT in the simulator. This is the step that has never happened.
Score with analyze_grasp_from_trace.py's FINGER-STALL test - fingers cannot pass
through an object - which is the real-world twin of the object-displacement
check that exposed a convincing false "grasp" in sim.
NEVER accept "gripper closed" as evidence of a grasp, in either environment.
```

### Step 4 — Keep the simulator as a REGRESSION HARNESS

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
0.  DONE - robustness campaign. Verdicts: appearance free, geometry ~one
    orange, DECOYS FATAL -> the real table must be CLEAN. Camera: 2 cm slack.
0b. *** DONE 2026-08-06 *** SIM-TO-REAL PREFLIGHT - first run COMPLETE, all
    stages passed. Verdicts: Stage A client VERIFIED end to end (incl. live
    handshake); BGR swap has NO behavioral signature (source check is the only
    guard); WHITE BALANCE is the one killer (0/3) -> new hard rig requirement;
    staleness free; single-orange scene passes.
    (STANDING PROTOCOL - repeats before EVERY future hardware deployment):
      Stage A  client equivalence: field-by-field desk check of the real
               client vs the validated sim client + no-robot smoke test.
               THE Era-1 check. Any mismatch is fixed before power-on.
      Stage B  failure-signature runs: BGR swap, noise, blur, JPEG, white
               balance, stale observations, camera ANGLE, wrist-cam jitter -
               one defect per run, so hardware misbehaviour can be matched
               against a known signature instead of guessed at.
      Stage C  exact-scene match: sim run with the scene the user will
               physically build.
    ~2.5 h total. Decision rules pre-agreed.
    -> sim_to_real_preflight_protocol_20260806.md
1.  AS-IS HARDWARE TEST of the sim-trained N1.6 - 0b PASSED; waits ONLY on the
    user's hardware half now (full checklist: STATE_20260806.md section 2):
     me:   DONE - lerobot 0.4.4 installed (torch intact), client patched,
           smoke-tested, live handshake verified
     user: plug in arm + front/wrist cameras, mount front camera (careful not
           obsessive), LOCK WHITE BALANCE + EXPOSURE on both cameras,
           CLEAN TABLE - nothing orange-ish in the workspace
2.  In parallel, 8-bit Adam -> unblock fine-tuning (needed if step 1 fails,
    which is likely; costs nothing to prepare)
3.  v3.0 -> GR00T v2 converter for our 89 real episodes   (drop `top`)
4.  fine-tune GR00T N1.6 on our real data
5.  serve the fine-tune on the arm - SAME serving path step 1 already built -
    PREFLIGHT REPEATS first (Stages B/C: the policy changed; Stage A only if
    the client changed), then score with the finger-stall test
6.  (absorbed into 0b - the preflight IS the sim regression check, made
    systematic)

PARALLEL TRACK (user's proposal, investigation done, recipe ready):
  SM + variations + success filter -> diverse v3.0 episodes -> fine-tune Pi0.5
  (closes architecture-vs-data). One build item: sm_generate_varied.py.
  Batch matrix + honest throughput + memory caveat:
  -> sm_data_generation_track_20260806.md section 6
  Hardware STILL preempts this the moment the arm is plugged in.

Optional sim follow-ups, NOT gating anything:
  - characterize the decoy failure (does it GRAB decoys or freeze? log decoy
    positions in the eval script)
  - fix --add-plate (known broken) if the goal-ambiguity answer matters
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

## 6b. INSERTED 2026-08-08 — real-mimic battery before the fine-tune

The as-is hardware test is DONE and FAILED (`REALARM_RESULT_20260808.md`:
coherent motion, zero object-directedness). Before the N1.6 real-data
fine-tune, one overnight diagnostic runs on otherwise-idle GPU:
**`n16_realmimic_sim_battery_20260808.md`** — recreate the real rig's content
(tomato-red fruit, wood table, paper plate, camera offset) inside sim and
measure what each ingredient costs N1.6 at n>=3. It names the gap's
ingredients and derisks the post-fine-tune hardware test; it is a diagnostic,
NOT a gate — the fine-tune proceeds either way.

---

## 7. What "done" looks like

```text
The real SO-101 arm picks up an orange and places it, and the finger-stall trace
confirms the object was actually held - not the gripper closing on air.

That has never happened in this project. Every metric in every other document is
a proxy for it.
```
