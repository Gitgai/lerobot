# Plate round v1 — training results, 2026-08-26

Checkpoint: `n16_plate_v1/checkpoint-6000`
From: `orange_pick_baseline_v1` (the frozen 9/10 model)
Data: 99 episodes — 79 orange demos + 20 plate demos, two task strings
6000 steps, loss 0.0685 -> 0.011, saves every 1500.

## 1. Regression gate — PASSED

Scored on the 10 HELD-OUT orange episodes (never trained on, either round):

```text
                          honest   uses-eyes   beats-nothing
baseline (before plate)     2.41      +3.50         +3.11
plate step 1500             3.24      +3.10         +2.29   <- DEGRADED
plate step 3000             2.92      +2.94         +2.60
plate step 4500             2.72      +2.98         +2.80
plate step 6000             2.50      +3.34         +3.02   <- recovered
```

The old skill was damaged early and HEALED by continued training with the old
demos mixed in. Replay did not merely detect forgetting, it reversed it — and
stopping early would have shipped a degraded model. Use checkpoint-6000.

## 2. Plate behaviour learned — on training data

```text
error on plate episodes, baseline:  5.09   (no idea)
error on plate episodes, v1:        1.17
```

All 20 plate demos were in training, so this is FIT, not generalisation. The
arm decides whether it is real.

## 3. NEGATIVE RESULT: language is still ignored

Identical images, identical state, only the sentence changed:

```text
error with "...place it on the plate":     1.17
error with "...move it to another place":  1.13
penalty for the WRONG sentence:           -0.04
action difference between sentences:       0.92 deg
```

Two instructions in the training data did NOT make the model read them.

WHY (and this is the useful part): the SCENE already disambiguates. The plate
is physically present in plate episodes and absent in orange episodes, so the
model learns "plate visible -> plate behaviour" and the words stay redundant.
Redundant inputs get ignored - the same mechanism as when every demo shared
one sentence.

Consequence for Phase 2: two task strings are NOT sufficient. Language becomes
necessary only when the SAME scene demands different actions - orange AND apple
both present, the command choosing between them. Anything less will reproduce
this null result.

## Next
- arm test of checkpoint-6000: score orange-picking and plate-placing SEPARATELY
- expand to 60-80 plate demos before treating the plate skill as real
- Phase 2 must use same-scene/different-command data (see above)

## First arm test of plate-v1 — INCONCLUSIVE, and it implicates the SCENE

```text
plate-v1 checkpoint-6000, plate on the table:
  trial 1  no grasp - reached the orange, froze over it, gripper never
           commanded below 30 (min 37). Orange in the MIDDLE band (x=213).
  trial 2  no grasp - same signature, gripper 37-59. Orange MIDDLE (x=336).

CONTROL - orange_pick_baseline_v1 (the 9/10 model), same scene, plate present:
  trial 1  NO GRASP EITHER. gripper 36-54, pan -26..-3.
```

The model that scored 9/10 on 2026-08-20 cannot grasp on this table today.
Same checkpoint, same client, same instruction. So plate-v1 has NOT regressed -
something in the SCENE changed. This also vindicates the offline gate, which
said the two models were equivalent: they now fail equivalently.

Note on the gate's limits: the held-out probe measures SINGLE-STEP prediction
accuracy against recordings. It cannot detect a closed-loop failure - a policy
can predict well step-by-step and still stall when driving itself. Passing that
gate is necessary, not sufficient.

Two candidate causes, not yet separated:
1. THE PLATE IS ON THE TABLE. The baseline has never seen one, and this policy
   family's distractor tolerance measured near zero (four tape markers took it
   90% -> 0% on 2026-08-23). A white plate is a much larger intrusion.
2. Camera framing moved when the laptop was repositioned on 2026-08-25. It was
   verified against the reference (whole-frame shift x -2, y 0) but "within a
   few pixels" is not "identical", and this model is highly framing-sensitive.

THE DECIDING TEST, not yet run: baseline model, PLATE REMOVED, orange only -
exactly the 9/10 conditions. Grasps -> the plate is the disruption, and 20
plate demos against 79 plateless ones is nowhere near enough to normalise it.
Still fails -> the setup drifted and must be fixed before ANY model is judged.

Session ended here: the arm laptop dropped off the network (the Pi on the same
network stayed reachable, so the laptop itself went offline, not the link).
