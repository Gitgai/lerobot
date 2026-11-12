# New machine setup — SO-101 project

Updated: 2026-11-13. Read-only SSH inspection of ryzen9 completed; software migration
and runtime validation are pending. This guide replaces the August RunPod setup. The receiving agent has since added
a transfer inventory and AI90 package list; [the current handoff](docs/AGENT_HANDOFF_NEW_MACHINE_20261113.md)
records their findings and unresolved decisions.
Start with [START_HERE](START_HERE.md), the [workstation plan](docs/WORKSTATION_PLAN_20261113.md)
and [SSD policy](docs/SSD_STORAGE_POLICY_20261113.md).
The original is retained in [history](docs/history/NEW_MACHINE_SETUP_before_20261113.md).

## 1. What we are moving, and what is still unknown

The new workstation is now available. The “PC Build Analysis” conversation reported
these parts; they are not a live hardware inspection:

| Component         | Reported hardware                         |
| ----------------- | ----------------------------------------- |
| CPU               | AMD Ryzen 9 9950X                         |
| GPU               | NVIDIA RTX PRO 5000 Blackwell, 72 GB      |
| RAM               | G.Skill Flare X5, 32 GB total (2 × 16 GB) |
| Storage           | WD Blue SN5100, 4 TB                      |
| Motherboard       | ASUS ProArt B850-CREATOR WIFI NEO         |
| Additional camera | Luxonis OAK-D Lite AF                     |

Read-only SSH inspection confirmed:

- Host `ryzen9`, user `prakash-gaikwad`, Wi-Fi `192.168.1.23`, ZeroTier `192.168.194.23`.
- Ubuntu 26.04.1 LTS, kernel `7.0.0-43-generic`; Ryzen 9 9950X, 16 cores/32 threads.
- RTX PRO 5000 Blackwell 72 GB, driver `595.99.02`; no compute jobs at inspection.
- About 29 GiB usable RAM, 8 GiB swap; WD Blue SN5100 4 TB with about 3.4 TiB available.
- C270 camera detected. No arm serial devices or wrist camera were detected.
- Git and rsync installed; system Python 3.14.4. No uv/Python 3.12 found in inspected
  standard locations; no torch/lerobot/cv2 in system Python. Calibration absent;
  user not in dialout. The inspected `~/projects` directory was empty.

No software, driver or permission changes were made on ryzen9 by this task.
Handoff/reference documentation has been delivered; the receiving agent added
its own manifest/package list. No bulk project data or installed runtime is implied. GPU computation,
checkpoint loading, camera capture and robot operation have not been tested.
Motherboard/RAM-kit/OAK-D details in the reported-parts table were not independently
verified by this inspection.

Do not substitute the OAK-D for a trained front/wrist view during migration;
that is a separate camera integration and validation task.

There are three machine roles:

- **Acer source:** `gaikwad-prakash-Aspire-A14-52MT`; robot/camera integration,
  demonstrations, local client environments and trial evidence.
- **AI90 source:** historically `kiran@192.168.194.220`; GPU environments,
  model checkpoints and training data. Its connectivity and contents were not
  rechecked directly by this originating task. The later receiving-agent manifest
  reports a read-only inventory; distinguish that evidence from runtime validation.
- **New workstation (ryzen9):** planned primary home for daily robotics work, subject
  to hardware, memory and runtime validation. A 72 GB GPU does not establish
  that the 32 GB system RAM can run every training recipe.

## 2. Current project state

The latest reviewed record is the [FT4B execution plan](docs/fine_tune_4_execution_plan_20261108.md),
including the November 11 geometry diagnosis. The corrected 9,000-step run
completed, but checkpoint 9,000 scored **0/3** in the watched physical gate.
The diagnosis found mismatched starting pose, fruit placement and camera geometry.
This checkpoint is a diagnostic candidate, not a proven reliable deployment.

The November runtime uses **VLASH π0.5**, with
[`so101_base_policy_server.py`](scripts/so101_base_policy_server.py).
The older October OpenPI fruit work and September GR00T/LeRobot π0.5 work have
separate environments and evidence. Do not combine their install recipes,
checkpoint formats, action conventions, or success rates.

November recorded deployment contract:

- Instruction: `pick up the orange and place it on the plate`.
- Two 640×480 views: front and wrist; preserve their mounting and framing.
- Server mapping: front → `observation.images.base_0_rgb`, wrist →
  `observation.images.left_wrist_0_rgb`; the third model slot is masked.
- Six-joint order: shoulder_pan, shoulder_lift, elbow_flex, wrist_flex,
  wrist_roll, gripper. Preserve the existing units and normalization.
- Last watched gate: 20 executed actions per request at 30 Hz, 75-request cap,
  server `192.168.194.220:8081`. These describe a past run, not a command to launch.
- The next physical comparison must reproduce the demonstration geometry and
  use the decision gates in the FT4B plan. Migration itself does not validate motion.

## 3. Get the correct code

The source-controlled project is `https://github.com/Gitgai/lerobot.git`.
A default clone of `main` does not contain all November work.

| Branch verified on GitHub on November 13  | Commit before this migration | Purpose                                                |
| ----------------------------------------- | ---------------------------- | ------------------------------------------------------ |
| `codex/record-row-n-20261030`             | `6ac0b1a21`                  | Latest November records and scripts                    |
| `codex/consolidate-fruit-openpi-20261024` | `641123781`                  | October preservation and integration work              |
| `main`                                    | `f8eb9ed57`                  | Published main; 153 commits behind the November branch |

Use the migration branch, which starts from the November branch and adds this guide:

```bash
# On the new machine, in an unused destination directory:
mkdir -p ~/projects/Robotics
cd ~/projects/Robotics
git clone --branch codex/new-machine-migration-20261113 \
  https://github.com/Gitgai/lerobot.git lerobot
cd lerobot
git status --short --branch
git log -1 --oneline
```

Keep the October branch reachable. It contains five commits absent from the
November history, including selected OpenPI migration work. This guide does not
merge those changes into the November runtime. The preservation audit identifies
the separate refs and compares against both.

The original checkouts have machine-specific runtime paths. A new checkout under
`~/projects/Robotics/lerobot` is the planned destination, not proof that old launchers will
work there. Many contain `/home/gaikwad-prakash` or `/home/kiran` paths.

## 4. Verify the new machine before choosing an install recipe

From the cloned repository:

```bash
bash projects/testproject/scripts/collect_machine_profile.sh \
  "$HOME/new-machine-profile-20261113"
```

The collector only reads host, OS, GPU, storage and USB facts. It creates a private
output directory and refuses to overwrite an existing one. Missing tools/devices
are recorded in `status.txt`; the script finishing is not a readiness pass.
It does not install drivers, open cameras or serial devices, or load a policy.

Check the actual OS release, GPU name/VRAM/driver, system RAM, storage and serial
permissions. Select an NVIDIA/PyTorch build only after these facts are known and
validate GPU execution with a small tensor operation in the chosen GPU environment.
Do not copy the August instruction to install CPU-only PyTorch for the GPU server.

## 5. Preserve the source before moving it

Read [the November preservation audit](docs/NEW_MACHINE_PRESERVATION_AUDIT_20261113.md).
The old chat workspace occupies approximately **367 GiB allocated**. It contains
large recordings and environments as well as source files. It has no commits or
remote; selected copies elsewhere in Git do not establish that everything is saved.

Essential transfer groups:

| Source                                                                                | What must survive                                                             |
| ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Both Git branches above                                                               | Code, reviewed records and separate consolidation changes                     |
| `~/Documents/ChatGPT/Lerobot/` on Acer                                                | Unreconciled sources/docs plus original trial evidence                        |
| `~/.cache/huggingface/lerobot/calibration/` on Acer                                   | Both physical arms' calibration; preserve IDs and hashes                      |
| `~/orange_grasp_corrective_ft4_20261108/`, `~/matchbox_pickplace_ft4_20261108/`       | Original demonstrations, including rejected attempts and review metadata      |
| `~/ft4_datasets_20261108/`, `~/ft4_corrected_20261110/`, `~/ft4_reweighted_20261110/` | Distinct derivatives; rejected/reweighted data is not an approved replacement |
| `~/runs/`, `~/so101_trials/`, `~/bench_trace_*`, other trial folders                  | Raw images, action/state traces, manifests and cleanup evidence               |
| Custom `~/*.py` and `~/*.sh` bench scripts                                            | Installed launchers may differ from repository records                        |
| AI90 `/home/kiran/lerobot_assets/`                                                    | Models, training outputs, data, configurations and resumable state            |
| AI90 `/home/kiran/sim/vlash`, `/home/kiran/sim/vlash-venv`                            | Exact VLASH source, patches and dependency provenance                         |

This is a migration priority list, not a full-home backup inventory. The old
[August backup manifest](BACKUP_MANIFEST.md) describes historical paths and sizes.
Re-inventory AI90 and external mounts before transfer, including symlink targets.
For FT4B preserve the full
`/home/kiran/lerobot_assets/training/ft4b_orange_corrected_20261110` tree and its
base `/home/kiran/lerobot_assets/ckpt_mirror/row3_all169_conservative_010000`,
not just `pretrained_model`: optimizer, scheduler, RNG and adapter state matter
for resuming training.

A checked local source/calibration snapshot was prepared on Acer; see the audit.
It is on the **same disk** and excludes bulk evidence. It is not an independent
backup and does not make source deletion safe.

The destination login is verified; final paths follow the workstation plan. After
reviewing the transfer manifest and space budget, use a new staging directory
and a resumable transfer. The example below illustrates a dry-run copy; these
commands have not been executed, and even its mkdir creates destination folders:

```bash
DEST='prakash-gaikwad@192.168.1.23'
ssh "$DEST" 'mkdir -p ~/projects/Robotics/archive/migration/acer-workspace'
rsync -aHn --itemize-changes \
  "$HOME/Documents/ChatGPT/Lerobot/" \
  "$DEST:projects/Robotics/archive/migration/acer-workspace/"
# Review the destination and capacity; then repeat without -n.
```

No `--delete` is needed. This whole-workspace example includes environments for
preservation; they must not be treated as portable installed environments. Resolve
external symlink targets separately. Verify transferred files with a checksum
comparison (`rsync -aHnc --itemize-changes` using the same paths) while source
writers are stopped; no differing regular files should remain. Open representative
recordings and datasets on the destination. Verify calibration JSON hashes exactly.
Keep the source until evidence and runtime checks pass.

## 6. Rebuild separate environments from evidence

Local metadata captured on November 13:

| Role                  | Existing interpreter                                               | Measured packages                                                                           |
| --------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Acer bench/recording  | `~/PrakashProjects/lerobot/lerobot/.venv/bin/python`               | Python 3.12.13, LeRobot 0.5.2, torch 2.10.0, Rerun 0.26.2                                   |
| Older official client | `~/Documents/ChatGPT/Lerobot/.venv-official-client-061/bin/python` | Python 3.12.13, LeRobot 0.6.1, torch 2.7.1+cpu                                              |
| November GPU policy   | AI90 `/home/kiran/sim/vlash-venv`                                  | Receiver reports Python 3.11.15, torch 2.7.1+cu128, LeRobot 0.4.1, patched VLASH `22cbabfe` |

Package metadata is provenance, not a complete lockfile. The full local package
lists are captured with this audit. The receiving agent has now captured AI90
Python/package metadata and source revision; preserve the identified uncommitted
patches and verify the full dependency closure before rebuilding. Preserve any patched dependency files inside the old environments.
Do not infer that a clean project Git checkout also covers those patches.

The current repository's `pyproject.toml` is not the historical VLASH environment.
Blindly running a latest dependency install can produce an incompatible server.
Keep bench, VLASH and optional OpenPI environments separate. On the new machine,
verify imports resolve to the intended source, then test recorded observations
without a robot connection. Exact installation commands remain pending source-patch preservation,
dependency reconstruction and compatibility checks; this document does not claim a
rebuild has been tested.

## 7. Reconnect the existing rig

- Copy calibration for the same physical arms before enabling torque. Existing
  IDs are `my_so101_follower` and `my_so101_leader`. Recalibration is a separate
  action if the hardware or calibration identity has changed.
- Resolve USB serials, not `/dev/ttyACM0` numbering: follower `5B14114209`,
  leader `5B14029688`. Verify the actual destination paths.
- Current records describe Logitech C270 **front** and USB OV4689/AK-Camera
  **wrist**. The August Pi wrist proxy, laptop front camera and three-camera
  instructions are historical, not the November default.
- Match camera images to the saved demonstration reference montages, not merely
  image dimensions. November's diagnosis shows why the starting wrist roll and
  mounting geometry are part of the model's input conditions.
- Audit hardcoded home directories, Python paths, calibration locations, model
  paths, ports and Rerun executable paths before reusing any launcher. Setting
  only `LEROBOT_PYTHON` does not update the other hardcoded paths.

## 8. Completion gates

1. Source refs retained; source/calibration snapshot and bulk data verified on a
   separate destination. Unmatched files resolved or explicitly retained.
2. Machine profile reviewed; correct GPU available; enough system RAM/storage
   for the selected workload; chosen environment passes import and GPU checks.
3. Checkpoint and preprocessing verified against saved observations without
   hardware, including finite outputs, joint order, units and image mappings.
4. Camera images and calibration verified, with device identities and permissions
   recorded. Motor state checked using the reviewed runtime without changing settings.
5. A separately supervised physical test follows the current FT4B plan and
   demonstrates stop/cleanup and torque-off readback. An exited process alone
   is not proof that torque is off.

**Current completion:** guide, local inventory and source/calibration snapshot
prepared, and destination hardware/OS inspected over SSH. Destination transfer,
AI90 patch preservation, installation and hardware
validation remain pending. The receiving-agent metadata inventory is available. No new model, server, training job or robot motion was
started by this migration preparation.
