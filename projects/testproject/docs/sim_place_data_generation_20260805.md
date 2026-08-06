# Simulated Place Data: The Scripted Route To Our One Total Gap

Last updated: 2026-08-05
Prerequisite: the working sim stack in `new_machine_local_serving_20260804.md`
(driver 580.173.02 + Isaac Sim 5.1 + source-installed Isaac Lab 2.3.0 + LeIsaac).

---

## 1. Why This Matters

```text
PLACE is the project's ONE TOTAL GAP.
  0 successes across the ENTIRE project on the real arm
  (agent_handoff_pi05_20260803.md Section 3)
  Our 49-episode dataset contains NO completed place.
```

On 2026-08-04 a scripted state machine completed the full task in simulation:

```text
Episode success!
```

That is **the first completed place this project has recorded**, anywhere.
Simulated and scripted rather than learned - but complete, repeatable, free, and
generating trajectories we can train on.

---

## 2. What The State Machine Does

`source/leisaac/leisaac/datagen/state_machine/pick_orange.py` -
`PickOrangeStateMachine`, the ONLY task in LeIsaac with a state machine.

```text
Its own docstring: "...orange, grasps it, lifts it, transports it to the plate
and places it."
Success condition:  "all oranges are on the plate and the arm is at rest"

Phases: _phase_move_above_plate -> _phase_lower_to_plate
        -> _phase_release  <- THE PLACE  -> _phase_lift_gripper
```

The environment emits **six scored subtask terms**:

```text
0  pick_orange001          3  put_orange002_to_plate
1  put_orange001_to_plate  4  pick_orange003
2  pick_orange002          5  put_orange003_to_plate
```

**Three of six are explicit PLACE operations, individually tracked.** That is
free per-phase scoring - no trace analysis, no eyeballing. Compare the real-robot
workflow, where grasp/lift/carry/place counts come from
`analyze_grasp_from_trace.py` plus manual review.

`analyze_grasp_from_trace.py` remains the authority for REAL runs. Sim subtask
terms are ground truth we can validate scoring against, not a replacement.

---

## 3. The Recording Recipe

```bash
cd ~/sim/leisaac-src
LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets \
ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
~/sim/leisaac-venv/bin/python -u scripts/datagen/state_machine/generate.py \
  --task=LeIsaac-SO101-PickOrange-v0 --enable_cameras --num_envs=1 \
  --record --num_demos=<N> --dataset_file=./datasets/<NAME>.hdf5
```

Then convert in the PROJECT venv (which already has lerobot 0.5.2):

```bash
python ~/sim/leisaac-src/scripts/convert/isaaclab2lerobotv3.py   # -> LeRobot v3.0
```

### Why HDF5-then-convert, NOT --use_lerobot_recorder

```text
--use_lerobot_recorder FAILS in our sim venv:
  AttributeError: 'GenericDataRecorder' object has no attribute 'clear_episode_buffer'
CAUSE: lerobot is NOT INSTALLED in the sim venv. LeIsaac's [lerobot] extra pins
  lerobot==0.4.2, and we installed `-e source/leisaac` without that extra.

DO NOT just add it. The sim venv is pinned to torch 2.7.0+cu128 for Isaac Sim
5.1; dragging lerobot 0.4.2's dependency tree in risks breaking a stack that
took a driver downgrade to get working.

BETTER SEPARATION - keep the venvs single-purpose:
  sim venv     (torch 2.7.0, no lerobot) -> records HDF5
  project venv (lerobot 0.5.2, torch 2.10) -> converts HDF5 -> LeRobot v3.0
And isaaclab2lerobotv3.py emits v3.0, which is exactly our CODEBASE_VERSION,
so NO further conversion is needed.
```

### Bug: `--record` is effectively REQUIRED

```text
Without --record the run CRASHES AFTER SUCCEEDING:
  Episode success!
  ValueError: Termination term 'success' not found.

CAUSE (scripts/datagen/state_machine/generate.py): the script unconditionally
does `env_cfg.terminations.success = None`, but only RESTORES that term inside
`if args_cli.record:`. auto_terminate() then sets a term that no longer exists.
Harmless - the task had already succeeded - but it means no-record runs always
end in a traceback. Always pass --record.
```

Recording mode also sets `DatasetExportMode.EXPORT_SUCCEEDED_ONLY`, so **only
successful episodes are written**. The dataset self-filters. Contrast the real
data, which needed `merge_orange_49.py`, `clean_so101_pick_orange_move_dataset.py`
and per-episode fixes.

### Shutting these down - a trap that cost three stacked windows

```text
WRONG:  pkill -f 'teleop_se3_[a]gent'
        Reports success and kills only the WRAPPER SHELL. Launching with
        `nohup ... &` detaches python as a separate child, which SURVIVES.
        Result on 2026-08-05: three Isaac Sim instances accumulated, each
        holding GPU memory, ending in a black/stalled window.

RIGHT:  pkill -9 -f 'leisaac-venv/bin/pyth[o]n'
        Targets the interpreter, not the launcher. -9 is REQUIRED: Isaac Sim
        traps SIGTERM and a plain kill does nothing.

Verify, do not assume:
  pgrep -cf 'leisaac-venv/bin/pyth[o]n'          # expect 0
  nvidia-smi --query-gpu=memory.used --format=csv,noheader   # ~1.2 GB = desktop only
A healthy single run shows ~9 GB and 40-50% GPU utilisation.

This is a variant of the project's existing pkill self-match trap (bracket
patterns) - the bracket was right, the TARGET was wrong.
```

---

## 4. What This Does And Does Not Establish

```text
ESTABLISHED
  a full pick->lift->transport->PLACE cycle completes in sim, repeatably
  we can generate place demonstrations with NO robot, NO leader arm, NO teleop
  episodes self-filter to successes only
  output lands in LeRobot v3.0, the format we already train on
  per-phase subtask labels come for free

NOT ESTABLISHED - and this is the load-bearing unknown
  THAT SIM DEMOS TRANSFER TO THE PHYSICAL ARM.
  012000 was fine-tuned entirely on REAL teleop data. Sim renders, sim physics
  and sim camera poses are all out of distribution relative to our real rig.
  A policy trained on sim place data may place beautifully in sim and not at all
  on the table.

  This gives us the data to TEST that question cheaply. It does not answer it.
```

Also note the scripted policy is not a learned one: it uses privileged state
(`env.scene["Plate"].data.root_pos_w`) rather than camera observations. The
DEMONSTRATIONS are still valid training data - that is exactly how teleop demos
work - but the state machine is not a baseline policy to compare against.

---

## 5. Where This Fits The Roadmap

```text
It does NOT replace Stage 2 (the real recording session). Sim cannot teach the
model our table, our three cameras, our lighting.

It DOES attack the specific gap Stage 2 was carrying alone: PLACE, with clean
phase boundaries, at zero robot cost and in unlimited quantity.

Natural experiment, once real data exists:
  A) real data only          <- what 012000 had; place = 0/5
  B) real + sim place data   <- does the place phase appear at all?
  C) sim only                <- sim2real floor
Score with the Stage 4 matrix. See pi05_generalization_roadmap_20260802.md and
community_data_strategy_20260804.md (same co-training logic, different source).
```

---

## 6. Open Questions

```text
How many sim demos before place appears in a fine-tune?
Does sim2real hold at all for this arm, or is the visual gap fatal?
Can the kitchen scene's object/plate positions be varied, for the position
  generalization that is our other verified failure? (LeIsaac is editable-
  installed, so the task cfg is directly modifiable)
Does the 3-camera requirement hold in sim, and do sim camera poses need to
  match our real rig for transfer?
Is MimicGen (scripts/mimic/) worth it? It AUGMENTS recorded demos rather than
  generating from scratch - so it needs seed demos first, but could multiply
  whatever we record.
```

---

## 7. Testing OUR Pi05 Checkpoint In Sim (2026-08-05)

### The infrastructure WORKS - this part is solid

LeIsaac can drive a policy served by our own training-era LeRobot policy server
over gRPC. **The checkpoint stays on the code it was trained with**, so the
Era 1 code-pairing rule is preserved; only the observation SOURCE changes.

```text
  our training-era policy_server (e40b58a8, serving 012000)
          ^ gRPC
  LeIsaac scripts/evaluation/policy_inference.py  <- sends SIM observations

VERIFIED: 77+ observation->action round trips
  server: "Policy type: pi05 | Time taken to put policy on cuda:0: 54.25s"
          "action shape: torch.Size([1, 50, 6])"
          inference 144 ms  (matches the 143 ms standalone benchmark - sim
          observations cost nothing extra)
          total per observation 236 ms (the ~90 ms gap is transport + render)
  GPU: 18.3 GB total (Isaac Sim ~9 + policy ~9.5) of 32 GB
```

This is reusable for the GR00T comparison, for downloaded community checkpoints,
and for anything we fine-tune next.

### Three integration traps (all fixed, all non-obvious)

```text
1. PICKLE MODULE PATH - BOTH DIRECTIONS.
   leisaac/policy/lerobot/__init__.py DELIBERATELY rewrites its classes'
   __module__ to "lerobot.scripts.server.helpers" (the lerobot 0.4.2 layout).
   Our training-era code has them at lerobot.async_inference.helpers.
     receiving fails: No module named 'lerobot.scripts.server'
     replying fails:  No module named 'lerobot.async_inference';
                      'lerobot' is not a package   <- LeIsaac's fake `lerobot`
                      is a bare ModuleType, not a package
   FIX: scripts/policy_server_leisaac_shim.py - aliases the module AND rewrites
   __module__ on the classes we send. Also sets RemotePolicyConfig.rename_map as
   a CLASS attribute: pickle restores dataclasses via __dict__ without calling
   __init__, so that field (which LeIsaac never sends) would otherwise be absent.

2. ACTION SPACE MUST MATCH THE TELEOP DEVICE.
   use_teleop_device("so101_state_machine") -> 8-dim EE-pose actions
   use_teleop_device("so101leader")         -> 6-dim JOINT actions  <- pi05
     ValueError: Invalid action shape, expected: 8, received: 6
   FIX: use leisaac.utils.env_utils.get_task_type(task), as their own script does.

3. CAMERAS: the sim scene exposes ['wrist', 'front'] - THERE IS NO `top`.
   Our policy declares front/top/wrist, so `top` is padded with -1 and MASKED.
   Mechanically fine (verified in community_data_strategy_20260804.md Section 5)
   but the model has never seen a masked view.
```

### CORRECTION 2026-08-05: the first run was FAULTY. Pi05 DOES reach.

The "frozen arm" result below was wrong and nearly became a recorded finding
about 012000. A repeat run with a FRESHLY STARTED policy server, same script,
same checkpoint, same scene:

```text
                      RUN 1 (faulty)        RUN 2 (fresh server)
  ee_x range          0.000000 m            0.1546 m
  ee_z range          0.014 m               0.1428 m
  d_min               0.2278 -> 0.2394      0.2826 -> 0.1446   <- APPROACHES
  closest approach    never                 0.1446 m at step 503
  gripper_cmd range   0.0000 (frozen)       1.4209  (-0.38 .. +1.04)
  pick_* / put_*      all False             all False
```

**Pi05 012000 produces coherent REACHING behaviour in a simulated kitchen it has
never seen, with one of its three cameras masked out.** It moves ~15 cm, closes
to 14.5 cm of an orange, and actively modulates the gripper. It does NOT grasp
and does NOT place.

```text
"Reaches toward the object, never closes successfully on it" is EXACTLY the
documented real-robot failure mode. The model is behaving like itself.
```

Suspected cause of run 1: the policy server process had already served a session
under a DIFFERENT action-space configuration (before the so101leader fix) and
carried stale state. Run 2 used a freshly started server. **Unconfirmed** - if a
frozen run recurs, restart the server first and check whether that clears it.

```text
LESSON, and it is the more valuable output here:
  A SINGLE SIM RUN IS NOT EVIDENCE. This project already learned that on the
  real arm (run 5 of the five-run count was caught as an empty-finger lift).
  The same discipline applies in sim - repeat before recording.
  Compounding it: the harness was hours old, so BOTH the tool and the run
  needed validating. The 6-DoF action path was separately proven with
  scripts/sim_action_path_check.py (commanded joints, arm followed, 1.2459 rad).
```

### FOUR-RUN COUNT (2026-08-05) - the behaviour is REPRODUCIBLE

```text
run     steps  d_start  closest  d_end  grip_range  ee_motion  grasp  place
run2      600   0.239    0.145   0.218     1.421      0.155      no     no
run3      600   0.237    0.184   0.184     1.017      0.128      no     no
run4      600   0.236    0.181   0.211     1.354      0.143      no     no
demo     1500   0.248    0.130   0.196     1.395      0.169      no     no
                                                    (metres; grip in action units)
```

Consistent in every run: approaches 5-12 cm, moves the end-effector 13-17 cm,
actively modulates the gripper over a 1.0-1.4 range. **0/4 grasps, 0/4 places.**

**THE LONG RUN IS THE INFORMATIVE ONE.** At 1500 steps (2.5x the others) it:

```text
  reached its closest approach yet .......... 0.130 m
  spent 71% of all steps within 0.20 m
  spent 32% of all steps within 0.15 m
  ...and still never closed the last 10 cm.  Grasp range is 2-3 cm.
```

```text
=> MORE TIME DOES NOT HELP. 2.5x the steps bought 1.5 cm. The policy does not
   progressively close in and stall at the end - it CONVERGES TO A STABLE
   HOVERING DISTANCE around 13-18 cm and stays in that neighbourhood.

That is a sharper finding than "it fails". It is not lost, not wandering, and
not slowly converging. It reaches a CONSISTENT WRONG DISTANCE and holds there,
opening and closing the gripper without a grasp behind it.

Fits the documented split exactly: the COARSE APPROACH survived the fine-tune;
the FINAL POSITIONING is welded to the trained scene. A stable offset is what
you would expect from a policy whose depth/scale cues come from a camera
geometry that no longer matches.
```

That last point is testable and cheap: **S2 (add the `top` camera) and S1 (move
the orange) both bear on it.** If the hover distance is a camera-geometry
artefact, a third view should change it. If it is a positional prior, moving the
orange will not move the hover point.

**WHAT IT SHOWS**

```text
Pi05 012000 REACHES TOWARD AN ORANGE in a rendered kitchen it has never seen,
with one of its three cameras (top) absent and therefore masked. That is a far
larger domain shift than the one that produced 145 empty squeezes on our OWN
table, and it still produces directed motion.

But it closes only 25-40% of the distance and stalls at 15-18 cm. Grasping range
is ~2-3 cm. It reaches roughly the right way and stops.

This FITS the verified model of the checkpoint exactly:
  language understanding and COARSE APPROACH survived the fine-tune;
  GRASP GEOMETRY is welded to the trained scene.
The coarse part transfers even to a different room. The precise part does not
transfer across inches on our own table, let alone this.
```

**LIMITS - do not over-read this**

```text
- Failure is still WEAK evidence (Section 4a asymmetry); the domain gap is huge.
- Three runs of ONE scene configuration. Object positions were NOT varied.
- The approach may be a learned prior toward the table centre rather than
  genuinely ORANGE-DIRECTED. Distinguishing those needs runs with the orange
  MOVED - cheap here, since LeIsaac is editable-installed and positions are
  configurable. UNTIL THAT IS RUN, "it reaches for the orange" is NOT
  established; only "it reaches" is.
```

**The reusable output is the METHOD**: repeatable, ground-truth-scored policy
evaluation with no robot and no per-run cost. That is the harness the GR00T
comparison in `groot_vs_pi05_comparison_plan_20260804.md` needs.

### The superseded run 1 (kept for the record)

Scored from simulator ground truth (`scripts/sim_policy_eval_instrumented.py`),
900 steps:

```text
ee_x        range 0.000000 m     <- frozen
ee_y        range 0.003700 m
ee_z        range 0.014000 m     <- ~1.4 cm of total motion
d_min       0.2278 -> 0.2394 m   <- never approaches the nearest orange
gripper_cmd 0.0000, range 0      <- NEVER COMMANDED
pick_orange001/002/003          ever_true = False
put_orange001/002/003_to_plate  ever_true = False
```

No approach, no grasp, no place. **But this is NOT reported as evidence about
012000**, for one specific reason:

```text
gripper_cmd is EXACTLY 0.0000 with ZERO variance across 900 steps.
On the real arm the gripper operates in width units around 28-33. A constant
hard zero does not look like a model making bad predictions - it looks like a
value that is not arriving.

PROJECT RULE: "SUSPECT THE HARNESS BEFORE THE MODEL. Validate any new
measurement tool against a known-good answer before believing it."
This harness was written the same hour and has NEVER been validated against a
known-good answer. Era 1 cost ~a month to exactly this: local probes that
"proved" 012000 had collapsed, when the harness was wrong.
```

Unresolved: whether pi05's ABSOLUTE joint targets (real SO-101 calibration, in
degrees) survive `convert_lerobot_action_to_leisaac` into sim joint conventions.

```text
NEXT STEP TO SETTLE IT - log the RAW action values the server returns:
  varied, plausible joint targets that do not move the arm -> HARNESS bug
  genuinely flat/near-zero actions                         -> MODEL output
Until that is run, this experiment has NO bearing on 012000's quality.

And even if the model IS the cause: failure in sim is WEAK evidence (Section 4a
asymmetry). The checkpoint was fine-tuned on real frames of one table; a
rendered kitchen with a masked camera is far outside that. Only SUCCESS would
have been informative.
```

---

## 8. References

```text
LEISAAC UPSTREAM
  state machine   source/leisaac/leisaac/datagen/state_machine/pick_orange.py
  generator       scripts/datagen/state_machine/generate.py
  policy eval     scripts/evaluation/policy_inference.py
  converters      scripts/convert/isaaclab2lerobotv3.py  (v3.0 - use this one)
                  scripts/convert/isaaclab2lerobot.py    (v2)
  mimicgen doc    docs/docs/docs/features/mimicgen_env.md

OURS (projects/testproject/scripts/, committed - survive a reboot)
  policy_server_leisaac_shim.py     start our policy server so LeIsaac can
                                    talk to it (bidirectional pickle alias)
  sim_policy_eval_instrumented.py   run a policy in sim and SCORE IT FROM
                                    GROUND TRUTH (EE-to-orange distance,
                                    gripper command, GT subtask terms)
  leisaac_task_check.py             gate check: import / register / construct
  isaac_sim_smoke_test.py           does the Kit engine start at all
  hdf5_episode_to_video.py          render a recorded episode to MP4
                                    (2.2 GB raw -> ~2 MB h264)

DOCS
  setup + traps   new_machine_local_serving_20260804.md
  driver matrix   isaac_sim_blackwell_investigation_20260804.md Section 0
  sim-test policy community_data_strategy_20260804.md Section 4a (asymmetry)
```

---

## 9. Recorded So Far

```text
~/sim/leisaac-src/datasets/sim_pick_place.hdf5      23 GB, 8 episodes, 3 SUCCESS
~/sim/leisaac-src/datasets/sim_pick_place_ep4.hdf5  12 GB, 1 episode,  1 SUCCESS
  -> 4 successful episodes = 12 completed PLACE operations
  -> episodes carry a per-episode `success` attribute; failures ARE included
     (EXPORT_ALL, not EXPORT_SUCCEEDED_ONLY - that only applies with
      --use_lerobot_recorder)
  -> state machine success rate observed: 4/9 attempts (~44%)
  -> cameras per episode: front + wrist, 480x640 uint8, fixed 2340 steps

SIZE: ~2.9 GB per episode RAW in HDF5, but h264 is ~1000x smaller (2.2 GB of
frames -> 1.8 MB MP4). The HDF5 is a disposable fat intermediate; a converted
LeRobot dataset of 40-60 episodes should be a few hundred MB, NOT hundreds of
GB. Do not size the plan off the HDF5.

NOT YET DONE: conversion to LeRobot v3.0 via isaaclab2lerobotv3.py.
```
