# RTC Backport Plan: Graft Real-Time Chunking Onto The Trusted Serving Code

Last updated: 2026-07-31

> **PHASE 1 COMPLETE - AND SIMPLER THAN PLANNED.** Verified against upstream
> GitHub at e40b58a8: the training-era code ALREADY CONTAINS the full RTC
> module and Pi05 integration (my earlier "pod lacks RTC" check was a bad
> git probe - the commit didn't exist locally, so cat-file failed for the
> wrong reason). No modeling backport needed. The only missing piece in ANY
> version is the async-server adapter, now built and validated offline:
> scripts/runpod/apply_rtc_server_adapter.sh (idempotent, .rtc.bak,
> env-gated: RTC_ENABLE=1, RTC_EXEC_HORIZON, RTC_DELAY_MARGIN_S;
> applied to a local copy of the real old file: compiles, idempotent)
> scripts/runpod/rtc_gates_test.py (Gates A/B/C runner)
> Next session: pod up -> apply adapter -> run gates (~10 GPU min) ->
> if all green, live test per section 4. Top up ~$5 first.

## 0. Why This Plan Exists (evidence)

```text
The arm runs ~2x demo speed with violent plan-switch jumps (70-114 units/step)
because ~1 s of serving latency expires ~60% of every action chunk and the
default async stack discards expired actions (fast-forward). RTC is LeRobot's
official cure: each new chunk is generated pinned to the already-committed
actions, so switches are seamless.

2026-07-30 trust exam (pod GPU, 30 recorded observations from the successful
run, graded against the recorded live answers):
  NEWER lerobot code -> FAIL. Collapse signature: predicted gripper 40-41 on
  every observation while correct answers ranged 2-56. Gripper corr 0.197.
  Same GPU/checkpoint/processors/transformers as the trusted server - only
  the code version differed.
  => The "collapse" seen in all earlier laptop probes was the NEW CODE, not
  the environment. The newer tree cannot serve this checkpoint.
  => "Upgrade server for RTC" is dead. Backport RTC into the old code instead.
Results: /workspace/exam/exam_results.json, doc pi05_rtc_investigation_20260730.md
```

## 1. What Gets Backported (sized, from the new tree)

```text
NEEDED (server-side RTC inference only, absolute actions):
  policies/rtc/configuration_rtc.py   (~60 lines: RTCConfig)
  policies/rtc/modeling_rtc.py        (298 lines: RTCProcessor.denoise_step -
                                       the actual algorithm)
  RTCAttentionSchedule enum           (from lerobot.configs - a few lines,
                                       inline into configuration_rtc to avoid
                                       touching old lerobot.configs)
  pi05 modeling hook                  (~19 lines in the old modeling_pi05.py:
                                       init rtc_processor; in the denoising
                                       loop, call rtc_processor.denoise_step
                                       when enabled; accept kwargs
                                       inference_delay + prev_chunk_left_over
                                       in predict_action_chunk)
NOT needed:
  action_queue / latency_tracker / interpolator / debug_visualizer (client-
  side rollout engine helpers), relative.py (our actions are absolute)

NEW code we write (not a copy - the async adapter, ~40 lines in the OLD
policy_server):
  - remember the last chunk returned + its start timestep
  - on each inference: inference_delay = measured server processing time in
    timesteps (ceil(latency*fps)); prev_chunk_left_over = last chunk minus
    the part already executed (client's obs carries latest executed timestep)
  - call predict_action_chunk(obs, inference_delay=..., prev_chunk_left_over=...)
  - reset state on client reconnect / new episode
Enable switch: rtc_config injected into the policy config AT SERVER LOAD via
a flag (e.g. env var RTC_ENABLE=1) - checkpoint files stay untouched; RTC off
= byte-identical behavior to today.
```

## 2. Phase 1 - Build The Backport (laptop, free, ~2-3 h)

```text
1. Pull the OLD tree's three files from the pod (modeling_pi05.py,
   configuration_pi05.py, policy_server.py) - the pod's /workspace/lerobot is
   the source of truth for "old".
2. Assemble a patch kit under projects/testproject/scripts/runpod/rtc_backport/:
     rtc/configuration_rtc.py, rtc/modeling_rtc.py   (copies, enum inlined)
     modeling_pi05.rtc.patch                          (the ~19-line hook)
     configuration_pi05.rtc.patch                     (add rtc_config field)
     policy_server.rtc.patch                          (the adapter)
     apply_rtc_backport.sh                            (idempotent, .bak backups,
                                                      loud failure on mismatch -
                                                      same style as the proven
                                                      apply_jpeg_decode_patch.sh)
3. Desk-check the hook against the new tree's integration line by line.
Deliverable: a kit that turns old-code serving into old-code+RTC serving with
one command, reversible via the .bak files.
```

## 3. Phase 2 - Verify On The Pod (needs pod up; ~30-45 GPU min, ~$0.40)

```text
Gate A - "graft broke nothing" (RTC OFF):
  apply the kit, run the SAME trust exam (rtc disabled).
  PASS bar: same as the old code's known behavior - gripper corr >= 0.8,
  gripper MAE <= 6 vs the recorded live answers. FAIL -> revert .baks, stop.

Gate B - seam test (RTC ON, recorded observations, no robot):
  simulate the live cadence: obs N -> chunk N; obs N+1 (~1 s later) -> chunk
  N+1 generated WITH prev_chunk_left_over from chunk N and inference_delay=30.
  Metric: |chunk N+1 first executed action - chunk N action at switch point|
  per joint, over ~20 consecutive pairs.
  PASS bar: median seam <= 5 units (demo scale). Reference: live seams today
  are 70-114 units. Also check: RTC overhead <= ~100 ms per inference.

Gate C - sanity of content (RTC ON):
  chunks must still DO the task (approach/close where the recorded run did):
  gripper corr vs live answers >= 0.8 (RTC must not freeze the policy into
  only copying prefixes).
```

## 4. Phase 3 - Live Test (one session, full checklist)

```text
Pre-run gates (all standing rules apply):
  camera-reference match (top view vs successful-run frame), orange in open
  spot, gripper open 40-55, arm start pose, wrist proxy up, trace enabled,
  user at the arm.
Run 1: RTC ON, chunk_size_threshold 0.85, jpeg 92, defaults otherwise
  (max_relative_target null per user's requirement).
Expected on the trace: executed-action p95 gap < 0.1 s AND per-step deltas
  back to demo scale (median ~0.9, p95 < 5, no 70+ jumps) AND grasps that
  survive plan switches.
Then: the 5-run reliability count (same setup, 5 attempts, count successes) -
  this number decides whether data collection (place demos etc.) is next.
```

## 5. Risks And Fallbacks

```text
R1 Old denoising loop diverges too much from new for a clean hook
   -> the hook is written against the OLD loop's structure; only the
   denoise_step call is grafted. If truly incompatible: fallback ladder.
R2 RTC guidance vs our large delay (~30 steps > execution_horizon default 10)
   -> tune execution_horizon (10-30) in Gate B; it's a server-side knob.
R3 Gate A fails (graft changes outputs with RTC off)
   -> revert via .bak, nothing lost; investigate before retry.
R4 All gates pass but live still jerky
   -> measure which seams remain; suspect the client's aggregation (chunks
   now agree, but weighted_average may still blend); consider aggregate_fn
   latest (official option) in a follow-up run.
Fallback ladder if RTC path dies: nearer-region GPU; then max_relative_target
cap (needs user approval); then robustness/place demos + fine-tune.
```

## 6. Ops Notes (money and pods)

```text
- Pod migrations RESTART stopped pods; check state after every migration.
  Balance burned twice this way ($7 and $1.4).
- Stopped pods still bill storage (~$0.2-0.3/day). For multi-day pauses:
  terminate pod, keep the network volume ($7/mo) - everything lives on
  /workspace and env repair after resurrection is 2 min (pip install uv;
  uv python install 3.12.13).
- Top up ~$5 before Phase 2+3 (verification ~$0.40, live session ~$1).
- After every session: stop client, restore Pi timelapse, stop pod server,
  STOP POD, verify it stayed stopped.
```

## 7. Definition Of Done

```text
RTC serves from the trusted code; Gate A/B/C all green; one live run whose
trace shows demo-scale motion; then the 5-run count recorded in the tracker.
```
