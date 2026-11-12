# Agent handoff — move robotics work to ryzen9

Updated after gap review: 2026-11-13. Read this first, then [START_HERE](../START_HERE.md).
This is a continuation handoff, not a claim that migration has been executed.

## 1. User objective and current authorization

The user wants all future robotics work on the new workstation, organized simply
and professionally: one project home, one current entry document, traceable
experiments, sensible SSD use and preserved historical work.

The user explicitly said: **“Do not change anything, tell what we are going to do
now. check our new machine.”** We then performed read-only SSH inspection. Later
requests authorized creating/updating the plan documents and this handoff. Those
documentation changes were made on Acer and published to the migration branch.

**Current execution boundary:** the user subsequently authorized sending the handoff
to ryzen9 and checking it for gaps. Updating this handoff and delivering its supporting
documentation is authorized. Read-only inventory and local documentation work may
continue. That does not authorize bulk project/data transfer, software installation,
compression/deletion, service changes, training or robot motion. Obtain an execution
instruction for those steps unless a later user message already supplies it. Do not
ask again for an already authorized action.

**Important new state:** the receiving agent has already produced a transfer manifest
and AI90 package inventory on ryzen9. The first inventory is no longer pending.
Read those records and resolve their open decisions; do not redo them from memory.
They were discovered during this gap review and are attributed below. Their presence
is not evidence that any datasets, model weights or runtime patches were transferred.

## 1a. Receiving-agent documents and location

The handoff was originally copied to `~/Robotics/handoff`. It is now at:

```text
/home/prakash-gaikwad/projects/Robotics/handoff/
  AGENT_HANDOFF_NEW_MACHINE_20261113.md
  TRANSFER_MANIFEST_20261113.md
  AI90_VLASH_ENV_PACKAGES_20261113.txt
```

The first two folder components are **projects/Robotics**, not the previous
`~/Robotics`. We found the original handoff unchanged at this moved location;
its cause of relocation is not established. Preserve this existing tree rather
than creating a second project home. Final code/data placement is still decision
D1 in the manifest; plan examples provisionally follow this existing parent.

The refreshed delivery adds `README.md`, `reference/` and `delivery_manifest.json`
next to these files. The root handoff remains the user-facing entry. In the delivery
copy, Markdown links are adjusted to bundled references or commit-pinned GitHub
pages. The manifest records source commit and source/delivery hashes. This packet
is documentation, not an installed checkout or complete copy of cited trial assets.
Verify the delivery manifest after copying; its contents are the packet's exact scope.

The existing transfer manifest and package list are receiver-owned working records.
Do not overwrite them with an older snapshot. Their inspected SHA-256 hashes were:

```text
TRANSFER_MANIFEST_20261113.md
41bcc36217cdc47f43975abee0037ed8748afb385e95836b4bbaa11be9e8593f
AI90_VLASH_ENV_PACKAGES_20261113.txt
473aa4b58db7e0a8af726377e1a4c563fb7defc99001ae1264027e6495e5da5e
```

They contain source inventories/private paths and a warning about the public GitHub
repository. Keep their raw contents local unless publication is explicitly requested.
Only the continuation-relevant findings are summarized here; missing bulk checksums
and unavailable assets must remain visible.

For conflicting statements, use this gap review for current migration status and
the receiver manifest for its detailed source rows. Its original “everything fits”,
backup and cleanup-date conclusions remain provisional as explained in section 8.
Its old Git commit is superseded by `delivery_manifest.json`; update the working
manifest during the next review, without erasing the original observations.

The user prefers short, concrete explanations. Distinguish “we planned it”, “we
copied it”, “we verified it” and “it runs”. They were specifically confused about
whether the latest project was already on the new computer: **it was not**.

## 2. Where this handoff and code live

| Item                                        | Location / state                                                        |
| ------------------------------------------- | ----------------------------------------------------------------------- |
| Git repository                              | `https://github.com/Gitgai/lerobot.git`                                 |
| Active migration checkout on Acer           | `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot-new-machine`           |
| Active branch                               | `codex/new-machine-migration-20261113`                                  |
| Latest published commit before this handoff | `d47950f34` — original handoff; `39fb65c9e` — plans                     |
| Earlier preparation commit                  | `7162c83bb` — migration guide and preservation audit                    |
| November base branch                        | `codex/record-row-n-20261030`, last verified at `6ac0b1a21`             |
| November checkout on Acer                   | `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot-rowN-record`           |
| October consolidation branch                | `codex/consolidate-fruit-openpi-20261024`, last verified at `641123781` |
| Original installed checkout on Acer         | `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot`                 |
| Legacy chat workspace                       | `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot`                       |

The migration checkout was clean and matched GitHub before writing this handoff.
Inspect current Git status before edits. The delivery manifest pins the exact
revision of this updated packet; it supersedes the historical commit marker above. Read applicable `AGENTS.md` instructions in the checkout.

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
| Project state at initial inspection      | `~/projects` existed and was empty; documentation arrived afterward   |

These are dated observations, not a full software inventory or current health
monitor. NVIDIA driver visibility is not a GPU computation or inference test.
The existing `~/projects/Robotics/handoff` directory contains documentation only.
No runtime installation or hardware-setting change was made by this task. The user
authorized document delivery; SSH may also generate ordinary system access logs.

### Sources

- **Acer:** `gaikwad-prakash-Aspire-A14-52MT`, user `gaikwad-prakash`. Holds local
  environments, calibration, source variants, demonstrations and trial evidence.
  Current locally observed addresses: LAN `192.168.1.24`, ZeroTier `192.168.194.228`.
- **AI90:** historical login `kiran@192.168.194.220`. Holds models, training data and
  GPU runtimes. This originating task has not inspected AI90 directly. The receiving
  agent subsequently reports read-only access from ryzen9 and supplied the inventory
  summarized below. Preserve that provenance; recheck volatile state before execution.

## 4. Planned final layout

```text
/home/prakash-gaikwad/projects/Robotics/
├── handoff/       Existing documentation packet and receiving-agent inventory
├── lerobot/       Planned Git checkout and project docs
├── datasets/      originals/ and derived/
├── models/        base/ and trained/
├── runs/          training/ and trials/
└── archive/       migration/ and completed/
```

Separate environments/caches may use `.envs/` and `.cache/` under Robotics.
This provisionally follows the observed handoff location; confirm manifest D1
before creating the operational tree. It supersedes examples of `~/Robotics` or
`~/projects/lerobot`, which would create competing locations. Calibration stays
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
- Tokenizer assets: receiving manifest identifies AI90 `~/hf-cache-recovered`
  and `~/hf-cache-ft4`; resolve the actual files/config references before an
  offline load. A model checkpoint alone is not the complete inference bundle.
- Deployed server: AI90 `~/latency_probe/so101_base_policy_server.py`, reported
  to differ from the repository copy by a comment. Preserve and compare it along
  with launch arguments, environment variables and preprocessing configuration.
- Runtime source/environment: `/home/kiran/sim/vlash` and
  `/home/kiran/sim/vlash-venv`. Source headers mention VLASH `22cbabfe` plus patches
  and LeRobot 0.4.1. The receiving-agent inventory now records the measured Python
  and package versions and identifies uncommitted patches; the patch files still
  need preservation and checksums.

The separate Acer bench environment was measured as Python 3.12.13, LeRobot 0.5.2,
torch 2.10.0. An older official-client environment uses LeRobot 0.6.1 and torch
2.7.1+cpu. The receiving agent measured **Python 3.11.15 for VLASH**, torch
2.7.1+cu128, torchvision 0.22.1+cu128, LeRobot 0.4.1 and peft 0.18.0. Transformers
4.53.3 came from Git commit `dcddb970176382c0fcf4521b0c0e6fc15894dfe0`.
VLASH was editable at `22cbabfee0f57874987c75a35a7dac129e695db0` plus local changes.
The 122-entry package list is distribution metadata, not a tested reinstall lock.
Only installed files for LeRobot/Transformers/PEFT were reported checked against
package records; the other packages were not checked. Keep **bench Python 3.12**
and **VLASH Python 3.11** separate. GPU compatibility still needs execution testing.

Exact FT4B data identities from the experiment record:

- Acer `~/ft4_corrected_20261110/train29`: 29 entries / 28,494 frames.
- Acer `~/ft4_corrected_20261110/val6`: 6 held-out episodes / 5,907 frames.
- The training set contains 25 orange and four matchbox episodes. Keep validation
  held out; retain rejected original episodes outside training.
- AI90 reportedly trained from `~/lerobot_assets/datasets/ft4_corrected_20261110`;
  compare hashes before deciding that this equals the Acer derivative.
- Preserve checkpoints 003000, 006000 and 009000 with optimizer, scheduler, RNG,
  adapters, configs, base model and tokenizer assets. `checkpoints/last` is reportedly
  a symlink; inventory its target and do not copy a broken pointer.

Hardware identities: follower USB serial `5B14114209`, leader `5B14029688`;
calibration IDs `my_so101_follower` and `my_so101_leader`. Mapping is front →
`observation.images.base_0_rgb`, wrist → `observation.images.left_wrist_0_rgb`,
third model slot masked. Recorded joint order is `shoulder_pan`, `shoulder_lift`,
`elbow_flex`, `wrist_flex`, `wrist_roll`, `gripper`. Preserve angle/gripper normalization and the
reviewed motor protection settings; device enumeration alone is not calibration.
A crashed client does not establish torque-off. Hardware use remains separately supervised.

The experiment's next gate, once separately authorized, is three watched checkpoint
9,000 trials after matching demonstration pose/views/placement; expand to ten only
if at least two acquire and retain the orange. The image-space bounds apply only
to the restored 640×480 framing, not general physical coordinates. Consult
[the geometry diagnosis](../results/so101_bench_20261019/ft4b_gate_offline_diagnostic_20261111/README.md)
and its actual montage assets before moving hardware. Local inference changes
transport timing relative to AI90; record it as a changed variable, not an identical trial.

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

## 8. Inventory findings, unresolved gaps and next deliverable

**Continue the existing `TRANSFER_MANIFEST_20261113.md`.** Its rows are inventoried,
not bulk-checksum-verified, copied, runtime-validated or backed up. The receiving
agent's source observations below have not all been independently repeated here:

| Finding                                                                                                                 | What it changes / remaining verification                                                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AI90 FT4B training, server, evaluation and smoke logs are reportedly in RAM-backed `/tmp` with age cleanup              | Make these small files the first preservation batch once authorized; treat them as ephemeral. Recheck existence/cleanup rules rather than promising an exact deletion date. |
| VLASH has uncommitted changes in `modeling_pi05.py` and `run.py`, plus an upstream comparison copy                      | Preserve patches, originals, hashes and exact base revision before rebuilding; a package list alone is insufficient.                                                        |
| AI90 LeRobot has 7 modified tracked and 55 untracked files; OpenPI has 2 local commits; GR00T/LeIsaac also have changes | Capture source diffs/untracked files and retain commits/refs before choosing exclusions. Do not push to unrelated upstream remotes.                                         |
| The installed Acer checkout contains about 20.3 GiB of ignored artifacts and 0.2 GiB of ignored logs                    | Add these to migration coverage; clean Git status never covered them.                                                                                                       |
| The November checkout contains about 179 MiB of ignored trial frames                                                    | Preserve alongside the committed report; raw evidence is not fully represented in Git.                                                                                      |
| `ft4_reweighted_20261110` is now about 400 MiB                                                                          | Fresh independent check here measured 418,467,840 allocated bytes and 418,092,537 apparent bytes. Earlier 1.8 MiB figure is superseded; retain its rejected status.         |
| Legacy workspace `.git` is reportedly about 46.3 GiB despite no commits                                                 | Snapshot refs/recovery objects exist. Excluding it from transfer is a proposal, not proof it is disposable or permission to delete it.                                      |
| AI90 `/mnt/data4tb` is reportedly absent; checkpoint/probe/cache symlinks point into it                                 | Inventory is incomplete for those targets. Locate/reconnect the drive or explicitly record exclusions; do not claim all historical assets are accounted for.                |
| AI90 transfer sample was 0.02–0.05 MiB/s; roughly 29 GiB of FT4B essentials                                             | Resolve the transport plan before bulk copying; relay diagnosis is unconfirmed. Do not change network settings from a guess.                                                |
| Approximately 1.4 TiB of accessible robotics assets is reported                                                         | Provisional size only: account for overlap, hardlinks, missing drive, temp copies and verification space before accepting the fit.                                          |
| Independent backup is not established                                                                                   | Historical Acer backup exists in records but is not a verified current restore point. Do not retire sources.                                                                |

Receiver-created manifest recommendations to skip virtual environments, snapshot
objects or historical checkpoints are **not settled retention decisions**. The audit
excluded environment trees, and only some installed packages were compared. Capture
patched sources, lock/provenance data and unique recovery history before excluding
anything. Full hashes are still pending for the bulk datasets and checkpoints.
Do not duplicate every hardlinked/cached model blindly, and do not infer whole-file
identity from partial hashes.

Next deliverable: a reviewed manifest amendment and a concrete first-batch proposal:

1. Reconcile source coverage with the new ignored-artifact, patch, log and missing-drive
   findings. Preserve existing manifest rows/notes; avoid starting a competing inventory.
2. Propose the small ephemeral-log/patch/calibration/source-snapshot batch first.
   Source copying is still pending execution authorization; updating the handoff
   packet does not authorize it.
3. Resolve D1 (operational project root), D2 (AI90 transport), D3 (missing drive),
   D4 (historical checkpoint retention), D5 (backup destination), D6 (large Acer
   transfer connection) and D7 (agent-history retention/privacy) from the manifest.
4. Confirm the frozen dataset/base/checkpoint dependency set and a byte budget.
   Recheck changing paths, current branches and source writers immediately before copying.
5. After execution authorization, copy to a fresh staging destination without deletion,
   compare complete file hashes and metadata, preserve links/targets deliberately,
   then run offline and supervised acceptance gates. Retain partial transfers and
   report failures; do not overwrite source originals or stop unrelated AI90 workloads.

Each row must retain source host/path, destination, provenance, exact units for size,
checksum state, dependency/retention notes and the separate states `inventoried`,
`copied`, `checksum_verified`, `runtime_validated`, `backed_up`.

### Connectivity from the receiving agent

Acer → ryzen9 key authentication was directly verified by this task. The receiving
manifest reports ryzen9 → Acer and ryzen9 → AI90 inspection, but this task did not
install reverse keys or test those sessions itself. From the relevant host, use
existing authentication for `gaikwad-prakash@192.168.1.24` (or ZeroTier `.228`)
and `kiran@192.168.194.220`; LAN addresses may change. Do not copy private keys,
invent credentials or assume a known-host entry exists on a different host. If access
fails, record the failure and continue independent local review. The GitHub repository
is reported public by the receiving manifest; do not publish the private raw inventory,
credentials or agent conversation histories merely to make them portable.

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

## 10. Handoff acceptance checklist

- Correct receiving folder located; receiver-owned manifest and package inventory retained.
- Current authorization distinguishes documentation delivery from bulk execution.
- Bench and GPU Python versions separated; source patches and temporary logs identified.
- Original data, ignored artifacts, recovery refs, symlink targets and backups covered explicitly.
- Existing transfer manifest is the next agent's starting point; open decisions remain visible.
- Bundled document links resolve, unbundled references use a pinned repository revision,
  and remote bytes match the delivery manifest. The packet does not claim to contain
  models, datasets, calibration secrets, the private source snapshot or all trial assets.

Completeness here means the known gaps have owners and next checks. It is not a
claim that missing drives, full checksums, network throughput, backups or model
compatibility have already been resolved.
