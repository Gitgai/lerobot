# GR00T N1.7 evaluated in LeIsaac — and a trap in our ground truth

Date: 2026-08-05.
Checkpoint: **`robocurve/gr00t-n1.7-so101-molmoact2`**, local dir
`~/lerobot_assets/checkpoints/gr00t_n17_so101`. A broad community fine-tune
(MolmoAct2 SO-101 subset: 2,242 episodes, 1.8M frames, 39 repos; tabletop
pick/place, stacking, sorting). **Not** NVIDIA's so101-table-cleanup blog
checkpoint — see the correction in section 3.
Scene: `LeIsaac-SO101-PickOrange-v0`, 900 steps, scored from simulator GT by
`scripts/sim_policy_eval_instrumented.py`.

---

## 1. The headline

```text
GR00T N1.7 gets FAR closer than Pi05 - grasp frame to within 0.039 m, gripper
closed, predicate TRUE for 80 consecutive steps.

AND IT STILL NEVER ACQUIRES THE ORANGE.
The object moved 0.0001 m. It was lifted 0.0026 m. It never reached the plate.

So "grasp = TRUE" in our own instrumentation IS NOT A GRASP. See section 4 -
that is the most reusable thing learned today.
```

---

## 2. Three stacked bugs made the first GR00T run meaningless

The 2026-08-05 run reporting `grasp=TRUE` at `d_min=0.111 m` was **an artifact
of my adapter**, not a policy result. Three independent defects, all in
`scripts/gr00t_n17_client_adapter.py`:

```text
BUG 1  UNITS - the big one
       The sim speaks RADIANS. This checkpoint was trained on LeRobot MOTOR
       units. Its own experiment_cfg/dataset_statistics.json proves it:
           state single_arm  min ~ -103 ... max ~ +111
           state gripper     min ~ -3.9 ... max ~ +95.4
       against SO101_FOLLOWER_MOTOR_LIMITS (arm +/-100, gripper 0..100).
       => the model was shown a state pinned near the bottom of its input
          range, and its outputs were applied ~57x too large.

BUG 2  RELATIVE ACTIONS  *** AND THE OVERCORRECTION - READ SECTION 2b ***
       conf.yaml declares  use_relative_action: true  with
           modality_keys: [single_arm, gripper]
           reps:          [RELATIVE,   ABSOLUTE]
       which READS as "the arm output is a delta". I therefore added the current
       state to it. That was WRONG - see 2b. The config describes how the model
       was TRAINED, not what crosses the wire.

BUG 3  AN EXTRA CAMERA
       conf.yaml video.modality_keys = [front, wrist] - TWO views. The scene was
       still carrying the S2 `top` camera (an INVENTED pose that had already cut
       Pi05's near-object time 86% -> 23%), and the adapter forwarded every
       camera the scene exposed. Pi05's baseline ran with 2 cameras, so the
       comparison was also unfair.
```

**Why I did not hit this with Pi05:** LeIsaac's own `LeRobotServicePolicyClient`
calls `convert_leisaac_action_to_lerobot` / `convert_lerobot_action_to_leisaac`
(`utils/robot_utils.py:96,119`), which do the rad->deg **and** joint-limit ->
motor-limit affine remap in both directions. Writing a raw ZMQ client for GR00T
bypassed all of it.

> **Rule for the next non-LeRobot checkpoint:** LeIsaac's unit conversion is in
> the *client*, not the env. Any new serving path must reimplement it. The
> adapter now reuses LeIsaac's own limit constants (importing them inside Isaac
> Sim, parsing the same literals outside) so there is one source of truth.

Round-trip `motor_to_sim(sim_to_motor(x)) == x` to 1.5e-7.

---

## 2b. *** THE OVERCORRECTION: THE SERVER ALREADY COMPOSES ***

```text
conf.yaml says use_relative_action: true, so I made the adapter add the current
joint state to the arm output. THE SERVER HAD ALREADY DONE THAT.
N1.7's server applies to_absolute_chunking() itself, so the wire carries
ABSOLUTE motor-space targets. Adding state again DOUBLED every joint target.

THE PROBE THAT SETTLED IT - send a known state, print the raw reply in motor
units, and just look:

    state [ 5.21, -28.65, 23.36, 12.06, -3.58, 29.93]
    raw   [ 5.39, -27.17, 22.92, 11.69, -2.79, 20.64]   <- ABSOLUTE, not deltas

    near the state  => absolute, compose NOTHING
    near zero       => deltas, compose

CORROBORATION: LeIsaac's own Gr00t16ServicePolicyClient does NO composition
either. It converts units and returns - which is exactly the shape of a client
talking to a server that already composed.

=> THE CONFIG DESCRIBES TRAINING, NOT THE WIRE. Probe the wire.
=> runs 2, 4 and 5 were all driven with doubled joint targets and are VOID.
```

This is the fourth GR00T correction in one day (units, relative, camera count,
now the overcorrection). Every one was caught by measuring rather than reading,
and the config was actively misleading on two of them.

---

## 3. The four runs

```text
run                        closest  d_mean  <0.20m  gripRange  grasp  froze@
Pi05 012000 (its own task)  0.130   0.181    71%      1.395     no     -
GR00T run1  INVALID         0.056   0.189    60%     70.482    "YES"   -     <- 3 bugs
GR00T run2  orange instr.   0.164   0.378     4%      0.389     no    149
GR00T run3  TRAINING instr. 0.072   0.245    11%      0.348    yes*   178
GR00T run4  confirmation    0.110   0.245     -       -        yes*    -
                                    (d_grasp_min 0.039, 80 consecutive steps)
* proximity+closure only - the object never moved. See section 4.
```

Gripper range fell from **70.5** (bugged) to **0.35** rad — the same scale as
Pi05's 1.4, i.e. finally a physically sane command stream.

### The language instruction dominates — but NOT for the reason first written

```text
CORRECTION (same day). The first version of this doc said the checkpoint "was
trained on 'Grab pens and place into pen holder.'" THAT IS WRONG. That string
comes from NVIDIA's so101-table-cleanup blog tutorial, which is a DIFFERENT
checkpoint. What we are serving is:

    robocurve/gr00t-n1.7-so101-molmoact2
    fine-tuned on the SO-101 subset of allenai/MolmoAct2-SO100_101-Dataset
    2,242 episodes / 1.8M frames, filtered from 39 public community repos
    task family: tabletop pick/place, stacking, sorting
    the model card does NOT publish its instruction strings

So NEITHER sentence we tested is a verified training string.
```

The measurement stands; only its explanation changes:

```text
"pick up the orange..."  -> approaches to 0.164 m, RETREATS to 0.394 m,
                            freezes at step 149. No grasp attempt.
"Grab pens and place..." -> approaches, closes the gripper, holds. Predicate
                            fires for 80 steps.
```

Same checkpoint, same scene, same code — **only the sentence changed**. What
this demonstrates is **instruction SENSITIVITY**, not "match the training string
and it works". We cannot claim the latter, because we do not know this model's
training strings and the winning sentence names *pens* in a scene full of
*oranges*.

The plausible reading was that `"Grab <X> and place into <Y>"` matches a common
PHRASING PATTERN, while *"pick up the orange and move it to another place"* does
not — the policy keying on sentence form more than on the noun.

### THAT HYPOTHESIS IS NOW TESTED — and the canonical string is KNOWN

`meta/tasks.jsonl` of `LightwheelAI/leisaac-pick-orange`, the reference dataset
for this exact scene:

```text
{"task_index": 0, "task": "Grab orange and place into plate"}
```

The canonical form really is `Grab <object> and place into <container>`. Three
instructions, 900 steps each, same scene, same checkpoint:

```text
instruction                              d_min  d_grasp  pickTRUE  objLift
invented   "pick up the orange..."       0.164      -         0    0.0000
wrong-obj  "Grab pens and place..."      0.110    0.039      80    0.0029
CANONICAL  "Grab orange and place..."    0.100    0.047       3    0.0234
------------------------------------------------------------------------
state machine (known-good reference)     0.111    0.021     842    0.1959
```

**The canonical string wins on approach and is the ONLY GR00T run that moved the
orange at all** (0.023 m, 8x the pens run). It still holds for 3 steps and lifts
8x less than a real grasp.

```text
=> THE INSTRUCTION IS WORTH REAL PERFORMANCE, AND IT IS NOT ENOUGH.
```

*(Those three rows were all measured with the doubled-target bug of section 2b,
so treat them as a comparison BETWEEN INSTRUCTIONS under one consistent defect,
not as absolute numbers. The instruction ordering is the finding; the values
are superseded by the valid run below.)*

### THE VALID RUN — correct units, correct absolute actions, canonical string

```text
run                              d_min  d_grasp  <0.20m  pickT  objLift
GR00T N1.7  VALID                0.098    0.045    96%     31   0.0029
state machine (known-good)       0.111    0.021    58%    842   0.1959
Pi05 012000 (its own task)       0.130      -      71%      0   0.0000
```

**GR00T holds within 20 cm of the orange for 96% of the run** — closer, and far
more consistently, than Pi05 (71%) or even the successful state machine (58%,
which spends time carrying oranges to the plate). It reaches `d_grasp` 0.045 m,
inside the 0.05 m predicate threshold.

**And it still lifts the orange 0.0029 m against a real grasp's 0.196 m.**

```text
So the corrected result does NOT change the verdict, it sharpens it:
  APPROACH AND TRACKING  - genuinely good, better than our own fine-tuned Pi05
  ACQUISITION            - absent. It parks at the object and closes on air.
The failure is the FINAL CENTIMETRES AND THE GRIP, not perception or reaching.
That is the same failure mode Pi05 shows on the real arm.
```

Note also that the ENV and the DATASET disagree, and the dataset wins:

```text
env cfg.task_description  "Pick three oranges and put them into the plate, then
                           reset the arm to rest state."
dataset meta/tasks.jsonl  "Grab orange and place into plate"   <- what a model saw
```

> **Rule:** read `meta/tasks.jsonl` of the dataset the checkpoint was trained on.
> Not the env's `task_description`, and never a sentence you wrote yourself.
> `sim_policy_eval_instrumented.py` now sources it from a dataset-derived table.
> -> leisaac_environments_datasets_landscape_20260805.md section 4

A relative-action policy that outputs ~zero deltas holds position forever, which
is exactly the observed freeze: the model believes it is finished.

---

## 4. *** THE GROUND-TRUTH TRAP ***

```text
mdp.orange_grasped (tasks/pick_orange/mdp/observations.py) is:

    grasped = (distance(object, ee_frame[1]) < 0.05) AND (gripper_joint < 0.60)

That is PROXIMITY AND GRIPPER-CLOSED. It does NOT test contact, force, or lift.

A policy that parks its gripper next to the orange and closes on air scores
TRUE - for 80 consecutive steps, as run4 did, with the orange displaced by
0.0001 m.
```

This is the simulation twin of the real-arm lesson that produced
`analyze_grasp_from_trace.py`'s finger-stall test: **"gripper closed" is not
"object held."** We had assumed sim GT was immune because the simulator knows
everything. It knows everything; the *predicate* is what was weak.

**Every "grasp" number in this project's sim results must be read as
proximity+closure unless object displacement is also reported.**

### Instrumentation fixed as a result

`sim_policy_eval_instrumented.py` now logs:

- `d_grasp_min` — distance from `ee_frame` **index 1**, the frame the GT
  predicate actually uses. Index 0 (the tool origin) is what `d_min` reports and
  it reads ~0.06-0.07 m longer, which is why a legitimate approach looked
  impossible in run3 (`d_min` 0.092 while the grasp frame was inside 0.05).
- `o1/o2/o3 x,y,z` for **all three** oranges. run3 grasped Orange002 while only
  Orange001 was logged, so "did the object move" could not be answered at all.

The displacement + z-travel columns are what turn a predicate into evidence.

---

## 4b. THE POSITIVE CONTROL — the harness is PROVEN GOOD

Every policy we had scored in this scene FAILED, which left a hole we could not
argue our way out of: **is the harness even capable of registering a success?**
Until that was excluded, every negative result in this project was
uninterpretable.

`scripts/sim_harness_positive_control.py` settles it. It runs LeIsaac's own
scripted state machine — the actor that produced this project's 12 place
operations, so it is known to succeed — through the **same** ground-truth code
path used to score the policies.

```text
run                            grasps longest  place#   maxDisp   maxLift
STATE MACHINE (known-good)      3/3      212      16    0.3015    0.1959
GR00T N1.7 (best run)           1/3       80       0    0.0029    0.0029
```

```text
All three pick_orange00N fire, sustained 209-212 steps.
All three put_orange00N_to_plate fire - the PLACE term works too.
The oranges MOVE 0.30 / 0.056 / 0.031 m and LIFT 0.17-0.20 m.
d_grasp_min reaches 0.021 m, under the 0.05 threshold for 984 steps.

=> THE HARNESS DETECTS GRASPS, PLACES, AND OBJECT MOTION.
=> Therefore EVERY FAILURE WE HAVE RECORDED IS A REAL FAILURE.
   Pi05's 0 grasps: real. GR00T's closing-on-air: real.
```

This also calibrates section 4's trap with a number. A **real** grasp lifts the
orange **0.17-0.20 m**. GR00T's predicate-TRUE-for-80-steps lifted it
**0.0026 m** — roughly *seventy times less*. The predicate could not tell those
apart; displacement separates them instantly.

> Run the positive control again after ANY change to the scene, the env cfg or
> the scoring code. It is ~8 minutes and it is the only thing standing between
> "the policy failed" and "our measurement failed".

### How much of this was ALREADY known — an honest accounting

Fair challenge raised at the time: *we had already run the state machine several
times; didn't we know it works?* Partly yes, and
`sim_place_data_generation_20260805.md` already recorded both "Episode success!"
and that "the environment emits six scored subtask terms". **The fact that the
state machine succeeds on this machine was established and documented.** That
part was re-established rather than looked up.

What was genuinely NEW, and load-bearing:

```text
1. THE LIFT MAGNITUDE. Nobody had ever measured how far a REAL grasp moves the
   orange: 0.17-0.20 m. Without that number "GR00T lifted it 0.0026 m" is just a
   small number with nothing to compare against. This is the measurement that
   actually kills the false grasp, and it did not exist before.
2. That the CSV scoring path in sim_policy_eval_instrumented.py - the
   obs_dict["subtask_terms"] read, written the same day - emits positives. It
   had only ever been observed emitting zeros. The earlier place-data runs used
   LeIsaac's own recorder/termination success, NOT this code path.
```

So the honest framing is narrower than "we could not tell whether the harness
works": the *simulator* was known good; *our scoring code* was not, and the
*discriminating magnitude* did not exist. Both now do.

---

## 5. Honest standing

```text
Pi05 012000    trained on THIS task (orange pick) on OUR real arm, one table.
               Hovers 13-18 cm. Never satisfies even proximity+closure.

GR00T N1.7     trained on a BROAD community mix (2,242 eps / 39 repos) of
               tabletop pick/place - never on this task, this scene, or this
               arm's calibration.
               Reaches the orange to 3.9 cm and closes. Acquires nothing.
```

The comparison is **not** apples-to-apples and should not be quoted as
"GR00T beats Pi05". Pi05 is a single-task specialist doing only a sim-transfer;
GR00T is a broad generalist doing task-transfer *and* sim-transfer at once. That
the generalist's approach is better under the harder ask is interesting, not
conclusive — and it is the first datapoint that actually speaks to the project's
central bet ("large VLAs should generalise across similar SO-101 arms"). One
datapoint, with no acquisition, is not a verdict.

What is now solid: **the serving path for GR00T N1.7 is correct and verified**,
so any future GR00T result (including a fine-tune on our own sim episodes) is
measuring the model. That was not true this morning.

---

## 6. Next — the conclusion changed during the day

```text
STOP HUNTING PUBLIC CHECKPOINTS. FINE-TUNE INSTEAD.

Three public checkpoints have now failed this scene, and every REMAINING public
option costs an era-matched, Blackwell-capable environment build EACH (Era 1 vs
sm_120 - see leisaac_environments_datasets_landscape_20260805.md section 5).

Against that:
  - LightwheelAI/leisaac-pick-orange is ungated and matches our scene, robot,
    cameras and resolution EXACTLY. v2.1, 60 eps, 36,293 frames.
  - we can generate unlimited more with NO hardware (state machine AND Mimic)
  - the harness is PROVEN to detect grasp, place and lift (section 4b)
  - fine-tuning GR00T *N1.7* reuses the serving path verified today, so there is
    no era problem at all
```

Order:

1. Fine-tune GR00T N1.7 on `LightwheelAI/leisaac-pick-orange`.
2. Add `table_with_cube` (9 files) and bring up LiftCube as a second task.
3. Use Mimic to multiply episodes rather than recording by hand.
4. Still open, cheap, unblocked: drive the openpi checkpoint
   (`felixmayor/pi05_so101_orange_cube`) — LeIsaac speaks openpi natively.

**Unchanged:** nothing has been tested on the real arm.
