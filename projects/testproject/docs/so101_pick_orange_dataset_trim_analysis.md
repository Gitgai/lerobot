# SO-101 Pick Orange Dataset Trim Analysis

Date: 2026-06-30

## Goal

Clean the existing 30 demonstration episodes before the next Pi05 fine-tune.

The specific problem we are fixing:

```text
Some episodes continue after the orange has already been lifted.
Those late frames teach the model "do small holding/rest actions" instead of "reach, close, lift".
```

## Source Datasets

```text
/data/lerobot_datasets/so101_pick_orange_batch01
/data/lerobot_datasets/so101_pick_orange_batch02
/data/lerobot_datasets/so101_pick_orange_batch03
```

Batch sizes:

```text
batch01: 10 episodes, ~29.9 seconds each
batch02: 10 episodes, ~19.9 seconds each
batch03: 10 episodes, ~19.9 seconds each
```

Generated visual analysis sheets:

```text
/data/downloads/pi05_dataset_trim_analysis_20260630/batch01_front_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch02_front_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch03_front_timeline_fine_ffmpeg.jpg
```

Generated joint timing summary:

```text
/data/downloads/pi05_dataset_trim_analysis_20260630/joint_timing_summary.csv
```

## Corrected Behavior Finding

After reviewing the finer front/top/wrist timelines, the demonstrations are better described as:

```text
move toward orange -> pick up orange -> move orange away -> drop/place it elsewhere
```

They are not only "grasp/lift" episodes.

However, they are also not "put orange in the plate" episodes, because there is no consistent visible plate target in the current dataset.

The final placement/drop location varies across episodes. Sometimes the orange is moved to the side of the table, sometimes it is still near the gripper at the end, and sometimes the final drop is partially outside the camera view.

So the best current task description is closer to:

```text
pick up the orange and move it to another place
```

or:

```text
pick up the orange and put it on the table
```

It should not be:

```text
put the orange in the plate
```

unless we record new demonstrations with a plate.

## Episode-By-Episode Behavior Check

This table is based on visual inspection of the finer front/top timelines:

```text
/data/downloads/pi05_dataset_trim_analysis_20260630/batch01_front_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch01_top_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch02_front_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch02_top_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch03_front_timeline_fine_ffmpeg.jpg
/data/downloads/pi05_dataset_trim_analysis_20260630/batch03_top_timeline_fine_ffmpeg.jpg
```

| Episode     | Behavior                                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------------------------- |
| batch01 ep0 | Pick and move/drop elsewhere. Extra tail remains after useful motion.                                         |
| batch01 ep1 | Pick and move/drop elsewhere. Extra tail remains.                                                             |
| batch01 ep2 | Pick and move/drop elsewhere. Extra tail remains.                                                             |
| batch01 ep3 | Pick and move/drop elsewhere. Extra tail remains.                                                             |
| batch01 ep4 | Pick and move/drop elsewhere, but final part is less clean.                                                   |
| batch01 ep5 | Pick and move/drop elsewhere. Extra tail remains.                                                             |
| batch01 ep6 | Pick and move/drop elsewhere. Extra tail remains.                                                             |
| batch01 ep7 | Pick and move/drop elsewhere. Extra tail/rest-like part remains.                                              |
| batch01 ep8 | Pick and move/drop elsewhere. Extra tail/rest-like part remains.                                              |
| batch01 ep9 | Pick and move/drop elsewhere. Extra tail remains.                                                             |
| batch02 ep0 | Pick and move/drop elsewhere.                                                                                 |
| batch02 ep1 | Pick and move/drop elsewhere.                                                                                 |
| batch02 ep2 | Pick and move/drop elsewhere.                                                                                 |
| batch02 ep3 | Pick and move/drop elsewhere.                                                                                 |
| batch02 ep4 | Pick and move/drop elsewhere.                                                                                 |
| batch02 ep5 | Pick and move/drop elsewhere, but final target is less clear.                                                 |
| batch02 ep6 | Pick and move/drop elsewhere.                                                                                 |
| batch02 ep7 | Pick and move/drop elsewhere.                                                                                 |
| batch02 ep8 | Pick and move/drop elsewhere.                                                                                 |
| batch02 ep9 | Pick/move behavior is present, but this one should be manually reviewed because the end is less clear.        |
| batch03 ep0 | Pick and move/drop elsewhere.                                                                                 |
| batch03 ep1 | Pick and move/drop elsewhere.                                                                                 |
| batch03 ep2 | Pick and move/drop elsewhere.                                                                                 |
| batch03 ep3 | Pick/move behavior is present, but manually review because the sequence is less clear than the best episodes. |
| batch03 ep4 | Pick and move/drop elsewhere, but object starts near the edge/partly awkwardly placed.                        |
| batch03 ep5 | Pick and move/drop elsewhere.                                                                                 |
| batch03 ep6 | Pick/move behavior is present, but manually review because the end is less clear.                             |
| batch03 ep7 | Pick and move/drop elsewhere.                                                                                 |
| batch03 ep8 | Pick and move/drop elsewhere.                                                                                 |
| batch03 ep9 | Pick and move/drop elsewhere.                                                                                 |

Summary:

```text
Most episodes match the user's intended behavior:
arm moves toward orange -> picks it up -> moves/drops it elsewhere.

But the "elsewhere" location is not consistent enough to call it a plate/target task.
```

## Main Trimming Finding

Do not cut all episodes by one fixed number.

Reason:

```text
Some episodes lift the orange around 12-14 seconds.
Some episodes lift closer to 18-21 seconds.
Batch01 often has extra motion after the useful pick.
Batch02 and batch03 are shorter and cleaner, but still mixed.
```

So the best cleanup is episode-specific trimming.

## Batch 1 Analysis

Batch 1 episodes are too long for training as-is.

Most useful action is:

```text
reach -> close gripper -> lift orange
```

But many batch 1 episodes continue into:

```text
holding
lowering
rest-like movement
extra repositioning
```

Recommended first-pass trim points:

```text
batch01 episode 0: keep to ~22s
batch01 episode 1: keep to ~19s
batch01 episode 2: keep to ~22s
batch01 episode 3: keep to ~19s
batch01 episode 4: keep to ~25s
batch01 episode 5: keep to ~22s
batch01 episode 6: review manually; possible keep to ~22s or exclude if too mixed
batch01 episode 7: keep to ~16s
batch01 episode 8: keep to ~16s
batch01 episode 9: keep to ~22s
```

Batch 1 is the most likely source of confusing late/end frames.

## Batch 2 Analysis

Batch 2 is cleaner than batch 1.

Most episodes are useful by about:

```text
12s to 16s
```

Some episodes still need more time.

Recommended first-pass trim points:

```text
batch02 episode 0: keep to ~19s
batch02 episode 1: keep to ~15s
batch02 episode 2: keep to ~19s
batch02 episode 3: keep to ~13s
batch02 episode 4: keep to ~15s
batch02 episode 5: review manually; keep to ~19s if it is a valid pick
batch02 episode 6: keep to ~14s
batch02 episode 7: keep to ~13s
batch02 episode 8: keep to ~15s
batch02 episode 9: review manually; possible keep to ~19s or exclude if not a clean pick
```

## Batch 3 Analysis

Batch 3 is mixed.

Some episodes are good, but a few look partial or unclear from the front view.

Recommended first-pass trim points:

```text
batch03 episode 0: keep to ~19s
batch03 episode 1: keep to ~14s
batch03 episode 2: keep to ~17s
batch03 episode 3: review manually; possible exclude if it is not a clean pick
batch03 episode 4: keep to ~14s
batch03 episode 5: keep to ~14s
batch03 episode 6: review manually; possible exclude if it is not a clean pick
batch03 episode 7: keep to ~13s
batch03 episode 8: keep to ~15s
batch03 episode 9: keep to ~15s
```

## What I Think We Should Do

Do not immediately overwrite the original datasets.

Correct workflow:

```text
1. Keep the original batch01/batch02/batch03 unchanged.
2. Create a new cleaned dataset folder.
3. Trim each episode using the candidate cut times above.
4. Generate a visual contact sheet of the cleaned dataset.
5. Review the cleaned clips.
6. Exclude any episode that does not show a clean pick/lift.
7. Fine-tune Pi05 again on the cleaned dataset.
```

The cleaned dataset should contain:

```text
start pose / reach
close gripper
lift orange
stop shortly after lift
```

The cleaned dataset should not contain:

```text
long idle time
return-to-rest motion
reset motion
extra holding after success
failed/partial attempts
```

## Important

This cleanup helps training, but it is not magic.

For the next real-arm test, the arm should still begin from a reasonable pick-start condition. If the arm starts from a pose that looks like a late/end frame, the model may still output weak holding actions.
