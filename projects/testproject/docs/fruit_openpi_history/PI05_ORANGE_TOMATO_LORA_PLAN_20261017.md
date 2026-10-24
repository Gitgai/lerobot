> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/PI05_ORANGE_TOMATO_LORA_PLAN_20261017.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# π0.5 orange/tomato training — active plan

Updated 21 October 2026. Authoritative forward plan; filename retained for existing links.

**Historical configuration-preparation note:** [original configuration/budget proposal](fruit_review_20261017/OPENPI_FRUIT_CONFIGURATION_PROPOSAL_20261020.md). Its initial implementation gaps were addressed by the later isolated loader, fruit adapter and evaluator. The current approved execution status is below; the early proposal's “not launched” language is not a requirement to obtain new approval.

## Current decision and scope

**22 October recovery progress:** [scoped backup and stale-action guard](fruit_openpi_client/storage_investigation_20261022/RECOVERY_PROGRESS.md). 433 selected local project/code/log/calibration files verified by hash on AI90; converted 55-episode dataset and 4k/5k checkpoint layout confirmed there, not a full original-recording backup. Fresh SMART reports zero media errors but the NVMe reset cause remains unresolved. Added suspend-aware, latched project fail-stop timing checks; 14 pure tests and an actual server/saved-observation check passed, zero movement. Next remains original-data preservation and host reliability, then full non-moving integration. No physical retry until these issues are addressed.

**22 October pause diagnosis:** [NVMe reset evidence and recovery plan](fruit_openpi_client/storage_investigation_20261022/REPORT.md). Acer's root SSD reported READ/WRITE timeouts, I/O errors and one controller reset at 15:03:41, aligned with the shared camera/control pause. This strongly supports a host-storage stall, not proven model failure; exact hardware/firmware/kernel cause remains unresolved. Prioritize backup/host health and explicitly reviewed stale-action fail-stop behavior; do not launch another physical run or hide the issue by disabling keepalive. No physical access, disk repair, package change or control-behavior change occurred in this diagnosis.

**22 October first new-checkpoint physical trial:** [fruit OpenPI 4k trial 1](fruit_openpi_client/orange_trial_01_20261022/REVIEW.md) ran under supervision after workspace clearance. It sent 210 actions, then stopped on WebSocket keepalive timeout; torque-off verified on all six, no homing or repeat. No successful orange placement demonstrated. A ~56-second shared camera/control recording gap and delayed dispatch of request 7 require investigation. Next is a non-moving timing/transport investigation, not another unchanged trial, retraining or protection changes. This supersedes the no-physical-trial status below.

**22 October verified integration result:** [OpenPI real-arm integration report and next steps](fruit_openpi_client/README.md). The actual cameras + torque-off motor readings + 4k server + recording path passed with two valid predictions, 1,827 decoded frames, identical motor-setting snapshots and zero motor commands. A separate SIGTERM-during-request check verified torque-off cleanup. Two earlier wrist-camera startup failures remain in the evidence; subsequent concurrent camera checks succeeded but the cause is not established. Warm round trip was 6.563 s versus 74 ms inference. All owned processes stopped. Next is a freshly checked, supervised first physical trial; no new-checkpoint physical trial, task-success score or loaded cleanup validation exists yet. This supersedes the pending-check wording immediately below.

**22 October deployment integration:** [isolated OpenPI real-arm client plan](fruit_openpi_client/README.md) is the active next step. Implemented dataset-unit contract, separate networking worker, real LeRobot read-only/default and explicit execution paths, camera/response/dispatch recording and existing torque cleanup. Six pure contract checks and syntax validation passed; actual observation-only and stop-path checks are next. No physical trial yet. No installed environments, motor settings, RTC/JPEG configuration or training changed. This supersedes earlier descriptions of the client as not implemented, but not as yet physically validated.

**21 October scope update:** the user approved proceeding toward a supervised real-arm check with the new 4k fruit checkpoint, RTC off. [Real-arm preflight](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_real_preflight_20261021_PWDXx2/README.md) passed read-only six-motor/camera checks and two real-observation OpenPI requests; zero motor commands. Idle feedback 7.2–7.3 V, all Status=0 and torque off. The new OpenPI physical client, logging and stop/cleanup integration remain pending; old gRPC/RTC and approximate simulator mappings are not substitutes. This supersedes earlier simulation-only scope, not the obligation to verify deployment before movement. No trial has run.

**Current simulator result:** [normalized bridge investigation](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_sim_20261021/NORMALIZED_BRIDGE_REVIEW.md) completed five repeat setup attempts, bringing the total to ten. Numeric adapter checks passed but each repeat stopped at the simulator wrist-flex limit, with no fruit lift. Zero scored evaluations: no valid task-success rate yet. Model, data, real arm and installed environments remain unchanged; simulator and owned server stopped. Next is geometric/camera correspondence and physics validation, not further unchanged trials or retraining. Earlier statuses below are historical.

**Latest simulator run:** [five setup attempts and findings](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_sim_20261021/SETUP_RESULTS.md). The 4k checkpoint made 11 predictions and drove 278 simulated actions. All five attempts stopped on wrist-flex targets beyond the USD limit; calibration/scene correspondence remains unverified. No scored evaluation or physical trial was run. The setup is not ready for the proposed 20 scored attempts; model and simulator are stopped.

**Simulator rendering follow-up:** the user accepted NVIDIA's license and four static reference images were generated successfully. [Render review](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_sim_20261021/RENDER_REVIEW.md) documents visible scene mismatch and runtime physics warnings/errors. This proves rendering, not matched calibration or policy success. No physical trial or simulator policy rollout occurred.

**21 October simulator direction:** [offline fruit simulator plan and assessment](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/PI05_FRUIT_SIMULATOR_PLAN_20261021.md). Existing AI90 LeIsaac/SO101 assets and an OpenPI client were found, but stock normalized arm units, input keys and three-orange task do not match this checkpoint. Inventory and source assessment are complete; no simulator policy trial was launched. Next: explicit calibration/unit/camera/timing mapping and an isolated integration proposal. No physical trial, custom RTC or installed-environment change is authorized by this assessment.

**Latest offline follow-up:** [saved 4k checkpoint and serving check](fruit_review_20261017/SAVED_4K_SERVING_CHECK_20261020.md) passed fresh official reload, 33 recorded observations and two AI90-loopback server requests. This supersedes the reload-pending wording below. Previous LeRobot/RTC deployment compatibility is not established: the pinned OpenPI sampler lacks its prefix/delay interface. No environment replacement or custom RTC was introduced. **The user explicitly excludes physical trials; continue offline only.**

**Completed status, 20 October:** the approved 5,000-update LoRA-plus-vision run and all five full validations completed. The baseline and five checkpoint reports were subsequently audited across 61,842 evaluation rows with matching input/noise hashes. See [checkpoint comparison and next steps](fruit_review_20261017/OPENPI_FRUIT_CHECKPOINT_SELECTION_20261020.md). Keep both 4k (slightly lower arm error) and 5k (lower gripper error); 4k is a provisional first deployment-preparation candidate, not a proven physical winner. Fresh trained-checkpoint reload and serving compatibility remain unverified. No robot trial was performed.

The dated preparation/queued statements below are historical execution notes, superseded by this completed status.

**Explicit training approval,20 October:** the user authorized proceeding with the agreed5,000-update LoRA-plus-vision run and requested no repeated permission questions. A one-shot AI90 supervisor is active: finish the existing full baseline → real train/evaluate/train transition check → preflight → main training automatically. It stops on failure rather than retrying with altered settings. Training is currently queued, not yet executing main updates. See [approved execution/status paths](fruit_review_20261017/OPENPI_BASELINE_AND_MAIN_COMMAND_20261020.md). This approval supersedes earlier wording that another manual launch decision was required; it does not authorize changes to data, learning method or budget.

**20 October full baseline:** [baseline execution and staged main command](fruit_review_20261017/OPENPI_BASELINE_AND_MAIN_COMMAND_20261020.md). The full10,307-timestamp zero-update general-base evaluation has been launched on AI90; completion requires `base_full_result.json`. Main training is not launched. Captured repeats confirmed33/33 input/noise hashes match, same-process predictions match, and fresh-process target variation remains; see that report for units and limitations.

**20 October sustained timing/evaluation:** [follow-up results](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/OPENPI_EVALUATION_AND_THROUGHPUT_20261020.md). The30-update disposable benchmark passed; final20 averaged3.816s/update including immediate loader wait (~5h18m for5k, plus validation/save overhead). Per-fruit evaluator arithmetic checks passed; actual sampled prediction check status is in the linked report. This does not launch main training.

**20 October normalization/integration:** training-only statistics and full model preprocessing checks passed. The isolated six-update GPU/save/reload check is documented in [normalization and bounded-check status](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/OPENPI_NORMALIZATION_AND_TRAINING_CHECK_20261020.md). This is not the main 5,000-update run; actual GPU/checkpoint results must be read from that report, not inferred from this launch note.

**20 October real-loader preparation:** [implementation findings and remaining checks](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/OPENPI_LOADER_PREPARATION_20261020.md). The old OpenPI loader cannot directly consume the selected v3 metadata. An isolated packed-video/split-boundary bridge has been prepared without changing the reference environment. This is data preparation, not a training-speed measurement or full launch.

**Use the existing 45 newer orange + 10 tomato episodes for the next measured experiment. Collect no additional demonstrations for this experiment.** This is the user's 19 October decision. It supersedes the earlier initial +10 tomato and provisional +40 tomato/+10 orange collection proposals. New collection is not a prerequisite for offline preparation or this experiment.

Keep the 16 older-camera orange candidates separate; do not merge them automatically. Do not remove the existing tomato episodes. Limited tomato/session coverage is an accepted experimental limitation, not a reason to silently reinstate a collection gate.

The20 October user instruction authorized the agreed offline training workflow, now completed. It does not authorize unrelated dataset mutation, installed-package changes, robot movement or a different training recipe. Physical readiness remains necessary for later supervised trials.

## Agreed learning method

Use **our verified OpenPI LIBERO-style LoRA-plus-vision approach**, adapted to SO101:

- Learn LoRA adapters, vision encoder and intended action/time projection components.
- Freeze the remaining backbone according to the reference freeze filter.
- Initialize from the general π0.5 base, not the LIBERO-fine-tuned checkpoint.
- Do not substitute the smaller LeRobot adapter-only recipe or full fine-tuning.
- Use ordinary training without RTC-prefix conditioning. Guided RTC is a separate deployment integration; do not assume server support.

| Recipe                                        | What learns                       | Role                                       |
| --------------------------------------------- | --------------------------------- | ------------------------------------------ |
| Physical Intelligence published `pi05_libero` | Full fine-tuning                  | Benchmark reference, not our agreed method |
| Our `pi05_libero_low_mem_finetune`            | LoRA + vision + projections       | Reference for this fruit experiment        |
| October 17 fruit pilot                        | 1,287,168 adapter-only parameters | Completed, preserved; not the new recipe   |

Our historical LIBERO run used roughly 467M trainable parameters, ranks 16/32 for `gemma_2b_lora` / `gemma_300m_lora`, batch32, EMA disabled and a 10-action horizon. Its 30k-update budget is not automatically transferred. Source-level reference inspection is recorded in [coverage/reference results](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/coverage_20261018/RESULTS.md); verify actual trainable names/shapes when implementing.

Historical evaluation: selected 20k LIBERO checkpoint achieved 99.5% on 200 Spatial cases and 95.95% across 2,000 four-suite cases. These different scopes do not predict fruit success. Published PI four-suite mean 96.85% / Spatial 98.8% refers to its own checkpoint/protocol, not proof of identical training.

References: [saved reference audit](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/openpi_libero_audit_20261012/AI90_EXISTING_PLAN_SNAPSHOT.md), [LIBERO evaluation plan](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/OPENPI_LIBERO_AI90_PLAN_20261012.md), [official configuration](https://github.com/Physical-Intelligence/openpi/blob/main/src/openpi/training/config.py), [official results](https://github.com/Physical-Intelligence/openpi/blob/main/examples/libero/README.md). Pin revisions before implementation.

## Fixed experimental data scope

| Split      | Orange episodes | Tomato episodes | Timestamps |
| ---------- | --------------: | --------------: | ---------: |
| Training   |              36 |               8 |     40,677 |
| Validation |               9 |               2 |     10,307 |
| Total      |              45 |              10 |     50,984 |

Preserve the existing whole-episode split, source identities, approved trim, task labels and recovery annotations. Two camera views at one timestamp are one multimodal sample, not two independent examples. Existing manifests: [split/loader](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/PILOT_SPLIT_AND_LOADER.md), [dataset verification](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/MIXED_DATASET_READY.md), [pilot split JSON](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/pilot_split.json).

Mixing fruit types is not inherently contradictory: each example must retain the correct fruit instruction, front/wrist images, state and demonstrated action. Verify the instruction actually reaches the model—do not replace every example's task with a shared orange or tomato label. [Official OpenPI task-prompt example](https://github.com/Physical-Intelligence/openpi/blob/main/examples/ur5/README.md).

Risks accepted for this experiment:

- Tomato has only eight training and two validation episodes from one documented batch; it may generalize poorly outside those conditions.
- Episode proportions are not necessarily sample proportions: report actual per-fruit training timestamps and sampler exposure.
- Start with a documented ordinary timestamp sampler; do not silently add fruit balancing, oversampling, augmentation or a changed loss. Any proposed adjustment needs explicit rationale. Repeating tomato frames cannot create new scene diversity.
- Same-session validation and correlated frames do not establish independent generalization.
- Selecting the requested fruit when both fruits are present is not established by these single-fruit demonstrations; keep that evaluation claim out of scope.
- Above 90% success for each fruit remains an objective, not a forecast or launch prerequisite.

## Review evidence and qualifications

Completed:

- All 55 retained numeric hashes matched the manifest.
- Automated checks covered 101,968 camera images with no decode/count/strict-PTS failures; one isolated repeated RGB frame.
- All newer55 one-second paired timelines inspected: 3,532 sampled images; with three local every-frame intervals, 3,688 unique inspected images.
- 53 clear sampled final placements; orange50 and53 have cropped, qualified outcomes.
- Recovery examples include orange1/30/40 and tomato28. Orange40's recorded gripper action stayed constant through its checked drop interval; no opening command is supported there.
- All78 near-static intervals reconciled against state/actions; maximum measured arm-joint range 2.5495 degrees. This is not sensor-synchronization certification.
- Older16 denser paired timelines reviewed (832 images), all with observed placement; they remain outside this experiment because of the separate camera/setup/provenance decision.

Evidence: [timeline table](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/full_frame_20261018/TIMELINE_REVIEW_COMPLETE.md), [follow-up](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/full_frame_20261018/FOLLOWUP_RESULTS.md), [technical results](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/full_frame_20261018/TECHNICAL_RESULTS.md), [older review](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/plate20/dense/REVIEW.md), [archive compatibility](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/older_inventory_20261018/COMPATIBILITY_RESULT.md).

Full every-frame behavioral certification is not complete and must not be claimed. Keep remaining contact/release boundary and cropped-outcome uncertainty explicit. The user has chosen this existing pool for a measured experiment with these limitations; do not silently trim, exclude, expand or relabel it. Any newly discovered material defect must be reported before changing the manifest. Further targeted inspection can resolve specific questions without repeating completed reviews or requiring new demonstrations.

## Phase 1 — freeze reference and fruit adaptation

Read-only source inspection already identified OpenPI revision `0a0b19f2896856bb8e4cb3904ebf3b508c20a4f6`, base `gs://openpi-assets/checkpoints/pi05_base/params`, ranks/alphas16/16 and32/32, attention/FFN adapters, EMA off, cosine defaults warmup1k / peak2.5e-5 / decay30k to2.5e-6. These are reference values, not the selected fruit schedule.

Reconcile saved config/source hashes and actual trainable/frozen module names. Record exact base, revision, local changes, optimizer, precision and checkpoint format. Preserve the successful LIBERO environment.

Map front/wrist RGB, correct per-example instruction, six-component state and demonstrated actions. Verify joint order, degree/gripper-point units, absolute versus relative actions, padding, image preprocessing and normalization. Do not copy Panda/LIBERO action conventions or camera rotations blindly. Compute statistics from the fruit training split only for the actual OpenPI representation; old LeRobot statistics are reusable only if representation equivalence is verified.

Explicitly choose action horizon and execution cadence: ten actions at30Hz spans nominally0.33s, not the1s of ten at10Hz. Do not silently inherit either the LIBERO10 or old fruit50 horizon.

Deliverables: pinned reference manifest, adaptation difference table, processed samples from both fruits, verified task propagation and split/statistics identities.

## Phase 2 — resources, budget and checkpoint compatibility

Check GPU/CPU/disk availability and actual trainable components. Use isolated additive environment/output locations if dependencies must change. No source checkpoints or installed reference environments may be overwritten.

Verify a bounded training/save/fresh-process-reload check for the actual OpenPI fruit pipeline before the main run. The prior LeRobot adapter-only smoke test is not a substitute. Do not add mandatory fake-hardware robot tests or new motor limits.

Determine serving compatibility early: OpenPI checkpoints are not automatically loadable by the LeRobot π0.5 server. Establish supported serving or verified conversion preserving learned vision/adapters/projections, normalization and action semantics. Verify guided RTC separately.

### Budget selection

Do not choose 30k updates simply because LIBERO used that value. The current training split is40,677 timestamps versus273,465 in the historical LIBERO dataset.

At batch32, 30k updates would present960,000 samples: approximately23.6 fruit dataset-equivalent passes versus3.5 LIBERO passes. These are arithmetic comparisons, not optimal budgets or guaranteed frame coverage.

Choose and document a maximum budget, effective batch, expected sample presentations, learning-rate schedule, validation/checkpoint cadence and stopping/selection rule before launch. Measure validation separately for orange and tomato; aggregate loss alone must not determine success. A two-episode tomato holdout gives limited evidence and can be overfit through repeated checkpoint selection. Do not silently extend training or change sampling.

## Phase 3 — train and monitor the agreed experiment

After adaptation/resource checks and budget decision, freeze the command/config and create a unique output directory. Record hashes, data/split/statistics identities, trainable audit, sampler, effective batch, schedule, precision and start time.

Save complete resumable checkpoints and verify a fresh reload. Choose save cadence from measured storage and recovery needs. Do not reuse the adapter-only2h42m runtime estimate. Preserve the paused completed-run watcher; any new monitor must target this exact run explicitly. No automatic retries with modified settings.

## Phase 4 — evaluate each fruit separately

Report held-out first-action and full-chunk errors separately for orange and tomato, masking padded targets and retaining degree/gripper-point interpretation. Use consistent evaluation observations/seeds and report both per-fruit and overall results. Prediction loss is not physical success.

Before supervised trials, verify current rig/cameras, normalization and serving/RTC compatibility. Define starting conditions and complete grasp/placement success, predetermined trial counts, failures and uncertainty separately for each fruit. Do not selectively retry failures or claim >90% reliability from a few trials. Physical evaluation must remain separate from checkpoint selection. Both-fruit distractor selection is not part of the established task scope.

If tomato performance is weak, report that result honestly. Additional collection can be proposed afterward based on failures; it is not an automatic action or prerequisite now. No comparison with an old full-fine-tuned model is required.

## Preserve the completed pilot and rollback

October17 adapter-only pilot completed15k updates and validation in about2h42m. Final combined validation loss0.0442 (5k0.0498;10k0.0448), not physical success. Artifacts: `/home/kiran/sim/pi05-orange-tomato-lora-pilot-20261017/proposed_main_run`. Preserve all checkpoints and [historical handoff](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/MAIN_RUN_HANDOFF.md); do not relaunch that recipe.

Preserve original recordings, existing manifests, all models and reference environments. Rollback stops only newly owned processes and returns to preserved configuration; it does not delete experiments or modify motors. Document dependency/serving reversals before applying changes.

## Immediate next step and historical status

**Execution now proceeds automatically:** finish the running baseline, verify train/evaluate integration and preflight, then run the approved5,000 updates with full held-out evaluation every1,000. The supervisor is already queued; no further routine approval is needed and no duplicate launch should be made. Captured repeat analysis and a repeat-close-comparisons policy account for observed variation without claiming its exact cause or a universal bound. The30-update benchmark averaged3.816s/update over its final20. Additional collection and reconnecting the rig are not prerequisites.

The October18 device snapshot showed only the integrated webcam, no configured arm serial IDs or external cameras; it is historical, not today's live state. Recheck only when physical work is being prepared.

The earlier collection-first plan is preserved in [October18 plan snapshot](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/PLAN_HISTORY_BEFORE_20261019.md); the older chronology is in [earlier archive](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/PLAN_HISTORY_BEFORE_20261018.md). Collection instructions in historical reports are superseded by this19 October decision; their observations remain evidence.
