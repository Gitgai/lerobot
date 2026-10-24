# π0.5 full fine-tuning: 15,000-update option

Latest September 24 result: training completed and all three checkpoints were evaluated hardware-free. See [comparison and limitations](PI05_FULLFT_CHECKPOINT_EVALUATION_20260924.md). Provisional offline shortlist: 10k for full-sequence action agreement, 15k as a close short-horizon alternative. No previous-LoRA comparison. Earlier proposal/running statements are historical.

Date: 2026-09-23

## Current update: approved 45-episode derivative

Latest user decision: launch the prepared 15k full-fine-tuning run under the 16-hour / 150-GB additional-output guard. **Do not compare with the previous LoRA model.** Evaluate only this run's 5k/10k/15k checkpoints on the nine retained validation episodes. See the orange45 preparation document for current launch status; proposal and unstarted statements below are historical.

Launch confirmed 2026-09-23 at 10:50:56 UTC: training progressed to at least 11 updates with finite first-update loss/gradient norm. The run is active; earlier unstarted/proposal-only statements below are historical.

The user approved the conservative selection, now built separately: **36 training episodes / 33,493 timestamps and 9 validation episodes / 8,511 timestamps**. Episode 43 is trimmed to frames 0–509; five uncertain episodes are set aside without modifying originals. See [applied selection and verification](PI05_ORANGE45_PREPARATION_20260923.md). The new 15k configuration and manifest-bound worker replace the old dataset assumptions. Main training has not started. Older proposal/pending-choice statements below are historical, not the current dataset decision.

Status: documented proposal only. This document does not authorize or start training. No executable training configuration was changed for this request. The earlier validated 30,000-update configuration remains a separate proposal.

Latest 2026-09-23 follow-up: a **separate 15k candidate config has now been created and validated** during requested pre-training checks; the original 30k config was not changed. See [check results](PI05_PRETRAINING_CHECK_RESULTS_20260923.md). Actual sampler coverage, training-only statistics, 150 real target-window samples, 15 image-helper samples and checkpoint headers passed. Main training is not running; behavioral review and long-run execution safeguards remain open. The original creation-status sentence above is historical.

Later execution: [End-to-end check results](PI05_END_TO_END_CHECKS_20260923.md) record real batch-four fresh/save/resume testing of the separate long-run worker, supervisor tests and denser priority-episode evidence. The 15k main run remains unstarted; do not read earlier pending-integration text as the current test status.

## What choosing 15,000 updates means

Latest dataset decision work: [Review decisions v1](pi05_quality_gate_20260923/review_decisions_v1/REPORT.md). Recommendation counts are **44 keep / 1 trim / 5 uncertain**. Episode 43's proposed terminal cut removes 388 training rows; if all 50 remain, training timestamps become 37,082 and validation remains 9,408. This has not been applied. Inclusion of uncertain episodes requires an explicit dataset decision, not an implicit failure label or automatic exclusion. The evidence is whole-span sampled review plus a frame-by-frame cut-boundary check, not exhaustive semantic certification.

The more conservative first-run recommendation is to set aside the five uncertain episodes, not mark them failed. With the proposed trim, this would leave **36 training episodes / 33,493 timestamps and nine validation episodes / 8,511 timestamps**. No source episode changes sides. This is a proposal requiring the user's dataset choice, not an applied exclusion; the two partially clipped outcomes remain included with caveats.

The separate derivative, training-only statistics, boundary-window checks and manifest-bound worker are now prepared. Use the new orange45 config and worker, not the old hard-coded orange50 split. The previous-LoRA baseline evaluation is excluded by user instruction.

An update is one adjustment of the model's trainable weights after processing a batch of training samples. It is not one episode or one complete pass through the dataset.

At batch size 4, 15,000 updates mean **60,000 sample presentations**. Samples can repeat; this does not mean 60,000 unique frames or demonstrations. Each sample uses the front and wrist views together with robot state and a target action sequence. Two cameras do not double the sample count.

This is three times the updates of a 5,000-update experiment and half the updates of a 30,000-update experiment.

## Proposed setup

| Item                                       | Proposal                                                              |
| ------------------------------------------ | --------------------------------------------------------------------- |
| Starting model                             | Fresh general π0.5 base, not the LoRA export or diagnostic checkpoint |
| Training method                            | Full fine-tuning; no LoRA or deliberate vision/expert freezing        |
| Memory support                             | Existing tested custom CPU-offloaded AdamW integration                |
| Training demonstrations                    | Approved 36 orange episodes, 33,493 timestamps                        |
| Held-out validation demonstrations         | Approved 9 orange episodes, 8,511 timestamps                          |
| Task                                       | Pick up the orange and place it on the plate                          |
| Inputs                                     | Front and wrist camera images plus robot state                        |
| Batch size                                 | 4                                                                     |
| Updates                                    | 15,000                                                                |
| Sample presentations                       | 60,000, including repeated samples                                    |
| Action representation                      | Existing absolute six-joint actions, 50-action chunks                 |
| RTC                                        | Not part of this training experiment                                  |
| Proposed checkpoint and validation cadence | Every 5,000 updates: 5k, 10k, 15k                                     |

“Full” here means no deliberate parameter freezing: parameters connected to the action loss receive updates. Earlier checks found some language-output components outside that loss path. The memory-saving integration is custom; it does not modify the clean installed LeRobot files and should not be described as an entirely unmodified official training recipe.

## Expected time and storage

The completed batch-4 probe measured a mean of approximately 2.372 seconds per update, including data loading, over 11 steady samples.

- Estimated training-iteration time: **about 9.9 hours** for 15,000 updates.
- Full validation, model loading, checkpoint saving and runtime variability add time. Ten hours is not a completion guarantee; the short probe does not establish overnight stability.
- Each measured full checkpoint occupies approximately **35.3 GB decimal**, including model weights and optimizer state needed to resume training.
- Three checkpoints would occupy approximately **106 GB additional**, plus logs and other output. Temporary saving overhead also needs free space.
- Existing diagnostic checkpoints occupy approximately **70.7 GB** and are preserved. Existing datasets and LoRA results are also preserved.

The earlier 26-hour/250-GB limits belong to the 30k proposal, not an approved budget for this 15k option. Set explicit wall-time and new-output limits, and recheck live resources before launch.

## Why the learning-rate schedule must match

The learning rate controls the size of model adjustments. Warm-up starts with small adjustments; later decay reduces them for refinement.

A planned 15,000-update run should complete its warm-up and decay within those 15,000 updates. Stopping an unchanged 30,000-update schedule halfway does not complete the same learning-rate progression.

The separate validated 15k candidate now explicitly uses a 500-step warm-up, nominal peak learning rate 2.5e-5 and cosine decay through step 15,000 to 2.5e-6, preserving the earlier proposal's warm-up proportion. The actual installed scheduler values were checked and are recorded in the pre-training results. This is a candidate recipe, not a tuned quality guarantee or an executed training run.

The 5k and 10k checkpoints from this run are intermediate points on a **15k schedule**. They are not equivalent to separately planned 5k or 10k runs. Extending training later also requires a deliberate scheduler/resume decision.

## What we might gain—and what we cannot promise

More updates give the model more opportunities to learn the demonstrations, but improvement is not guaranteed. With a small dataset, later training can overfit: training loss improves while performance on unseen examples stagnates or worsens.

Do not assume the 15k checkpoint is best just because it is last. Compare all three checkpoints using:

1. Full loss on the same 9 retained held-out episodes, not the four-example diagnostic checks.
2. Offline action prediction errors with consistent preprocessing, units and evaluation settings.
3. Review around reaching, grasping, lifting and placing—not only an overall average.
4. Compare only this run's 5k, 10k and 15k checkpoints under matching evaluation conditions; no previous-LoRA comparison.

The validation episodes come from the existing recording sessions; they do not establish generalization to new environments. Lower offline error is not a physical grasp success rate. Full fine-tuning also does not solve deployment network latency or unresolved hardware issues.

## Steps before and after launch

### Required dataset-quality gate — not yet complete

Before the main run, review all 50 candidate episodes (40 train, 10 validation). Reuse existing evidence, but do not treat sparse contact sheets or successful decoding as complete behavioral review.

1. Review both synchronized views over each full episode; mark approach, grasp, lift, transport, placement/release, brief completion hold, recovery, idle and manual reset intervals. Movement toward the task is valid training content, not automatically noise.
2. Record source group/episode, mapped training-dataset episode, split, evidence frame/time ranges, outcome and uncertainty. Distinguish visible final placement from release evidence when the final resting location is outside the cameras.
3. Audit all selected videos for decoding/count problems, timestamps and numerical validity. Check image/action correspondence separately: matching counts alone cannot establish physical synchronization, and successful decoding cannot rule out baked-in visual corruption.
4. Produce one explicit decision per episode: accept, trim, exclude or unresolved, with reasons. Keep useful recoveries identified; never infer success from the task label or gripper closure alone.
5. Count reviewed samples/duration per phase and inspect actual preprocessed two-camera training samples. Do not automatically rebalance or discard movement/idle based only on joint-speed thresholds.
6. If trimming is warranted, create a separately versioned derivative and preserve originals. Keep both cameras, state and actions aligned; prevent 50-action targets from crossing removed intervals or episode boundaries. Verify the trainer's padding/masking behavior at retained ends before choosing a boundary policy.
7. Preserve episode-level train/validation separation, including all segments from a common source episode. Recompute training-only statistics and sample counts after changes. Use the same retained validation data for all new full-fine-tuned checkpoints; no previous-LoRA evaluation.
8. Freeze the reviewed manifest, hashes, unresolved limitations and effective sampler coverage before launch. The 37,470/9,408 counts and 1.6-pass estimate are provisional if this review changes the corpus.

Existing evidence: `PI05_ORANGE_REVIEW_20260922.md`, `PI05_PREPARATION_PROGRESS_20260922.md`, `PI05_ORANGE_CANDIDATES_20260922.json` and `PI05_DATASET_AUDIT_20260922.json`. The candidate manifest explicitly says full sequence/intervention review is pending. Recovery source episodes 18, 19, 21, 22 and 27 have follow-up wrist release evidence, but their final resting states remain unverified. Do not silently relabel them failed or fully confirmed.

Completion requires a traceable decision for every episode and explicit resolution or disclosure of uncertainty, not a claim that all frames are good. No automatic training launch on technical audit success.

2026-09-23 installed-source check: `dataset_reader.py::_get_query_indices` clamps future indices to the episode's last row and supplies padding flags. `PI05Policy.forward` averages action loss without consuming `action_is_pad`. Thus terminal repeated actions contribute to loss in this inspected path. Review retained terminal poses deliberately; do not assume padded targets are ignored. No masking or training-code change has been made. Fresh audit progress is recorded in [dataset-quality report](PI05_DATASET_QUALITY_GATE_20260923.md).

Expanded audit result: all 50 source/GPU state-action arrays match; 1,600/1,600 sampled camera frames are pixel-identical. Fifty paired sequence sheets have been visually inspected. Outcome evidence: 43 clear sampled plate outcomes, two partial and five final-resting-state-unverified. These are not acceptance labels. A 16.06% low-motion-window measurement is diagnostic only, not a discard percentage. Continuous behavioral review and exact phase/trim boundaries remain unresolved; no dataset was changed or main training launched. Use `pi05_quality_gate_20260923/episode_review.json` as the traceable worklist rather than restarting the technical scan.

### Launch and evaluation sequence

1. Confirm selection of the 15k option and its resource budget.
2. Create a separately named, validated 15k configuration; preserve the earlier 30k proposal.
3. Verify dataset membership, training-only normalization, both camera inputs, base revision and effective scheduler settings.
4. Use a long-run worker with bounded logging and checks for non-finite loss/gradients, memory pressure, disk usage and elapsed time. Do not reuse unbounded diagnostic logging unchanged.
5. Start from the general base, save complete resumable checkpoints at 5k/10k/15k, and preserve unrelated services and files.
6. Evaluate the checkpoints and report the best-supported candidate, including weaknesses.
7. Treat physical deployment as a separate supervised decision. This document authorizes no robot movement, motor-setting changes or camera access.

## Recommendation

15,000 updates is a reasonable middle-ground experiment if approximately an overnight run and over 106 GB of additional output are acceptable. Select the checkpoint using evaluation evidence rather than its step number.

## Evidence and related documents

- [Completed end-to-end capability gate](PI05_FULLFT_END_TO_END_GATE_20260922.md): measured throughput, memory, checkpoint size, resume and inference checks.
- [Full fine-tuning plan](PI05_FULL_FINETUNING_PLAN_20260922.md): broader preparation and prior proposal.
- [Saved 30k proposal](fullft_gate_evidence_20260922/main_proposal.json): historical proposal, not a 15k launch configuration.

This document records the discussion and previously measured results; it is not a fresh inspection of GPU availability or running processes.
