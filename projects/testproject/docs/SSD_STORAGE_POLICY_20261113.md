# SSD storage, compression and backup policy

Updated: 2026-11-13. Applies to the planned `~/Robotics` workspace on ryzen9.
This is a plan, not an installed monitor or authorization to delete data.
No files were moved, compressed or deleted while writing it.

## 1. What space we actually have

The read-only inspection found a WD Blue SN5100 4 TB, an ext4 root filesystem,
approximately 3.6 TiB filesystem size and **3.4 TiB user-available space** with
about 31 GiB used. Decimal drive capacity and binary filesystem units differ;
these rounded figures are not evidence of missing data. Recheck `df -h` before
large operations; space changes as the machine is used.

The new SSD has room to start the migration. The Acer chat workspace alone was
approximately **367 GiB allocated**, but AI90 models/data and other Acer folders
have not all been inventoried. We cannot yet promise that every historical asset
fits unpacked on this one SSD.

Keep the existing filesystem. Use folders and a catalog; no repartitioning,
filesystem conversion or disk tuning is required by this plan.

## 2. Working-space policy

**Target at least 750 GiB available** on the filesystem containing the outputs.
This is our operational allowance for copies, downloads, unpacking, checkpoints
and temporary training files, not a manufacturer requirement or an implemented guard.

| Available space  | Planned response                                                                       |
| ---------------- | -------------------------------------------------------------------------------------- |
| At least 750 GiB | Normal work, provided the full next job fits with reserve                              |
| 500–750 GiB      | Review growth; postpone optional duplication/unpacking and plan archival               |
| Below 500 GiB    | Do not start new bulk imports, training or recording until the space plan is corrected |

Before a job, require `available >= 500 GiB + worst-case additional output + temporary/verification space + stop/finalization margin`.
Budget all concurrent jobs. For copying or recompression, account for the source,
new copy/archive and verification/extraction copy while they coexist. An archive
on the same disk does not save space until a separately reviewed original copy
is removed; moving a folder on the same filesystem saves no space.

These thresholds apply to ryzen9. The older Acer proposal for a 50 GiB recorder
reserve is not enabled here. A future recorder guard must be implemented and
validated separately, including controlled shutdown, queued writes and torque-off
verification. Until then, perform a manual preflight and supervise free-space
growth; do not claim automatic protection or kill an active robot process abruptly.

Initial soft budgets, to be revised after the complete inventory:

| Category                                                         | Planning allowance |
| ---------------------------------------------------------------- | -----------------: |
| Code, separate runtime environments and download/build caches    |            200 GiB |
| Active original and derived datasets                             |            800 GiB |
| Base models and trained checkpoints                              |            700 GiB |
| Recent training/trial evidence                                   |            500 GiB |
| Incoming transfers and locally retained compressed archives      |            300 GiB |
| **Total working allocations**                                    |      **2,500 GiB** |
| **Preferred available-space reserve, separate from allocations** |        **750 GiB** |

These are flexible planning envelopes, not partitions or quotas. OS/app use and
other workloads are outside the working allocations. Count a shared file only
once when assessing allocated capacity. Check actual filesystem availability,
not merely the sum of folder estimates. Keep a transfer batch within its budget;
a single 367 GiB import already exceeds the initial 300 GiB staging allowance and
must be split or explicitly rebudgeted.

## 3. What to compress

| Data                                             | Recommendation                                                           | Conditions                                                                                                 |
| ------------------------------------------------ | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| Completed text logs, JSON/JSONL and CSV traces   | Good first candidates for lossless `.zst` or per-run `.tar.zst` archives | Close the run first; retain a small readable summary and index; readers may require extraction             |
| New or weakly compressed PNG trial frames        | Sample lossless PNG recompression on copies                              | Preserve image pixels, dimensions, channels, metadata and frame/timestamp mapping; verify all replacements |
| Already optimized PNG recordings                 | Low priority; measure before touching                                    | Prior savings cannot be claimed again                                                                      |
| Completed raw numerical arrays                   | Consider a lossless archive after a sample test                          | Preserve original bytes or exact dtype/shape/values; keep active random-access data in its working format  |
| MP4, JPEG, existing compressed archives          | Leave as-is by default; benchmark before claiming benefit                | Do not repeatedly re-encode originals to chase size savings                                                |
| Active training datasets                         | Keep in the verified loader-compatible layout                            | Do not archive in place, change codecs or rewrite Parquet/HDF5 settings during migration                   |
| Active model weights and full resume checkpoints | Keep directly loadable                                                   | First reduce accidental duplication; compression benefit must be measured on real files                    |
| Old model checkpoints retained for history       | Optional lossless archive, one experiment or checkpoint per unit         | Record required base dependencies, hashes and restore procedure; keep full resume state when needed        |
| Source code and small docs                       | Keep in Git                                                              | Not a meaningful bulk-storage target; no manual `.git` object deletion                                     |
| Environments and tool caches                     | Inventory dependencies and patches; manage later                         | Do not assume old environments are reproducible or patched files are disposable                            |

For finished text-heavy runs, start a sample with Zstandard level 3 and bounded
worker count, then compare size, time and memory before selecting a policy.
Zstandard provides lossless compression with a speed/ratio tradeoff; stronger
settings are not automatically better for a working workstation.
[Official Zstandard documentation](https://github.com/meta/zstd).

PNG encoding has its own compression controls. Codec support alone does not
establish that our recorder meets timing or that a replacement preserves all
metadata. Test the exact installed encoder and existing viewer on copied data.
[FFmpeg encoder documentation](https://ffmpeg.org/ffmpeg-codecs.html).

Do not equate compression with quantization, lower precision, frame dropping,
resolution reduction or ordinary lossy video transcoding. Those change experimental
inputs or models. Small MP4 review videos can be useful derivatives, clearly labeled
as such, while the source evidence is retained.

## 4. What our earlier compression already achieved

Existing Acer records show:

| Completed operation            | Coverage                                                       |  Recorded savings |
| ------------------------------ | -------------------------------------------------------------- | ----------------: |
| October 8 historical PNG batch | 438,106 images recompressed; skipped cases separately recorded |        179.71 GiB |
| October 24 RTC/fruit PNG batch | 107,190 images verified                                        |         45.26 GiB |
| **Total already recovered**    | Separate completed batches                                     | **About 225 GiB** |

The October 8 record includes one pre-existing invalid PNG that was retained;
completed compression is not a claim that every historical image is valid.
Both batches' ledgers must accompany migration. Do not re-run them expecting
another 225 GiB. Newer recordings, including the 20k fruit directory, need fresh
sampling; no additional saving is promised in this plan.

Source evidence remains on Acer:

```text
/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/STORAGE_MANAGEMENT_PLAN_20261008.md
/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/storage_maintenance/compression_20261008_final.json
/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/storage_maintenance/compression_20261024/final.json
```

The earlier 223.188 GiB Git cleanup was another completed, narrowly scoped
operation in the old chat workspace. It is not a compression opportunity or a
reusable deletion list. Preserve current refs and the raw evidence; no Git cleanup
is part of this migration plan.

## 5. Prevent duplicate growth

- Store one pinned copy of each base-model revision. Checkpoint/run catalogs refer
  to it explicitly; do not make an extra model copy for every trial.
- Preserve full resume state for the latest active run and all checkpoints selected
  for comparison. Historical intermediate checkpoints remain until a retention
  review confirms what is reproducible and independently backed up. No automatic
  “keep last N” policy is enabled.
- Separate originals and reproducible derivatives. Keep the processing recipe and
  hashes so regeneration is possible; do not remove originals because a merged
  dataset exists.
- Keep downloads in one deliberate cache per compatible tool configuration.
  Hugging Face uses a shared blob/snapshot cache; paths may be symlinks, and deletion
  must respect referenced revisions. Use its version-appropriate inspection tools
  before any approved cleanup. Preserve symlink targets when transferring.
  [Hugging Face cache guide](https://huggingface.co/docs/huggingface_hub/guides/manage-cache).
- Never broadly clear `~/.cache/huggingface`: our calibration lives beneath it.
  Preserve patched dependencies and environment provenance before cache/env cleanup.
- Keep recordings, checkpoints and environment folders outside the Git checkout,
  and verify ignore rules. Git tracks code and small reviewed metadata.

## 6. Compression verification and archive catalog

Start with representative copies from each eligible folder, including large and
small files. Record source/encoded bytes, elapsed time, peak memory and decode/read
checks. Use a practical default only if the measured benefit justifies the work.
Do not run heavy recompression beside a timing-sensitive robot trial.

Each archive is a self-contained experiment or manageable batch, not one giant
archive of the whole workstation. Store a readable index next to it with source
paths, file counts, original/archived sizes, SHA-256 manifest, codec/tool version,
creation date, restore commands and backup location. Test extraction into a fresh
directory and compare checksums to the source before recording `restore_verified`.

For byte-preserving archives, every extracted file must match its source hash.
For PNG recompression, file hashes change by design: retain both hashes and verify
decoded pixels, dimensions/channels and required metadata for every replaced image,
plus frame IDs/timestamps and unchanged non-image files. Keep damaged inputs and
errors explicit; never silently drop frames.

Create new outputs first and keep originals. No deletion or in-place bulk
replacement follows automatically from this plan. Any later cleanup uses a precise
list with ownership, dependency checks, backup/restore evidence and agreed retention.

## 7. Backup and the review routine

An `archive/` folder on this SSD is organization, not backup. Keep an independent
verified copy of unique demonstrations, calibration, selected/full resume checkpoints,
source changes and valuable raw trial evidence. GitHub protects committed code and
docs; it does not automatically protect those large artifacts.

Acer and AI90 originals remain during migration. Identify a separate backup target
with enough measured capacity before declaring handover complete. The historical
external Acer backup had unresolved live-file differences; it is not automatically
a complete or current restore point for ryzen9.

Proposed manual routine, not a scheduled automation:

- **Before a run or transfer:** check available bytes and inode usage, forecast growth,
  confirm output paths and avoid overwriting an existing run.
- **After a run:** finalize files, record outcome and size, update the catalog, push
  code/docs and verify the independent copy of irreplaceable new data.
- **Weekly:** review largest folders, cache growth, duplicate candidates, failed
  downloads and disk-health indicators. Review candidates before cleanup.
- **Periodically and before source retirement:** restore a representative dataset,
  checkpoint and run from backup and verify them against their manifests.

The first storage action is a read-only full transfer inventory, including AI90.
Then sample only unoptimized eligible data on copies. No urgent compression is
needed on the nearly empty new SSD; correctness and an organized move come first.
