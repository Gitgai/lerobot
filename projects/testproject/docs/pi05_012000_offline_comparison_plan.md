# Pi05 012000 Offline Comparison Plan

Last updated: 2026-07-23

This is the next evidence step after the two official 012000 real-arm traces.

## 1. Purpose

We need to answer one question before another ordinary real-arm run:

```text
When 012000 sees successful training/focus frames, does it predict the correct close/lift/move actions?
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

## 5. Acceptance Criteria

012000 is good enough for the next real-arm test only if:

```text
it improves over 003000 on selected focus frames
it predicts strong/near close when recorded actions close
it does not predict open gripper during held-close windows
it predicts lift/move direction after close on many examples
```

If 012000 does not improve:

```text
do not run the real arm again
inspect dataset balance, gripper normalization, action timing, and checkpoint training depth
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

## 7. Next Physical Test Gate

The next real-arm test should not be a repeat of the same setup.

Before the next physical evaluation:

```text
complete this offline comparison
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
The next run must remove avoidable start-state ambiguity.
```
