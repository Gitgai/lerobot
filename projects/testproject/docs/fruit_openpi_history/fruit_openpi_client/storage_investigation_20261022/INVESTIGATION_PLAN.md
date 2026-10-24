> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/storage_investigation_20261022/INVESTIGATION_PLAN.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# SSD reset investigation plan

Created: 22 October 2026. Status: planned; backup content verification and root-cause investigation remain open.

## Purpose

Find why the laptop's SSD stops responding, protect the data, and establish evidence of reliable operation before another moving robot trial. An SSD reset is Linux restarting the storage controller after disk requests fail to complete. The reset is a recovery action; its original trigger is still unknown.

This document plans the work. Creating it does not run diagnostics, change system settings or start a trial.

## What we know

| Finding                                                                                                                     | Meaning and limits                                                                                              |
| --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Resets recorded on October 4 at 10:39:22, October 8 at 06:34:05, and October 22 at 15:03:41 India Standard Time (UTC+05:30) | The failure recurs and predates the new model trial. These are retained-log observations, not a lifetime count. |
| October 8 used kernel 7.0.0-34; October 22 used 7.0.0-38                                                                    | More than one kernel build is affected. This does not rule out a shared driver issue.                           |
| October 22 reset aligns with about 56 seconds of camera/control interruption                                                | Storage failure strongly supports a host-stall explanation; the underlying trigger is unconfirmed.              |
| WD PC SN5000S, firmware 34230100; BIOS V1.32                                                                                | Starting inventory from the existing investigation; recheck before compatibility decisions.                     |
| Zero reported media errors; historical temperature-warning/critical counters are nonzero                                    | Neither a clean health summary nor historical heat counters identify the cause of this incident.                |
| Four checked source-dataset copies on AI90 match source filenames and sizes                                                 | File-content hashes and original-dataset coverage still need verification.                                      |
| 441 selected code/log/calibration files were hash-verified on AI90                                                          | A scoped backup exists; it does not cover all recordings or later edits.                                        |
| Current local firmware catalog showed no SSD update                                                                         | Vendor availability and applicability remain to be checked; no update was installed.                            |

Evidence: [investigation report](REPORT.md), [recovery progress](RECOVERY_PROGRESS.md), [health results](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/storage_investigation_20261022/fresh_smart.json). Capacity management is tracked separately in the [storage plan](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/STORAGE_MANAGEMENT_PLAN_20261008.md). Compression and free space do not establish that the reset problem is fixed.

## 1. Verify and complete independent backups

- [ ] Map each local source directory to its exact AI90 copy. Start with the four dataset mappings documented in recovery progress; do not substitute converted training exports for original demonstrations.
- [ ] Inventory irreplaceable original demonstrations, recordings, numerical traces, checkpoints, calibration and project changes. Mark each item as covered, missing, intentionally excluded or awaiting a retention decision.
- [ ] Generate SHA-256 manifests at both ends containing relative path, file size and content hash. Read files sequentially with limited concurrency; avoid simultaneous bulk scans or recording. Check for files changing during hashing and recheck those files after writers stop.
- [ ] Compare path sets and hashes. Report missing files, mismatches, read failures and destination-only extras separately. Do not delete extras or overwrite a discrepant copy automatically.
- [ ] Copy missing or changed irreplaceable data to a new destination snapshot, verify its hashes, and retain existing copies until discrepancies are resolved.
- [ ] Test reading representative backed-up videos, metadata and numerical traces on AI90. Preserve manifests and a verification summary independently of the laptop.

**Stop condition:** If hashing produces an I/O error, new reset or unreadable file, stop bulk verification and prioritize recovery/service assessment. Hashing is read-only but still puts load on the SSD.

**Completion evidence:** Exact verified scope, source/destination locations, counts, bytes, hashes and exclusions. All required files must match, with zero unresolved read failures. Matching files cannot prove that a source was already uncorrupted before copying; representative reads provide an additional check.

## 2. Compare the recorded failures

- [ ] Preserve journal evidence around each incident, initially ten minutes before and after, plus boot ID, kernel version and available earlier context. Use boot IDs instead of changing relative boot numbers.
- [ ] Build a timeline of first timeouts, abort attempts, reset, read/write errors and queue recovery. Align trial timestamps with kernel events and document any clock uncertainty.
- [ ] Compare available recording activity, free space, sleep/wake events, AC/battery transitions, temperature readings, thermal counters, PCIe errors, memory pressure and system stalls. Mark missing historical measurements as unknown.
- [ ] Separate observations from hypotheses. A recording write load or old temperature counter alone is not proof of causation.

**Completion evidence:** One incident comparison table showing common features, differences and missing evidence. Do not infer the stall duration solely from the instant at which queued kernel messages were logged.

## 3. Check firmware, platform and Linux compatibility

- [ ] Confirm exact laptop model, SSD model/firmware, BIOS version, installed kernel, boot parameters and power-management configuration using read-only inventory.
- [ ] Check Acer, the SSD vendor and official Linux/Ubuntu sources for issues matching this model and timeout signature. Record source URLs, dates, affected versions and whether each finding applies.
- [ ] Distinguish the existing local firmware-catalog result from a fresh vendor check. Document any newer supported release without assuming it fixes this fault.
- [ ] Rank candidate explanations using evidence: SSD/controller fault, firmware/driver interaction, power-management transition, cooling/temperature or PCIe/platform problem. For each, state what observation would strengthen or weaken it.

**Completion evidence:** A short list of supported next actions, with expected benefit, uncertainty, recovery/rollback procedure where available and any reboot requirement. Do not assume firmware can be rolled back.

## 4. Test one hypothesis at a time, without arm movement

Begin after required backups are verified. Keep the robot disconnected from motion control.

- [ ] Define a bounded baseline test before starting: exact workload, duration, write budget, available-space reserve, temperature limits from device/vendor data and stop conditions.
- [ ] Collect kernel events, temperature, disk latency/I/O pressure, free space and application timing with modest logging. Preserve an independent copy of results so a laptop stall does not hide the evidence.
- [ ] Start with ordinary read activity or saved-observation replay; avoid destructive tests, heavy write benchmarks and filesystem repair on the mounted root filesystem.
- [ ] If evidence supports a configuration or software change, document the exact change and recovery route first. Schedule disruptive changes separately; this plan does not execute firmware updates, reboot or power-setting changes.
- [ ] Change one variable, repeat the same bounded workload and compare results with the baseline. Do not combine kernel, firmware and power changes in one experiment.
- [ ] Stop on any new timeout/reset, I/O error, unresponsive host or exceeded test limit. Preserve evidence and assess vendor/service diagnosis rather than repeatedly forcing the fault.

**Completion evidence:** Before/after measurements and a clear result: supported hypothesis, weakened hypothesis or inconclusive. One clean run cannot establish that an intermittent fault is fixed. Repeated errors despite supported remediation warrant hardware/service assessment.

## 5. Decide whether moving trials may resume

- [ ] Required backups and exclusions are documented and verified.
- [ ] Storage reliability has an evidence-based resolution or service disposition; an unexplained repeated reset remains an open gate.
- [ ] The agreed observation-only validation completes with no new storage errors or unexplained camera/control gaps. Its duration, workload and remaining uncertainty are recorded.
- [ ] Validate the revised full client, recording and cleanup paths without movement, including rejection of stale predictions after a simulated interruption.
- [ ] Review results before one supervised moving trial. Preserve existing motor protections, operator supervision and physical power cutoff; do not automatically retry or resume stale actions.

The existing freshness guard can reject old actions once the host resumes. It cannot guarantee motor release while the entire laptop is stalled. A passing SMART summary, restored disk capacity or one successful test is insufficient by itself to close this gate.

## Progress and next action

Update [RECOVERY_PROGRESS.md](RECOVERY_PROGRESS.md) after each stage with evidence paths, findings, remaining uncertainty and the next decision. Mark a cause as confirmed only when the evidence distinguishes it from alternatives; otherwise record the mitigation and unresolved uncertainty explicitly.

**Next action: verify the four dataset copies by file-content hashes and establish coverage of original, irreplaceable recordings.**
