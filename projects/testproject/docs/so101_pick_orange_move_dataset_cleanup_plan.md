# SO-101 Pick Orange Move Dataset Cleanup Plan

## 1. Goal

Create a cleaner dataset for the next Pi05 fine-tune.

The original episodes are not only:

```text
grasp the orange
```

They are closer to:

```text
move toward orange -> pick up orange -> move orange away -> drop/place it elsewhere
```

So the cleaned dataset should teach that exact behavior.

## 2. Correct Task Text

Use this task text for the cleaned dataset:

```text
pick up the orange and move it to another place
```

Do not use:

```text
pick the orange and put it in the plate
```

Reason: the current episodes do not show a consistent plate target.

## 3. Source Datasets

Keep these unchanged:

```text
/data/lerobot_datasets/so101_pick_orange_batch01
/data/lerobot_datasets/so101_pick_orange_batch02
/data/lerobot_datasets/so101_pick_orange_batch03
```

Current combined dataset:

```text
/data/lerobot_datasets/so101_pick_orange_30eps
```

This combined dataset is useful, but it contains confusing tails and the old task text.

## 4. New Cleaned Dataset

Write the cleaned dataset to a new folder:

```text
/data/lerobot_datasets/so101_pick_orange_move_cleaned
```

Do not overwrite the original datasets.

## 5. What To Keep

For each episode, keep:

```text
start
reach orange
close gripper / pick up orange
move orange away
drop/place orange elsewhere
short confirmation after drop
```

The final dataset should show the complete behavior we want Pi05 to learn.

## 6. What To Remove

Remove:

```text
long idle time
unnecessary holding after drop
return-to-rest movement
reset movement
wandering after the task is already complete
failed or unclear attempts
```

## 7. Why This Matters

Pi05 learns from "what action comes next from this state."

If the dataset contains many late frames where the robot is resting, holding, or moving aimlessly after the useful task, the model can learn weak next actions.

Cleaner episodes make the learning signal sharper:

```text
instruction -> reach -> pick -> move -> drop
```

instead of:

```text
instruction -> reach -> pick -> move -> drop -> wait -> rest -> extra motion
```

## 8. Episode Review Inputs

Use these generated contact sheets for manual review:

```text
/data/downloads/pi05_dataset_trim_analysis_20260630/batch01_front_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch01_top_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch02_front_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch02_top_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch03_front_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch03_top_timeline_fine_ffmpeg.jpg
```

The top view is especially useful because it shows where the orange was moved/dropped.

## 9. Cleanup Workflow

1. Define per-episode end times.
2. Trim each episode to its useful task segment.
3. Rewrite metadata so frame indices, episode indices, and timestamps are consistent.
4. Rewrite videos for top/front/wrist with the same trimmed time range.
5. Change task text to:

```text
pick up the orange and move it to another place
```

6. Generate cleaned dataset contact sheets.
7. Verify that each cleaned episode shows the full behavior.
8. Fine-tune Pi05 again only after the cleaned dataset is verified.

## 10. Success Criteria

The cleaned dataset is ready when:

```text
all episodes start before the reach
all episodes include pickup
all episodes include moving the orange elsewhere
all episodes include drop/place
no episode contains long rest/reset tail
task text matches the visible behavior
metadata loads without errors
videos play correctly
```

## 11. Next Engineering Step

Create a dataset cleanup script that:

```text
reads batch01/batch02/batch03
applies per-episode trim times
writes /data/lerobot_datasets/so101_pick_orange_move_cleaned
generates review contact sheets
```
