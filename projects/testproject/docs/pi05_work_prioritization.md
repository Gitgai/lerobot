# Pi05 Work Prioritization

Last updated: 2026-08-05 (banner); body 2026-07-25

> ## CURRENT PRIORITY ORDER (2026-08-05)
>
> The principle below is unchanged and still correct: **priority = evidence
> value.** What changed is the machine and the option set.
>
> **REFINEMENT (2026-08-04): rank by evidence value, then do the highest-value
> AVAILABLE item.** A blocked top priority does not idle everything beneath it.
> This matters right now because P0 is blocked on a file transfer that only the
> user can perform - which is a queue for *them*, not a stop for *us*.
>
> **STRATEGY CHANGE (user, 2026-08-05): SIM-FIRST.** The simulator is now the
> REFERENCE and the real rig will be built to match it - not the reverse. So
> "blocked on hardware" is the wrong frame: **the rig is the final validation
> step, not a blocker.** The S-items below are the main line of work, not a
> stopgap. -> `sim_first_strategy_20260805.md`
> Decided there: ADD a `top` camera to sim (keeping three), define its pose in
> the config FIRST, and mount the real camera to match. GR00T does NOT force us
> back to two - `modality_keys` is a plain list with no code limit; two cameras
> is their EXAMPLE. View selection is a config swap, so record once with three
> and evaluate 2-cam vs 3-cam off the same episodes.
>
> ```text
> P0  TRUST EXAM   ** ✅ PASSED 2026-08-05 - THE STACK IS SOUND **
>     first-gripper correlation 0.714 (pod 0.826, broken-harness sig 0.197);
>     closed-ish frames n=21 and recorded mean 21.4 BOTH MATCH THE POD EXACTLY,
>     which is what proves the frame selection reproduced the protocol.
>     MAE 5.45 vs pod 4.41. Not identical - candidates are torch/GPU differences
>     (2.11.0+cu128 on a 5090 vs the pod's July build on a 3090) or indices off
>     by a frame. Unexplained but NOT the failure mode: 0.714 is 3.6x the broken
>     signature and in the pod's regime.
>     => **THE FOUR SIMULATOR RUNS STAND.** They used this same stack, so
>     "Pi05 hovers at 13-18 cm" is a real measurement. S1 is now clear to run.
>     -> new_machine_local_serving_20260804.md Section 5
>
> (historical) P0 as originally blocked:
>     ~/lerobot_assets/datasets/so101_orange_49_plus_grasp_pick_move_focus
>       v3.0, 89 episodes (49 original + 40 focus), 40,712 frames, 3 cameras.
>       Verified independently: 0 symlinks, 0 zero-byte files.
>     Script and checkpoint were already here. NOTHING IS MISSING.
>     Target: gripper corr 0.826 / MAE 4.41.  Broken-harness signature: 0.197.
>     NOT a real-robot gate - it validates the SERVING STACK, and that same
>     stack fed all four SIMULATOR runs. **If it fails, every number measured on
>     this machine is void, including "Pi05 hovers at 13-18 cm".**
>     => It now outranks S1. Do not build further on an unvalidated stack.
>
> WAITING ON THE USER
>   P2  subtask probe         needs the physical rig - now LATE in the order
>
> DONE
>   P1  second checkpoint copy       backup exists (user-confirmed)
>   P3  camera-count gate            ANSWERED YES - community data not excluded
>
>   P5  ISAAC SIM PROBE + DRIVER FIX   ** DONE 2026-08-04/05 **
>       The 6.0.1 container ran cleanly, proving the machine and Blackwell were
>       never the problem. Driver then downgraded to 580.173.02 and
>       **THE SIMULATOR NOW WORKS LOCALLY**: Isaac Sim 5.1 + Isaac Lab 2.3.0 +
>       LeIsaac, SO-101 scene rendering and controllable. Pi05 serving did NOT
>       regress (143 ms/chunk, better than 153 ms).
>       -> isaac_sim_blackwell_investigation_20260804.md Section 0
>   --  SIM PLACE DATA   ** DONE 2026-08-05 ** 4 successful episodes recorded
>       = 12 completed PLACE operations, the project's first, via the scripted
>       state machine. -> sim_place_data_generation_20260805.md
>   --  SIM POLICY-EVAL HARNESS   ** BUILT AND VALIDATED ** and already used on
>       Pi05 012000 (3 clean runs: reaches 5-9 cm, 0/3 grasps, 0/3 places).
>
> AVAILABLE NOW (no hardware, no dataset) - ordered by evidence value
>   BASELINE THESE TWO ARE MEASURED AGAINST (4 runs, 2026-08-05):
>       Pi05 converges to a STABLE HOVER 13-18 cm from the nearest orange and
>       stays there. 1500-step run: closest 0.130 m, 71% of steps within 0.20 m,
>       32% within 0.15 m, 0/4 grasps. 2.5x the time bought 1.5 cm - so it is
>       NOT slowly converging and running out of time. It settles at a
>       CONSISTENT WRONG DISTANCE.
>
>   S1  ** DONE 2026-08-05 - THE REACH IS OBJECT-DIRECTED **
>       Moved all 3 oranges +0.15 m in y. The arm followed +0.095 m over the run
>       and +0.117 m once settled - 64-78% of the object displacement. A
>       positional prior would have given ~0.
>       => 012000 RETAINS VISUAL GROUNDING, and it survived a room-scale domain
>       shift. **The failure is FINAL POSITIONING, not perception.**
>   S2  ** DONE 2026-08-05 - A THIRD CAMERA MADE IT WORSE **
>       Added an overhead `top` camera to the sim. Closest approach unchanged
>       (0.133 -> 0.136) but time within 0.20 m COLLAPSED from 86% to 23%.
>       The pose was INVENTED, so the model got a `top` slot full of pixels
>       matching nothing it trained on. A masked view it can ignore; a WRONG
>       view it cannot. => the fix is not "add a camera".
>       Keep separate: EVALUATING 012000 needs a pose matching what it was
>       TRAINED with; TRAINING a new policy can choose the pose freely.
>       NOTE: local edit to LeIsaac, backup at ~/sim/single_arm_env_cfg.py.orig
>   -> s1_s2_results_20260805.md
>
>   (superseded description of S1/S2 below)
>   S1  MOVE THE ORANGE, re-run Pi05.
>       PRE-REGISTERED READING (decide before running, not after):
>         hover point FOLLOWS the orange -> the reach is genuinely
>           OBJECT-DIRECTED. Visual grounding survived a room-scale domain
>           shift and the failure is specifically FINAL POSITIONING. Real
>           finding about what the fine-tune preserved.
>         hover point STAYS PUT -> it is a learned trajectory toward a
>           remembered spot. "Pi05 reaches for the orange" collapses to
>           "Pi05 reaches", and the four runs mostly measured a PRIOR.
>       Until this runs, the docs must keep saying only "it reaches".
>       Cheap, ONE variable, no hardware, no dataset.
>
>   S2  ADD A `top` CAMERA TO THE SIM SCENE, re-run Pi05 with all three.
>       Now DIAGNOSTIC, not exploratory: a stable positional OFFSET is exactly
>       what you would expect if depth/scale cues come from a camera geometry
>       that no longer matches training.
>       PRE-REGISTERED READING:
>         hover distance CHANGES -> camera geometry is implicated; the missing
>           view is carrying real cost, and matching cameras matters.
>         hover distance UNCHANGED -> the third view is not the constraint;
>           look to appearance/lighting/physics instead.
>       DIRECTION: choose the sim pose DELIBERATELY - that choice becomes the
>       spec the real camera is later mounted to (sim-first). Do NOT match a
>       real camera we may re-mount anyway.
>       Feasible - cameras are plain TiledCameraCfg objects in the
>       editable-installed template.
>   S1b TEST DOWNLOADED SO-101 CHECKPOINTS.  ** PARTLY DONE 2026-08-05 **
>       Screened 3, one survives and now RUNS:
>         pi05_so101_orange_cube  openpi format -> runnable via openpi (installed,
>                                 not yet driven); LeIsaac has an openpi client
>         smolvla-so101-digits    OUT - needs observation.target_drawing, an
>                                 input no environment we have can supply
>         gr00t-n1.7-so101        ** WORKING ** gated backbone access granted
>                                 (Cosmos-Reason2-2B, 4.6 GB cached, also
>                                 unblocks S3/S5), server up on ZMQ :5555, and
>                                 scripts/gr00t_n17_client_adapter.py bridges
>                                 LeIsaac's n1.6 client to N1.7's wire format.
>                                 Smoke test: (1,96) float32 = 16 steps x 6 DoF.
>       REMAINING: wire the adapter into sim_policy_eval_instrumented.py and
>       score GR00T from GROUND TRUTH in the same scene as Pi05, so the numbers
>       are directly comparable to "hovers 13-18 cm, 0/6 grasps".
>       COST NOTE: bridging N1.7 took ~an hour of protocol work. The goal was to
>       AVOID hours; this checkpoint was not "as-is". Adapter is reusable.
>
>       (original framing below)
>   S1b TEST DOWNLOADED SO-101 CHECKPOINTS IN OUR SIM.
>       GOAL (user): find a public checkpoint that works and USE IT AS IS,
>       skipping fine-tuning entirely. Worth testing - hours of evaluation vs
>       many hours of training.
>       ORDER MATTERS - test GR00T FIRST:
>         012000 uses ABSOLUTE joint targets (use_relative_actions: False), which
>         are tied to a SPECIFIC ARM'S CALIBRATION. A stranger's pi05 checkpoint
>         emits angles calibrated to THEIR arm - same robot model, different zero
>         points, so systematically offset commands.
>         GR00T DEFAULTS TO RELATIVE ACTIONS (gripper excluded), which carry no
>         calibration assumption. => structurally far better suited to this plan.
>       TEST ALL OF THEM ANYWAY, do not stop early. An earlier draft advised
>       skipping the pi05 candidates if GR00T failed; that was a PREDICTION
>       SUBSTITUTING FOR A CHEAP MEASUREMENT. A uniform negative is itself a
>       finding - it redirects effort to fine-tuning with evidence.
>       COST IS BANDWIDTH, NOT COMPUTE: ~15 GB of weights at ~2 MB/s is a couple
>       of hours of downloading; ~20 min GPU per evaluation. Batch downloads.
>       TEMPERING FACT: "large models generalize" is contradicted by our own
>       data - 012000 is 4.14B and still gives 145 empty squeezes when an onion
>       moves a few INCHES on its own table.
>       -> public_so101_datasets_and_checkpoints_20260805.md
>
>       (superseded framing below)
>   S1b TEST A DOWNLOADED SO-101 CHECKPOINT IN OUR SIM.
>       The harness is already built and validated; this is just a different
>       --policy_checkpoint_path. Public SO-101 fine-tunes exist for BOTH
>       families:
>         yen-0/smolvla-so101-digits-0707        0.5B  <- START HERE, 8x smaller
>                                                        than Pi05, loads in
>                                                        seconds vs 60 s
>         robocurve/gr00t-n1.7-so101-molmoact2   3B    <- N1.7, our repo version
>         felixmayor/pi05_so101_orange_cube            <- ORANGE, our object
>       Any of them performing well in our sim kitchen would be a STRONG signal
>       (the asymmetry: success is strong, failure is weak).
>       CONDITIONS: Era 1 rule still applies - identify each checkpoint's
>       training-era code before believing its result; most repos have NO model
>       card, so that may be impossible and the result then uninterpretable.
>       -> public_so101_datasets_and_checkpoints_20260805.md
>
>   S3  GR00T PIPELINE VALIDATION on NVIDIA's own dataset.
>       UPGRADED 2026-08-05: izuluaga/finish_sandwich is NOT a generic smoke
>       test. Verified: robot_type so101_follower, 80 eps / 70,277 frames, v3.0,
>       front+wrist - STRUCTURALLY IDENTICAL to what we would produce. Frames
>       inspected: toy food stacked onto bread, i.e. a real PICK-AND-PLACE task
>       with an unambiguous place target.
>       WARNING: its `front` camera is TOP-DOWN. Same key name as ours, different
>       geometry - do not assume matching keys mean matching views.
>       NOTE: this trains
>       nvidia/GR00T-N1.7-3B (their BASE model) on THEIR data to produce OUR
>       first GR00T checkpoint. The resulting sandwich policy is useless to us;
>       the point is proving convert -> train -> eval works on this machine
>       BEFORE debugging our own two-hop HDF5->v3->v2 conversion on top of an
>       unproven pipeline. GR00T installed + GPU-verified (0.1.0, torch 2.9.0).
>       -> groot_vs_pi05_comparison_plan_20260804.md Section 4b
>   S4  DOWNLOAD MORE LEISAAC SCENES (6 declared, we have 1) and generate
>       PickOrange demos across environments. This is the ENVIRONMENT DIVERSITY
>       our single real table structurally cannot provide - PI's ablation ranks
>       it the most damaging variable to remove.
>       PROMOTED IN IMPORTANCE 2026-08-05: this is the concrete first step of
>       "STRATEGY B" - make sim diverse enough that the REAL rig falls inside its
>       distribution, rather than building one real setup to match one sim scene.
>       S2 showed a MISMATCHED match is worse than none, and our own 012000 is
>       welded to ONE table; matching a single sim scene risks reproducing that
>       brittleness somewhere new. Object positions are config values and six
>       scenes are declared, so the diversity is cheap.
>       -> sim_first_strategy_20260805.md Section 5b
>   S4b PULL jinseonylee/SO101_PickAndPlace_Fruit - closest PUBLIC data to our
>       actual task (fruit pick-and-place on an SO-101). Also
>       gpudad/so101_pick_cube_chunked (1.46M rows, the largest available).
>   S5  Convert our sim episodes to LeRobot v2, fine-tune GR00T on them.
>   P3b mine MolmoAct2 for wrist-view place datasets. Still not urgent.
> ```
>
> **Honest state as of 2026-08-05.** Two items still wait on the user (the
> dataset transfer, the physical rig) and neither moved today. But the sim track
> is no longer speculative: it works, it produced the project's first completed
> PLACE operations, and S1-S2 are real experiments on a real model costing only
> GPU time. **S1 is the highest-value available work** - it decides whether the
> day's most interesting result means what it appears to mean.
>
> Caution retained: only PickOrange has a state machine, so sim auto-generation
> covers ONE task; the other 14 need teleop and therefore the leader arm. And
> **sim2real transfer remains UNPROVEN** - the load-bearing unknown beneath all
> of it. -> sim_capability_and_camera_plan_20260805.md
>
> Applying the principle to today's situation:
>
> ```text
> P0  THE TRUST EXAM. A freshly built serving stack on a new machine has NEVER
>     been checked against the pod's known-good numbers (gripper corr 0.826,
>     MAE 4.41 on 21 closed-ish frames; the broken-harness signature was 0.197).
>     Pi05 012000 loads locally and emits finite actions - ON RANDOM NOISE.
>     That proves nothing about correctness.
>     Highest evidence value; needs no hardware, no simulator, no driver change.
>     Era 1 cost ~a month to precisely this blind spot.
>     -> new_machine_local_serving_20260804.md Section 5
>
>     BLOCKED ON ONE TRANSFER (found 2026-08-04): the exam needs a DATASET, and
>     none is on this machine. Have + need:
>       script   scripts/runpod/pi05_episode29_offline_compare.py    HAVE
>       policy   ~/lerobot_assets/checkpoints/pi05_012000/           HAVE
>       dataset  /data/lerobot_datasets/                             OLD LAPTOP
>                  so101_orange_49_plus_grasp_pick_move_focus
>     The pod run used 40 focus-window frames, one per focus episode at
>     t=1.667s, so the focus-only dataset may suffice and be much smaller -
>     check both sizes before transferring. Link runs ~2 MB/s.
>     Read-only: the script never opens a serial port and never moves the arm.
>
> P1  SECOND COPY OF THE CHECKPOINT.  ** RESOLVED 2026-08-04 - backup exists **
>     User confirms a backup of the checkpoint exists, so the local 8.8 GB copy
>     is not a single point of failure. No action needed; do not re-raise.
>
> P2  SUBTASK-SWITCHING PROBE.  ** BLOCKED: needs the physical rig **
>     Still the highest-value robot experiment and still unanswered.
>     ~15 min of robot time, no training.
>     -> agent_handoff_pi05_20260803.md Section 9 item 1
>
> P3  DATA STRATEGY GATE.  ** DONE 2026-08-04 - ANSWERED YES **
>     Can pi05 train on datasets with fewer cameras than the policy declares?
>     YES. Missing cameras are padded with -1 and MASKED OUT, derived per batch
>     (modeling_pi05.py:1150). rename_map is a top-level TRAINING config field
>     (configs/train.py:120), not just a serving option - and 012000's own
>     train_config.json already carries it.
>     The 1,222-dataset community corpus is NOT architecturally excluded.
>     CAVEAT: this is code reading. It proves the mechanism, not that such a mix
>     trains well. Empirical proof needs a training run, hence the P0 dataset.
>     -> community_data_strategy_20260804.md Section 5
>
> P3b SUCCESSOR TASK, AVAILABLE NOW: mine the MolmoAct2 index for place-style
>     datasets that carry a WRIST view. Promoted because P3 surfaced a real
>     risk: our weakest skill is grasp geometry, the wrist camera is the view
>     that matters most for grasp, and most community datasets lack one. A
>     wrist-less corpus could add environment diversity while diluting the exact
>     capability we need. CAMERA COMPOSITION MAY MATTER MORE THAN EPISODE COUNT.
>
> P4  SIM WORK.  ** RESOLVED 2026-08-05 - IT RUNS LOCALLY **
>     The version deadlock is GONE: driver downgraded to 580.173.02, so Isaac
>     Sim 5.1 + Isaac Lab 2.3.0 + LeIsaac all work on this machine. Brev is not
>     needed and was declined anyway. This is no longer speculative - it has
>     produced the project's first completed PLACE operations and a working
>     policy-evaluation harness. Successors are S1-S5 in the banner above.
>     -> isaac_sim_blackwell_investigation_20260804.md
>     -> sim_place_data_generation_20260805.md
>
> P4b WRITING STATE MACHINES for the other 14 sim tasks.  ** NOT YET - by choice **
>     Feasible: base.py is 100 lines with 5 abstract methods, pick_orange.py is
>     312 lines, and they use PRIVILEGED STATE (exact object poses) so no
>     perception is needed. ~300 lines per task.
>     But judged against our gaps, only CleanToyTable (places into a BOX) clearly
>     earns that: LiftCube has no place phase, AssembleHamburger is far from our
>     task, FoldCloth is bi-arm and we have one arm.
>     CHEAPER ROUTE TO THE SAME BENEFIT: our remaining gap is POSITION/SCENE
>     generalization, and S1/S4 attack it by varying the state machine we ALREADY
>     have - no new code. **Exhaust variation of PickOrange before writing a new
>     task.** -> sim_capability_and_camera_plan_20260805.md Section 3
>
> P5  Isaac Sim 6.0 capability probe, GR00T comparison, driver work.
>     ** 6.0 probe AVAILABLE NOW; rest deferred **
>     The 6.0 probe answers only "can this machine run Isaac Sim at all?" -
>     ~18 GB, touches nothing that works. The driver downgrade is REJECTED
>     outright: it would disturb the verified 5090 baseline and the working
>     Pi05 stack for no gain.
> ```
>
> **Anti-pattern to avoid, stated explicitly:** do not fabricate a green check
> for a blocked task. The trust exam could be made to "run" against any public
> dataset - and it would produce a correlation number that means nothing,
> because the exam's value is comparison against a KNOWN-GOOD result on the
> SAME data. A meaningless pass is worse than a visible blocker. Era 1 was a
> month lost to a harness that looked fine.
>
> **Cost model changed too.** Items below priced in dollars assumed a rented
> pod. Training and inference now run on a local RTX 5090; the pod is stopped.
> Compute is no longer the scarce resource - **robot time is.**
> "Debug RunPod" has left the list entirely.

This document defines how we decide what to work on first for the SO-101 Pi05 orange-pick project.

It exists because the project has many possible next actions:

```text
fix cameras
run official LeRobot async
record more demos
fine-tune more
add instrumentation
change action chunk settings
inspect video
inspect logs
debug RunPod
```

Without prioritization, we can easily do busy work that does not answer the real question.

## 1. Main Principle

Priority is based on evidence value.

The highest priority task is the one that most directly answers:

```text
Where exactly is the failure happening?
```

The failure could be:

```text
camera input
robot state input
Pi05 output
LeRobot action queue
robot execution
timing/latency
training data coverage
hardware setup
```

We should work in that order only when evidence supports it.

## 2. Priority Levels

### P0: Blocks Meaningful Evidence

P0 means:

```text
We cannot run a valid test or collect useful evidence until this is fixed.
```

Examples:

```text
wrist camera not readable by official LeRobot
policy_server not running
SSH tunnel broken
SO-101 follower not connected
checkpoint incomplete
camera images stale or wrong
```

Rule:

```text
Do P0 before model/data changes.
```

### P1: Produces Required Evidence

P1 means:

```text
This produces evidence needed for the next decision.
```

Examples:

```text
one clean official async run
camera precheck images
saved logs
external video
outcome label
log review
```

Rule:

```text
Do P1 after P0 is cleared.
Do not skip P1 and jump to fine-tuning.
```

### P2: Explains A Specific Failure

P2 means:

```text
This is useful after a real failure is observed and basic logs/video are not enough.
```

Examples:

```text
read-only async trace instrumentation
action chunk analysis
executed action comparison
training dataset comparison
close-range correction demo decision
```

Rule:

```text
Do P2 only after the P1 run shows what needs deeper investigation.
```

### P3: Optimization Or Improvement

P3 means:

```text
This may improve performance but is not needed to identify the current failure.
```

Examples:

```text
more fine-tuning
more episodes
camera angle refinement after cameras already work
queue tuning
additional dashboards
cleanup docs
```

Rule:

```text
Do P3 only when evidence says it is the right fix.
```

## 3. Current Priority Order

> **SUPERSEDED FOR DAY-TO-DAY WORK (2026-08-05).** The list below was written
> for the real-arm Pi05 failure investigation and is kept for that context. The
> project is now SIM-FIRST on a local 5090, so the live order is:
>
> ```text
> DONE 2026-08-05: the INSTRUCTION SWEEP and the HARNESS POSITIVE CONTROL.
>   canonical string is "Grab orange and place into plate" (from the reference
>   dataset's meta/tasks.jsonl, NOT the env's task_description). It wins on
>   approach and is the only GR00T run that moved the object - and it is STILL
>   not enough. The positive control PASSED: grasp, place and lift all detected,
>   so every failure recorded is a real failure.
>
> *** STOP HUNTING PUBLIC CHECKPOINTS. FINE-TUNE. ***
> Three have now failed this scene, and every remaining one costs an era-matched,
> Blackwell-capable env build EACH - Era 1 and sm_120 CONFLICT on a 5090.
>
> *** AND THEN A SIM-TRAINED POLICY ACTUALLY PICKED THE ORANGE UP. ***
> 12e21/gr00t_n1d6_leisaac_pick_orange (N1.6): lifted 0.173 m, carried 0.260 m,
> held 59 consecutive steps, vs the state machine's 0.196 m. It did NOT place.
> The n1.6 environment is BUILT (~1 h, no sudo), so further n1.6 checkpoints are
> nearly free. -> gr00t_n16_sim_trained_SUCCESS_20260805.md
>
> N1. WHY DOES IT GRASP BUT NEVER PLACE? It lifts and carries, then loses the
>     orange. This run was 900 steps; the state machine needs ~2,300 for three
>     full place cycles. Longer runs, multiple seeds. Cheapest open question we
>     have AND it concerns a policy that demonstrably works.
> N2. FINE-TUNE on LightwheelAI/leisaac-pick-orange (ungated, v2.1, 60 eps /
>     36,293 frames, front+wrist, so101_follower - our scene, robot, cameras and
>     resolution exactly). Target the N1.6 reference: 0.173 m OF LIFT, not a
>     predicate. N1.7 is the version we already serve, so no era problem.
> N3. Add table_with_cube (9 files) -> LiftCube as a second task.
> N4. Use Isaac Lab Mimic to multiply episodes instead of recording by hand.
>     Mimic covers PickOrange AND LiftCube; the shipped state machine covers
>     PickOrange only. Neither needs hardware.
> N5. Cheap now the n1.6 env exists: tshiamor/groot-n1.6-leisaac-pick-block.
> N6. Drive the openpi checkpoint (felixmayor/pi05_so101_orange_cube) - cheap,
>     unblocked, LeIsaac speaks openpi natively, still not driven.
> ```
>
> **Report object displacement with every "grasp" from now on.** The sim's own
> grasp predicate is proximity+closure and does not test lift.
>
> **Note on P0 below:** the three-camera gate applies to OFFICIAL REAL-ARM runs.
> In sim, S2 showed that adding a third camera at an INVENTED pose is actively
> harmful (near-object time 86% -> 23%). Do not read P0 as "always add a top
> camera in sim" — a mismatched view is worse than a masked one.

Current priority order:

```text
P0. Keep the official three-camera gate: top, front, and wrist are required.
P1. Official async 3-camera run, video review, log review, and trace run are complete for the current failure.
P2. The 49-episode training dataset has been reviewed for full grasp-pick-move windows.
P2. Offline focused-dataset builder was approved, created, and validated.
P3. Option A 003000 fine-tune is complete: original 49 episodes plus focused grasp-pick-move windows once.
P1. Option A staged 012000 checkpoint is complete and has been tested twice on the real arm.
P1. Sampled CPU offline probe is complete: 012000 failed to predict close/hold on six successful focus frames.
P1. Next: full GPU offline audit 012000 across all focus windows, with 003000 baseline if available.
P1. Then: decide whether the issue is training depth, action normalization/timing, gripper-dimension learning, or data weighting.
P1. Then: run a start-state-controlled official 3-camera trace only if offline evidence improves or the user explicitly approves a diagnostic run.
P3. Record new correction episodes only if the evidence says existing focused windows are still insufficient.
```

## 4. What Always Comes Before Fine-Tuning

Fine-tuning is expensive and can hide the real problem.

Before fine-tuning more, we need evidence for at least one of:

```text
Pi05 did not command close/lift even with good camera inputs.
Training data lacks complete align-close-lift-move-place examples.
Training data camera views differ from deployment camera views.
Gripper close timing in training data does not match the needed behavior.
The current checkpoint is clearly undertrained and infrastructure is already proven good.
The current checkpoint fails to reproduce successful training/focus frames in offline comparison.
```

Fine-tuning should not be prioritized if:

```text
cameras are not working
official async run has not been tested cleanly
logs show infrastructure failure
we do not know what Pi05 actually output
we only have one external video and no action evidence
```

## 5. What Always Comes Before Changing LeRobot Settings

Do not change:

```text
actions_per_chunk
chunk_size_threshold
aggregate_fn_name
robot.max_relative_target
camera mapping
task text
```

until we know what problem the change is intended to solve.

Required evidence examples:

```text
queue empty often -> maybe inspect official queue settings
latency too high -> maybe adjust inference/timing setup
camera missing -> fix camera mapping/source
action too large and unsafe -> discuss robot safety setting
task text mismatch -> compare training task/instruction text
known-good close frame predicts open -> inspect training/action handling before more physical tests
```

Every non-default must be recorded in the run manifest:

```text
value changed
reason
evidence
user approval
expected effect
```

## 6. What Always Comes Before Instrumentation

Instrumentation is allowed only when it is justified.

Before code instrumentation:

```text
official LeRobot path must be attempted
default official logs/video must be checked
we must identify the exact missing evidence
Codex must explain what code will change
user must approve
```

Instrumentation priority becomes P2 when:

```text
the robot reaches/touches but does not grasp
logs do not show exact action values
video alone cannot prove whether Pi05 commanded close/lift
we need to link exact camera images to exact action chunks
```

Instrumentation stays deferred when:

```text
the camera setup is still broken
policy_server cannot load
the robot does not connect
the run fails before Pi05 returns actions
```

## 7. Decision Tree

Use this tree after every test.

```text
Did all cameras work?
  no  -> P0 camera fix
  yes -> continue

Did policy_server load the model?
  no  -> P0 RunPod/checkpoint/env fix
  yes -> continue

Did robot_client receive action chunks?
  no  -> P0/P1 async connection/log review
  yes -> continue

Did the arm move meaningfully toward the orange?
  no  -> inspect camera/state/action trace need
  yes -> continue

Did the gripper center around the orange?
  no  -> inspect camera images and Pi05 action chunks
  yes -> continue

Did the gripper close?
  no  -> inspect Pi05 gripper action and training close examples
  yes -> continue

Did it lift/move the orange?
  no  -> inspect lift actions and training lift examples
  yes -> repeat for reliability
```

## 8. Evidence-To-Priority Matrix

| Evidence | Priority Result | Work To Do |
| --- | --- | --- |
| Wrist camera not readable | P0 | Fix camera before model tests |
| ESP32 appears only as serial/JTAG | P0 | Do not use it as wrist unless it becomes UVC `/dev/videoX` |
| Top/front/wrist precheck images bad | P0 | Fix camera placement/source |
| Checkpoint missing weights | P0 | Use complete checkpoint |
| Policy server not listening | P0 | Fix RunPod server |
| Robot client fails before motion | P0 | Fix config/hardware/camera |
| Action chunks return but queue is empty/stale | P2 | Inspect queue/timing, then consider setting changes |
| Video shows reach/touch but no grasp | P2 | Add trace or inspect actions before collecting data |
| Trace shows no gripper close | P3 after evidence | Collect close-range correction demos or fine-tune |
| Trace shows close command but robot does not close | P1/P2 hardware | Inspect gripper execution and robot state |
| Trace shows good grasp/lift once | P2 reliability | Repeat controlled runs and measure success rate |
| Dataset review finds 35+ good grasp-pick-move windows | P2 | Build focused dataset from existing approved windows before recording more demos |
| Dataset review finds fewer than 20 good grasp-pick-move windows | P3 data collection | Record new focused correction episodes |
| Option A fine-tune completes | P1 | Evaluate new checkpoint on real arm with official async, three cameras, trace, and video |
| Option A still reaches but does not lift/move | P2 | Compare new Pi05 action chunks to the previous traced failure before recording new episodes |

## 9. Work-In-Progress Limit

Only one active P0/P1 investigation should be open at a time.

Current WIP limit:

```text
1 hardware/camera blocker
1 official test run
1 analysis task
```

Do not start:

```text
fine-tuning
new dataset recording
setting experiments
instrumentation
```

while a P0 camera/server/robot blocker is still open.

## 10. How We Track Priority Changes

When a priority changes, update:

```text
docs/pi05_active_work_tracker.md
```

Add:

```text
date
task ID
old priority
new priority
evidence causing change
next action
```

Example:

```text
Date: 2026-07-19
Task: T06 read-only trace instrumentation
Old priority: deferred
New priority: P2
Evidence:
  Official async 3-camera run reached/touched but did not grasp.
  Logs did not include numeric Pi05 action chunks.
Next action:
  Ask user approval to add read-only trace instrumentation.
```

## 11. Current Do-Not-Do List

Do not do these now:

```text
Do not start the long expert fine-tune before the 200-step smoke train passes.
Do not record correction demos yet; use approved existing windows first.
Do not change APQ-style behavior manually.
Do not add robot.max_relative_target unless user approves.
Do not remove official defaults silently.
Do not create custom eval scripts.
Do not run top/front-only as Pi05 evaluation.
Do not use the connected ESP32 serial/JTAG device as a camera.
```

These can become valid later, but only when evidence makes them the smallest correct next step.

## 12. Current 012000 Evidence Rule

The 012000 checkpoint has already been tested twice through official LeRobot
async execution.

```text
trace 230756:
  reached/contacted orange
  strong close <=25 count: 0
  final 100 actions stayed partial/open-ish, gripper 32.56-47.48
  no pick/lift

trace 233341:
  reached/contacted orange
  strong close <=25 count: 85
  strong close happened at timesteps 0-84
  final near-orange window was open, gripper 54.33-58.88
  no pick/lift

sampled CPU offline probe 20260725:
  selected successful close/hold focus frames: 6
  recorded first gripper mean: 21.80
  predicted first gripper mean: 40.35
  predicted strong close in next 10 actions: 0/6
  predicted near close in next 10 actions: 0/6
```

Priority rule:

```text
Do not repeat the same ordinary 012000 real-arm run again as the next step.
First run the full GPU offline 012000 audit on all successful focus-window phases.
Use 003000 as a baseline if available.
Then fix training/action handling if the full audit confirms the sampled failure.
Only then control the real-arm start state before any next physical evaluation.
```

Reason:

```text
The current failure is not basic reach, camera connection, LeRobot execution, or action clamp.
The current failure is close timing/action selection and grasp geometry.
The sampled offline probe already shows 012000 failed to imitate six successful close/hold frames.
Repeating the same robot setup is lower evidence value than quantifying and fixing that offline failure.
```
