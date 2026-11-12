# Workstation organization and migration plan

Updated: 2026-11-13. User decision: daily robotics work will move to ryzen9.
Status: documentation and read-only machine inspection complete; transfers and
installation are pending. This revision changes documentation only.

## 1. One project home

Use `/home/prakash-gaikwad/Robotics` on ryzen9. This supersedes the earlier proposed
`~/projects/lerobot` destination; no existing repository has been relocated.

```text
~/Robotics/
├── lerobot/                 Git checkout: code, configuration, docs, small reviewed results
│   └── projects/testproject/START_HERE.md
├── datasets/
│   ├── originals/           Unmodified demonstrations and their metadata
│   └── derived/             Versioned training/validation derivatives
├── models/
│   ├── base/                Pinned base-model revisions and their dependencies
│   └── trained/             Named checkpoints and full resumable training state
├── runs/
│   ├── training/            Training configurations, logs and evaluation results
│   └── trials/              Images, observations, actions, videos and cleanup evidence
└── archive/
    ├── migration/           Incoming source copies, manifests and unresolved variants
    └── completed/           Cataloged historical experiments, optionally compressed
```

Environment directories and download caches are implementation details, kept outside
Git under `~/Robotics/.envs` and `~/Robotics/.cache` where the relevant tools support
explicit paths. Those locations are planned, not configured. Keep separate bench,
VLASH and optional OpenPI environments. Do not move a live environment by renaming it.

The installed robot calibration must remain at the paths required by the validated
loader, initially `~/.cache/huggingface/lerobot/calibration/`. Preserve a private
backup separately. Never treat this calibration directory as disposable cache.
Credentials stay in the user's normal private credential stores, outside Git.

## 2. Roles during and after the move

| Location                       | During migration                                                     | After verified handover                                                |
| ------------------------------ | -------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| ryzen9                         | Destination and offline validation machine                           | Main workstation for code, recording, training, inference and review   |
| Acer                           | Source of bench code, calibration, demonstrations and trial evidence | Retained source/recovery copy; no new daily experiment work by default |
| AI90                           | Source of checkpoints, datasets, GPU environments and patches        | Retained source/recovery copy; workload exceptions recorded explicitly |
| GitHub                         | Version history for code, configuration and documentation            | Continue using the same repository                                     |
| Independent backup destination | Must be identified and capacity-checked                              | Protect unique data and models; not another folder on ryzen9's SSD     |

The previous Acer external backup is historical evidence, not a verified current
backup of November datasets or future ryzen9 work. Confirm destination identity,
capacity, checksums and restore behavior before counting it as protection.

## 3. Move in reviewable batches

| Phase            | Work                                                                                                               | Completion evidence                                             | Current state                                                      |
| ---------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------ |
| A — inventory    | Enumerate required sources on Acer and AI90, branch refs, runtime patches, symlink targets, sizes and dependencies | Transfer manifest with every required item assigned             | Acer workspace audit done; AI90 and broader home inventory pending |
| B — preserve     | Copy calibration, source snapshot, current code and essential datasets/checkpoints to staging                      | Content hashes match; originals retained                        | Pending                                                            |
| C — organize     | Place verified files in final locations; retain unresolved variants in migration archive                           | Catalog resolves every active dataset/model/run to one location | Pending                                                            |
| D — rebuild      | Recreate bench and VLASH environments using captured versions/patches                                              | Imports, GPU computation and saved-observation inference pass   | Pending                                                            |
| E — validate rig | Verify calibration, devices, camera geometry and reviewed launch paths                                             | Documented readiness and supervised test evidence               | Pending                                                            |
| F — handover     | Update working commands and current pointers; verify independent backup                                            | START_HERE matches actual paths and tested commands             | Pending                                                            |

Start with the current FT4B project. Then inventory and transfer remaining historical
robotics assets in batches. “All work on ryzen9” does not require every old runtime
to be installed or every archive to remain unpacked. No unreviewed variant replaces
active code merely because its timestamp is newer.

Each manifest entry must record: source host and absolute path, artifact role,
logical/allocated size, required base model or dataset lineage, destination path,
copy status, source/destination checksum results, and validation/backup status.
Use states `inventoried`, `copied`, `checksum_verified`, `runtime_validated` and
`backed_up`; do not conflate them. The manifest itself has not yet been populated
for the complete project.

First required sources:

- Acer source/calibration snapshot and the two preserved project branches.
- Original orange and matchbox FT4 demonstrations, accepted/rejected episode records,
  and the exact FT4B training/validation derivatives. Retain original data.
- AI90 FT4B checkpoints 003000/006000/009000, the base checkpoint and all required
  tokenizer/configuration/normalization artifacts; retain full resume state.
- AI90 VLASH sources, exact Git revision, local patches and dependency inventory.
- Raw trial evidence associated with the latest diagnosis and the November reference views.

Older OpenPI, GR00T, simulation and unrelated machine projects have separate inventory
rows. They are not silently merged into the FT4B runtime. Source host-wide backups
must not be copied into the robotics checkout as though they were project code.

## 4. Clear experiment records

Use IDs such as `20261113_143000_ft4b_geometry_trial01`; include enough date/time
and a suffix to avoid collisions. Never overwrite a previous run.

Every run records the Git commit and dirty state, environment identity, model
revision/hash and base dependency, dataset version/split, exact instruction,
configuration, start/end time, evidence paths, outcome and failure/stop reason.
Physical trials additionally record calibration identity, camera mapping, starting
pose, observations/actions and cleanup/torque readback. Training records preserve
seed, optimizer/scheduler, checkpoints and resume state.

Store checkpoints once under `models/trained/<experiment>/`. A run points to that
location; it does not keep another convenience copy of the same weights. Catalog
entries pin revisions/hashes. A `current` label may be added later for convenience,
but run provenance always resolves to an immutable version.

Keep `originals` unchanged. Derived datasets name their source versions, processing
recipe, rejected episodes and train/validation split. Human-review videos may be
smaller copies; they never silently replace training data or exact evidence.

## 5. Git and navigation

- Primary entry point: [`START_HERE.md`](../START_HERE.md).
- Current preparation branch: `codex/new-machine-migration-20261113`, based on
  November branch `codex/record-row-n-20261030` at `6ac0b1a21`.
- Retain `codex/consolidate-fruit-openpi-20261024`; its five separate commits still
  need reconciliation. Do not imply that the branches are already merged.
- Keep bulk data, checkpoints, virtual environments, caches and credentials outside
  the code checkout. Review Git ignore rules before any new recording workflow.
- Update the current experiment ledger after a run and START_HERE after a decision
  changes. Avoid creating competing documents each claiming to be current.

## 6. Storage and readiness

Follow [the SSD storage policy](SSD_STORAGE_POLICY_20261113.md): keep working space
available, test compression on copies, and verify an independent backup. Thresholds,
retention reviews and the weekly review routine are proposed operating rules;
no scheduler, deletion policy or recorder guard has been installed.

Future GPU installation choices must use the inspected host and captured AI90
runtime. The new GPU being recognized is not proof that the model can run or that
32 GB of system RAM is sufficient for every training recipe. Validate the intended
workload before planning large training runs.
