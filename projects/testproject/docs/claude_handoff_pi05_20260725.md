# Claude Handoff: SO-101 Pi05 Orange Pick

Last updated: 2026-07-28

> **SUPERSEDED IN PART, 2026-07-28.** Sections 5-7 (CPU probe evidence, "best
> explanation", and the GPU-audit-first plan) are outdated: the July 25 CPU
> probe was a broken-harness result. Pod evidence recovered 2026-07-28 shows
> 012000 learned close/hold correctly and beats 003000 offline. Retraining is
> off; live deployment mismatch is the active track.
> Read first: `pi05_012000_pod_evidence_correction_20260728.md`
> Active plan: `pi05_live_mismatch_investigation_plan_20260728.md`
> Sections 2-4 (hard rules, checkpoints/dataset, real-arm trace facts) remain
> valid.

This handoff is for Claude or another agent taking over the SO-101 Pi05 orange-pick work.

## 1. Start Here

Repo:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
```

Project folder:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject
```

Read these docs first:

```text
projects/testproject/docs/pi05_active_work_tracker.md
projects/testproject/docs/pi05_012000_cpu_probe_close_frames_20260725.md
projects/testproject/docs/pi05_012000_offline_comparison_plan.md
projects/testproject/docs/pi05_012000_trace_vs_training_analysis_20260723.md
projects/testproject/docs/pi05_work_prioritization.md
projects/testproject/docs/pi05_staged_finetuning_execution_plan.md
projects/testproject/docs/so101_pi05_agent_handoff.md
```

Current source-control status at handoff time:

```text
The July 25 documentation updates are not committed yet.
Only docs should be pending.
Do not add videos, images, traces, datasets, checkpoints, or generated CSVs to git.
```

## 2. Hard Rules From User

Use official LeRobot first:

```text
official robot_client
official policy_server
official SO-101 robot class
official camera system
official defaults unless user approves a change
```

Do not create or use custom robot movement scripts unless:

```text
1. official LeRobot does not provide the needed capability
2. the reason is explained clearly
3. the user approves before creation/use
```

Read-only investigation is allowed:

```text
traces
offline comparisons
dataset analysis
logs
metrics
no robot movement
```

Valid real-arm Pi05 evaluation requires three cameras:

```text
top: /dev/video0
front: /dev/video2
wrist: /dev/video6 via Raspberry Pi bridge
```

Do not run 2-camera tests as a clean Pi05 result.

Never call a grasp a grasp without object displacement (added 2026-08-05):

```text
A "gripper closed" signal is NOT a grasp - on the real arm OR in simulation.

REAL ARM: analyze_grasp_from_trace.py uses the finger-stall test, because
  fingers cannot pass through an object.
SIMULATION: mdp.orange_grasped is
      distance(object, ee_frame[1]) < 0.05  AND  gripper_joint < 0.60
  which is PROXIMITY AND CLOSURE. It tests no contact, no force, no lift.
  A policy that parks beside the object and closes on air scores TRUE
  indefinitely - GR00T N1.7 did exactly that for 80 consecutive steps while
  displacing the orange by 0.0001 m.

=> Report OBJECT DISPLACEMENT (and z-travel) alongside every grasp claim.
=> We assumed sim ground truth was immune because the simulator knows
   everything. It does. The PREDICATE was the weak part.
-> gr00t_n17_sim_evaluation_20260805.md section 4
```

PROBE THE WIRE. The config describes TRAINING, not what crosses it (2026-08-05):

```text
The GR00T N1.7 checkpoint declares  use_relative_action: true  with
reps [RELATIVE, ABSOLUTE], which reads as "the arm output is a delta". So the
adapter added the current joint state to it. THE SERVER HAD ALREADY DONE THAT -
it applies to_absolute_chunking() itself. Every joint target was DOUBLED and
three scored runs were void.

ONE PROBE SETTLES IT. Send a known state, print the raw reply in the same units:
    state [ 5.21, -28.65, 23.36, 12.06, -3.58, 29.93]
    raw   [ 5.39, -27.17, 22.92, 11.69, -2.79, 20.64]   -> ABSOLUTE
  near the state => absolute, compose NOTHING
  near zero      => deltas, compose
Corroboration: LeIsaac's native Gr00t16ServicePolicyClient composes nothing
either - the shape of a client talking to a server that already composed.

=> A CONFIG FLAG IS A HYPOTHESIS. The wire is the evidence.
```

CHECK THE VERSION PIN BEFORE WRITING AN OPTION OFF (added 2026-08-05):

```text
Claimed, without checking: "old checkpoint eras pin old torch, which has no
sm_120, so Era 1 and Blackwell always conflict on the 5090."
TRUE for n1.5 (torch 2.5.1). FALSE for n1.6 (torch 2.7.1, sm_120 present).

That error nearly cost the project its FIRST SUCCESSFUL GRASP - the n1.6
checkpoint that picked the orange up was declared unreachable on an assumption.
Verifying it was ONE curl against the GitHub release tag.

=> Era 1 and Blackwell conflict SOMETIMES, not always. Read the pin.
```

The task string comes from the DATASET, never from you (added 2026-08-05):

```text
Read meta/tasks.jsonl of the dataset the checkpoint was trained on.
NOT the env's cfg.task_description - they disagree, and the dataset wins:

  env      "Pick three oranges and put them into the plate, then reset the arm
            to rest state."
  dataset  "Grab orange and place into plate"     <- what a trained model saw

NEVER invent one. Three separate runs on 2026-08-05 used a sentence written by
the agent, and instruction wording measurably changes behaviour:

  invented   "pick up the orange..."   object moved 0.0000 m, 0 predicate steps
  CANONICAL  "Grab orange and place..." object moved 0.0234 m, closest approach

The canonical string was the ONLY GR00T run that moved the object at all - and
it STILL lifted 8x less than a real grasp. The instruction is worth real
performance and is not a substitute for a model that can do the task.
```

Process management: never trust a pattern match (5th occurrence 2026-08-06):

```text
pgrep -f / pkill -f MATCH THEIR OWN CALLER whenever the pattern appears in the
calling shell's command line. This has now bitten FIVE times: two pkill
self-kills, one kill of the wrong sim, and one "batches running" that was the
checker matching itself while nothing ran.

RULES
1. Filter every pgrep -f through /proc/PID/comm (python vs bash) before
   believing or killing anything.
2. Kill by explicit PID once identified, never by re-running the pattern.
3. Verify a launch by its OUTPUT ARTIFACT (log file content, output file
   growing), never by process greps.
4. Long chains that wait-then-launch-then-commit break at timeouts and leave
   HALF-DONE state. Launch, verify, commit as separate steps.
```

Read a checkpoint's own config before trusting any number from it (2026-08-05):

```text
UNITS        experiment_cfg/dataset_statistics.json - arm ~+/-100 and gripper
             ~0..100 means LeRobot MOTOR units, not the sim's radians
ACTION SPACE conf.yaml use_relative_action + per-modality reps: [RELATIVE,...]
CAMERAS      conf.yaml video.modality_keys is the authority; sending a view the
             model never trained on is actively harmful (S2 proved it)

All three were wrong on the first GR00T run and it produced a confident,
completely false "grasp=TRUE". "The server replied with varied numbers" only
proves the wire format parses.
```

## 3. Current Checkpoints And Dataset

Main focused training dataset:

```text
/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
episodes: 89
frames: 40,712
composition: original 49 full episodes + 40 verified grasp/pick/move focus windows once
```

Current 012000 checkpoint on RunPod:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model
```

Local 012000 checkpoint copy:

```text
projects/testproject/artifacts/checkpoints/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/012000/pretrained_model
```

003000 baseline checkpoint on RunPod, if available:

```text
/workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
```

Important: there is no confirmed local 003000 checkpoint copy in the latest local artifacts.

## 4. What Happened With 012000 On The Real Arm

The 012000 checkpoint was tested twice using official LeRobot async execution:

```text
laptop robot_client -> RunPod policy_server -> Pi05 -> SO-101 follower
three cameras
official defaults
robot.max_relative_target=None
read-only trace enabled
```

Trace 1:

```text
official_async_3cam_012000_trace_20260722_230756
observations: 37
Pi05 chunks: 29
executed actions: 422
strong gripper close <=25: 0 frames
outcome: reached/contacted orange, no pick/lift
```

Trace 2:

```text
official_async_3cam_012000_trace_20260722_233341
observations: 21
Pi05 chunks: 16
executed actions: 220
strong gripper close <=25: 85 frames
strong close timing: timesteps 0-84, too early
final near-orange gripper: open
outcome: reached/contacted orange, no pick/lift
```

Evidence-based physical conclusion:

```text
The policy learned reach/contact better than reliable grasp.
The failure is close timing/action selection and grasp geometry.
It does not reliably do:
orange centered between fingers -> close strongly -> keep closed -> lift/move
```

## 5. Latest Offline Evidence: July 25 CPU Probe

A local CPU-only offline probe loaded the 012000 checkpoint and tested six successful focus-window frames where the recorded/demo action clearly says close and hold.

Output artifacts:

```text
projects/testproject/artifacts/offline_compare_012000_focus_20260725_cpu_probe/
summary.json
012000_cpu_probe_close_frames.csv
```

Result:

```text
selected successful close/hold frames: 6
recorded first gripper mean: 21.80
012000 predicted first gripper mean: 40.35
predicted strong close in next 10 actions: 0/6
predicted near close in next 10 actions: 0/6
```

Interpretation of gripper values:

```text
<=25 = strong close
<=35 = near close
>=45 = open
```

Example:

```text
Episode 49 frame 59

Current observed gripper state:
33.68

Recorded/demo gripper action:
24.98, 24.82, 24.90, 24.90 ...

012000 predicted gripper:
40.64, 41.63, 40.96, 37.63 ...
```

Meaning:

```text
The demo says close/hold.
012000 predicts open-ish/partial.
```

Important additional finding:

```text
The mismatch is not only gripper.
First-action mean absolute errors over the six sampled frames:
shoulder_pan: 27.47
shoulder_lift: 70.07
elbow_flex: 19.35
wrist_flex: 59.34
wrist_roll: 14.28
gripper: 18.55
```

So the sampled 012000 output does not reproduce the recorded grasp action chunk overall.

## 6. Current Best Explanation

The most evidence-backed explanation is:

```text
012000 is uncertain at the close/hold moment and falls back near the common dataset action instead of selecting the strong close action.
```

Why:

```text
Dataset gripper median action: 40.48
012000 sampled predicted first gripper mean: 40.35
```

That is almost identical. The model is predicting near the dataset's normal/median gripper action, not the recorded close action.

What is not the likely cause:

```text
not a robot clamp issue: CPU probe had no robot movement
not missing 3-camera config: dataset and checkpoint both include top/front/wrist
not "Pi05 cannot ever close": trace 233341 had 85 strong-close executed frames
not no close data: focus windows contain many close frames
```

What is still not fully proven:

```text
the CPU probe tested 6 frames, not all 40 focus windows
it used local CPU replay, not the exact RunPod GPU runtime
it tested only 012000, not 003000 baseline
it did not fully quantify lift/move direction errors across all phases
```

## 7. Next Correct Work

Do not repeat another ordinary real-arm test yet.

Next highest priority:

```text
Run full GPU offline audit on all 40 successful focus windows.
Compare 012000 against 003000 baseline if available.
```

Audit must cover these phases:

```text
before close
centered close
held close
lift begins
move begins
```

Metrics to save:

```text
recorded action chunk
012000 predicted action chunk
003000 predicted action chunk if available
gripper close miss
held-close open error
lift/move direction error
per-joint first-action error
per-joint chunk error
timing shift check: did close appear early or late in the 50-action chunk?
```

Decision rule:

```text
If 012000 fails the full offline audit:
  do not run the real arm again yet
  inspect training depth, gripper/action normalization, gripper-dimension learning,
  frame/action timing, and focused-window weighting

If 012000 succeeds offline but fails physically:
  investigate live deployment mismatch:
    start gripper state
    camera geometry
    orange placement
    timing/latency
```

Audit validity requirements (added 2026-07-25, must hold for the audit result to be trusted):

```text
1. Use the checkpoint's own saved processor artifacts in the RunPod training runtime.
   The local CPU probe had to rebuild processors from current PI05Config plus dataset
   stats because the saved config used the old registry name relative_actions_processor.
   A rebuilt pipeline can distort predictions (delta handling, normalization stats).
   The GPU audit must not inherit this rebuild; load the saved processors as trained.

2. Treat 003000 as a control, not only a comparison.
   If 003000 closes correctly on the same frames and 012000 does not: training regression.
   If BOTH predict open-ish ~40 on known close frames: suspect the replay/processor
   path or the audit harness before suspecting training.

3. Sample each frame 3-5 times, or fix and record the seed.
   Pi05 samples noise at inference, so a single prediction per frame has variance.
   Report per-frame spread so borderline results are not noise.

4. Gate on wrist_flex posture, not only gripper.
   Recorded closed/hold wrist_flex median: ~91. Live trace wrist_flex median: ~-1.
   If offline predictions get wrist_flex right on focus frames but the live trace
   drove it to ~-4, live observation mismatch becomes the stronger hypothesis even
   if gripper predictions still miss.

5. Distinguish two failure signatures in the results:
   a) collapse to dataset median: predicted gripper stays near 40 on every frame
      regardless of input (probe showed 37.6-43.0 across all 6 frames)
   b) close at the wrong time: strong close appears somewhere in the 50-action
      chunk but shifted (trace 233341 closed at t=0-84, too early)
   These have different training fixes; the timing-shift check must separate them.
```

## 8. Training Context

012000 training config:

```text
batch_size: 4
steps: 12000
effective samples seen: 48000
dataset frames: 40712
approx dataset passes: 1.18
chunk_size: 50
n_action_steps: 50
action_delta_indices: 0..49
use_relative_actions: false
normalization: ACTION=QUANTILES, STATE=QUANTILES
train_expert_only: true
image transforms: disabled
```

Dataset gripper stats:

```text
all frames:
  median gripper action: 40.48
  <=25 strong close: 10,109 / 40,712 = 24.83%
  <=35 near close: 17,560 / 40,712 = 43.13%

focus windows:
  median gripper action: 27.23
  <=25 strong close: 4,449 / 10,988 = 40.49%
  <=35 near close: 6,832 / 10,988 = 62.18%
```

This means close examples exist. The problem is likely learning/timing/weighting or replay mismatch, not simply "no close data".

## 9. Important RunPod Notes

RunPod endpoints migrate. Do not assume old IP/port is valid.

Before using RunPod:

```text
ask/check current Connect tab
verify SSH
verify checkpoint paths
verify available disk
verify GPU
```

Do not save checkpoints every 1000 steps unless storage is expanded or old checkpoints are actively pruned. A previous run failed saving at step 6000 because of disk quota.

## 10. Suggested First Commands For Next Agent

From parent repo:

```bash
cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
git status --short --untracked-files=all
```

Read current docs:

```bash
sed -n '1,230p' projects/testproject/docs/pi05_active_work_tracker.md
sed -n '1,240p' projects/testproject/docs/pi05_012000_cpu_probe_close_frames_20260725.md
sed -n '1,260p' projects/testproject/docs/pi05_012000_offline_comparison_plan.md
```

Check local probe artifacts:

```bash
ls -lh projects/testproject/artifacts/offline_compare_012000_focus_20260725_cpu_probe/
sed -n '1,40p' projects/testproject/artifacts/offline_compare_012000_focus_20260725_cpu_probe/012000_cpu_probe_close_frames.csv
```

Check dataset metadata:

```bash
sed -n '1,220p' /data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus/meta/info.json
sed -n '446,620p' /data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus/meta/stats.json
```

## 11. What Not To Do Next

Do not:

```text
repeat ordinary 012000 real-arm tests without new offline evidence
switch to 2-camera evaluation
change official LeRobot defaults without explaining why and asking the user
create custom robot execution scripts without approval
commit videos/images/traces/checkpoints/datasets/generated CSVs
paste or store Hugging Face tokens in docs/scripts/git
```

The clean next move is the full GPU offline audit.
