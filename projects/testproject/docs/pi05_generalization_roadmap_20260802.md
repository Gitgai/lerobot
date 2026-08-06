# Generalization Roadmap: From One-Orange Specialist To Multi-Task Robot

Last updated: 2026-08-04 (banner); roadmap body 2026-08-02

> ## ⚠️ STAGE 2 AND THE BUDGET LINES ARE SUPERSEDED (2026-08-04)
>
> **Stage 2 as written cannot deliver what this roadmap is built on.** Its
> "standing insight" is that diverse data widens the policy - but Stage 2
> records 40-60 episodes in ONE room, on ONE table, under ONE lighting setup.
> That buys object and position variety; it cannot buy **environment** variety,
> which PI's own ablation ranks as the single most damaging thing to remove
> (OOD success -> 31%). You cannot un-weld a model from a scene using more data
> from that same scene.
>
> A public corpus of ~1,222 SO-100/101 datasets from **377 users** - i.e. 377
> different rooms - supplies exactly that missing variable.
> **Do not skip Stage 2; restructure it.** Record fewer, more focused episodes
> covering OUR scene, OUR three cameras and the PLACE phase, and let community
> data supply environment diversity. Co-train, as PI did.
> Read: **`community_data_strategy_20260804.md`**
> Gating question there: can pi05 train on datasets with fewer cameras than the
> policy declares? If not, this narrows sharply.
>
> **Costs are also stale.** Stages priced at $0.50-$5 assumed a rented pod. The
> policy now runs on a local RTX 5090 and the pod is stopped, so training and
> evaluation cost electricity. Sequencing changed too: simulation work comes
> before hardware, and testing checkpoints in sim is now nearly free.
> Read: `new_machine_local_serving_20260804.md`
>
> Stages 0, 1, 1-RESULTS and 1-ADDENDUM are historical record and stand as
> written. Stages 3-5 stand, with costs reinterpreted as local GPU time.

User goal, verbatim intent: the robot should NOT depend on fruit size or type,
and should progress toward doing other tasks (onion, tomato, more) without a
fine-tune per task.

Standing insight this roadmap is built on: fine-tuning on ONE task narrows the
policy into a specialist; fine-tuning on DIVERSE data widens it back into a
body-adapted generalist. We do not escape fine-tuning - we make each round of
it buy MORE generality, until new tasks fall inside what the model already
knows. Full background: pi05_feature_backlog_20260801.md and the sessions doc.

## Stage 0 - Big-Orange Count (next session, ~40 min, ~$0.50)

```text
The controlled diagnostic: five runs, demo-sized orange, frozen h35 recipe.
Answers: (a) does carry-retention recover at demo geometry (edge-grip theory,
user-confirmed on video)? (b) does the never-tested PLACE phase complete?
Shapes Stage 2's data emphasis. Unchanged from the prior plan.
```

## Stage 1 - Zero-Shot Probe Session (NEW; ~30 min, no training)

Measure how much generalist survived the orange fine-tune, before adding data.
One session, correct/honest prompt per trial, ~2 attempts each:

```text
P1 "pick up the onion and move it to another place"    (in-family, new object)
P2 "pick up the tomato and move it to another place"   (in-family, new object;
    NOTE tomato is soft - watch grip force, expect squishing; log it, that IS
    the datapoint)
P3 "pick up the ball/block and move it"                (in-family, new shape)
P4 "pick up the banana and move it to another place"   (in-family, ELONGATED
    shape - the geometry probe: a banana cannot be gripped like a sphere;
    watch whether the wrist rotates to align across the banana's width, and
    where along its length the fingers land)
P5 "push the orange to the left side of the table"     (OUT-of-family motion -
    the informative one: does any non-pick behavior remain accessible?)
P6 "pick up the banana and put it on the plate"        (GOAL probe - plate on
    the table for THIS probe only; run after P4 so the P4-vs-P6 difference is
    attributable to the instruction/goal change. Prediction: plate ignored.)
Scene rule: the plate stays OFF the table for P1-P5 (single-novelty
discipline); the user's plate idea becomes standard in Stage 2.
Scene protocol: for P1-P4 place the NAMED object AND the small orange on the
table, well apart - each trial then also tests object SELECTION: does it obey
the instruction, or does the orange-specialist grab the orange regardless?
Scoring per prompt: approached the NAMED object? / attempted the right MOTION
(pick vs push)? / completed?
Prediction on record: P1-P3 partial success (approach+grab attempts, geometry
misses on odd shapes), P4 likely reverts to picking. Whatever happens, we get
the real generality baseline - and every probe failure tells Stage 2 exactly
what data to include.
```

## Stage 1 RESULTS (2026-08-02 session - completed same day it was planned)

```text
PROBE       SELECTION  PICK        CARRY              NOTES
P4 banana   YES        no          -                  sustained wrist ROTATION
                                                      (-17..-37) aligning to the
                                                      elongated shape - novel
                                                      behavior; pick blocked by
                                                      flat low profile vs learned
                                                      approach height
P1 onion    YES        YES (w30)   BEST EVER: ~40 s,  zero-shot object out-
                                   full height,       performed the trained
                                   grip never wavered fruit; slipped only after
                                                      long parked hold at top
P2 tomato   YES (vs    YES (w33,   full height,       fastest grab-to-carry ever
            look-alike  ~7 s -     stable             (~15 s); NO crushing -
            orange!)    fastest)                      learned squeeze is
                                                      soft-fruit safe
P6 tomato   YES        unstable    partial            THE GOAL PROBE: across 3
 -> plate               (fruit                        attempts, ZERO plate-
                        degraded                      directed motion in any
                        by session                    lifted moment. Goal-
                        end)                          conditioning NOT observed
                                                      (prediction confirmed,
                                                      moderate confidence).
P3 ball / P5 push: not run (session length); P5 remains the most interesting
open question for a future session.

HEADLINE: SELECTION 4/4. The "orange specialist" obeys OBJECT words nearly
perfectly - the specialization lives in grasp GEOMETRY and GOALS, not in
language. Novel behaviors observed zero-shot: wrist alignment (banana),
soft-grip compatibility (tomato), superior carry (onion).

WHAT THIS SHARPENS FOR STAGE 2: (a) approach-height diversity is the top
data need (flat/low objects like the banana); (b) the plate-goal must be
TAUGHT (P6 confirms it will not emerge on its own); (c) object variety
mostly works already - fewer episodes needed per object than feared.
```

## Stage 1 ADDENDUM (2026-08-02 evening + 08-03 code investigation)

```text
ONION -> PLATE, two runs, both FAILED - and the failure is informative.
Run 1 (healthy: 1.73 obs/s, 20.9 act/s): 3 stalled squeezes vs 145 EMPTY over
10 minutes. Zero real holds. Same onion, same checkpoint, same recipe that
carried it 40 s that MORNING. The variable was the SCENE: plate added to the
view, onion at an unpracticed spot. -> POSITION/SCENE generalization is a
verified failure mode, now co-top Stage 2 priority alongside approach height.
Run 2: starved (0.39 obs/s = one image every 2.6 s, tunnel dying) - discarded
as infrastructure. An external video analysis (codex) independently read the
same runs as "reach and press, never a real grasp"; the traces confirmed it.
Because no pick completed, the PLATE/GOAL question got NO new evidence - the
"goal-conditioning not observed" finding still rests on the midday P6 runs.

NEW TOOL: scripts/analyze_grasp_from_trace.py - the finger-stall test (fingers
cannot pass through an object: commanded squeeze + measured width STALLS =
real grasp; measured FOLLOWS the command down = closed on air). It corrected
two verbal claims, including an assistant's own "carries happened" read.
Also gates on obs rate: below 0.8 obs/s a run is BLIND, discard behaviorally.
Use it to score every Stage 4 run instead of eyeballing video.

ARCHITECTURE FINDING (full detail in agent_handoff_pi05_20260803.md Section 6):
Physical Intelligence released only pi05's LOW-LEVEL half - openpi states
"we currently only support the flow matching head". The high-level brain that
decodes subtask TEXT ("pick up the pillow") before acting was never released,
so lerobot could not port it. Our compound instruction goes straight to the
motor expert. Verified by code reading (incl. the training-era commit the pod
runs) that the task string is re-read and re-tokenized on EVERY inference with
no caching -> we can switch it mid-episode from the laptop with zero pod
changes. Hence the new first experiment:

  SUBTASK-SWITCHING PROBE (do before Stage 2 recording, ~15 min):
  start "pick up the onion"; when the live stall test says it is held, switch
  to "put the onion on the plate". Onion at its PRACTICED spot, plate
  elsewhere (isolate the goal question). Either outcome sharpens Stage 2 -
  and if switching helps, subtask-style strings become standard in how we run
  AND how we record.

Also found: use_relative_actions (OpenPI DeltaActions) exists in the port and
is OFF by default; we trained ABSOLUTE joint targets, which encode the
practiced table position - precisely the failure above. Training-time only ->
Stage 3 decision below.
```

## Stage 2 - The Generalist Data Round (recording, ~2-3 h teleop)

```text
40-60 episodes on the SAME task family, maximum variety:
  objects: small orange, big orange, ONION, TOMATO (gentle-grip exemplars!),
           BANANA (elongated - teaches grip orientation/alignment),
           a ball or block - 4-6 objects across sizes/shapes/colors
  POSITIONS: vary object AND plate positions widely across the table (added
           2026-08-02 evening: the specialist fails at unpracticed spots).
           Vary scene too - background, lighting, small camera nudges. PI's
           own ablation ranks ENVIRONMENT diversity as the single biggest
           driver of out-of-distribution success.
  TASK STRINGS AT TWO LEVELS: some episodes compound ("pick up the onion and
           put it on the plate"), some single-subtask ("pick up the onion" /
           "put the onion on the plate"). This is how PI built the hierarchy
           and it makes subtask switching trainable rather than a hack.
  every episode driven to full completion: grasp -> lift -> carry -> PLACE
  PLACE TARGET = THE PLATE (user's idea, adopted): every episode ends with
  the object set down ON the plate; task strings become
  "pick up the X and put it on the plate" - a consistent, visually salient
  goal that gives the place phase a clear learning signal and makes success
  unambiguous (object-on-plate) for later evaluation
  varied placements (object AND plate positions); slight camera nudges
  between some episodes
  correct per-object task strings - this is what re-teaches
  instruction-following
If Stage 1's P4 motivates it and energy allows: +10-15 push/slide episodes as
a second task family ("push the X to the left") - the first true step beyond
pick-and-place.
```

## Stage 3 - The Generalist Fine-Tune (overnight, ~$3-5)

```text
Train on the NEW lerobot code (code-pairing rule; native RTC - adapter
retires). Enable the banked features: image_transforms ON, wandb ON,
eval_split ON.
DECIDED 2026-08-03: use_relative_actions=true (gripper excluded) -
  --policy.use_relative_actions=true --policy.relative_exclude_joints='["gripper"]'
  Absolute targets encode the practiced table position; relative offsets from
  the current state make the SHAPE of a grasp reusable anywhere. Pairs with
  the position diversity above - flag and data work together, neither alone.
DECIDED 2026-08-03: init from BASE, not 012000. The base weights carry the
  web + multi-robot co-training that our single-task fine-tune partially
  overwrote; body adaptation is cheap to re-learn from diverse data, that
  education is not (PI ablations: dropping those data sources costs tens of
  points of OOD success).
Gate offline (exam harness) before any robot time.
```

## Stage 4 - Measured Generality (the scoreboard becomes a matrix)

```text
Five-run counts PER OBJECT (and per task family if push was trained):
              grasp  lift  carry  place
  big orange    /5    /5     /5     /5
  small orange  /5    ...
  onion         /5
  tomato        /5    (+ squish rate!)
  novel object NOT in training (e.g. a lemon) - the true generalization test
"Size/type-independent" becomes a table of numbers, not a claim.
```

## Stage 5 - Long-Term Ambitions (honest tiering)

```text
REACHABLE with this arm, later data rounds:
  new task families: push/slide, stack, drop-into-container, handover
  wipe a surface with a sponge (dry) - the realistic cousin of dish-washing
  gripper load/current signal into observations (crude touch) if soft-object
  grips (tomato!) stay clumsy after Stage 3
NOT REACHABLE with current hardware (parked honestly):
  washing dishes - needs water (unsafe near unsealed servos/electronics),
  bimanual coordination, and dexterity beyond a single 6-DoF hobby arm.
  Revisit only with a hardware change (sealed gripper, second arm, sink rig).
```

## Sequencing And Budget Reality

```text
Stage 0: next session          ($0.50)
Stage 1: same or next session  ($0.50)
Stage 2: one focused evening   (free; teleop labor)
Stage 3: one overnight         ($3-5, on a healthy pod; wandb this time)
Stage 4: 1-2 sessions          ($1-2)
Total: roughly a week of casual evenings to a measured, multi-object robot.
Ops rules unchanged: camera-reference gate every session, stop pods, one
variable at a time, offline gates before live.
```
