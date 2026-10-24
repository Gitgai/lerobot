> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/OPENPI_FRUIT_CHECKPOINT_SELECTION_20261020.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# Fruit LoRA-plus-vision checkpoint comparison

Updated 20 October 2026. Offline evaluation only; no robot movement or environment changes.

Follow-up: [fresh saved-checkpoint reload and loopback serving passed](SAVED_4K_SERVING_CHECK_20261020.md). This supersedes reload-pending statements below; full previous-client/RTC integration remains unverified. User has explicitly excluded physical trials.

## Result and recommendation

The approved 5,000-update run completed with all five checkpoints and full evaluations. Both 4k and 5k improve on 1k, 2k and 3k across all eight pooled fruit/metric combinations.

There is no universal winner: **4k has lower arm error; 5k has lower gripper error**, on both fruits. Preserve both. Provisionally prepare 4k first if arm-target accuracy is the selection priority, keeping 5k as the gripper-error alternative. This priority is an explicit recommendation, not evidence that 4k picks fruit better. Do not automatically deploy the last checkpoint or extend training.

## What was compared

- Agreed OpenPI LIBERO-style LoRA + vision + projections, 466,957,072 trainable parameters; not the earlier adapter-only pilot.
- General π0.5 base initialization, batch 32, 5,000 updates, 30-action horizon, ordinary training without RTC-prefix conditioning.
- Training: 36 orange + 8 tomato episodes, 40,677 timestamps.
- Validation: 9 orange + 2 tomato episodes, 10,307 timestamps (8,511 orange / 1,796 tomato).
- Baseline and every checkpoint evaluated on the same complete held-out manifest and seeded inputs/noise, with 10 denoising steps.
- First-action error compares the immediate predicted action with the demonstration. Chunk error compares all valid actions in the predicted 30-action sequence; episode-end padding is excluded.
- Arm MAE averages absolute differences over five joints, in degrees. Gripper MAE is in normalized 0–100 points. These are different units and are not combined into a single score.
- This compares the current run with its zero-update general-base baseline, not with previous LoRA or full-fine-tuned models.

## Orange results

Lower is better. Pooled, target-weighted MAE.

| Checkpoint      | First arm ° | First gripper points | Chunk arm ° | Chunk gripper points |
| --------------- | ----------: | -------------------: | ----------: | -------------------: |
| Base, 0 updates |      48.530 |               12.859 |      49.043 |               13.088 |
| 1k              |       8.096 |                3.642 |       9.352 |                4.315 |
| 2k              |       6.211 |                2.653 |       7.809 |                3.464 |
| 3k              |       5.490 |                2.138 |       7.151 |                3.154 |
| 4k              |       5.050 |                2.128 |       6.765 |                3.021 |
| 5k              |       5.078 |                1.986 |       6.843 |                2.992 |

## Tomato results

| Checkpoint      | First arm ° | First gripper points | Chunk arm ° | Chunk gripper points |
| --------------- | ----------: | -------------------: | ----------: | -------------------: |
| Base, 0 updates |      47.149 |               14.405 |      47.703 |               14.639 |
| 1k              |       8.392 |                3.077 |       9.526 |                4.007 |
| 2k              |       6.630 |                2.740 |       8.050 |                3.957 |
| 3k              |       6.053 |                2.032 |       7.597 |                3.274 |
| 4k              |       5.579 |                1.779 |       7.110 |                3.013 |
| 5k              |       5.619 |                1.742 |       7.220 |                2.920 |

## How meaningful is the 4k–5k difference?

Compared with 4k, 5k increases first-arm MAE by only 0.028° for orange and 0.040° for tomato. Chunk-arm MAE increases 0.078° and 0.110°. First-gripper MAE decreases 0.143 and 0.037 points; chunk-gripper MAE decreases 0.029 and 0.093 points.

At episode level, 4k has lower first-arm error on 7/9 orange and 2/2 tomato episodes. 5k has lower first-gripper error on 7/9 orange but only 1/2 tomato episodes. Therefore pooled improvements do not mean every episode improves.

Earlier small repeatability checks found fresh-process prediction variation despite identical inputs. That experiment is not a universal error bound. This comparison has not repeated full 4k/5k evaluations to establish ranking uncertainty. Treat the small differences as a trade-off, not proof of statistically significant superiority or proof of overfitting.

Only two tomato validation episodes are available. Correlated timestamps and overlapping action chunks are not thousands of independent task trials. Offline imitation accuracy does not establish grasp success, physical safety, RTC performance, or the desired >90% task-success rate.

## Audit performed

The comparison script checked all 61,842 records across the baseline and five checkpoints:

- Exactly 10,307 unique matching observation identities per report.
- Zero input/noise-hash mismatches against baseline.
- Correct fruit counts, valid-action masks and joint counts.
- Finite, nonnegative error sums.
- Recalculated pooled metrics agree with saved report values.
- All five saved checkpoints contain parameters and training state; their normalization assets match the training-only normalization file.

Evidence: [machine-readable comparison](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/completed_checkpoint_comparison.json), including source-report SHA256 hashes, per-episode metrics and checkpoint paths; [audit script](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/compare_completed_checkpoints.py).

These evaluations used current training-state weights during validation. Checking that checkpoint files exist is **not** a fresh reload test of a trained saved checkpoint. The earlier six-update save/reload check does not replace that remaining deployment check.

## Saved outputs and timing

AI90 checkpoint root:

`/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX/checkpoints/pi05_fruit55_lora_vision/fruit55_lora_vision_5k`

Subdirectories `1000`, `2000`, `3000`, `4000`, `5000` are actual completed-update counts. Each includes `params`, `train_state` and normalization assets. Validation files are `validation_001000.json` through `validation_005000.json`.

Environment: `/home/kiran/sim/openpi/.venv/bin/python`.

Main launch 2026-10-19 20:19:29 UTC; completion 2026-10-20 05:52:02 UTC: approximately 9h32m33s including all five validations and saves, excluding the earlier baseline.

## Next phase

1. Fresh-load the selected saved 4k checkpoint and its exact normalization/configuration; verify prediction outputs and action units without commanding hardware.
2. Verify compatibility with the intended serving/client path, camera mappings, task instruction, JPEG and guided RTC requirements. Do not assume the old LeRobot checkpoint loader can load this OpenPI checkpoint unchanged.
3. Preserve 5k and all existing environments. Document launch and rollback commands before deployment; do not silently replace an installed policy.
4. When deployment is verified and the rig is ready, conduct supervised trials and report orange and tomato success separately. No new motor limits or mandatory fake-hardware tests are added.
5. If a robust offline winner is needed before choosing, repeat the close 4k/5k comparison on the same manifest and report observed spread. Do not claim that this repeat was already done.

This turn completed comparison and documentation only. No serving process, physical trial, extra training or checkpoint deletion was performed.
