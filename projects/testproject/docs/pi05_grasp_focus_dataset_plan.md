# Pi05 Grasp Focus Dataset Plan

Last updated: 2026-07-21

This plan explains how we will reuse the best grasp/pick/move parts from the existing 49-episode SO-101 orange dataset before recording more episodes.

The goal is not to guess that more data is needed.

The goal is to check whether the data we already have contains the exact behavior Pi05 failed to do during the traced real-arm run:

```text
see orange near gripper
center both gripper fingers around orange
close gripper while centered
lift orange
move orange to another place
```

## 1. Why We Are Doing This

The official traced run showed:

```text
Pi05 saw the orange from top/front/wrist cameras.
LeRobot sent the same action values Pi05 requested.
No robot.max_relative_target clamp was used.
The arm reached near the orange.
The gripper did not commit to a clean close-and-lift at the close-range moment.
```

That means the next question is about training data coverage:

```text
Did the 49 episodes teach the final grasp moment strongly enough?
```

A full episode may contain many reach frames and only a short grasp window.

Example:

```text
Episode length: 720 frames

frames 0-300:
  arm moves toward orange

frames 300-360:
  gripper gets close and aligns

frames 360-390:
  gripper closes

frames 390-520:
  orange lifts and moves

frames 520-720:
  reset, resting, extra motion, or end behavior
```

For our failure, the most important training signal is:

```text
frames 300-520
```

So we want to mine those useful windows from all 49 episodes.

## 2. What We Already Have

Main dataset:

```text
/data/lerobot_datasets/so101_orange_49
```

Dataset facts checked locally:

```text
total episodes: 49
total frames: 29,724
fps: 30
camera streams: top, front, wrist
state/action: 6D SO-101 joints
task: pick up the orange and move it to another place
```

Useful candidate window audit:

```text
projects/testproject/artifacts/dataset_grasp_window_audit_20260720/candidate_grasp_pick_windows.csv
```

First automatic result:

```text
likely close/lift windows found in 47 of 49 episodes
```

Important: that result is a signal, not a final label.

The automatic audit finds where close/lift probably happens. For training, we still need to visually extend or trim each candidate into a full grasp-pick-move window.

Before building any dataset, confirm gripper direction from real dataset evidence:

```text
Pick at least 3 episodes.
Inspect frames before close, during close, and after close.
Confirm whether lower gripper.pos means more closed and higher gripper.pos means more open.
Record the observed open/closed value ranges in the review notes.
```

Confirmed gripper direction from the dataset review:

```text
lower gripper.pos = more closed
higher gripper.pos = more open
```

Evidence:

```text
episode 00: about 49.4 open -> 26.3 closed
episode 07: about 55.3 open -> 19.7 closed
episode 29: about 51.6 open -> 0.8 closed
```

## 3. What We Mean By A Good Window

A good window is a short segment from one episode that contains the full final task chain.

Good example:

```text
orange visible in at least wrist camera and one outside camera
gripper approaches from useful angle
orange becomes centered between both fingers
gripper closes around orange
arm lifts orange from table
arm moves orange to another place
orange is released or clearly held at the new place
```

Bad example:

```text
gripper pushes orange from the side
gripper closes on empty air
orange is blocked by hand or robot body
wrist camera cannot see the grasp moment
orange never lifts
orange lifts but does not move to another place
segment starts after the important close already happened
segment mostly shows reset or resting motion
```

Mixed example:

```text
gripper touches orange but does not lift
gripper grasps and lifts but does not move the orange to another place
```

A mixed example should not be used as positive grasp-pick-move training unless we deliberately label it as correction/failure data.

For the main focused dataset, use only clean successful grasp-pick-move windows.

Definition of "moved to another place":

```text
good:
  orange is lifted clear of the table and visibly translated away from its original table position

not good:
  orange lifts slightly but stays in the same place
  orange is pushed or rolled without being held
  orange is held but the move destination is unclear
```

The move does not need to end at a perfect fixed target.

It must clearly show:

```text
grasp -> pick/lift -> move away from original position
```

## 4. What We Extract

We do not extract only still images.

For Pi05 training, each segment must include:

```text
top camera frames
front camera frames
wrist camera frames
observation.state
action
timestamp
frame_index
episode_index
task_index / task text
```

Reason:

```text
Pi05 learns the next motor action from image + robot state + task.
If we train with images only, the arm cannot learn what motor command should follow.
```

## 5. Step By Step Workflow

### Step A: Freeze Inputs

Do not modify the original dataset.

Input stays read-only:

```text
/data/lerobot_datasets/so101_orange_49
```

Output artifacts go under:

```text
projects/testproject/artifacts/
```

Output datasets go under:

```text
/data/lerobot_datasets/
```

Do not commit videos, images, or extracted dataset files to git.

### Step B: Generate Candidate Windows

Use the existing candidate CSV as the first pass:

```text
candidate_start_frame
candidate_end_frame
close_frame
gripper_before
gripper_min
gripper_drop
post_close_arm_motion_abs
likely_close_lift_window
```

Example:

```text
episode 7
candidate window: frames 329-494
close frame: 374
```

Plain meaning:

```text
Look at episode 7 around frames 329-494 because that is where the gripper closes and the arm moves after close.
```

The candidate CSV is only a starting point.

Final approved windows should follow this rule:

```text
approved_start_frame:
  1-2 seconds before final alignment or gripper close starts

approved_end_frame:
  after the orange has been lifted and moved to the new place
```

At 30 FPS, that means:

```text
start about 30-60 frames before close
end when move/place is visible, not just when lift begins
```

Example:

```text
automatic candidate:
  frames 329-494

visual review finds move finishes later:
  approved window becomes frames 320-560
```

Why:

```text
We want grasp-pick-move, not grasp-only.
Stopping immediately after lift would teach only part of the task.
```

### Step C: Create Contact Sheets For Review

For each candidate window, create a visual sheet with top/front/wrist rows.

Each sheet should show enough frames to see the whole chain:

```text
9-12 timestamps per candidate window
include before close
include final alignment
include close moment
include lift
include move
include final/end state
```

Example sheet layout:

```text
episode 7

frame 320  frame 340  frame 360  frame 380  frame 420  frame 460  frame 500  frame 540  frame 560
top        top        top        top        top        top        top        top        top
front      front      front      front      front      front      front      front      front
wrist      wrist      wrist      wrist      wrist      wrist      wrist      wrist      wrist
```

The sheet lets us answer:

```text
Is orange visible?
Is gripper visible?
Is orange centered between fingers before close?
Did close happen on the orange?
Did orange lift?
Did the segment include useful move/place behavior?
```

### Step D: Label Each Candidate

Create a review CSV:

```text
projects/testproject/artifacts/dataset_grasp_window_audit_20260720/grasp_pick_move_review.csv
```

Columns:

```text
episode_index
candidate_start_frame
candidate_end_frame
label
reason
approved_start_frame
approved_end_frame
holdout
gripper_direction_checked
open_gripper_value_observed
closed_gripper_value_observed
move_to_another_place_observed
notes
```

Labels:

```text
good
grasp_only
bad
needs_trim
uncertain
```

Examples:

```text
good:
  gripper centers orange, closes, lifts, moves orange to another place

needs_trim:
  candidate is useful but starts too early or ends too late

grasp_only:
  gripper centers, closes, and lifts, but the move-to-new-place part is missing or unclear

bad:
  closes on air, pushes orange, no lift, or no useful task completion

uncertain:
  camera view is not enough to verify
```

Holdout rule:

```text
Keep 5 approved windows out of the focused training dataset as visual holdout examples.
Choose holdouts across early, middle, and late episode ranges.
Do not train on them in the first focused fine-tune.
Use them for inspection/comparison and sanity checks.
```

Suggested holdout selection rule:

```text
after review, sort approved good windows by episode_index
hold out 1-2 from early episodes
hold out 1-2 from middle episodes
hold out 1-2 from late episodes
total holdout count: 5
```

### Step E: Build A Focused LeRobot Dataset

Only after review, create a new dataset from approved windows.

Building this dataset requires an offline dataset-processing script.

Before creating that script, Codex must explain and get approval for:

```text
input dataset path
review CSV path
output dataset path
that the source dataset will not be overwritten
that no robot movement is involved
that videos/images/datasets stay out of git
```

Proposed output:

```text
/data/lerobot_datasets/so101_orange_49_grasp_pick_move_focus
```

This dataset contains short episodes, one per approved window.

Example:

```text
source episode 7:
  original frames 0-721

focused episode:
  frames 320-560
```

Each focused episode must keep synchronized:

```text
top video
front video
wrist video
state parquet rows
action parquet rows
timestamps reset or preserved consistently
task text
metadata
```

### Step F: Validate The Focused Dataset

Before training, validate:

```text
LeRobotDataset can load it.
episode count matches approved windows.
videos decode correctly.
top/front/wrist frame counts match parquet rows.
state/action names match the original dataset.
task text matches the training task.
random samples show correct camera/state/action alignment.
```

Acceptance:

```text
No missing video stream.
No frame/action count mismatch.
No bad or uncertain windows included as positive examples.
```

### Step G: Choose Training Mix

Do not replace the original 49 episodes immediately.

Choose the training mix only after visual review.

Recommended first training mix:

```text
Option A:
original 49 episodes
+ focused grasp/pick/move segments
```

Plain meaning:

```text
Keep teaching reach behavior.
Show the final grasp-pick-move behavior more often.
```

If LeRobot training accepts one merged dataset cleanly, create:

```text
/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
```

If merging is risky, train with an explicit dataset strategy only after verifying what LeRobot supports in our current version.

Do not start with repeated/duplicated focus windows.

Option B is only for a later run:

```text
Option B:
original 49 episodes
+ focused grasp/pick/move segments
+ same focused segments repeated one or two more times
```

Plain meaning:

```text
Show the final grasp-pick-move behavior 2-3 times more often.
```

Use Option B only if Option A still reaches the orange but does not close/lift/move reliably.

Risk of Option B:

```text
The model may over-focus on close-range behavior and become weaker at reaching from the normal start pose.
```

Decision thresholds after review:

```text
35 or more good grasp-pick-move windows:
  use Option A first

20-34 good grasp-pick-move windows:
  use Option A first, but expect that a second focused pass may be needed

fewer than 20 good grasp-pick-move windows:
  do not fine-tune from this focused set alone
  record new grasp-pick-move correction episodes
```

### Step H: Fine-Tune And Evaluate

After dataset validation, fine-tune from the current Pi05 checkpoint or base plan checkpoint.

Evaluation must use:

```text
official LeRobot async path
top/front/wrist cameras
official defaults unless user approves a change
read-only trace enabled
external video when possible
```

Success criteria:

```text
arm reaches orange
gripper centers orange
gripper closes while orange is between fingers
orange lifts clear of table
orange moves to another place
behavior repeats across multiple attempts
```

Minimum evaluation:

```text
Run 5 official async attempts.

success:
  orange lifts clear of table and moves to another place

partial:
  arm reaches/touches orange but no successful lift/move

failure:
  no meaningful reach, unsafe motion, or wrong target
```

## 6. What This Can Prove

If many good windows exist:

```text
The dataset does contain the grasp skill.
Then we inspect training mix, checkpoint step count, Pi05 config, or distribution mismatch.
```

If few good windows exist:

```text
The dataset is weak at the exact failure point.
Then close-range correction episodes are justified.
```

If windows exist but camera view differs from deployment:

```text
The issue may be camera distribution mismatch.
Then fix camera placement or collect matching correction demos.
```

If good windows exist but action labels close too early/late:

```text
The model may learn wrong timing.
Then trim/relabel windows or collect cleaner correction demos.
```

## 7. Execution Result

Current result as of 2026-07-21:

```text
Focused windows-only dataset:
  /data/lerobot_datasets/so101_orange_49_grasp_pick_move_focus
  40 approved non-holdout windows
  10,988 frames
  LeRobotDataset load/decode passed

Option A training dataset:
  /data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus
  original 49 full episodes + focused windows once
  89 episodes
  40,712 frames
  LeRobotDataset load/decode passed

RunPod training result:
  /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
  3000-step expert-only Pi05 continuation from checkpoint 005000
  checkpoint saved successfully
```

This means the dataset-building and Option A training parts of this plan are done.

The plan is not fully proven until the new checkpoint is evaluated on the real arm:

```text
official LeRobot async
top/front/wrist cameras
official defaults unless approved otherwise
read-only trace enabled
external video when possible
```

## 7. What Not To Do Yet

Do not:

```text
delete or overwrite /data/lerobot_datasets/so101_orange_49
train on auto-detected windows without visual review
include bad pushes/misses as successful grasp examples
commit videos/images/datasets to git
record new episodes before checking the existing windows
change official LeRobot execution settings to hide the issue
```

## 8. When New Grasp-Pick-Move Episodes Are Needed

Record new grasp-pick-move correction episodes only if review shows one of these:

```text
too few good close-range examples
wrist camera rarely shows gripper/orange alignment
gripper closes before centering in many demos
lift or move-to-new-place behavior is missing or inconsistent
camera placement in demos differs from current test setup
```

Then record short correction demos like:

```text
start with gripper already near orange
slightly offset gripper
human corrects alignment
center orange between fingers
close gripper
lift
move orange to another place
```

This teaches the exact missing behavior instead of adding many more long reach-only frames.

## 9. Immediate Next Action

Status:

```text
The visual contact sheets, first-pass review, focused dataset build, Option A dataset build, and local package are complete.
```

Evidence produced:

```text
review CSV:
  projects/testproject/artifacts/dataset_grasp_window_audit_20260720/grasp_pick_move_review.csv

contact sheet pages:
  projects/testproject/artifacts/dataset_grasp_window_audit_20260720/contact_sheet_pages_v2/

review notes:
  projects/testproject/artifacts/dataset_grasp_window_audit_20260720/codex_visual_review_notes.md
```

First-pass result:

```text
good: 45
uncertain: 2
bad: 1
grasp_only: 1
holdout good windows: 5
trainable good windows after holdout: 40
```

Current immediate next action:

```text
Evaluate the new Option A checkpoint on the real arm:
  /workspace/outputs/pi05_orange49_plus_grasp_focus_expert/checkpoints/003000/pretrained_model
```

This must not modify:

```text
/data/lerobot_datasets/so101_orange_49
```

The focused dataset and Option A training dataset both loaded through LeRobotDataset with top/front/wrist frames.

## 10. Gaps Closed In This Plan

This plan now explicitly covers:

```text
definition of "moved to another place"
verification of gripper open/close direction from dataset frames/actions
exact review CSV path and required columns
contact sheet density: 9-12 timestamps per candidate
approval required before creating the offline dataset-building script
training mix thresholds based on number of good windows
holdout selection across early/middle/late episodes
5-run real-arm evaluation rule
```

Remaining open item:

```text
The new checkpoint has not yet been tested on the real robot.
We need one official LeRobot async run with top/front/wrist cameras, read-only trace, and external video if possible.
```
