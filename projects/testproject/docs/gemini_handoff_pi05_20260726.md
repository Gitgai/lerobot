# Gemini Agent Handoff: SO-101 Pi05 Orange Pick

Last updated: 2026-07-26

This handoff is for a Gemini agent taking over the SO-101 Pi05 orange-pick work.
It is self-contained, but the full evidence trail lives in the docs listed below.

## 1. Start Here

Repo:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
```

Project folder:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject
```

Read these docs, in this order:

```text
projects/testproject/docs/pi05_smooth_run_session_plan_20260728.md             (CURRENT EXECUTABLE PLAN - next robot session: pod patch, smoke run, full attempt)
projects/testproject/docs/pi05_012000_first_successful_grasp_20260728.md       (FIRST SUCCESSFUL GRASP 2026-07-28 + stutter root cause and fixes)
projects/testproject/docs/pi05_012000_pod_evidence_correction_20260728.md      (retracts the local-probe collapse conclusion; 012000 DID learn)
projects/testproject/docs/pi05_live_mismatch_investigation_plan_20260728.md    (completed investigation - trace replay + input comparison; section 4 below is superseded)
projects/testproject/docs/pi05_training_investigation_retrain_plan_20260727.md (ON HOLD - see correction doc)
projects/testproject/docs/pi05_012000_saved_pipeline_probe_20260726.md         (RETRACTED probe - kept for harness forensics)
projects/testproject/docs/claude_handoff_pi05_20260725.md        (previous agent handoff, most detail)
projects/testproject/docs/pi05_012000_offline_comparison_plan.md (the audit spec you must execute)
projects/testproject/docs/pi05_012000_cpu_probe_close_frames_20260725.md
projects/testproject/docs/pi05_active_work_tracker.md
projects/testproject/docs/pi05_work_prioritization.md
```

Source-control status at handoff time:

```text
Pending changes are docs only. Do not commit videos, images, traces, datasets,
checkpoints, or generated CSVs to git. Do not store Hugging Face tokens anywhere.
```

## 2. Hard Rules From The User

```text
1. Use official LeRobot components first: robot_client, policy_server, SO-101
   robot class, camera system, official defaults. No custom robot movement
   scripts without explicit user approval and a clear reason.
2. Read-only investigation (traces, offline comparisons, dataset analysis, logs)
   is always allowed. Robot movement is not.
3. A valid real-arm Pi05 evaluation requires three cameras:
     top: /dev/video0
     front: /dev/video2
     wrist: /dev/video6 via Raspberry Pi bridge
   Never report a 2-camera run as a clean Pi05 result.
4. Do NOT run another ordinary real-arm test before the full GPU offline audit
   is complete, unless the user explicitly approves a diagnostic run.
```

## 3. The Situation In Short

Checkpoint `012000` (Pi05 fine-tuned on 89 episodes / 40,712 frames, including
40 verified grasp-focus windows) was tested twice on the real SO-101 arm using
official LeRobot async execution, 3 cameras, official defaults,
`robot.max_relative_target=None`:

```text
Trace 230756: 422 executed actions, ZERO strong-close (<=25) frames.
              Reached/contacted orange, never commanded a strong close.
Trace 233341: 85 strong-close frames, but all at timesteps 0-84 (far too early).
              Gripper was open (~54-59) by the time it was near the orange.
Both runs: reach/contact yes, pick/lift no.
```

Gripper value convention for this dataset:

```text
<=25 = strong close    <=35 = near close    >=45 = open
Lower means more closed.
```

A local CPU-only offline probe (2026-07-25) then tested 012000 on 6 successful
focus-window frames where the recorded demo clearly closes and holds:

```text
recorded first gripper mean: 21.80 (close)
012000 predicted first gripper mean: 40.35 (open-ish)
predicted strong or near close in next 10 actions: 0/6 frames
predicted values were nearly constant: 37.6-43.0 across all 6 frames
dataset median gripper action: 40.48  <- suspiciously equal to the predictions
```

So the current best hypothesis is: 012000 falls back to the dataset-median
gripper action instead of selecting close at the right moment. But this is NOT
yet proven, because the CPU probe had known validity gaps (section 5).

## 4. Your Task: The Full GPU Offline Audit

Execute the plan in `pi05_012000_offline_comparison_plan.md`. Summary:

Compare two checkpoints on successful focus-window frames:

```text
baseline: /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model   (RunPod)
current:  /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model   (RunPod)
local 012000 copy: projects/testproject/artifacts/checkpoints/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/012000/pretrained_model
```

Dataset:

```text
/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
89 episodes, 40,712 frames
focus windows listed in: meta/grasp_focus_windows.csv
```

Frames to select: all 40 focus episodes, ~5 frames each, covering phases
before-close, centered-close, first strong close, held close, lift begins,
move begins. Target ~200 evaluated observations.

Save per frame: recorded future action chunk, 003000 predicted chunk, 012000
predicted chunk, per-joint first-action error, per-joint chunk error, gripper
close miss, held-close open error, lift/move direction error, and a timing-shift
check (does close appear anywhere in the 50-action chunk, and at what offset?).

Output goes under:

```text
projects/testproject/artifacts/offline_compare_012000_focus_YYYYMMDD/
(selection.csv, 003000_predictions.csv, 012000_predictions.csv,
 comparison_summary.csv, failure_examples.csv, contact_sheets/, notes.md)
```

Do not commit these generated artifacts.

## 5. Validity Requirements (the audit is worthless without these)

```text
1. PROCESSORS: load each checkpoint's own saved processor artifacts, in the
   RunPod training runtime. The CPU probe had to rebuild processors because the
   saved config used the old registry name relative_actions_processor (current
   code calls it delta_actions_processor). A rebuilt pipeline can distort delta
   handling and normalization, which could fake or hide the close failure.

2. CONTROL LOGIC: 003000 is a control, not just a comparison. Interpretation:
     003000 closes correctly, 012000 does not  -> training regression in 012000
     BOTH predict open-ish ~40 on close frames -> suspect the audit harness
                                                  (your script, processor path,
                                                  normalization) before training.
   Reason: two different checkpoints independently producing the identical wrong
   answer usually means the shared measurement pipeline is broken, not both
   models. The prediction ~40.35 equals the dataset median 40.48, which is
   equally consistent with model collapse OR a broken un-normalization step.
   Only the 003000 control separates these.

3. VARIANCE: Pi05 samples noise at inference. Sample each frame 3-5 times, or
   fix and record the seed. Report per-frame spread.

4. POSTURE GATE: include wrist_flex in pass/fail, not only gripper. Recorded
   closed/hold wrist_flex median is ~91; the failed live trace held ~-1. If
   offline predictions get wrist_flex right but the live run drove it to ~-4,
   live observation mismatch (camera geometry, start pose) becomes the stronger
   hypothesis even if gripper predictions still miss.

5. FAILURE SIGNATURE: separate two patterns in the results:
     a) collapse to dataset median: gripper ~40 on every frame regardless of input
     b) time-shifted close: strong close exists in the chunk but at wrong offset
   The CPU probe pattern matches (a); real-arm trace 233341 matches (b). They
   have different training fixes, so the report must say which one the full
   audit shows.
```

## 6. Decision Rule After The Audit

```text
012000 fails the audit (confirms the CPU probe):
  -> do NOT run the real arm.
  -> investigate training: gripper/action normalization (QUANTILES), gripper-
     dimension learning/weighting, action timing, focused-window weighting,
     training depth (012000 saw only ~1.18 dataset passes at batch_size 4).

012000 passes the audit (contradicts the CPU probe):
  -> first explain why the CPU probe disagreed (almost certainly the rebuilt
     processor path) and document it.
  -> then investigate live deployment mismatch: start gripper state (should
     read ~40-55 open at start, not 20-30), camera geometry, orange placement,
     timing/latency.
  -> next real-arm run only per the gate in the plan doc section 7, with
     read-only trace enabled.

Both checkpoints fail identically:
  -> fix the audit harness first; the audit is not measuring the models yet.
```

## 7. Key Training Facts (checkpoint 012000)

```text
batch_size 4, 12000 steps, ~1.18 dataset passes
chunk_size 50, n_action_steps 50, action_delta_indices 0..49
use_relative_actions: false
normalization: ACTION=QUANTILES, STATE=QUANTILES
train_expert_only: true, image transforms disabled
Close data exists: focus windows are 40.49% strong-close frames, so "no close
examples" is ruled out as the cause.
```

## 8. Environment Notes

```text
Local machine: CPU-only PyTorch, ~22 GB RAM. transformers==5.5.4 is required
for this LeRobot checkout (5.14.x breaks create_causal_mask/cache_position).

RunPod: endpoints migrate; verify the current Connect tab, SSH, checkpoint
paths, disk, and GPU before use. Do not save checkpoints every 1000 steps
without pruning; a previous run hit disk quota at step 6000.

PaliGemma tokenizer is gated; it needs HF authentication at runtime. Never
write tokens into docs, scripts, logs, or git.

Prefer `uv run` for Python commands in this repo.
```

## 9. What Not To Do

```text
- No real-arm runs before the audit passes or the user approves a diagnostic run.
- No 2-camera evaluations reported as clean results.
- No custom robot movement scripts without user approval.
- No changing official LeRobot defaults silently.
- No committing generated artifacts (CSVs, images, traces, checkpoints, videos).
- No tokens in any file.
```

The single clean next move is the full GPU offline audit under the validity
requirements in section 5.
