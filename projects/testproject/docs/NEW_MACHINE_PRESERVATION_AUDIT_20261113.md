> **Follow-up:** The destination was subsequently inspected over SSH without changes. Its verified facts and the updated migration/storage plan are in [START_HERE](../START_HERE.md). The audit below preserves the state at the original inventory; statements that the login/profile were pending are historical. Transfer and runtime validation remain pending.

# New-machine preservation audit — 2026-11-13

This audit was performed on `gaikwad-prakash-Aspire-A14-52MT`. It prepares a
migration; it does not establish that the new workstation has been installed or
that all project data has an independent backup.

## Results

- The legacy chat workspace has **zero tracked files, no commits and no remote**.
  `git status` reported 451 untracked entries with directories collapsed.
- Allocated space for that workspace was **367 GiB** (`du -sh`). The source scan
  inventoried 630,648 regular files / 338,943,409,842 logical bytes outside its
  excluded trees. These are different measurements; do not add them together.
- **1,214** small source/document/configuration files were hashed (33,790,409 bytes).
  **45** have byte-identical committed copies in the three refs inspected.
  **1,169** do not have byte-identical copies in those refs. Of those, **214** have
  same-name candidates; **955** have no same-name candidate. Neither category
  proves that equivalent content is absent under another name or in older history.
- The 1,169 non-exact files comprise 351 Python files, 145 Markdown files,
  656 JSON files, 13 text files, one Word document, one YAML, one shell script,
  and one HTML file. Generated JSON evidence is included in this count.
- **No scan/read errors** were reported. Twenty environment/cache/vendor trees
  were explicitly skipped and two symlinks were recorded without following them.
- No files were deleted, no installed runtime was changed, and no physical
  hardware or remote GPU job was started.

Content comparison is exact Git blob identity, independent of pathname. Formatting,
import-path adaptation, and substantive edits all count as non-exact. Manual
reconciliation is still needed before promoting old workspace files into active
code or deleting originals. This audit does not silently replace newer code with
older variants.

## Git preservation and branch selection

These remote branch heads were queried directly from GitHub on November 13:

| Branch                                    | Commit                                     | State of its local checkout at the audit         |
| ----------------------------------------- | ------------------------------------------ | ------------------------------------------------ |
| `codex/record-row-n-20261030`             | `6ac0b1a216b62307b8ab9ec1d264ac198e410c28` | Clean; identical to remote                       |
| `codex/consolidate-fruit-openpi-20261024` | `641123781ac61813f6f3840406cae9b42bcc3cf8` | Clean; identical to remote                       |
| `main` on GitHub                          | `f8eb9ed574eb4d3b84b4bc9408d7181da429086c` | Local `main` at `aff7b4c71` is 33 commits behind |

The November branch is 153 commits ahead of GitHub main. The October branch has
five commits not in the November history. Its selected fruit OpenPI integration,
provenance and formatting work remain on that branch. A default clone of main or
copying only the November checkout does not reproduce every branch's working tree.

The new `codex/new-machine-migration-20261113` branch starts at `6ac0b1a21` and adds
migration documentation, the read-only audit/profile tools and compact audit data.
Existing branches and runtime checkout locations remain in place. No merge into
main or claim of repository-wide green CI is part of this work.

## Verified local snapshot

A private archive was created outside the legacy workspace:

```text
/home/gaikwad-prakash/Documents/ChatGPT/migration-audit-20261113/
  source-and-calibration-snapshot.tar.gz
  source_inventory.jsonl
  summary.json
  snapshot_verification.json
  bench-packages.json
  official-client-061-packages.json
```

The archive contains:

- all 1,214 hashed workspace candidates, preserving their relative paths;
- 76 regular `.py`/`.sh` files directly under the Acer home directory;
- both calibration JSON files from `~/.cache/huggingface/lerobot/calibration/`;
- an internal `MANIFEST.json` with per-file SHA-256 hashes.

All **1,292** archived source/calibration entries were read back and their hashes
verified. The archive is 4,971,242 bytes, mode `0600`, with SHA-256:

```text
1b3023500801b239bf5225fc352684384b109f18912d8c25736e7722291303ec
```

This is a **same-disk snapshot**, not an independent backup. It excludes raw bulk
recordings, files outside the candidate rules, environment trees and AI90 data.
It is private and is not included in the Git commit. Transfer it to the new machine
or another backup device and verify its SHA-256 before relying on it. The 76 home
scripts were preserved, but were not included in the workspace-versus-Git matching
counts above.

## Largest workspace evidence groups

Logical byte totals, excluding skipped subtrees; not checksum-verified backups:

| Directory                   |           Bytes | Regular files |
| --------------------------- | --------------: | ------------: |
| `jpeg_trial_20260930`       | 211,570,288,807 |       438,360 |
| `fruit_openpi_20k_client`   |  48,254,107,390 |        52,365 |
| `rtc_remote_draft_20261007` |  47,901,880,670 |       100,303 |
| `fruit_openpi_client`       |  28,389,216,092 |        35,006 |

Keep these as evidence during migration. A clean Git status, small source archive,
or copied report does not preserve their underlying frames and traces.

## Other locally confirmed data locations

These directories were present and measured with `du -sh`; their full contents
were not hashed in this audit:

| Acer path relative to home               | Allocated size |
| ---------------------------------------- | -------------: |
| `orange_grasp_corrective_ft4_20261108`   |        340 MiB |
| `matchbox_pickplace_ft4_20261108`        |         61 MiB |
| `ft4_datasets_20261108`                  |        728 MiB |
| `ft4_corrected_20261110`                 |        399 MiB |
| `ft4_reweighted_20261110`                |        1.8 MiB |
| `esp_recovery`                           |        257 MiB |
| `esp_apple`                              |         12 KiB |
| `plate_demos`                            |        113 MiB |
| `runs`                                   |        3.3 GiB |
| `so101_trials`                           |        2.7 GiB |
| `.cache/huggingface/lerobot/calibration` |         28 KiB |

Additional `bench_trace_*`, `trial_*_frames`, simulator assets, other datasets,
external backup mounts and other project directories need a separate transfer
inventory. The table is intentionally not represented as a complete home inventory.
The Acer filesystem had approximately 391 GiB available during the audit; this
is not a capacity measurement of the new workstation.

## Runtime provenance and remaining gaps

Local package metadata was captured without importing robot code:
[bench environment](migration_20261113/bench-packages.json) and
[older client environment](migration_20261113/official-client-061-packages.json).
Package versions alone do not preserve editable sources, modified installed files,
GPU driver compatibility or all system dependencies.

The November server source identifies AI90 `/home/kiran/sim/vlash-venv` and VLASH
`22cbabfe` plus patches. Its live package inventory, source modifications and data
availability were not rechecked. Capture those before rebuilding the GPU runtime.
The currently documented FT4B source paths and model contract are in
[the updated setup guide](../NEW_MACHINE_SETUP.md).

The new machine's Ubuntu installation, login, IP, driver and connected rig are
pending confirmation. Its reported hardware came from the “PC Build Analysis”
conversation; a local hardware profile must verify it.

## Reproduce and inspect the audit

Run from the repository root on Acer (read-only source scan; output goes elsewhere):

```bash
python3 projects/testproject/scripts/audit_workspace_preservation.py \
  --workspace /home/gaikwad-prakash/Documents/ChatGPT/Lerobot \
  --repo . \
  --ref codex/record-row-n-20261030 \
  --ref codex/consolidate-fruit-openpi-20261024 \
  --ref origin/main \
  --output /home/gaikwad-prakash/Documents/ChatGPT/migration-audit-rerun
```

The script records resolved commits, so later branch movement is visible. Selection
is by the explicit suffix list and maximum size of 8 MiB, not a claim to identify
all valuable files. Symlinks are inventoried, not dereferenced. The skipped-tree
list and per-directory totals are in [summary.json](migration_20261113/summary.json).

The committed [compact source inventory](migration_20261113/source_inventory.jsonl)
contains one path/hash/status record per candidate. The fuller local JSONL also
includes exact repository paths and same-name candidate paths for manual review.
[snapshot_verification.json](migration_20261113/snapshot_verification.json) records
the private archive's hash and scope. Neither inventory includes source file contents.

## Preparation validation

All applicable staged pre-commit checks passed: size/conflict checks, Python
formatting/lint, spelling, Markdown formatting, secret detection and Bandit.
This is scoped validation of the migration changes, not repository-wide CI.
Temporary fixture repositories verified exact matching across renames, differing
same-name files, unmatched files, skipped environments, symlinks, binary inventory,
and rejection of output inside the source, for both SHA-1 and SHA-256 Git formats.
Twenty-five relative Markdown links resolved. The profile collector passed shell
syntax validation, ran on Acer, and refused to overwrite an existing output folder.
On Acer it recorded the missing NVIDIA tool and serial paths as failures rather
than declaring hardware ready. No destination-machine validation was performed.

## Remaining completion criteria

1. Confirm the new workstation login and collect its read-only profile.
2. Transfer and verify the private snapshot and original data on an independent
   destination; preserve both Git branches.
3. Capture AI90 runtime provenance, patches, datasets and full checkpoints.
4. Review non-exact source candidates before integrating them into active code.
5. Rebuild and validate the selected runtime offline, then validate cameras,
   calibration and a separately supervised hardware test.

Until those checks pass, the correct state is **migration prepared; transfer and
runtime validation pending**.
