> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/README.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# Fruit OpenPI real-arm deployment — 22 October 2026

## Approved scope

One supervised orange trial with the newly trained fruit 4k checkpoint, after verified deployment. RTC off, JPEG off. Preserve existing training/model files, both Python environments and motor settings. No new motor limits, calibration changes, homing, automatic repeat or custom RTC. This is **project-side transport/recording integration**, not an unchanged official turnkey LeRobot/OpenPI client.

## Current status

**Recovery implementation:** [backup, fresh SMART and stale-action checks](storage_investigation_20261022/RECOVERY_PROGRESS.md). 433 selected code/plan/log/calibration files backed up to AI90 with matching SHA-256; existing 55-episode converted dataset and 4k/5k checkpoints inventoried there. This is not a full originals backup. Fresh SMART has no media errors but does not explain/clear the kernel reset. New project timing guard (1 s control-check gap, 2 s received-response age, suspend-aware clock) passed 14 pure tests and one saved-observation real-server check. No physical run. Host storage cause remains unresolved; physical retries stay paused.

**Latest diagnosis:** [October 22 storage/host-pause investigation](storage_investigation_20261022/REPORT.md) found a system-NVMe controller reset and READ/WRITE timeouts at the end of the 56-second pause. Host storage reliability and resuming stale actions must be addressed before physical retry. No motor/client behavior changes or disk repairs were made during diagnosis. See the phased recovery plan; do not treat longer network timeouts as a fix.

**First physical trial has now run:** [October 22 trial 1 review](orange_trial_01_20261022/REVIEW.md). 210 actions dispatched, no successful placement demonstrated, stopped on WebSocket keepalive timeout. All six torque-off readbacks verified; no homing. A correlated ~56-second camera/control trace gap preceded dispatch of an already-received response. Root cause remains unresolved; investigate with non-moving checks before another trial. Earlier statements below saying no physical trial has run describe preflight history and are superseded by this result.

**14:58 India Standard Time (UTC+05:30) readiness refresh, October 22:** all six motors reported Status=0, torque off, matching calibration and 7.2 V idle feedback. Current front/wrist images are `../rig_preview_m3vnuyki/`. The front image shows an additional blue bottle beside the orange in the workspace. Physical launch was withheld pending removal of that object; no holding torque, target writes or trial dispatch occurred. The exact 4k server was loaded and then stopped. This is a readiness pause, not a failed policy trial or a new motor fault.

Implementation prepared; six pure input/output contract checks and Python compilation passed. Real hardware observation-only integration and torque-off stop checks **passed on October 22**, after two camera-startup failures retained as evidence. **No moving trial with this client has run.** Earlier October 21 motor checks are historical. Current results and limitations follow below.

### Executed results

| Check                    | Result                                                                                                                                        |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `observe_20261022_01`    | Wrist camera first-frame timeout with automatic format; zero commands; torque-off verified                                                    |
| `observe_20261022_02`    | Wrist first-frame timeout even with MJPG and eight-second warmup; zero commands; torque-off verified                                          |
| Camera diagnostics       | Direct V4L2 streams passed both separately and concurrently; a subsequent simultaneous LeRobot camera-only check passed                       |
| `observe_20261022_03`    | Full real-camera/read-only-motor → OpenPI → recording path passed; two finite 30×6 responses; zero dispatches                                 |
| `stop_check_20261022_01` | SIGTERM after request submission stopped the actual observation-only client, closed cameras/worker and verified torque off; no cleanup errors |

Successful full run: 799 front + 1,028 wrist frames, all 1,827 decoded at 640×480; recording reported no drops. Both actual request input images were spot-reviewed, not all frames semantically reviewed. Gains/protection/operating-mode snapshots were identical before and after. Gripper Max_Torque_Limit=500, Protection_Current=250, Overload_Torque=25. This is current readback, not a recommendation to raise settings.

Request timings: cold 12.132 s (server inference 9.584 s), warm 6.563 s (server inference 0.0744 s). The approximately 6.49 s outside warm inference is not isolated to a specific network component. Network waiting remains variable; no smoothness claim.

The stop exercise saved another 407 front + 485 wrist frames with no reported drops. It verifies **torque-off process cleanup**, not torque release under load or physical response to a motor fault. Physical dispatch and loaded cleanup remain untested in this new client.

Both earlier camera failures remain unexplained; later success does not prove a permanent fix. The first failed run also exposed a camera read-thread teardown exception in installed LeRobot. No installed source was patched. Opening the rig afresh must verify both streams before torque. MJPG is the cameras' USB acquisition format, matching the known preview settings; model network payload remains decoded raw RGB, **not JPEG-compressed transport**.

All owned client/server/tunnel processes were stopped. No motors were enabled, no model/data/environment packages changed, and unrelated GPU workloads were preserved. Evidence occupies about 2.7 GiB and is retained. See `observe_20261022_03/audit.json`, `result.json`, `trace.jsonl`, `recording/summary.json`, and the stop-check result/log.

## Architecture and unchanged settings

- `server.py`: official saved OpenPI loader on AI90, exact 4k checkpoint, loopback port 18762.
- `transport.py`: official MessagePack array format/WebSocket transport in the already-existing Acer LIBERO client venv. No robot imports. Separate process avoids installing networking packages into the robot environment.
- `client.py`: existing LeRobot SOFollower observation/action APIs, exact dataset joint order/units. Physical startup is explicit, not import-time. Does not call `configure()` or `calibrate()`; these would rewrite registers. Reads current operating mode, gains and protection values and records them. Requires position mode, matching calibration, zero Status and torque-off start.
- `contract.py`: raw 640×480 RGB uint8 cameras, six state values; 30×6 finite output targets. No simulation mapping, interpolation or target clipping added.
- Existing project `FrameRecorder` records both cameras, including while waiting for inference. Separate synchronous trace preserves request ID, complete model response, row-specific dispatch and measured state. API return is not proof of target reached.
- Explicit execution path preloads current raw encoder targets, verifies them and enables torque. It uses the existing cleanup helper for per-motor torque release/readback. No protection registers or motor gains are written.

## Timing and execution semantics

The trained horizon is 30 actions at 30 Hz. The proposed synchronous client executes all 30 rows, then requests a fresh prediction. That is a documented project choice matching the full trained horizon, not a universal LeRobot default. It does not overlap inference and movement. Network waiting can cause pauses: the October 21 warm raw-image request took 2.986 s versus 0.0745 s server inference. No claim of smooth operation or RTC.

Warmup inference is performed torque-off and its output discarded. Physical execution fetches a new observation and response after torque enable. Status and operator-stop checks continue while waiting for the transport worker. RPC deadlines are 60 s in the worker and 70 s in the controller, diagnostic/project failure bounds, **not LeRobot defaults or trial timers**. There is no overall trial timer, automatic success stop or automatic home. A person must supervise physical execution.

## Commands and output

Robot interpreter: `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python`.
Network interpreter: `../openpi_split_validation_20261015/venv/bin/python`.

Default `client.py --output ABSOLUTE_FRESH_DIRECTORY` connects real cameras and reads real motors, blocks motor-write APIs, makes two actual predictions, and exits. It is **not fake hardware**, and cannot execute motor targets.

Adding `--execute` is the separately labeled movement mode. Do not launch until the observation-only integration, stop path and fresh supervised readiness are verified. Server/tunnel ownership and launch are separate; never connect to an unverified model server.

Outputs: `manifest.json`, lossless per-request `request_*.npz`, `trace.jsonl`, `result.json`, `transport.log`, and `recording/` with camera frames and coverage summary. Existing recorder uses uncompressed PNG and can consume substantial space; check capacity before execution, and stop if recording fails or drops coverage. No new storage guard is claimed.

Normal stop: SIGTERM to the exact client PID, or create `STOP` in that client's output directory. The client stops dispatch, releases torque if it attempted to enable it, reads torque back, closes cameras and drains recording. A failed readback is not confirmation of torque off. Hardware cutoff remains necessary if software/USB cannot stop the arm.

Updated interruption behavior: `--max-control-gap-s 1.0` and `--max-response-age-s 2.0` are explicit project fail-stop timing policies; see recovery progress for rationale/limits. They are not motion limits or a total trial timer. A normal long inference wait with active polling is distinguished from a frozen controller. No stale chunk is intentionally resumed after a detected violation. These changes do not repair the SSD or guarantee stopping during a whole-host freeze.

## Verification phases

1. Completed: pure data-contract checks (six), syntax validation; no fake-actuator test required.
2. Completed: actual camera+motor observation-only two-request run; audited trace/frame coverage, unchanged register snapshots and torque-off exit.
3. Completed within torque-off scope: operator-stop exercise with real devices; worker/camera cleanup and torque readback passed. This does not validate loaded torque release.
4. Pending: refresh real-arm readiness, launch one supervised execution, preserve videos/traces, review grasp/placement. Do not count preflight requests as trials.

## Rollback

Stop only owned client/server/tunnel processes; verify torque release for a moving run. These files are isolated in `fruit_openpi_client/`; no installed code or prior launcher has been edited. Retain evidence. Do not switch automatically to an old checkpoint/client. No motor configuration restore is needed because none is changed; if register snapshots disagree, stop and investigate rather than rewriting them.
