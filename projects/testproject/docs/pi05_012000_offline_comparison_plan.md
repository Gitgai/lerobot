# Pi05 012000 Offline Comparison Plan

Last updated: 2026-07-28

> **ANSWERED 2026-07-28.** The question this plan poses was already answered on
> 2026-07-22 by a pod-side comparison (recovered 2026-07-28): 012000 DOES
> predict close/hold/lift correctly on focus frames (gripper corr 0.83,
> MAE 4.4 on closed frames) and improves on 003000 on every joint. The July 25
> sampled CPU probe cited below was a broken-harness result (wrong lerobot
> code version for this checkpoint) and is retracted. Per section 5's own
> decision rule, the live-deployment-mismatch branch is now active.
> See: `pi05_012000_pod_evidence_correction_20260728.md` and
> `pi05_live_mismatch_investigation_plan_20260728.md`.
> Validity lesson: section 4b requirement 1 (training-runtime processors) was
> the one that mattered - add "training-era CODE version" to it, not just
> saved processor files.

This is the full offline evidence plan after:

```text
two official 012000 real-arm traces
one sampled local CPU probe on successful close/hold focus frames
```

## 1. Purpose

We need to answer one question before another ordinary real-arm run:

```text
Across the full focus-window dataset, does 012000 predict the correct close/hold/lift/move actions when it sees successful training/focus frames?
```

Why this matters:

```text
If 012000 fails on known-good training frames, the problem is model/training.
If 012000 succeeds on known-good training frames, the problem is more likely live deployment mismatch:
  start gripper state
  camera geometry
  object placement
  timing/latency
```

Current partial result from 2026-07-25:

```text
A sampled local CPU probe tested 6 successful close/hold focus frames.
Recorded first gripper mean: 21.80
012000 predicted first gripper mean: 40.35
Predicted strong-close frames in next 10 actions: 0/6
Predicted near-close frames in next 10 actions: 0/6
```

Plain meaning:

```text
The first sampled evidence says 012000 did not reproduce close/hold actions on
known-good focus frames. The full audit must now confirm whether that problem is
general across the 40 focused windows.
```

Detailed sampled-probe report:

```text
projects/testproject/docs/pi05_012000_cpu_probe_close_frames_20260725.md
```

## 2. Inputs

Dataset:

```text
/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
repo_id: local/so101_orange_49_plus_grasp_pick_move_focus
episodes: 89
frames: 40,712
```

Current real-arm checkpoint:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model
```

Local 012000 checkpoint copy used by the sampled CPU probe:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/artifacts/checkpoints/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/012000/pretrained_model
```

Comparison baseline:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
```

Focus-window source:

```text
/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus/meta/grasp_focus_windows.csv
```

Trace evidence to compare against:

```text
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_230756
projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_233341
```

Sampled probe artifacts:

```text
projects/testproject/artifacts/offline_compare_012000_focus_20260725_cpu_probe/
```

## 3. Frame Selection

Use successful focus windows only.

Select frames around:

```text
before close
orange centered between fingers
first strong close
held close
lift/move begins
after lift/move
```

Minimum selection:

```text
10-20 focus episodes
5-7 frames per episode
at least 50 evaluated observations
```

Preferred selection:

```text
all 40 focus episodes
5 frames per episode
about 200 evaluated observations
```

Frame selection must include episodes with different gripper patterns:

```text
strong sustained close
close then reopen
low/min gripper values
moderate close values
different wrist/top/front views
```

## 4. Metrics

For each selected frame, save:

```text
dataset episode index
frame index
timestamp
task text
top/front/wrist image references
observation state
recorded future action chunk
003000 predicted action chunk
012000 predicted action chunk
```

Compare:

```text
full action mean absolute error
first-action mean absolute error
gripper action mean absolute error
shoulder/elbow/wrist lift-motion error
recorded strong close but predicted open
recorded open but predicted close
recorded lift/move but predicted hover
```

Critical gripper checks:

```text
recorded gripper <=25 and predicted gripper >35
recorded gripper <=35 and predicted gripper >=45
predicted close occurs before the close frame
predicted opens during a recorded held-close window
```

Critical motion checks:

```text
after close, predicted shoulder/elbow/wrist deltas should match the recorded lift/move direction
predicted action chunk should not only hover around the orange
```

## 4b. Validity Requirements

The audit result is only trustworthy if all of these hold:

```text
1. Processors: load the checkpoint's own saved processor artifacts in the RunPod
   training runtime. Do not rebuild processors like the local CPU probe had to
   (relative_actions_processor -> delta_actions_processor rename). A rebuilt
   pipeline can distort delta handling and normalization, which could fake or
   hide the close failure.

2. Control: run 003000 on the exact same frames. If both checkpoints predict
   open-ish ~40 on known close frames, suspect the audit harness or processor
   path before suspecting training.

3. Variance: Pi05 samples noise at inference. Sample each frame 3-5 times or fix
   and record the seed, and report per-frame spread.

4. Posture: include wrist_flex in the pass/fail gate. Recorded closed/hold
   wrist_flex median is ~91 while the live trace held ~-1. Correct offline
   wrist_flex with wrong live wrist_flex points at live observation mismatch.

5. Failure signature: separate "collapse to dataset median gripper ~40 on every
   frame" from "close present in the chunk but time-shifted". The CPU probe
   pattern (37.6-43.0 on all 6 frames, dataset median 40.48) matches collapse;
   trace 233341 (close at t=0-84, too early) matches time-shift. Different fixes.
```

## 5. Acceptance Criteria

012000 is good enough for the next ordinary real-arm test only if the full GPU audit contradicts or materially improves on the sampled CPU-probe failure:

```text
it improves over 003000 on selected focus frames
it predicts strong/near close when recorded actions close
it does not predict open gripper during held-close windows
it predicts lift/move direction after close on many examples
```

If 012000 does not improve:

```text
do not run the real arm again
inspect dataset balance, gripper/action normalization, action timing, gripper-dimension loss, focused-window weighting, and checkpoint training depth
```

If 012000 improves offline but real arm still fails:

```text
investigate deployment mismatch:
  live start gripper state
  live camera geometry
  orange placement
  timing/latency
```

## 6. Output Artifacts

Save comparison output under:

```text
projects/testproject/artifacts/offline_compare_012000_focus_YYYYMMDD/
```

Required files:

```text
selection.csv
003000_predictions.csv
012000_predictions.csv
comparison_summary.csv
failure_examples.csv
contact_sheets/
notes.md
```

Do not commit generated CSVs, images, or model outputs unless the user explicitly asks.

Existing sampled-probe output:

```text
projects/testproject/artifacts/offline_compare_012000_focus_20260725_cpu_probe/
```

## 7. Next Physical Test Gate

The next real-arm test should not be a repeat of the same setup.

Before the next physical evaluation:

```text
complete the full GPU offline audit
confirm the checkpoint predicts close/hold/lift on successful focus frames, or get explicit user approval for a diagnostic physical run despite offline failure
start the arm in the normal original-episode start pose
open the gripper visibly
confirm first observed gripper state is closer to 40-55, not 20-30
use official LeRobot async
use three cameras
use robot.max_relative_target=null
enable read-only trace
```

Reason:

```text
The 012000 trace evidence shows close timing/geometry failure.
The sampled CPU probe shows 012000 failed close/hold on known-good frames.
The next physical run must not hide a model/training issue behind another mixed live result.
```
