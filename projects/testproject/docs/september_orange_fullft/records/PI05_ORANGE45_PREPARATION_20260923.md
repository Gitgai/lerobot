# Approved orange45 training preparation

Latest deployment follow-up: [10k saved-input deployment/network results](PI05_FULLFT10K_DEPLOYMENT_CHECK_20260924.md). Correctness passed; timing remains unresolved for continuous control. All temporary test services were stopped and no robot movement occurred.

## Latest status — September 24

The 15k run completed successfully in about 12 hours 9 minutes. All three checkpoints passed structural checks and fresh-process inference. See [completed checkpoint evaluation](PI05_FULLFT_CHECKPOINT_EVALUATION_20260924.md): 10k has the lowest sampled full-sequence action error; 15k is a close alternative with slightly lower short-horizon error; 5k has the lowest recorded validation loss. No LoRA comparison or physical trial occurred. Earlier running/unstarted statements below are historical.

Date: 2026-09-23. The user approved launching the 15,000-update full-fine-tuning run and explicitly removed the previous-LoRA comparison. The separate derivative is built and verified. Launch status is recorded below after startup verification.

## Launch verified — training running

Dispatched 2026-09-23 at 10:50:56 UTC (16:20:56 India time), supervisor PID 137593, worker PID 137594. The actual log reached **11/15,000 updates** during startup verification. First-update loss 0.203444 and gradient norm 5.610522 were finite; this is startup health evidence, not a quality score. Model loading reported all keys loaded successfully; 4,143,404,816 parameters require gradients. Telemetry updates every 100 steps after the first, so its update count can lag the live progress log.

Output: `/home/kiran/sim/pi05-fullft-orange50-20260922/orange45_fullft_15k_candidate`.

Live status/log: `/home/kiran/sim/pi05-fullft-orange50-20260922/orange45_15k_control/status.json` and `worker.log` in that directory. The detached GPU process survives closing the SSH connection. The supervisor enforces the configured resource checks; no scheduled assistant monitoring was installed. No checkpoint exists yet at this initial verification. Evaluation/checkpoint saving is configured for steps 5,000, 10,000 and 15,000; only these new full-FT checkpoints are in comparison scope.

## Applied selection

Original recordings and existing datasets/checkpoints remain untouched. Original merged episode numbers below are preserved in a mapping because the derivative renumbers episodes consecutively, 0–44.

- Keep 45 orange demonstrations, including the two partially clipped outcomes 50 and 53 with their review caveats.
- Set aside original episodes 48, 49, 51, 52 and 57 because final outcomes remain uncertain, not because they were proved failures.
- Retain original episode 43 frames 0–509. Remove its subsequent 388 timestamps from the derivative only.
- Preserve each retained episode's original train/validation side.

| Split      | Episodes | Timestamps |
| ---------- | -------: | ---------: |
| Training   |       36 |     33,493 |
| Validation |        9 |      8,511 |
| Total      |       45 |     42,004 |

Selection manifest SHA-256: `e17b50b475aec58209df60e5ec89a6517082f1993a2d12002e6cb7abda8af307`.
It references frozen review v1, whose original recommendation-only status is preserved as historical evidence.

## Storage and camera handling

GPU machine: `kiran@192.168.194.220`.

Dataset: `/home/kiran/sim/pi05-fullft-orange50-20260922/orange45_preparation_20260923/dataset`.

Camera MP4 files are independent, byte-identical copies of the packed source videos, verified by SHA-256. They still physically contain unindexed excluded footage; dataset metadata and numeric rows expose only retained episode intervals. No video re-encoding or source mutation occurred.

State/action statistics were recomputed using only the 33,493 retained training timestamps. Validation uses those training statistics. Image statistics remain source-episode sampled estimates, including the untrimmed source estimate for episode 43; the configured vision normalization is IDENTITY and does not use those estimates. This is not a claim that every metadata statistic was recomputed from every retained pixel.

## Verification

The actual installed LeRobot loader confirms the 36/9 split and 33,493/8,511 row counts. The training sampler covers every retained training index once per pass and reshuffles on the next pass. Numeric hashes and finite state/actions are checked for all selected rows. Six normalization statistics per state/action are independently recomputed and compared for both loaders.

135 actual loader samples (start, middle and final timestamp of all 45 episodes) verify both camera tensors, exact task text, 50-action target windows, terminal padding, tokenization and action normalization round trips. The trimmed episode ends at original frame 509: subsequent target positions repeat that final retained action, never original frame 510 or later. This follows the installed official loss/padding behavior; padded terminal targets still contribute to its loss.

The worker has a manifest-bound gate that verifies dataset path, train/validation identities, counts and manifest checksum. The remote previous integration-tested worker is preserved; the updated worker is deployed separately as `fullft_orange45_main.py`. Dataset-gate testing is not a new full optimizer/save/resume test. The earlier real batch-four integration remains the evidence for unchanged optimizer/checkpoint machinery.

All 19 existing supervisor, checkpoint-validator and frozen-review tests passed again. The worker's actual dataset-gate code is exercised separately: the correct manifest is accepted and an incorrect digest is rejected.

## Configuration and checkpoint evaluation

New config: `/home/kiran/sim/pi05-fullft-orange50-20260922/orange45_preparation_20260923/train_config.json`.

Fresh general π0.5 base; full fine-tuning with the already tested external CPU-offloaded AdamW support; batch four; 15,000 updates; 500 warmup and 15,000 decay; checkpoint/evaluation every 5,000 updates. No LoRA, deliberate vision/expert freezing, RTC or robot movement. Nominal 60,000 sample presentations correspond to about 1.79 passes through the retained training timestamps. Two camera views form one sample, not two.

Per the user's instruction, do not run or report comparisons against the previous LoRA model. Earlier rescore artifacts are preserved as historical files only; they are not part of checkpoint selection. Evaluate only this run's 5k, 10k and 15k checkpoints using the same nine validation episodes, consistent preprocessing, action units and random seeds. Include full-validation loss, offline action error and reaching/grasping/placement weaknesses; do not assume the final checkpoint is best.

## Remaining execution, not additional dataset permission

The approved selection is applied and the user has authorized training. Launch uses the guarded resource limits (16 hours / 150 GB additional output), the new config, and both manifest environment values:

`launch_pi05_orange45.py` is the prepared entrypoint on the GPU machine. Without arguments it only validates readiness and prints the command/budgets; `--start` explicitly launches through the tested supervisor. It refuses existing output and does not auto-resume. No main training was launched during preparation.

`FULLFT_SELECTION_MANIFEST=/home/kiran/sim/pi05-fullft-orange50-20260922/orange45_preparation_20260923/manifest.json`

`FULLFT_SELECTION_SHA256=e17b50b475aec58209df60e5ec89a6517082f1993a2d12002e6cb7abda8af307`

After training, evaluate and compare only the new 5k/10k/15k checkpoints on the same retained validation data. No previous-LoRA comparison. Offline error does not establish physical success or resolve the historical hardware/deployment issues. Physical deployment remains a separate supervised decision; training sends no motor commands.

Review limitation remains: whole-span 1 Hz plus final-frame inspection and a frame-by-frame trim-boundary check, not exhaustive behavioral certification of every frame. All evidence and configuration copies are under `pi05_quality_gate_20260923/orange45_preparation/` beside this document.
