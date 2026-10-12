# GR00T N1.6 official-execution baseline and supervised trials

## Superseding user decision — 2026-10-04

The user accepts the existing custom client and asks to disable its custom RTC, not rebuild an entirely official environment. **Active plan: GR00T existing client, RTC off**, with JPEG92, same recovery6000 checkpoint/task/cameras, evidence logging and unchanged motor protections. The strict isolated official/raw-image baseline phases below are retained as historical planning and are NOT current prerequisites. No package installs, official-server replacement or raw-transport switch is needed for this decision.

Use the existing sequential branch (default8 executed actions per reply, nominal30Hz intra-chunk pacing). This removes the RTC workers, age-based skip and transition blend. That scheduling/execution difference is intentional; it does not prove equivalent timing or smoothness. Keep the16-step model output unchanged. Diagnostics and stops are owner-thread based; synchronous inference can delay status polling, so do not promise uninterrupted10Hz polling or a hard real-time fault stop while blocked on a request.

Initial set is **three supervised `tomato-rtc-off` trials1–3**, separately numbered from earlier RTC-on tomato trial1. Before each: fresh fault/pose/camera/server check; home if needed; user supervises and resets between runs. On overload, stop, preserve evidence, verify cleanup and investigate before another motion attempt. Do not raise protections or automatically retry. No new trial timer or fake-actuator test.

Launcher command after readiness (real movement):

```bash
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python -u /home/gaikwad-prakash/Documents/ChatGPT/Lerobot/run_numbered_groot_trial.py 1 --series tomato-rtc-off
```

Append `--show-command` for a no-hardware/no-files preview. The launcher now requires an explicit series. Backup is `run_numbered_groot_trial.before_rtcoff_20261004.py`; only launcher selection/metadata changed, not the underlying client or driver. Restoring a launcher must not silently resume RTC-on trials. Record visual verdicts and compare like-for-like where possible; differing starting poses/object condition remain confounders. This supersedes the strict official implementation recommendation in the audit while retaining its factual findings.

Status: planned; no baseline implementation or new physical trial performed by this document update.

2026-10-04 audit update: [GROOT_N16_BASELINE_AUDIT_20261004.md](GROOT_N16_BASELINE_AUDIT_20261004.md) records the pinned N1.6 reference findings. Official execution is synchronous/raw with8 actions paced30Hz. Acer lacks GR00T and has incompatible LeRobot imports; a separate pinned environment is needed. Existing server JPEG support is a local patch. No software/hardware execution changes made. Processor/weight provenance and pinned-driver settings remain preparation checks, not completed equivalence claims.

## Decision and scope

The user wants to test GR00T as provided, without this project's custom RTC scheduler. Pause further use of that scheduler for the new baseline. Turning `--rtc=false` in the custom client is not, by itself, verification of an official execution path.

First audit and prepare the version-matched official path, then run a few supervised tomato trials. Proposed initial set: **three trials**, one at a time, with review/reset between them. This is a small diagnostic set, not a statistically reliable success-rate benchmark. Defer deeper root-cause investigation of the historical overload until it recurs or readiness checks reveal a current fault; do not declare the historical fault fixed.

Do not disable motor protections, raise torque/current/overload settings, add speed/acceleration limits, add an arbitrary trial timer, or introduce mandatory fake-hardware tests. Keep existing stop, cleanup, ownership and recording safeguards where compatible, documenting them as local integration rather than official policy behavior. No unattended chaining or automatic fault retries.

## Phase 1 — audit the official version and current implementation

Read the actual NVIDIA N1.6 release source matching this checkpoint and the installed AI90 checkout. Record upstream URL/tag, resolved commit, installed commit and local diffs; do not substitute current main/N1.7 documentation silently.

Inventory and compare:

| Area | Baseline requirement / evidence to collect |
|---|---|
| Model | Recovery checkpoint6000, exact path, configuration, weight identity and startup log; no retraining/checkpoint change |
| Task/data | Tomato task exactly `pick up the tomato and place it on the plate`; verified recovery dataset metadata includes10 tomato and50 orange episodes |
| Action interpretation | Official embodiment adapter, joint order, normalization, state-relative arm action conversion and absolute gripper conversion; calibration/units checked |
| Execution | Official chunk/execution horizon and rate for this release; distinguish prediction horizon from how many actions execute |
| Scheduling | Remove custom asynchronous workers, age-based skip-ahead and three-tick target blending from this baseline; identify official synchronous/non-RTC path rather than merely changing a flag |
| Transport | Audit project JPEG encoding and network wrapper against official server/client support. Use the official supported choice; if JPEG is custom, do not retain it silently under an “as-is” label |
| Device integration | Verify SO-101 compatibility with official SO100/embodiment interfaces and LeRobot versions; keep necessary adaptation explicit |
| Motor setup | Record actual configure() values and startup readback where supported. Do not import pi05's increased register values or silently change GR00T values |
| Diagnostics | Save observations, actual dispatched targets and motor feedback without target rewriting; measure/report diagnostic timing overhead |
| Stop/cleanup | Preserve exact-process stop and verified torque release; document local lifecycle integration separately |

Current project reference: `/home/gaikwad-prakash/n16_realarm_client.py`. Current numbered launcher still selects custom RTC; it must not be used unchanged for the new baseline. GR00T server reference: `/home/kiran/srv_wrap_recov.py`; GR00T venv: `/home/kiran/sim/Isaac-GR00T-n16/.venv` on AI90. Acer GR00T venv: `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv`.

Deliverable: a concise compatibility/difference table with exact supported command and pinned versions. If the official release lacks a compatible SO-101 path, report the specific gap and obtain a decision before adding a new adapter. Never call a new custom path “official as-is”.

## Phase 2 — prepare without disturbing the working environment

Preserve existing client, launchers, environment and evidence. Put the baseline launcher/configuration in a separate, clearly named location; use an isolated environment only if needed for verified dependencies. Record hashes/backups before modifying any integration file. Do not upgrade the working venv in place or stop/reconfigure a shared server without need and scope.

Verify imports, CLI/config parsing, checkpoint/task/camera names and serialization from source or saved data. These are software/read-only checks, not mandatory fake-actuator tests. No motor movement during preparation. Ensure recording/reporting works with the chosen official path: the current custom Journal hook does not automatically cover a different client.

Label the result accurately: either official policy/execution plus documented SO-101/safety/logging integration, or unresolved compatibility—not an unqualified official implementation claim.

## Phase 3 — fresh physical readiness

Before the first baseline trial, check exact serial identities, current process/device ownership, all-six motor communication/status/torque, stored calibration and measured pose. Warm cameras and inspect fresh front/wrist images. Verify the server/checkpoint and successful communication. Keep the operator present, workspace clear and power cutoff accessible; inspect tomato for damage from the previous grip.

If homing is needed, use the established requested homing procedure and verify it. A past torque-off/home check is not current readiness. Do not bypass a fault found during startup; address it before movement. Do not change the physical supply or servo protections to make a check pass.

## Phase 4 — three supervised baseline tomato trials

Use a **new series: `GR00T official-baseline tomato 1–3`**. Historical `groot-tomato-trial-001-20261004` remains **GR00T + custom RTC, tomato trial1**; never rename/overwrite it or combine the series' success rates. These three are the initial subset of the broader intended tomato testing; review before deciding any additional runs.

For each trial:

1. Record release/commit, exact command, checkpoint, task, object, initial camera views, start pose, motor settings, transport, horizon/rate, and execution mode. Unknown provenance stays unknown.
2. Operator resets the tomato and plate, confirms clear workspace, then starts one run. Use comparable initial placement within this series and record any deliberate variation.
3. Record both camera streams, their timestamps, requested/applied actions and sampled motor position/load/voltage/status. Keep the original evidence even if the run fails. Avoid camera-reader competition.
4. Stop on operator request, unsafe contact, overload/other fault or communication failure. A completed placement does not guarantee auto-home/auto-stop. No new fixed-duration timer is imposed by this plan.
5. Verify cleanup/torque-off first. Then generate the automatic metrics and inspect the grasp/lift/carry/release/final-rest footage before declaring success. Report integrity, dropped frames and review scope.
6. Update the ledger and tell the operator the result before resetting for the next trial. Do not automatically start the next process.

Task success: policy grasp, lift, transport and release onto plate, fruit remaining there, without manual placement. Record bruising/crushing and operator intervention separately. A fault-associated drop is not a normal policy release. Separate task outcome from stop reason and cleanup outcome.

## Phase 5 — if overload happens again

On Status32, stop the current trial through existing fault handling, preserve evidence and verify all-six torque release. Do not clear and immediately restart, raise protections, or continue the planned set automatically. Investigate before the next motion attempt. The user does not need a new lengthy investigation before a fault-free baseline trial, but recurring or startup faults change that decision.

Correlate frames with actual gripper targets, measured position, load samples, voltage, fault packet and timestamps. Distinguish nonsimultaneous register reads. Compare with the earlier tomato grasp and successful orange sequences under their respective configurations. Inspect contact geometry, fruit condition and binding. Separate motor-overload reporting from input-voltage faults; sampled voltage cannot exclude all transients. Do not convert raw load counts into force or treat a position gap alone as proof of a fault.

If the same fault occurs without custom RTC, custom RTC is not necessary for that failure. It still does not prove the entire mechanical/electrical cause. If three trials do not fault, report “not reproduced in this set”, not “fixed”. Do not claim improvement is caused by one change if the audit required multiple execution/transport changes.

## Documentation and completion criteria

Maintain the existing ledger and curated review records with series, object, trial ID/date, code/weights provenance, official-vs-local differences, mode/transport/horizon, task outcome, failure stage, stop reason, time to placement, saved frame counts, fault evidence, cleanup and reviewer scope. Keep human observations separate from visually confirmed results. Label historical GR00T trials as using custom RTC; human teleoperation is not a policy result.

This plan is complete when the official-version audit and isolated baseline setup are documented, the initial trial set is reviewed (or paused on a fault with investigation findings), and every attempted run has an evidence-backed verdict. No promise that turning RTC off fixes overload or that official timing will be smoother over this network.

## Rollback

Stop only the owned baseline trial and verify cleanup before switching launchers. Keep baseline evidence. Restore only the exact changed integration files from the captured backups after checking for newer unrelated edits; leave the clean/working environments intact. Isolated environments can remain installed without being used. Reverting software does NOT authorize resuming custom RTC physical trials: the user's current baseline decision excludes it. Never delete existing records or silently restore old motor values through a different environment.

## Current next action

Initial read-only compatibility audit completed; see the linked report. Next: isolated official-environment preparation and remaining processor/driver/provenance checks. **No software execution-mode change or physical trial has been performed.**
