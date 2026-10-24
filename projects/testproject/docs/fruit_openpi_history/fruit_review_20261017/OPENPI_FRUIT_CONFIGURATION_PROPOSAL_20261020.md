> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/OPENPI_FRUIT_CONFIGURATION_PROPOSAL_20261020.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# OpenPI fruit experiment — configuration and budget proposal

20 October 2026. **Proposal, not a runnable or validated training configuration. No training launched.** Implements planning for the user-selected existing55 pool; no extra collection prerequisite.

## Recommendation

Prepare an initial **5,000-update ceiling at batch32**, with validation/checkpoints every1,000 updates. Preserve the agreed LIBERO-style LoRA+vision method; adapt inputs/outputs to the physical SO101. This ceiling is a bounded experiment, not a claim that5k is optimal. Do not automatically extend it to30k.

## Fresh read-only evidence

AI90 SSH `kiran@192.168.194.220` responded as `kiran-AI90`. RTX PRO5000:73,415MiB total,20MiB used; RTX5090:32,607MiB total,8,833MiB used. Approximately47GiB system RAM available;857GiB disk available on the filesystem containing `/home/kiran/sim`. These are snapshots, not reservations or measured training peaks. Leave GPU0 and its existing job untouched; recheck GPU identity/availability before launch.

`/home/kiran/sim/openpi` remains at `0a0b19f2896856bb8e4cb3904ebf3b508c20a4f6`, with no changes reported by `git status --short`.

- `training/config.py` SHA256: `be1211696c1047c014bd7cd7ba53bd85eca4e3df88e83f676cf21ac2e5d9daa1`.
- `training/data_loader.py` SHA256: `99221d1fec5eff2d3f54ea1a14015302164dac7e494e65bb339feb4630f57f4a`.
- Local split manifest SHA256 rechecked: `6fdd75dab818340e7f73087fa4ee2aa909e8c58c5c3b87b1e59a23e1652e95b7`.

## Proposed settings versus reference

| Item                   | Proposal                                                                                   | Reason/status                                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| Base                   | General `gs://openpi-assets/checkpoints/pi05_base/params`                                  | Same base as reference, not LIBERO checkpoint                                                       |
| Method                 | `gemma_2b_lora` + `gemma_300m_lora`, reference freeze filter; vision/projections trainable | Preserve agreed method; actual parameter audit required                                             |
| LoRA ranks/alphas      | 16/16 and32/32, reference attention/FFN targets                                            | Source-audited reference; no smaller adapter-only substitution                                      |
| EMA                    | Disabled                                                                                   | Preserve reference                                                                                  |
| State                  | Six SO101 components, continuous (`discrete_state_input=False`)                            | Preserve verified joint order/units                                                                 |
| Actions                | Six absolute joint-position targets; no extra LIBERO delta transform                       | SO101 data contract, verify round trip                                                              |
| Cameras                | Front→`base_0_rgb`, wrist→`left_wrist_0_rgb`; missing right wrist zeroed and masked        | Standard model slots, not extra training camera                                                     |
| Instruction            | Per-episode fruit/plate task, `prompt_from_task=True`                                      | Test both fruit prompts end-to-end                                                                  |
| Horizon                | **Propose30 actions at30Hz**                                                               | Approximately1s horizon like10 at10Hz; explicit adaptation, not reference default or proven optimal |
| Batch                  | 32, one RTX PRO5000                                                                        | Subject to real pipeline memory check; no silent fallback                                           |
| Update ceiling         | 5,000                                                                                      | Shorter data-scaled experiment, not automatic30k                                                    |
| LR                     | Cosine, peak2.5e-5, endpoint2.5e-6, warmup500, decay_steps5,000                            | Peak/end preserved; warmup and schedule deliberately adapted                                        |
| Optimizer/precision    | Inherit pinned reference configuration                                                     | Record resolved values and audit before launch; no custom offload added                             |
| Seed                   | 1000, explicitly logged                                                                    | Experiment choice                                                                                   |
| Sampling               | Ordinary shuffled training timestamps, no fruit oversampling                               | Preserve actual exposure and report it                                                              |
| Checkpoints/validation | Baseline and each1,000 updates, plus final                                                 | Per-fruit evaluation must be implemented/verified                                                   |
| RTC                    | No RTC-prefix training                                                                     | Guided RTC serving is separate                                                                      |

All proposed differences are explicit. Horizon30, warmup500, budget5k, seed and evaluation cadence are project choices, not official mandatory defaults. Increasing horizon may change compute cost. Do not use the old adapter-only run's2h42m estimate. No reliable duration or checkpoint-storage estimate exists until the actual pipeline is measured.

## Data and budget arithmetic

Existing mixed artifact: `/home/kiran/sim/pi05-orange-tomato-lora-pilot-20261017/dataset`. It includes both splits; **do not point the unmodified stock training loader at all55 episodes**.

Train36 orange+8 tomato:33,493 orange timestamps+7,184 tomato=40,677. Validation9 orange+2 tomato:8,511+1,796=10,307. Use the existing mixed-ID mapping, not original merged IDs as if they were identical. Do not restore footage outside retained intervals.

| Budget at batch32                             | Sample presentations | Dataset-equivalent passes |
| --------------------------------------------- | -------------------: | ------------------------: |
| 1,000 updates                                 |               32,000 |                      0.79 |
| 3,000 updates                                 |               96,000 |                      2.36 |
| 5,000 updates                                 |              160,000 |                      3.93 |
| 30,000 updates, not recommended automatically |              960,000 |                     23.60 |

At the natural timestamp proportions, the5k run exposes roughly132k orange and28k tomato samples; actual counts depend on shuffling and dropped partial batches. These are repeated timestamp presentations, not unique demonstrations or camera-frame counts. Future action targets overlap, so presentations are not independent lessons. The roughly3.9 passes are comparable in scale to historical LIBERO's roughly3.5, but this does not establish equivalent diversity or the optimal duration.

## Specific implementation gaps found in installed source

1. `create_torch_dataset` constructs `LeRobotDataset(repo_id, delta_timestamps=...)` without our explicit episode lists. **Split filtering is not currently supplied by that factory.** Choose a separate isolated adapter/factory that applies the saved episode lists, or train-only/validation-only derived artifacts. Verify exact row membership and retained bounds. Do not patch the clean reference checkout in place.
2. `LiberoOutputs` returns seven dimensions; SO101 needs six. Implement the named fruit input/output adapter rather than reusing seven-action output unchanged.
3. The inspected `scripts/train.py` has no held-out per-fruit validation loop. A separate deterministic checkpoint evaluator or explicit isolated integration is needed. Do not claim automatic validation because a plan lists a cadence.
4. Recompute statistics from the actual training-only OpenPI representation. Verify normalization/inverse transforms, image RGB/layout, prompts, padding and chunk end behavior. Do not blindly reuse LeRobot or LIBERO statistics.
5. Inspect the official loss/padding behavior and distinguish it from evaluation masking. Report errors only for real SO101 dimensions and valid future targets; do not silently change the reference training loss to implement evaluation masking.
6. Save/fresh reload and serving of all learned components must work before the main run; OpenPI weights are not a drop-in LeRobot adapter.

## Validation and checkpoint decision rule

Use all11 validation episodes, report both sample-weighted and per-episode results separately for each fruit. Report first action/full chunk, five-joint degree MAE and gripper-point MAE separately; no mixing degrees with gripper points into one unexplained metric. Use fixed evaluation seeds/noise draws and identical observations for comparisons; validate every retained timestamp if compute permits and otherwise disclose the exact fixed sample manifest before training. Do not skip difficult intervals or near-end samples without reporting masks.

Record a pre-training base evaluation, then evaluate each saved checkpoint. Flag simultaneous worsening of both fruits' comparable metrics across two successive evaluations for review; do not automatically extend the budget or restart with altered settings. Select checkpoints using per-fruit evidence, not final-step number or overall training loss alone. If checkpoints trade orange against tomato performance, report the tradeoff rather than calling one universally best. Two tomato holdout episodes cannot prove robust generalization or90% task success.

## Next execution sequence

1. Prepare isolated fruit adapter/config and explicit train/validation membership; verify actual processed real samples for both fruits and episode boundaries. No fake robot required.
2. Run the agreed bounded resource/save/reload check only after the real data pipeline is verified. Record trainable names/counts, memory, step time, checkpoint size and actual GPU selection.
3. Reconcile any necessary change to this proposed batch/horizon/schedule explicitly; produce the final executable command and measured time/storage estimate.
4. Launch only the finalized run in a new output location; preserve old data, models and reference environments. No robot connection is required for these offline steps.

This proposal does not create a new collection requirement or authorize physical trials. The full preparation is not complete merely because resource availability was checked.
