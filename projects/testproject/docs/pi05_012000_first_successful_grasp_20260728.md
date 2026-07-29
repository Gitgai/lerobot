# FIRST SUCCESSFUL PI05 GRASP: 012000 Picked Up The Orange

Last updated: 2026-07-28

On 2026-07-28, checkpoint 012000 - unchanged, no retraining - reached, grasped,
held, lifted, and carried the orange on the real SO-101 arm using official
LeRobot async execution, after the two deployment fixes from the live-mismatch
investigation were applied.

Trace (read-only, full):

```text
projects/testproject/artifacts/traces/official_async_3cam_012000_fixed_20260728_021800
```

## 1. What Changed vs The Two Failed Runs (and nothing else)

```text
1. chunk_size_threshold: 0.5 -> 0.85  (queue never starves; fresh observations)
2. start gripper state: opened to 54.1 (failed runs started at 28.6 / 21.2)
3. correct camera devices after enumeration shift (by-id paths; C270=top,
   laptop built-in=front, Pi=wrist via laptop-side proxy)
Same checkpoint, same policy server, same robot, same task string.
```

## 2. Result

```text
executed actions: 700 (run stopped manually in the carry phase)
strong close (<=25) EXECUTED: 395 actions, first at action index 304
  (failed run 230756: ZERO strong-close actions in 422)
min gripper action: -0.4 (full close commanded and held)
grip physically held: commanded ~5-17 while finger state pinned at 28.8
  -> object between the fingers from close until manual stop
sequence completed: reach -> close at the orange -> hold -> lift -> carry
place/release: NOT completed - the policy looped in the carry phase at the
  raised start posture and never set the orange down; run stopped at 700
  actions with the orange still held
```

Queue starvation - the failure mechanism of the earlier runs - is gone:

```text
queue at observation: median 42 of 50 (old runs: drained to 0 every cycle)
```

## 3. Remaining Issues (next work items)

```text
1. STUTTER PERSISTS despite the full queue: effective rate 2.2 Hz, action-gap
   p95 ~2.4 s, matching the chunk latency (median 1839 ms, p90 2947 ms - worse
   than the failed runs' 1392 ms, likely because threshold 0.85 sends
   observations far more often: 208 obs vs 37).
   Implication: the client stalls on something tied to the obs->chunk cycle
   even when the action queue is full - suspect blocking behavior in the
   client's observation send / chunk receive path, not starvation.
   The task succeeded ANYWAY, so this is a smoothness/robustness issue now,
   not a blocker - but fixing it should make grasps far more reliable.
2. NO PLACE/RELEASE: the model carried the orange back to the raised start
   posture and wandered instead of placing. Possible causes: carry states
   beyond demo length are off-distribution; stutter-distorted dynamics; or
   weak place coverage in the 40 focus windows (which emphasized grasp).
3. Server-side latency itself (~1.5-1.8 s per chunk on the RTX 3090 through
   the tunnel) is worth profiling: inference steps vs serialization vs network.
```

## 4. Evidence Chain That Led Here (for the record)

```text
1. Local probes said the model collapsed -> WRONG (broken local harness,
   newer lerobot code; see pi05_012000_pod_evidence_correction_20260728.md)
2. Pod comparison proved the model learned close/hold (corr 0.83)
3. Trace replay proved the live server was faithful and the model planned
   closes at chunk offsets 43-49 - the part async execution discards - and
   that a closed-ish start gripper triggers instant false closes
4. Camera check caught device renumbering (would have fed the model the
   laptop face camera as top AND front)
5. Fix set applied -> first successful grasp+lift+carry
```

## 5. Stutter Root Cause + Fix (implemented 2026-07-28, later the same day)

Diagnosis (from the successful run's trace + code reading + benchmarks):

```text
- All 169 action stalls >0.5s each contained exactly one observation event.
- The control loop was single-threaded: each observation froze actuation for
  capture + pickle + upload.
- The payload was RAW pixels: 3 x 640x480x3 = 2.77 MB per observation.
- GPU inference is NOT the bottleneck: 417 ms median (1774 chunks measured
  from archived server logs).
- The raw uplink is fast (2.77 MB in ~0.1-0.3 s via plain ssh), but the
  gRPC-over-SSH-tunnel path moves only ~2 MB/s effective, so 2.77 MB cost
  ~1.4 s per observation. Latency budget: ~1.4 s transport + 0.42 s
  inference = the measured ~1.8 s chunk latency.
```

Fixes implemented in src/lerobot/async_inference (our fork):

```text
1. image_codec.py (new): JPEG-92 compress observation images client-side,
   decode server-side. Measured on real trace frames: 2.77 MB -> 189 KB
   (14.6x), encode 3.8 ms, decode 2.9 ms, mean pixel error 0.4/255.
   Client flag: --jpeg_quality (wrapper: --jpeg-quality 92). Off by default.
2. robot_client.py: observation capture/upload moved to its OWN thread; the
   action loop never blocks on cameras or network. A robot_lock serializes
   motor-bus access (send_action vs get_observation). New config
   obs_min_interval_s (default 0.3 s) stops the decoupled thread from
   flooding the server.
3. policy_server.py (local): decodes JPEG markers after deserialization.
```

REQUIRED before the next run - the POD's server is old code and must be
patched once (pod was stopped when fixes landed):

```text
bash projects/testproject/scripts/runpod/apply_jpeg_decode_patch.sh <POD_IP> <POD_PORT>
```

Expected effect: smooth ~30 Hz actuation (no stalls), chunk latency ~0.6 s
(0.42 s inference + ~0.15 s transport), observations 3x fresher.

## 6. Suggested Next Steps

```text
1. Next pod session: run apply_jpeg_decode_patch.sh, then re-test with
   --jpeg-quality 92 added to the client command. Verify in the new trace:
   executed-action p95 gap < 0.1 s and chunk latency < 800 ms.
2. If place/release still fails on a smooth run: record additional demos
   emphasizing place/release, or extend focus windows to cover it.
3. Keep the run gates: by-id cameras verified, gripper open 40-55, wrist
   proxy up (laptop-side, port 8092), lights on, trace enabled.
```
