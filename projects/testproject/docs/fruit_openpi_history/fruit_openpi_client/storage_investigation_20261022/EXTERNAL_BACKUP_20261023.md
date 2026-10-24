> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/storage_investigation_20261022/EXTERNAL_BACKUP_20261023.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# Acer external backup — 23 October 2026

## Authorization and destination

The user requested backing up all of Acer to the connected SSD and confirmed that the external SSD contains no files to keep after being told that preparing it as ext4 erases its existing contents.

- Source: Acer Aspire A14-52MT, internal WD PC SN5000S serial `25191R800696`.
- Destination: USB Crucial X9 Pro `CT1000X9PROSSD9`, serial `2545EABA2D78`, 1,000,204,886,016 bytes.
- The preparation procedure reformats only the external drive's existing large APFS data partition as ext4, label `ACER_BACKUP`, and changes that partition's type to Linux filesystem. The small existing 200 MiB EFI partition is retained, unused by this file backup.
- The exact device model, serial, transport, capacity and original APFS UUID are checked before formatting. Internal storage is never a formatting target.

## Procedure prepared

Script: `/home/gaikwad-prakash/.local/state/acer-external-backup/backup.py`.

Administrator authentication succeeded through the standard desktop prompt. The external APFS data partition was formatted as ext4 with UUID `33c047c9-cdd7-4410-814e-37417cbaa6cc` and mounted at `/mnt/acer-external-backup`. Copying started at **00:58:41 India Standard Time (UTC+05:30) on October 23**. EFI copying completed successfully; the main root-filesystem copy is running. Content verification remains pending. This document records launch status; consult the destination's live status file for subsequent progress.

After authentication, the script mounts the destination at `/mnt/acer-external-backup` and writes:

```text
acer-backup-20261023/
  rootfs/     Persistent root filesystem files, including /home and /data
  efi/        Files from /boot/efi
  metadata/   Status, copy/verification logs, partition layout and restore notes
```

The copy preserves numeric ownership, permissions, timestamps, ACLs, extended attributes, hardlinks and sparse files. It excludes virtual filesystems, RAM-backed temporary files, active swap and the backup mount itself. Other mounted filesystems are not traversed; EFI is copied separately. No source files are deleted, and no destination `--delete` operation is used.

Current policy (October 24, 00:20 India Standard Time (UTC+05:30)): the user explicitly requested full-speed copying without a software temperature limit. The active run uses `--monitor-temperature-only`, with no rsync bandwidth cap. Internal SSD temperatures are sampled every 0.5 seconds and appended to `metadata/temperatures.jsonl` every five seconds; status updates include the highest sampled temperature for the current stage. The script does not stop or pause based on temperature in this mode. Hardware/firmware thermal protection is unchanged. Storage errors, loss of temperature monitoring, a missing destination, low destination space or a stage time limit still stop the operation with partial data retained. Full-system freezes can delay software monitoring. Earlier thermal policies are recorded below as history.

After copying, rsync performs a separate read-only content-checksum comparison using SHA-1 plus metadata checks. Temperature logging and storage-error checks remain active during verification, using the same selected temperature policy. A live system can change during copying or verification. Any remaining differences are reported as requiring review; they must not be called a complete verified backup.

## Status and resume

**October 24, 00:20:09 India Standard Time (UTC+05:30) — monitor-only resume:** Administrator authentication succeeded. EFI copying completed and the main copy resumed with no bandwidth cap and no software temperature cutoff. Initial hottest internal SSD sensor: 77.85°C. The preceding run stopped at 00:05:54 at 80.85°C. A subsequent successful read-only comparison measured 48,555,791,463 bytes (45.22 GiB) across 332,914 regular files still needing transfer; this is a pre-resume estimate, not a checksum verification. No source deletion or destination reformat was performed. Check live status and temperature history for subsequent progress.

**October 24, full-rate request:** The user requested copying without a speed limit and stopping above 80°C. The script now omits the transfer bandwidth limit, samples temperatures every 0.5 seconds and stops at or above 80°C on any internal SSD sensor, with no automatic cooling/restart cycle. Storage-error, mount, identity and free-space checks remain active. A privileged replacement command was launched to terminate only the identified prior backup process group and resume the existing destination without formatting. Authentication and actual runtime status must be checked before describing the new run as started. Software monitoring responds to sampled readings and cannot guarantee zero overshoot or responsiveness during a host-wide stall.

**October 23, 23:55 India Standard Time (UTC+05:30) restart request:** The 23:24 resume stopped at 23:45 after a ten-minute cooling timeout; no new storage error was recorded. About 681 GiB was allocated on the external SSD. The hottest sensor subsequently read 76.85°C. The copy limit was reduced from 32 to **16 MiB/s**, retaining the existing 80°C pause, 74°C resume and error checks. Administrator authentication was requested for another resume without formatting. The checksum-only verification phase is still not transfer-rate limited. Consult live status to determine whether this latest request has actually started.

**October 23, 23:24 India Standard Time (UTC+05:30) resume:** The user requested resuming. Administrator authentication succeeded; the existing ext4 volume and device identity were verified without formatting. EFI reconciliation completed and the main root-filesystem copy resumed against the existing destination. The corrected USB filter is active, and a sleep inhibitor now wraps the entire backup/verification process. Content verification remains pending; inspect live status for progress or errors.

**October 23, 15:20 India Standard Time (UTC+05:30) check:** The first copy stopped at 06:56:37 after a USB camera (`usb 3-4`, AK-Camera) disconnected. The monitor's generic USB-disconnect filter was too broad: it stopped the backup even though the external SSD uses `usb 2-1` and remained mounted. About 674 GiB was allocated on the external filesystem; main copying and verification were incomplete. The retained journal search found no new NVMe/storage I/O/ext4 error or external-drive disconnect since backup start.

The monitor was corrected to watch the external SSD's actual USB path and any parent hubs, while retaining storage-error, temperature and mount checks. Filter checks distinguish the camera event from the external SSD disconnect and detect NVMe/I/O/ext4 failures. Earlier logs and status are now archived on resume rather than mixed into new verification results. A resume command without `--initialize` was launched through the administrator authentication prompt. Consult live status to see whether authentication and copying have resumed; no reformat is requested.

Check `metadata/status.json` and stage logs on the destination. The long-running copy and verification can take many hours. It is not complete merely because the volume was formatted or some files were copied.

After successful initialization, resume an interrupted operation with administrator authentication and **without** `--initialize`:

```bash
sudo python3 /home/gaikwad-prakash/.local/state/acer-external-backup/backup.py --monitor-temperature-only
```

This is a file-level recovery backup, not an atomic snapshot or a bootable clone. Restore testing, bootloader setup and reconciliation of files that changed while Acer was running remain separate steps. Original data stays on Acer.
