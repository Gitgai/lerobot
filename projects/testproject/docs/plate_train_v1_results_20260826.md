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
