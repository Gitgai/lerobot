# Pi05 012000 Offline Probe With The Checkpoint's Own Saved Pipeline

Last updated: 2026-07-28

> **RETRACTED 2026-07-28.** The collapse this probe measured was an artifact of
> the local replay environment (newer lerobot code than the checkpoint was
> trained with), not a property of the model. A pod-side comparison from
> 2026-07-22, recovered on 2026-07-28, shows 012000 predicting close correctly
> (gripper corr 0.83, MAE 4.4 on closed frames) and beating 003000.
> See: `pi05_012000_pod_evidence_correction_20260728.md`.
> The harness-forensics content below (stats verification, frame-index
> mislabeling in the July 25 probe) remains valid.

This is the follow-up to the July 25 CPU probe. It removes the main validity
doubts of that probe and extends the test to three frame categories. It was
read-only: no robot movement, no training, no dataset changes.

## 1. What Is Different From The July 25 Probe

```text
1. Processors were NOT rebuilt. The checkpoint's own saved
   policy_preprocessor.json / policy_postprocessor.json and their saved
   normalization safetensors were loaded directly. The only change was
   registering the old step name relative_actions_processor as an alias of the
   current class (same code, renamed registry key) and running on cpu.

2. Harness pre-checks passed before any inference:
   - The checkpoint's saved normalization stats are IDENTICAL to the dataset's
     meta/stats.json (q01/q99/mean/std match to the last decimal).
   - The relative/delta actions step was DISABLED at training
     (enabled: false in the saved preprocessor). Actions are plain absolute
     values. The delta-vs-absolute confound is ruled out.

3. Three frame categories instead of one, all from focus episodes (49-88),
   all with >=50 frames left in the episode:
   - close:    next-10 recorded gripper actions all <=25 (verified in data)
   - open:     next-10 recorded gripper actions all >=45
   - preclose: currently open (>=40), recorded strong close begins inside the
               next 50 actions (tests timing inside the chunk)

4. Two seeds per frame (Pi05 samples noise at inference).

5. Full 50-action chunks compared per joint, not only the first action.
```

## 2. Correction To The July 25 Probe Doc

The July 25 probe's frame table was mislabeled. Verified against the dataset's
own meta/episodes metadata and ds[i] lookups:

```text
Claimed index -> claimed frame        Actual dataset row
29783 = ep49 f59 (close 24.98)       ep49 f59, gripper 24.98  CORRECT
30889 = ep54 f55 (close 24.02)       ep53 f13, gripper 48.51  WRONG (open frame)
33258 = ep64 f20 (close 14.54)       ep62 f147, gripper 8.19  wrong label, still close
34377 = ep69 f43 (close 24.42)       ep66 f275, gripper 42.57 WRONG (open frame)
35639 = ep74 f55 (close 23.66)       ep72 f37, gripper 40.44  WRONG (open frame)
36793 = ep79 f20 (close 19.21)       ep75 f295, gripper 46.60 WRONG (open frame)
```

The recorded gripper values the July 25 doc reports do not match the dataset
rows at those indices, so either its selection or its labeling was broken.
This probe selects close frames programmatically and verifies each against the
recorded actions, so the ambiguity is gone. (The July 25 headline conclusion
survives anyway; see below.)

## 3. Results (16 frames x 2 seeds = 32 predictions)

Artifacts: `projects/testproject/artifacts/offline_compare_012000_focus_20260726_cpu_probe2_v2/`
(probe2_results.csv, probe2_summary.json, per-frame chunk .npy files, probe script copy).
Do not commit these.

```text
Category   n   recorded first gripper   predicted first gripper
close      12  23.1 - 25.0 (mean 24.2)  40.0 - 42.9 (mean 41.3)
open       12  46.8 - 54.6 (mean 50.3)  39.9 - 42.6 (mean 41.2)
preclose    8  46.0 - 51.6 (mean 47.8)  40.0 - 42.2 (mean 41.1)
```

The decisive facts:

```text
1. Predicted first gripper across ALL 32 predictions: 39.9 - 43.4.
   The dataset median gripper action is 40.48.
   The prediction does not depend on the input at all: a deeply closed frame
   (recorded 23) and a wide open frame (recorded 55) get the same ~41.

2. Strong close (<=25) appeared in ZERO of the 32 predicted 50-step chunks.
   Even near close (<=35) appeared in ZERO chunks.
   Lowest gripper value the model ever produced anywhere: 35.8.

3. Preclose timing test: on frames where the recorded close begins 9 or 40
   steps into the chunk, the predicted chunk never closes at any offset.
   This is not a timing shift. Close is absent entirely.

4. The arm joints are also wrong on training frames:
   chunk MAE  close/open/preclose
   shoulder_lift: 39.9 / 67.4 / 61.1   (with sign flips: recorded +35, predicted -40)
   wrist_flex:    68.6 / 46.8 / 42.6   (recorded grasp posture 65->103, predicted 10-26)
   wrist_roll:     9.0 / 10.8 /  9.9
   The model does not reproduce the demonstrated trajectories even on frames
   it was trained on.

5. Seed variance is small (~2 units on the gripper). The collapse is stable,
   not sampling noise.
```

## 4. Failure Signature: Collapse, Not Timing

Of the two candidate signatures from the plan doc, the offline evidence is
category (a):

```text
(a) collapse to dataset median  <- THIS. Gripper pinned at ~41 regardless of input.
(b) close at the wrong time     <- NOT this offline. Close never appears at all.
```

The live trace 233341 early close (t=0-84) remains a live-only observation; the
offline model never closes.

## 5. Why The Harness Explanation Is Now Weak

```text
- The saved pipeline was used end-to-end (no rebuild).
- The saved normalization stats equal the dataset stats exactly, so the July 25
  rebuilt pipeline was numerically equivalent anyway.
- The offline predictions match the LIVE robot behavior signature: low
  wrist_flex (predicted 10-26 offline, live trace ~-1 vs demo ~91) and no
  strong close near the object. The live path ran on RunPod through the
  official policy server - a completely different harness - and produced the
  same behavior. Two independent harnesses agreeing points at the model.
```

Remaining caveats (for the RunPod audit):

```text
- CPU float32 runtime, not the training GPU runtime (weak caveat; float32 is
  the checkpoint dtype).
- 003000 control still not run (no local copy). Still worth doing on RunPod as
  final confirmation, and to check whether 003000 was ever better.
- 16 frames, not all 40 windows.
```

## 6. Conclusion

```text
Checkpoint 012000 did not learn the grasp behavior. It outputs a nearly
input-independent "average" trajectory: gripper pinned at the dataset median,
wrist/shoulder far from the demonstrated grasp posture, no close anywhere in
any predicted chunk. This matches both real-arm failures.

Per the decision rule: do NOT run the real arm. The problem is
training/model-side, not live deployment mismatch.
```

Leads for the training investigation, in rough priority:

```text
1. Training depth: 12000 steps x batch 4 = ~1.18 passes over 40,712 frames.
   That is very little for fine-tuning a flow-matching VLA; the model may
   simply be far from converged (consistent with predicting the mean).
2. Verify the training loss curve actually decreased and the restart-from-
   003000 loaded weights correctly.
3. QUANTILES action normalization: check whether the gripper dimension's
   normalized targets have enough spread during training.
4. Focus-window weighting: focus frames are 27% of the data; close moments are
   a small fraction of a 50-step chunk loss.
```
