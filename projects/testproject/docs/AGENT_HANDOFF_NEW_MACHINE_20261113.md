# Agent handoff — move robotics work to ryzen9

Prepared: 2026-11-13. Read this first, then [START_HERE](../START_HERE.md).
This is a continuation handoff, not a claim that migration has been executed.

## 1. User objective and current authorization

The user wants all future robotics work on the new workstation, organized simply
and professionally: one project home, one current entry document, traceable
experiments, sensible SSD use and preserved historical work.

The user explicitly said: **“Do not change anything, tell what we are going to do
now. check our new machine.”** We then performed read-only SSH inspection. Later
requests authorized creating/updating the plan documents and this handoff. Those
documentation changes were made on Acer and published to the migration branch.

**Current execution boundary:** continue read-only inventory and document preparation.
No transfer, installation, directory creation on ryzen9, compression, deletion,
service change, training or robot motion has been executed or newly authorized by
the documentation requests. Before starting those steps, obtain the user's execution
instruction unless their next message already gives it. Do not ask again for an
action clearly authorized in a later message. Never treat historical run commands
or earlier unrelated cleanup approvals as authorization for a new run.

The user prefers short, concrete explanations. Distinguish “we planned it”, “we
copied it”, “we verified it” and “it runs”. They were specifically confused about
whether the latest project was already on the new computer: **it was not**.

## 2. Where this handoff and code live

| Item                                        | Location / state                                                        |
| ------------------------------------------- | ----------------------------------------------------------------------- |
| Git repository                              | `https://github.com/Gitgai/lerobot.git`                                 |
| Active migration checkout on Acer           | `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot-new-machine`           |
| Active branch                               | `codex/new-machine-migration-20261113`                                  |
| Latest published commit before this handoff | `39fb65c9e` — workstation organization and SSD policy                   |
| Earlier preparation commit                  | `7162c83bb` — migration guide and preservation audit                    |
| November base branch                        | `codex/record-row-n-20261030`, last verified at `6ac0b1a21`             |
| November checkout on Acer                   | `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot-rowN-record`           |
| October consolidation branch                | `codex/consolidate-fruit-openpi-20261024`, last verified at `641123781` |
| Original installed checkout on Acer         | `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot`                 |
| Legacy chat workspace                       | `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot`                       |

The migration checkout was clean and matched GitHub before writing this handoff.
Inspect current Git status before edits; the handoff's own commit will follow the
commit above. Read applicable `AGENTS.md` instructions in the checkout.

The November branch was 153 commits ahead of GitHub main (`f8eb9ed57`) when checked.
The October branch contains five commits absent from the November history. Both
are preserved on GitHub; they are **not merged together**. Do not clone default main
and assume it contains all current work. No main-branch merge is part of this handoff.

The legacy chat workspace has no commits, no tracked files and no configured remote.
Its clean project counterparts do not imply that all its contents are in Git.

## 3. Machine access and verified facts

### New workstation — destination

```bash
# From Acer; existing public-key authentication was verified:
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes \
  prakash-gaikwad@192.168.1.23
```

The user ran `ssh-copy-id` and added the Acer's existing Ed25519 public key.
Do not request the password again or copy private keys into the project. Authentication
from another host is not established by the successful Acer connection.

Observed through read-only commands during this task:

| Fact                                     | Observation                                                           |
| ---------------------------------------- | --------------------------------------------------------------------- |
| Host / user                              | `ryzen9` / `prakash-gaikwad`                                          |
| LAN / ZeroTier                           | `192.168.1.23` on Wi-Fi / `192.168.194.23`                            |
| OS / kernel                              | Ubuntu 26.04.1 LTS / `7.0.0-43-generic`                               |
| CPU                                      | AMD Ryzen 9 9950X, 16 cores / 32 threads                              |
| GPU / driver                             | NVIDIA RTX PRO 5000 Blackwell 72 GB / `595.99.02`                     |
| GPU state at inspection                  | 32°C, about 18 MiB used, no compute processes                         |
| RAM / swap                               | About 29 GiB usable, 18 GiB available at inspection / 8 GiB swap      |
| SSD                                      | WD Blue SN5100 4 TB; ext4 root; about 3.4 TiB available               |
| Python                                   | System Python 3.14.4                                                  |
| Present tools                            | Git 2.53.0, rsync                                                     |
| Not found in inspected paths/environment | uv, Python 3.12, ffmpeg, v4l2-ctl; torch/lerobot/cv2 in system Python |
| Rig                                      | C270 detected; no arm serial devices or wrist camera detected         |
| Calibration / permissions                | Expected calibration directory absent; user not in dialout            |
| Project state                            | `~/projects` existed and was empty; no project copied by this task    |

These are dated observations, not a full software inventory or current health
monitor. NVIDIA driver visibility is not a GPU computation or inference test.
The new `~/Robotics` folders are planned, not created. No remote system changes
were made by this task; SSH itself may generate ordinary system access logs.

### Sources

- **Acer:** `gaikwad-prakash-Aspire-A14-52MT`, user `gaikwad-prakash`. Holds local
  environments, calibration, source variants, demonstrations and trial evidence.
- **AI90:** historical login `kiran@192.168.194.220`. Holds models, training data and
  GPU runtimes. It was **not contacted or re-inventoried in this migration task**.
  Recheck access and paths; do not claim its contents or services are currently ready.

## 4. Planned final layout

```text
/home/prakash-gaikwad/Robotics/
├── lerobot/       Git checkout and project docs
├── datasets/      originals/ and derived/
├── models/        base/ and trained/
├── runs/          training/ and trials/
└── archive/       migration/ and completed/
```

Separate environments/caches may use `.envs/` and `.cache/` under Robotics.
This supersedes the earlier proposed `~/projects/lerobot` path. Calibration stays
at the path expected by the validated loader, initially
`~/.cache/huggingface/lerobot/calibration/`, with a separate private backup.
Do not clear that directory as disposable cache. Audit all absolute Acer/AI90 paths
before launching copied scripts; changing only the Python executable is insufficient.

## 5. Current robotics experiment

The latest recorded work is **VLASH π0.5 FT4B**, not the older October OpenPI fruit
stack. The 9,000-step training run completed; checkpoint 9,000 scored **0/3** in
its watched physical gate. November 11 analysis identified mismatched starting
wrist roll, camera geometry and fruit placement. This is not a reliable deployed
policy and moving computers does not fix the experiment automatically.

Read [the FT4B execution plan](fine_tune_4_execution_plan_20261108.md) for the
next experimental gate and reference views. Preserve:

- Exact task: `pick up the orange and place it on the plate`.
- Two 640×480 views, front and wrist. Do not substitute the newly purchased
  OAK-D camera for a trained view during migration.
- Last watched gate settings: 20 actions/request, 30 Hz, 75-request cap, AI90
  port 8081. Historical evidence only; not a current launch instruction.
- Full FT4B training output on AI90:
  `/home/kiran/lerobot_assets/training/ft4b_orange_corrected_20261110`.
- Base dependency:
  `/home/kiran/lerobot_assets/ckpt_mirror/row3_all169_conservative_010000`.
- Runtime source/environment: `/home/kiran/sim/vlash` and
  `/home/kiran/sim/vlash-venv`. Source headers mention VLASH `22cbabfe` plus patches
  and LeRobot 0.4.1; live versions and modifications still need capture.

The separate Acer bench environment was measured as Python 3.12.13, LeRobot 0.5.2,
torch 2.10.0. An older official-client environment uses LeRobot 0.6.1 and torch
2.7.1+cpu. Do not combine these into one blind latest-version installation.

## 6. Preservation already completed

Acer workspace audit:

- About 367 GiB allocated; 630,648 regular files inventoried outside excluded trees.
- 1,214 selected source/doc/config files hashed: 45 exact committed matches,
  1,169 non-exact files needing review; 214 have same-name candidates.
- Non-exact does not mean wholly missing from Git: formatting, renamed/adapted
  versions and historical commits require review. No originals were deleted.
- Twenty environment/cache/vendor trees were excluded and symlinks were not followed.
  The audit is not a complete machine backup or dependency-patch inventory.

Private same-disk snapshot on Acer:

```text
/home/gaikwad-prakash/Documents/ChatGPT/migration-audit-20261113/
  source-and-calibration-snapshot.tar.gz
  source_inventory.jsonl
  summary.json
  snapshot_verification.json
  bench-packages.json
  official-client-061-packages.json
```

Archive: 4,971,242 bytes, mode 0600; 1,292 entries comprising 1,214 selected
workspace files, 76 home scripts and both calibration files, plus its manifest.
All file hashes were read back and checked. Archive SHA-256:

```text
1b3023500801b239bf5225fc352684384b109f18912d8c25736e7722291303ec
```

This snapshot is on the **same Acer SSD**, excludes bulk evidence/environments,
and has not been transferred to ryzen9. It is not an independent backup.
The source archive is private and is not committed to Git.

Acer original datasets needing inventory/transfer include
`~/orange_grasp_corrective_ft4_20261108`, `~/matchbox_pickplace_ft4_20261108`,
`~/ft4_datasets_20261108`, `~/ft4_corrected_20261110` and
`~/ft4_reweighted_20261110`. Keep the rejected/reweighted derivative distinct from
the approved corrected recipe. Also inventory `~/runs`, `~/so101_trials`,
`~/bench_trace_*` and the large legacy workspace recording directories.

## 7. SSD decisions already documented

Follow [the storage policy](SSD_STORAGE_POLICY_20261113.md), rather than inventing
a competing cleanup plan:

- Target 750 GiB available; below 500 GiB do not start new bulk work until space
  is reviewed. These are proposed operating rules, not installed guards.
- Budget full temporary/output space and concurrent jobs; inventory AI90 before
  asserting that all historical assets fit.
- Finished text logs are good candidates for lossless archives. Test new/weakly
  compressed PNGs on copies with full image and metadata verification.
- Preserve active datasets/checkpoints directly loadable; do not quantize models,
  drop frames or replace original data with lossy review videos to save space.
- Historical PNG jobs already saved about 225 GiB. Do not count those savings again.
- No compression, automatic cleanup, recorder modification or monitoring automation
  was enabled. Archive-on-the-same-disk is not backup.
- Identify an independent backup destination. The old external Acer backup was not
  fully reconciled and is not established as a current November restore point.

## 8. Next agent's first deliverable

Prepare a **complete source-to-destination transfer manifest**, using read-only
inspection of Acer and, if reachable, AI90. Do useful inventory before asking for
information already available in files or tools. If AI90 is unreachable, record
that gap and continue the Acer inventory instead of treating the whole plan as blocked.

For each required artifact record source host/path, role, size, checksum or pending
checksum status, base dependencies, proposed final/staging path, copy/validation/
backup state and retention notes. Keep states distinct: `inventoried`, `copied`,
`checksum_verified`, `runtime_validated`, `backed_up`.

Order the eventual execution batches:

1. Source/calibration snapshot, branch refs and current code.
2. Accepted original FT4 demonstrations and exact train/validation derivatives.
3. FT4B checkpoints and base dependencies, full resume state and runtime provenance.
4. Latest trial evidence and geometry references.
5. Remaining historical work in measured batches, preserving unresolved variants.

Present the concrete batch sizes/paths and unresolved dependencies to the user.
Wait for an execution instruction before destination writes under the current
boundary. Once authorized, transfer into a fresh staging area, verify content,
rebuild environments, test saved observations, and only then plan supervised rig
validation. Do not stop existing AI90 services or launch models just to inventory them.

## 9. Navigation and validation

Read in this order:

1. [START_HERE](../START_HERE.md).
2. [Workstation plan](WORKSTATION_PLAN_20261113.md).
3. [Setup guide](../NEW_MACHINE_SETUP.md).
4. [Preservation audit](NEW_MACHINE_PRESERVATION_AUDIT_20261113.md).
5. [SSD policy](SSD_STORAGE_POLICY_20261113.md).
6. [FT4B experiment record](fine_tune_4_execution_plan_20261108.md).

Earlier documentation changes passed scoped pre-commit checks, secret scanning and
local-link checks. The audit helper passed temporary SHA-1/SHA-256 fixture checks;
the profile helper was tested on Acer, not installed on ryzen9. No full-repository
CI, destination runtime validation or model test is implied by those checks.

Preserve historical documents as history. Update the existing current pages when
facts change and leave a precise status at the end of each phase. The user should
never need to search several conversations to understand what is actually ready.
