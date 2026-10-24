> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/storage_investigation_20261022/RECOVERY_PROGRESS.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# Recovery progress — 22 October 2026

Execution sequence and completion criteria: [SSD reset investigation plan](INVESTIGATION_PLAN.md). The plan starts with backup content verification and keeps storage reliability as a gate before moving trials.

## Latest follow-up — 23 October, 00:23 India Standard Time (UTC+05:30)

**00:58 India Standard Time (UTC+05:30) backup update:** After the user confirmed that the connected Crucial X9 Pro contains no files to keep, its large data partition was formatted as ext4 following desktop administrator authentication. A full persistent-filesystem backup plus EFI files has started on that external drive. EFI copying finished; main copying and later content verification are not yet complete. See [external backup procedure and live-status location](EXTERNAL_BACKUP_20261023.md). No source files were deleted.

The user explicitly requested skipping backup verification and proceeding with a load test. A bounded direct-I/O read-only test started on the Acer SSD, then stopped after about 0.568 seconds when internal Sensor 1 reached the precautionary 80°C cutoff (observed 80.85°C; composite 57.85°C). It completed 1.331 GiB of reads with no observed read error or new matching kernel storage event. Later stages were not run. This was an incomplete test, not a reliability pass or proof that heat caused the previous resets. No robot access, firmware/power change, write workload or backup verification occurred. See the [load-test report](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/storage_investigation_20261022/load_test_20261023/REPORT.md) and raw results for the cutoff's interpretation and limitations.

User approved proceeding with backup checks, read-only SSD health inspection and stale-prediction fail-stop implementation. No physical trial or motor connection was made in this work.

## 1. Scoped independent backup completed

**Final follow-up snapshot:** `/home/kiran/lerobot_backups/acer_critical_20261022_155025` contains 441 selected files (6,023,706 bytes), including the final guard code, tests and recovery report. All 441 destination hashes matched; see `backup_verified_20261022_155025.json`. This supersedes the earlier snapshot below as the latest backup. Scope remains selected text/code/calibration—not all recordings.

Copied **433 selected project files, 5,917,758 bytes**, to AI90:

`/home/kiran/lerobot_backups/acer_critical_20261022_154718`

Each source file's SHA-256 and size was verified at the destination: zero mismatches. Manifest and result are `backup_manifest_20261022_154718.json` and `backup_verified_20261022_154718.json` here. Scope: project code, Markdown plans, training reports, client/trial text logs and a follower calibration snapshot. No deletions or overwrites of existing backup folders. Raw frame PNGs, NPZ observations, environments and all original datasets were not included. **This is not a complete Acer backup.** Files added or edited after this snapshot need a later snapshot.

Also inspected these existing AI90 paths (presence/layout/counts, not full content hashing in this turn):

- `/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX/dataset_v21`: 55 Parquet files, 110 video paths, 172 files total. Logical file lengths total 20,554,717,966 bytes; this does not account for shared/hard-linked storage. Converted/trimmed training dataset, not proof of all untrimmed original demonstrations backed up.
- `.../checkpoints/pi05_fruit55_lora_vision/fruit55_lora_vision_5k/4000`: 27 files, 9,523,871,067 logical bytes, params/train_state/assets/checkpoint metadata present.
- Corresponding `5000`: 27 files, 9,524,990,738 logical bytes, same top-level layout.

The 4k loader succeeded again in the saved-observation check below. These files are independent of Acer's SSD, but AI90's own disk remains a single storage location, not a separately audited redundant backup system.

## 2. Fresh read-only SSD health obtained

Used existing UDisks `SmartUpdate` and `SmartGetAttributes` with interactive authentication disabled. No tools installed, self-test initiated, repair or firmware/power change. Raw replies in `fresh_smart.json`.

- `media_errors = 0`, `num_err_log_entries = 0`.
- Available spare 100; percentage-used field 0.
- 40 cumulative unsafe shutdowns; not attributed to this trial.
- Nonzero historical temperature-warning/critical-time counters are reported; their event timing was not established. Do not assign them to this reset.
- Current critical warning list empty; controller live. These facts **do not negate the kernel's confirmed I/O timeout/controller reset** or certify reliability.
- No additional matching kernel NVMe error cluster appeared in the refreshed current-boot evidence through 15:48:59 India Standard Time (UTC+05:30). No forced reproduction was attempted.

The root cause remains unresolved: SSD/controller hardware, firmware, platform power management or kernel interaction are not isolated. `smartctl`/`nvme-cli` installation was unnecessary for this health read and was not performed.

## 3. Fail-stop behavior implemented and checked without movement

New `freshness.py` is a project-side control check, **not LeRobot defaults, new motor limits or RTC**:

- `CLOCK_BOOTTIME` includes system suspend. Local worker timestamps the response immediately after receiving it; the controller checks the same-host timestamp.
- Maximum active control-check gap: **1.0 second**. Rationale: one complete trained action horizon (30 rows at 30 Hz), far longer than normal ~33 ms dispatch / ~100 ms waiting polls, and far shorter than the recorded 55.6-second pause.
- Maximum received-response age: **2.0 seconds**. Rationale: the nominal one-second chunk plus one second of explicit scheduling allowance. This is an engineering fail-stop budget, not a validated universal safe age or action speed limiter. The user can inspect both explicit arguments and the manifest.
- These checks are armed after torque-off warmup. A normal multi-second inference wait is allowed while the controller continues checking status/stop; a long interruption is not. Warmup response age is also checked before it is discarded.
- Checks run before/after status reads, before holding enable, and again immediately before each action send, including after trace logging. Thus a blocked trace write cannot knowingly be followed by an over-age target without rechecking.
- Failure latches and exits through cleanup; no reconnect-and-resume or automatic retry. No clipping, blending, speed/acceleration limiting or servo-configuration changes.

All **14 pure contract/timing tests passed**, including the actual recorded 55.5925-second interval, normal 30-row execution, monitored long RPC wait, old worker response, invalid timestamps and latched failure. These are numeric/control-policy tests, not a fake robot trial.

Actual new worker → actual 4k OpenPI server test used an existing saved observation only: valid 30×6 response, local worker-to-consumer age 0.00125 s, fresh check passed. A counterfactual replay of the recorded pause rejected that response. Cold RPC took 22.083 s, including 9.508 s inference. No cameras/motor APIs used, no motor targets sent. See `guarded_transport.json`.

The shared-host timing guard cannot stop or release motors **while the entire host is stalled**, and a pause between the last software check and the system call cannot be made atomic with this code. On recovery it can reject known-stale dispatch and attempt cleanup. Physical supervision and power cutoff remain necessary; a hardware watchdog would be a separate design decision. Full revised live-client/loaded cleanup is not validated by this saved-observation test.

## Follow-up investigation — 22 October, approximately 16:49 India Standard Time (UTC+05:30)

**Recurrence confirmed:** retained boot `-4` (boot ID `09dac44660be4e55948fcbb0a344040b`) contains an earlier incident at **8 October 2026, 06:34:05 India Standard Time (UTC+05:30)**: two `I/O error, dev nvme0n1` read-error records, `timeout, reset controller`, and multiple read/write timeout records. That boot used **7.0.0-34-generic**; today's boot uses **7.0.0-38-generic**. Therefore this storage failure signature predates the new fruit 4k trial and occurred on two kernel builds. This does not isolate hardware versus firmware versus a shared kernel/platform issue.

Read-only reproduction of the evidence: `journalctl -k -b -4 --no-pager --grep='nvme.*(timeout|reset)|I/O error, dev nvme'`. Boots -1, -2 and -3 had no matches for the narrower reset/read-error/PCIe-error filter; absence in retained logs is not proof of continuous health. Current-boot checks still show the October 22 15:03:41 cluster, with no later matching cluster at the time checked.

Existing firmware inventory reports SSD firmware **34230100**, BIOS **V1.32**, BIOS date **2025-11-27**. `fwupdmgr get-updates --json` listed only a Secure Boot dbx update, not an SSD/BIOS update. No catalog refresh or firmware installation was performed. This is a statement about the current local catalog, not proof that Acer has no applicable firmware or that an update would fix the problem.

Located older independent AI90 source-dataset copies at `/home/kiran/lerobot_assets/datasets/new30_20260915/{orange_final10_v21,orange_adjusted10_v21,tomato10_v21}` and `/home/kiran/lerobot_assets/datasets/recovery30_v21`. These are distinct from the trimmed 55-episode training export. Checking relative file names and lengths is only an inventory check, not full content verification, and these converted directories do not establish complete backup coverage of `/data/lerobot_datasets` originals. No bulk transfer, deletion, repair, reboot, environment change or robot access was performed in this follow-up.

### Remaining gates (unchanged)

The four sequential `rsync -rni --size-only --exclude=.cache/` dry-run comparisons completed successfully with no itemized differences. Every checked local source file therefore had a same-path/same-length remote counterpart under those four mapped directories. This did not hash video contents or check for remote-only extra files; no data was transferred. Full original-recording backup verification remains open.

1. Complete independent backup coverage for any irreplaceable original Acer recordings not covered by the AI90 converted dataset and this small source/log backup.
2. Investigate SSD firmware/platform/kernel reliability through supported vendor diagnostics; do not treat zero SMART media errors as permission to resume physical trials. No firmware update, reboot or mounted-filesystem repair was performed.
3. After the host issue is addressed, verify the revised full observation-only client and recording path with host/kernel/frame-age monitoring, avoiding a heavy-write stress test on the suspect disk.
4. Only then resume one supervised physical trial. No new physical trial was run or left active here; owned server/tunnel stopped.
