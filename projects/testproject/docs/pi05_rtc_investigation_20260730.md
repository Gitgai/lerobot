# RTC (Real-Time Chunking) Investigation - Phase A Findings

Last updated: 2026-07-31

> **UPDATE 2026-07-30/31:** Step 1 (trust exam) RAN and FAILED - the newer
> code collapses to gripper ~40-41 on every observation on the pod GPU too
> (corr 0.197 vs the recorded live answers). This proves the historic
> "collapse" was the newer CODE, not the laptop/CPU. The upgrade path is dead;
> the active plan is now the backport:
> `pi05_rtc_backport_plan_20260731.md`

Goal: fix the ~2x fast-forward / plan-switch jerks of remote async serving by
enabling LeRobot's official RTC feature. This doc records what exists in the
code and what it takes to use it in OUR setup.

## 1. What Exists (newer lerobot code, our local checkout)

```text
src/lerobot/policies/rtc/            full RTC module
  configuration_rtc.py               RTCConfig: enabled, prefix_attention_schedule
                                     (LINEAR), max_guidance_weight=10, execution_horizon=10
  modeling_rtc.py                    RTCProcessor.denoise_step: guides each denoising
                                     step so the new chunk matches prev_chunk_left_over
                                     over the prefix (inpainting w/ prefix attention)

src/lerobot/policies/pi05/modeling_pi05.py
  Full integration: PI05Pytorch(config, rtc_processor=...), enabled when
  config.rtc_config.enabled; predict_action_chunk accepts kwargs
  inference_delay + prev_chunk_left_over.

src/lerobot/rollout/inference/rtc.py
  A complete RTC inference engine (background inference thread, LatencyTracker,
  ActionQueue) - BUT built for LOCAL inference (policy on the same machine as
  the robot), part of the lerobot.rollout stack.
```

## 2. The Two Gaps For Our Setup

```text
GAP 1: The async client/server stack (what we use: policy on RunPod, robot on
  laptop) has ZERO RTC wiring - in every version, old and new. The
  policy_server calls predict_action_chunk with no prev-chunk/delay info.

GAP 2: The pod serves with the training-era code (e40b58a8), which predates
  the entire RTC module. RTC inference requires the NEWER pi05 modeling code
  on the server.
```

## 3. What It Takes (the plan)

```text
STEP 1 - trust the newer code on GPU (blocking prerequisite):
  Run the trace-replay control on the pod with the NEWER lerobot: feed
  recorded observations from the successful run, compare outputs to the live
  chunks (same method that resolved the harness saga). If the newer server
  reproduces the known-good behavior on GPU, it is safe to serve with.
  (The earlier "newer code = broken replay" result was on laptop CPU; never
  isolated code-version vs CPU. This test isolates it on the pod GPU.)

STEP 2 - small RTC adapter in our fork's async policy_server (~1-2h):
  The server already knows everything RTC needs:
    - prev_chunk_left_over: the chunk it returned last, minus the part already
      executed (client sends obs.timestep = last executed action)
    - inference_delay: measured server latency in timesteps
  Change: keep last-returned chunk in server state; on each inference call
  predict_action_chunk(obs, inference_delay=..., prev_chunk_left_over=...).
  Enable via rtc_config in the policy config at load (checkpoint config is
  untouched; enable through server-side config override).
  Note: our actions are ABSOLUTE (relative disabled), which is the simple RTC
  path (no reanchor_relative_rtc_prefix needed).

STEP 3 - dry seam test on recorded observations (no robot):
  Generate chunk N from obs N and chunk N+1 from obs N+1 with RTC on;
  measure the discontinuity at the switch point. PASS = seam steps ~demo
  scale (<5 units) vs the 70-114 unit jumps measured live.

STEP 4 - live test under the standing checklist (camera reference match,
  open gripper, clean scene), then the 5-run reliability count.
```

## 4. Honest Risk Notes

```text
- RTCConfig defaults look sane (execution_horizon 10 = ~0.33s at 30fps;
  our delay is ~30 steps at 1s latency - inference_delay is passed per-call,
  so the schedule adapts; verify horizon vs delay interplay in Step 3).
- Step 1 could fail (newer code may genuinely serve this checkpoint wrong on
  GPU). Then RTC via lerobot upgrade is blocked, and the fallback ladder is:
  nearer-region GPU, then the max_relative_target cap (user approval), then
  robustness demos.
- The RTC adapter touches the serving path only; the checkpoint, dataset and
  client stay unchanged.
```
