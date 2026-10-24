> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/orange_trial_01_20261022/REVIEW.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# Fruit OpenPI 4k — first physical orange trial, 22 October 2026

## Result

**Follow-up diagnosis:** [storage investigation](../storage_investigation_20261022/REPORT.md) found root NVMe read/write timeouts and an explicit controller reset at 15:03:41, aligned with the end of the ~56 s pause. This strongly supports a storage-related host stall; the lower-level cause remains unknown. The earlier suspend-focused journal search below did not include this evidence. Physical retries remain paused, with data preservation/host health and stale-dispatch handling the next priorities.

**Interrupted by transport failure; no successful placement demonstrated.** One actual physical trial ran after the operator removed the bottle and said Ready. No automatic retry or homing. Client verified torque off on all six motors with no cleanup errors. Owned server/tunnel exited; camera/serial devices were released. No protection or gain settings changed.

## Configuration and execution

Exact newly trained fruit 4k checkpoint; OpenPI, RTC off, raw RGB network images (no JPEG transport), synchronous 30 actions per response at nominal 30 Hz. Same motor settings as read-only preflight. Both cameras acquired MJPG over USB, decoded to RGB for inference. Camera acquisition MJPG is not network JPEG encoding.

Eight complete predictions: request 0 was warmup and discarded; requests 1–7 supplied all 210 dispatched actions. Request 8 failed during WebSocket send. All 210 returned dispatches match their recorded model response rows exactly. These API records do not certify physical attainment of every target.

Recording ran approximately 146 seconds including startup/warmup. First-to-last dispatch span was 93.906 seconds. Within chunks, median dispatch interval was 33.44 ms, p95 35.14 ms. This does not imply continuous 30 Hz control across requests.

## Stop cause and timing anomaly

`transport.log` ends with:

`ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout; no close frame received`

Client detected worker exit and stopped. This is a network/transport failure report, not a reported gripper overload or voltage fault. Status checks did not report motor faults; this does not prove continuously fault-free hardware during unobserved intervals.

Warm requests took 1.102–9.349 s while reported server inference took about 74–75 ms. Cold warmup took 22.767 s including 9.294 s inference. Do not attribute all remaining time to a measured network cause: transfer, host handling and scheduling are not separately instrumented.

**Critical shared pause:** request 7 response was recorded at elapsed 90.002 s, but its first dispatch at 145.595 s—about 55.593 s later. Largest host camera-frame gaps were 55.830 s front and 55.782 s wrist. Thus recorded activity stopped in both camera and control paths over approximately the same interval, and an older prediction was dispatched afterward. No matching suspend/sleep/stop/OOM event was found in the available filtered journal for 15:01–15:04 India Standard Time (UTC+05:30). The cause is **unresolved**; absence of a journal match does not rule out host/process scheduling or suspension.

The recording queue reported no drops and every saved image decoded, but this **does not mean continuous camera coverage**: the timestamp gap is real. The keepalive failure and shared pause may be related; causality is not established. Do not fix this by simply disabling keepalive or increasing timeouts and declaring it resolved.

## Visual evidence and review scope

Decoded all 4,115 saved images: 1,742 front and 2,373 wrist. Reviewed six evenly spaced images per view plus live-selected front frames, not every image semantically. See `front_review.jpg` and `wrist_review.jpg`.

The front samples show the gripper moving toward/above the orange, which remains on the table in the last frame; the plate remains empty. No completed grasp/lift/placement is demonstrated by this review. The first front image is black during startup warmup; later input views are illuminated. This startup frame is not evidence that model inference consumed a black image.

## Next work

Keep physical retries paused while investigating the shared host/control/camera pause and transport keepalive timeout using saved events, host metrics and a non-moving end-to-end run. Determine why a response sat for about 56 seconds before dispatch, and specify how interrupted/stale inference should be rejected before resuming movement. Any resulting behavior change must be explicit, not advertised as an existing LeRobot default. Do not retrain, change motor protections, add custom RTC or silently enable JPEG on the basis of this interrupted trial.

This is one interrupted physical attempt, not a statistically useful checkpoint success-rate estimate. Preserve all raw files and review artifacts; approximately 3.6 GiB at audit time. See `audit.json`, `trace.jsonl`, `transport.log`, `result.json`, `recording/events.jsonl` and `recording/summary.json`.
