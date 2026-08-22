# Pi05 012000 CPU Probe On Close Frames

Last updated: 2026-07-25

This document records the local read-only offline probe run on checkpoint
`012000`. It was created to answer a narrow evidence question:

```text
When 012000 sees successful focus-window frames where the recorded action closes
and holds the gripper, does 012000 also predict close?
```

This probe did not move the robot. It only loaded a local checkpoint copy,
loaded frames from the focused dataset, and compared recorded actions against
Pi05 predicted actions.

## 1. Inputs

Local checkpoint copy:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/artifacts/checkpoints/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/012000/pretrained_model
```

Dataset:

```text
/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
```

Output artifacts:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/artifacts/offline_compare_012000_focus_20260725_cpu_probe/
```

Generated files:

```text
summary.json
012000_cpu_probe_close_frames.csv
```

These generated files are evidence artifacts and should not be committed to git.

## 2. Runtime Notes

Local machine status:

```text
PyTorch CUDA available: false
CPU-only probe
RAM available during setup: about 22 GB
```

Dependency note:

```text
transformers==5.5.4 was required for compatibility with this LeRobot checkout.
```

Why:

```text
The repo declares transformers >=5.4.0,<5.6.0.
Using transformers 5.14.1 caused a create_causal_mask/cache_position mismatch.
After using transformers 5.5.4, the checkpoint model keys loaded successfully.
```

Local replay compatibility notes:

```text
The checkpoint config included pretrained_revision, but the local PI05Config did
not accept that field. For this local probe only, a temporary config copy was
used with pretrained_revision removed.

The saved processor config used an older registry name, relative_actions_processor.
The current code uses delta_actions_processor. For this local probe, processors
were rebuilt from current PI05Config plus dataset stats.
```

Important:

```text
Do not store Hugging Face tokens in docs, scripts, logs, or git.
The PaliGemma tokenizer is gated and requires authentication at runtime.
```

## 3. Selected Frames

The probe selected six successful focus-window frames spread across the focused
episodes. Each selected frame had recorded future gripper actions that were
strong close for the next 10 actions.

| Dataset Episode | Frame | Dataset Index | Recorded First Gripper | Predicted First Gripper | Predicted Min In Next 10 | Predicted Max In Next 10 |
| --------------- | ----: | ------------: | ---------------------: | ----------------------: | -----------------------: | -----------------------: |
| 49              |    59 |         29783 |                  24.98 |                   40.64 |                    37.63 |                    43.20 |
| 54              |    55 |         30889 |                  24.02 |                   40.46 |                    37.89 |                    42.69 |
| 64              |    20 |         33258 |                  14.54 |                   42.31 |                    37.86 |                    42.31 |
| 69              |    43 |         34377 |                  24.42 |                   38.14 |                    37.18 |                    41.37 |
| 74              |    55 |         35639 |                  23.66 |                   37.64 |                    35.52 |                    40.63 |
| 79              |    20 |         36793 |                  19.21 |                   42.96 |                    39.92 |                    45.42 |

Interpretation of gripper values for this dataset:

```text
<=25 = strong close
<=35 = near close
>=45 = open
```

So these frames asked a simple question:

```text
Recorded demonstration says: close and hold.
Does 012000 also say: close and hold?
```

## 4. Result Summary

Probe summary:

```text
num_frames: 6
recorded_all_are_strong_close_first: true
pred_frames_with_any_strong_close_10: 0
pred_frames_with_any_near_close_10: 0
pred_frames_with_open_ge45_in_10: 1
mean_recorded_first_gripper: 21.8034
mean_pred_first_gripper: 40.3512
```

Plain-language meaning:

```text
The recorded training examples said close.
The 012000 checkpoint predicted mostly open-ish gripper values.
Across the six sampled frames, 012000 did not predict even one near-close value
in the next 10 predicted actions.
```

Example:

```text
Episode 49 frame 59:
  recorded next grippers:
    24.98, 24.82, 24.90, 24.90, 24.90 ...
  012000 predicted next grippers:
    40.64, 41.63, 40.96, 37.63, 43.20 ...

The demonstration action is close/hold.
The checkpoint prediction is open-ish/partial.
```

## 5. Evidence-Based Meaning

This sampled probe supports this conclusion:

```text
The 012000 checkpoint is not reliably reproducing close/hold actions even on
successful focus-window frames from the training-style dataset.
```

That matters because the real-arm traces showed similar behavior:

```text
Trace 230756:
  reached/contacted orange
  no strong close near the orange

Trace 233341:
  strong close happened early
  gripper opened again near the orange
```

The CPU probe now gives an offline model-side reason that matches the physical
failure: the checkpoint has not reliably learned the conditional rule:

```text
orange centered between fingers -> close -> keep closed -> lift/move
```

## 6. What This Does Not Prove Yet

This was a useful probe, but it is not the full final audit.

Still open:

```text
It tested 6 frames, not all 40 focused windows.
It used the local CPU environment, not the exact RunPod GPU training runtime.
It tested only 012000, because no local 003000 checkpoint copy was available.
It does not quantify lift/move direction errors across all focus stages.
```

Therefore the next evidence step is not another ordinary robot run. The next
step is a full offline GPU audit.

## 7. Next Plan

Run a full offline comparison on RunPod or another GPU environment:

```text
012000 checkpoint vs all 40 successful focus windows
003000 checkpoint baseline if available
frames: before close, centered close, held close, lift begins, move begins
metrics: gripper close miss, held-close open error, lift/move direction error
```

Decision rule:

```text
If full audit confirms the sampled failure:
  do not run the real arm again yet
  inspect training depth, action normalization, gripper dimension loss, action
  timing, and focused-window weighting

If full audit contradicts the sampled failure:
  inspect the local replay path before changing training

Only run another real-arm evaluation after the checkpoint passes the offline
close/hold/lift gate, or after explicit user approval for a diagnostic run.
```
