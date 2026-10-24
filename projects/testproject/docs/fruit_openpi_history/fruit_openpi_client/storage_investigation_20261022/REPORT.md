> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/storage_investigation_20261022/REPORT.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# Trial 1 pause investigation — 22 October 2026

## Finding

**Acer's system NVMe device suffered I/O timeouts and a controller reset at 15:03:41 India Standard Time (UTC+05:30), at the end of the approximately 56-second camera/control pause.** This is concrete host-storage failure evidence, not just a model/network timing hypothesis. It strongly supports a storage-related host stall. The precise underlying SSD/firmware/power-management/kernel cause is not yet isolated; a controller reset does not prove permanent flash failure.

No physical arm access, trial, disk stress test, filesystem repair, package installation, firmware change, power-setting change or protection change was performed in this investigation.

## Evidence

Saved `kernel_nvme_events.json` contains 56 matching kernel records from this boot, all at 15:03:41:

- 36 records containing `timeout`, including the reset record; not 36 independently established incidents.
- One explicit `timeout, reset controller`.
- Ten `I/O error, dev nvme0n1` block-layer records, plus corresponding NVMe status/error records.
- Timed-out READ and WRITE operations both appear. The controller subsequently reports its queues initialized.

Representative messages:

```text
nvme nvme0: I/O tag 452 ... timeout, aborting req_op:READ(0) size:4096
nvme nvme0: I/O tag 72 ... timeout, aborting req_op:WRITE(1) size:131072
nvme nvme0: I/O tag 452 ... timeout, reset controller
I/O error, dev nvme0n1, sector ... op 0x0:(READ)
```

The trial trace shows request 7 response → first dispatch delay of **55.5925 s**. Camera host timestamp gaps were **55.8302 s** front and **55.7824 s** wrist. The client then dispatched all 30 rows of request 7 before the worker failed when sending request 8. Its error was `keepalive ping timeout`.

An unrelated desktop main-thread-jank report is also present at 15:03:41 in the journal. This is consistent with a wider host disruption, not proof that one Python motor read alone blocked everything. Earlier investigation filtered for suspend/sleep/OOM and missed NVMe errors; the previous 'cause unresolved' report must be read with this new evidence.

## Storage scope and health limits

`findmnt` places the root filesystem and trial workspace on `/dev/nvme0n1p2`, ext4, currently read/write. Device: WD PC SN5000S SDEQNSJ-1T00-1014, firmware 34230100. Kernel 7.0.0-38-generic. Approximately 164 GiB free at investigation time. This is not evidence of a disk-full condition.

Current controller state is `live`. Sysfs temperature was about 50.85°C with temperature-alarm value 0. Cached UDisks health exposed an empty critical-warning field, temperature 323 K and power-on-hours 147. These are current/cached summaries, not proof of temperature or full health at failure. `SmartSelftestStatus: success` is an exposed cached property; **no self-test was initiated**, and its date/provenance was not established. Full media/error counters were not obtained. `smartctl` and `nvme` executables are absent; neither was installed.

Only this one matching error cluster was found in the available current-boot kernel records. That does not establish lifetime absence of failures or durable recovery. The trial wrote about 3.6 GiB of recordings. That adds storage load, but the evidence does not prove that recording caused the controller failure.

## Three separate concerns

1. **Confirmed storage event / probable host stall:** root-device timeouts and reset align with the shared camera/control gap. Whether firmware, hardware, power or kernel interaction caused it remains open.
2. **Confirmed stale-dispatch behavior:** the client sent a response after an approximately 56-second interruption. Existing Status checks do not detect response age. A motor can report Status=0 while the controller's plan is stale. This is a limitation of the new project integration, not established policy failure.
3. **Confirmed transport termination:** the worker reported a keepalive timeout. Installed WebSocket defaults are ping interval 20 s and ping timeout 20 s. The host interruption is consistent with loss of keepalive responsiveness; exact ping traffic wasn't captured, so this causal link is inference. Separately, normal raw-image RPCs took 1.1–9.35 s despite ~74–75 ms inference.

## Recommended recovery plan

### A — preserve data and establish host reliability first

- Keep physical retries paused. Back up irreplaceable demonstrations, checkpoints and project changes to an independent verified destination before heavy diagnostics. This investigation did not copy the user's broader data or assume backup completeness.
- Obtain fresh full NVMe health/error information with appropriate access and review SSD firmware, platform/BIOS and kernel compatibility using vendor-supported procedures. Do not update firmware, reboot, change NVMe power parameters or run repair tools automatically.
- Do not run filesystem repair against the mounted root filesystem, or write benchmarks/stress tests merely to reproduce this event. Escalate recurring resets/I/O errors to hardware/service diagnosis.

### B — address the deployment gap explicitly

- Propose and review a fail-stop check for interrupted control/over-age predictions **before another physical run**. It should stop, discard pending actions and require a fresh start rather than resume an old chunk. No automatic reconnect-and-resume.
- Timing thresholds must be explicitly justified from the chosen control contract and measured delays; they are project behavior, not invented LeRobot defaults. No new speed/acceleration limits or custom RTC are implied. No such code change was made in this diagnostic turn.
- In-process checks can reject stale actions after execution resumes; they cannot guarantee torque release while the whole host is stalled. Continue physical supervision/power cutoff. A hardware watchdog would be a separate design change, not silently assumed present.
- Do not simply disable keepalive or extend its timeout to hide the host stall.

### C — validate without movement, then retry once

- After storage reliability is addressed, run a bounded observation-only test with host I/O pressure, kernel events, frame timestamps and request/response/dispatch-age instrumentation.
- Review lower-overhead recording separately; maintain auditable camera coverage and do not claim it fixes an SSD fault. Network JPEG remains a separate explicit experiment, not a substitute for host reliability.
- Resume one supervised trial only after those checks pass. Keep the same checkpoint/motor protections for causal clarity. No automatic retraining or model-success conclusion from this infrastructure-interrupted run.

## Follow-up: reset meaning and earlier incidents — 22 October 2026

A read-only search across all retained kernel journal boots found three explicit `timeout, reset controller` events for `nvme0`:

| Date (India Standard Time (UTC+05:30)) | Time     |
| -------------------------------------- | -------- |
| 2026-10-04                             | 10:39:22 |
| 2026-10-08                             | 06:34:05 |
| 2026-10-22                             | 15:03:41 |

Command: `journalctl _TRANSPORT=kernel --no-pager -o short-iso --grep='reset controller|controller is down|reset failure|A[E]R:.*(error|severity)|EXT4-fs error'`. These are observed events in retained logs, not a lifetime failure count. The earlier current-boot-only finding remains correct, but the problem has recurred across boots. The equivalent `[E]` regular-expression spelling avoids a repository spell-check false positive; the matched kernel text is unchanged.

In plain language, Linux restarted the SSD controller to recover disk access after requests failed to complete. This is a recovery operation, not a format or intentional deletion. It does not establish that every in-flight operation succeeded: the latest event includes ten block-layer read errors. The upstream [Linux NVMe timeout handler](https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux.git/+/0506158ac7363a70f0deb49f71d26ccb57e55990/drivers/nvme/host/pci.c) schedules this reset when an I/O request remains incomplete after an abort attempt. This explains the logged recovery mechanism, not the original reason for the stall or every detail of the installed Ubuntu build.

The latest controller queue-initialization message follows the errors, and its current state reads `live`. A targeted kernel-log search from 14:55 to 15:05 found no matching thermal, suspend/resume, CSTS, PCIe Bus Error, watchdog/lockup or out-of-memory messages. Absence of those messages does not rule out an unlogged hardware, firmware or power-management problem.

The later health read in `fresh_smart.json` reports zero media errors and device error-log entries, but nonzero historical warning/critical temperature-time counters. No temperature measurement at the reset is available, so overheating is a lead to investigate, not an established cause. The controller-reset events also cannot be explained away by the healthy media counters. See `RECOVERY_PROGRESS.md` for the later health results and scoped backup coverage.

Conclusion: recurring storage-request timeouts and recovery resets are confirmed; the underlying cause remains unresolved. Preserve independent backups and investigate SSD/platform firmware, cooling, power-management and kernel compatibility through supported diagnostics. No firmware, power settings, filesystem repair or stress test was changed or run in this follow-up.

## Evidence files

- `summary.json`: collection time, counts, mount, free space and controller metadata.
- `kernel_nvme_events.json`: timestamped kernel messages.
- `udisks_cached_health.txt`: cached read-only health output.
- `../orange_trial_01_20261022/audit.json`: trace/frame gap measurements.
- `../orange_trial_01_20261022/transport.log`: keepalive exception.
