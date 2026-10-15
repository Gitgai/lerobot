# π0.5 orange45: full-fine-tuned checkpoint evaluation

Follow-up complete: [hardware-free 10k deployment check](PI05_FULLFT10K_DEPLOYMENT_CHECK_20260924.md). All 32 network predictions exactly match the offline reference and preprocessing parity passed. Compressed SSH median 1.737 s remains a material delay; no physical trial or integrated 10k fake-actuator launch was performed.

Date: 2026-09-24. Scope: the new 5k, 10k and 15k full-FT checkpoints only. No LoRA comparison, robot connection, camera capture, motor command, retraining or checkpoint edit.

## Completed training

The 15,000-update run exited successfully with code 0. The supervisor recorded 43,759 seconds (about 12 hours 9 minutes), including startup, training, validation and saving. New output was 106,029,961,685 bytes (about 106 GB decimal).

It trained from the general π0.5 base, with batch four, full-FT flags, BF16, gradient checkpointing and the previously tested external CPU-offloaded AdamW support. Training used 36 episodes / 33,493 timestamps; validation used nine episodes / 8,511 timestamps. All source recordings and older checkpoints remain preserved.

| Checkpoint | Recorded full-validation loss |
|---|---:|
| 5,000 | 0.0327 |
| 10,000 | 0.0370 |
| 15,000 | 0.0420 |

These are the trainer's recorded validation-loss values, not robot success rates. The trainer averages batch loss, including terminal repeated targets in its installed loss path. These are not numerically interchangeable with decoded-action errors below. A rising loss suggests possible overfitting, but a single run does not establish its cause.

## Checkpoint verification

All three checkpoint structures passed the existing validator: seven required JSON files parsed, five required tensor files were present, nonempty and structurally consistent, expected step/batch metadata matched, and tensor shapes/byte offsets/file lengths were checked. Each model file is 9,354,050,752 bytes; each optimizer-state file is 25,988,800,372 bytes.

Each model is additionally loaded in a separate inference process, its parameters checked for finite values, and its saved processors used. Model SHA-256 digests are recorded. This is not a bitwise scan of all optimizer values or a fresh optimizer-resume test for these main-run checkpoints. The earlier save/resume integration evidence is separate.

The existing 13 checkpoint-validator and resource-supervisor tests passed again before comparison. These tests do not certify physical task behavior.

## Matched prediction protocol

- Original validation episode identities: 2, 7, 12, 17, 32, 37, 42, 46 and 58; use the orange45 manifest to map their derivative indices.
- Ten evenly spaced timestamps per episode, including its first and last: **90 distinct inputs**. This is not inference over every validation frame.
- Seeds 0, 1 and 2 at every input: **270 predictions per checkpoint**, 810 across the three models, plus one same-seed repeat check per model.
- Both recorded camera views, robot state and task text are used. Demonstrated action targets are removed before inference so they cannot leak into predictions.
- Fifty predicted absolute six-joint targets are decoded with each checkpoint's saved postprocessor. The first five joints are degrees; the gripper uses normalized calibrated position points.
- Compare only real target positions; omit repeated padded targets from reported action error. Last-frame windows therefore contribute one valid target per seed.
- Verify identical sampled input hashes, targets, states, padding masks, seeds and saved processor-component hashes across the models.
- Normalize each joint's absolute error by its retained-training q99–q01 span before averaging percentages across joints. A percentage here is a scale-normalized action error, **not accuracy or success probability**.
- Also report native-unit joint errors, first-action error, horizons 1/5/10/16/25/50, per-episode/per-seed results and dynamic-window results. Dynamic means demonstrated target variation above 5% of a training span; it is not a safety threshold or a human grasp-phase annotation.

The all-window metric weights valid target positions, whereas every window contributes equally to first-action error. Temporal windows and seeds are correlated; no significance or independent-test claim is made.

## Output locations

GPU checkpoint root:
`/home/kiran/sim/pi05-fullft-orange50-20260922/orange45_fullft_15k_candidate/checkpoints`

GPU evaluation root:
`/home/kiran/sim/pi05-fullft-orange50-20260922/orange45_comparison_20260924`

Each step has `structural_audit.json`, `report.json` and `predictions.npz`, with a separate supervisor status/log directory. `comparison.json` holds the cross-checkpoint metrics. The evaluation allows 20 minutes and 2 GB of new output per checkpoint; it preserves other GPU services.

Scripts: `evaluate_orange45_checkpoints.py` and `run_orange45_comparison.py` in this workspace, copied into the GPU full-FT workspace. No installed LeRobot files were changed.

## Completed result and decision

All three inference processes completed with exit code zero. All 810 seeded predictions were finite; each model's same-seed repeat check had maximum difference zero. Loaded parameters were finite. Sample/input hashes, targets, states, masks and processor-component hashes matched across all checkpoints. An independent local recomputation from the downloaded NPZ arrays reproduced all three aggregate action-error metrics. Each seed has 4,059 valid target positions across the 90 windows; padding is excluded.

| Checkpoint | Full-sequence action error, % span ↓ | First-action error, % span ↓ | First-16-action error, % span ↓ | Dynamic-window error, % span ↓ |
|---|---:|---:|---:|---:|
| 5k | 4.5160 | 1.6458 | 2.7748 | 5.1283 |
| 10k | **3.8819** | 1.3512 | 2.4286 | 4.7303 |
| 15k | 3.9490 | **1.2988** | **2.3903** | **4.6673** |

There are 62 dynamic windows under the diagnostic definition above. The 10k checkpoint's full-sequence error is about 14.0% lower than 5k. The 15k error is only about 1.73% higher than 10k. No statistical significance is claimed for that small difference.

### Why this does not match the validation-loss ranking

The installed π0.5 source computes a flow-matching MSE with sampled noise/time during `forward`; action inference instead integrates a predicted trajectory and decodes it into joint units. The recorded trainer loss covers the full validation loader and includes repeated terminal targets. This comparison uses 90 windows, fixed inference seeds, native decoded actions, per-joint span normalization and nonpadded targets only. These are different quantities, not contradictory calculations.

Consequently, **5k is best by recorded validation loss, but not by this sampled decoded-action evaluation**. The loss trend alone was insufficient to diagnose simple overfitting. Do not call the 15k model universally worse: it has slightly better immediate/short-horizon and dynamic-window errors here.

### Joint-level residuals

Full-sequence native-unit mean absolute errors, nonpadded targets only:

| Joint | Units | 5k | 10k | 15k |
|---|---|---:|---:|---:|
| shoulder_pan | degrees | 4.55 | 3.78 | 3.74 |
| shoulder_lift | degrees | 7.20 | 6.46 | 6.62 |
| elbow_flex | degrees | 8.34 | 7.91 | 8.01 |
| wrist_flex | degrees | 11.94 | 8.97 | 10.12 |
| wrist_roll | degrees | 2.32 | 2.05 | 1.97 |
| gripper | normalized position points | 3.51 | 3.13 | 2.92 |

Wrist-flex disagreement remains substantial, especially later in the horizon. These are disagreements with demonstrated future targets, not measured hardware tracking errors, force errors or evidence that every predicted alternative would fail.

The 10k full-sequence metric improves over 5k on all nine evaluated episodes. Against 15k, 10k is lower on five of nine episode aggregates and 50 of 90 window aggregates; 15k is better on the remaining four episodes. Across the three seeds, 10k scores 3.732/3.808/4.106 versus 15k's 3.841/3.974/4.032, so 10k does not win on every seed either.

Hardest episode aggregates for 10k are original episode 58 (6.113% span) and 17 (5.177%). Representative high-error windows include episode 46 frame 99 (3.30 s, 10.664% span), episode 58 frame 497 (16.57 s, 9.356%), and episode 17 frame 231 (7.70 s, 8.899%). These are exact sample identifiers for targeted follow-up, not newly verified task-phase labels. The earlier sampled phase anchors can guide visual inspection, but cannot certify exact contact timing.

### Recommendation

Use **10k as the primary candidate for further offline deployment testing** when prioritizing agreement across the full 50-action sequence. Keep **15k as the close alternative**, particularly if a separately chosen execution strategy uses only a short prefix. Do not choose or change the execution horizon just to favor a checkpoint; that requires its own timing/control decision.

Preserve 5k and its best recorded validation-loss result. No checkpoint was promoted into a live service, exported over an existing policy, deleted or physically tested. A single definitive task-performance winner is not established by these correlated offline samples.

Next work is a fresh deployment-path replay of the shortlisted model using recorded inputs, checking input/processor consistency and end-to-end timing before any separately authorized supervised robot trial. Continue to exclude LoRA comparisons. Existing GR00T process PID 11632 remained running; GPU free memory returned to about 23,203 MiB after these tests.

Local evidence: [comparison.json](orange45_comparison_20260924/comparison.json), plus per-checkpoint reports, predictions, structural audits and supervisor logs in the same directory. The 90-window evaluation itself took about 50–56 seconds per checkpoint after model loading; those times include sample loading, inference and report hashing and are not pure inference-latency benchmarks.
