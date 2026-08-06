# GR00T N1.7 evaluated in LeIsaac — and a trap in our ground truth

Date: 2026-08-05. Checkpoint: `gr00t-n1.7-so101` (NVIDIA blog fine-tune).
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

BUG 2  RELATIVE ACTIONS
       conf.yaml declares  use_relative_action: true  with
           modality_keys: [single_arm, gripper]
           reps:          [RELATIVE,   ABSOLUTE]
       The arm output is a DELTA from the current state; only the gripper is an
       absolute target. The adapter passed both through as absolute.

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

### The language instruction dominates

This checkpoint was trained on **"Grab pens and place into pen holder."**
(so101-table-cleanup). We had been commanding *"pick up the orange and move it
to another place"* — a task string it never saw.

```text
"pick up the orange..."  -> approaches to 0.164 m, RETREATS to 0.394 m,
                            freezes at step 149. No grasp attempt.
"Grab pens and place..." -> approaches, closes the gripper, holds. Predicate
                            fires for 80 steps.
```

Same checkpoint, same scene, same code — **only the sentence changed**. The
project's existing rule ("the instruction MUST match the training string
exactly") is now demonstrated on a second, independent checkpoint.

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

## 5. Honest standing

```text
Pi05 012000    trained on THIS task (orange pick), real data.
               Hovers 13-18 cm. Never satisfies even proximity+closure.

GR00T N1.7     trained on a DIFFERENT task (pens -> pen holder), real data.
               Reaches the orange to 3.9 cm and closes. Acquires nothing.
```

The comparison is **not** apples-to-apples and should not be quoted as
"GR00T beats Pi05". GR00T is doing a task-transfer *and* a sim-transfer at once;
Pi05 is doing only the sim-transfer. That GR00T's approach is better under a
harder ask is interesting, not conclusive.

What is now solid: **the serving path for GR00T N1.7 is correct and verified**,
so any future GR00T result (including a fine-tune on our own sim episodes) is
measuring the model. That was not true this morning.

---

## 6. Next

1. The obvious test of the section-4 trap: re-score every historical run for
   object displacement, not just the predicate.
2. Drive the openpi checkpoint (`felixmayor/pi05_so101_orange_cube`) — LeIsaac
   speaks openpi natively; still not driven.
3. GR00T pipeline validation on `izuluaga/finish_sandwich` (S3).
4. Fine-tune GR00T on our own 12 sim place operations — now worth doing, because
   the serving path underneath it is trustworthy.

**Unchanged:** nothing has been tested on the real arm.
