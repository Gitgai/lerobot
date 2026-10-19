# R3a — Serving adapter: the public π0.5 (VLASH stack) behind the bench client's Zenoh protocol, verified WITHOUT the arm

Date: 2026-10-20. Status: **PROPOSED — awaiting go.** Parent: pi05_so101_real_base_audit_plan_20261019.md (R3).

## Why
dongyoonkim/so101-pi05-base serves at 57 ms/call on AI90 (R1), but the bench client in Pune speaks the
operator's remote-serving protocol (pi05-rtc-remote-draft-20261007: a Zenoh policy server on LeRobot 0.5.2,
`src/lerobot/policy_server/server.py`), while the checkpoint only loads through VLASH's policy classes (R1
gotcha 1). Without a bridge the 20 bench trials cannot run; with it the bench client runs unchanged.

## What the draft server already does (read 2026-10-20)
Loads a policy from a manifest via PreTrainedConfig / policy_class.from_pretrained; clients send an
observation + an RTC PREFIX (the tail of the chunk they are still executing) + a DELAY hint; the server
calls predict_action_chunk(delay, prefix) — LeRobot's guided RTC — if the policy "supports_rtc", else plain
chunks; warm-up on load; per-session timing logs (timing_server.log). A saved-data probe
(`probe_timing.py --recording … --count N [--measured-delay]`) replays recorded frames through the real
codec and server with no robot driver — the arm-less test harness already exists.

## The adapter (on AI90, ~1 day)
```text
A1  a policy wrapper the draft server can load: type "vlash_pi05" → VLASH PI05Policy (author's patches,
    empty_cameras=1, compiled) exposing predict_action_chunk(obs[, delay, prefix]); slot mapping
    front→base_0_rgb, wrist→left_wrist_0_rgb; state/action 6-D as recorded; chunk 50 → return 20
A2  RTC mode — a design decision, default chosen now:
      default  NO guided RTC inside the adapter (prefix ignored, delay logged): plain 20-step chunks, the
               client's pipelined loop keeps one request in flight (what the Aug 9/10 baseline did)
      later    guided RTC (prefix-conditioned denoising) only if VLASH's sampler exposes its denoising
               loop cleanly; VLASH's own "inference_overlap_steps" blend is a client-side alternative
A3  env: the draft runs LeRobot 0.5.2; VLASH pins 0.4.1 → run the adapter in /home/kiran/sim/vlash-venv
    and have the draft's server import only its codec/transport from there, OR run two processes
    (draft server ↔ local VLASH policy over a unix socket). Decide at build from what imports cleanly.
A4  manifest entry + systemd user unit `so101-base-server`; timing logs kept; port/keys as the draft uses
```

## Verification WITHOUT the arm (pre-registered, all on AI90 + the Acer over ZeroTier)
```text
G1  loopback replay   probe_timing.py against the adapter with the draft's saved observations
                      (timing_samples/observations, 12 frames) → codec round-trips, chunk shape 20×6, finite
G2  open-loop replay  replay a WHOLE recorded real episode of ours (so101_orange_89_v21, front+wrist+state,
                      task string) frame by frame at the recorded cadence; compare the chunk's first 10
                      actions with the recorded next 10 actions → per-joint MAE and gripper agreement across
                      the episode; repeat for 5 episodes. Reading: small, bounded error (≤ a few degrees on
                      arm joints, gripper open/close in step) = the model understands our rig; a drift or
                      flat output = mapping/normalisation bug. This is a sanity floor, NOT a success rate.
G3  remote replay     the same probe run FROM THE ACER in Pune over ZeroTier (needs AI90's key on the Acer or
                      the operator to run one command) → true end-to-end latency per call, jitter, and the
                      client's pipelined duty cycle at that latency; compare with the 300-500 ms figure and
                      L6's cliff (plain chunking dies at 500 ms; 20 steps @30 fps = 667 ms chunk here).
G4  fault cases       dropped frame, stale delay hint, client reconnect → server stays up, timing logged
G5  the bench         20 trials, RTC/pipelining on, filmed (R3 proper) — only after G1-G4
```
Outputs: results/so101_bench_adapter_20261020/{g1_loopback.json, g2_openloop_ep*.json, g3_remote_acer.json}
and a run record here. Cost: ~1 day build + 2 h verification; GPU 0 (9 GB) while serving.

## What it will and will not tell us
WILL  the bridge works end to end at the real latency, before anyone stands at the arm;
      whether the public model's actions on OUR frames track OUR recorded demonstrations.
WON'T whether it picks the orange. Open-loop agreement is necessary, not sufficient — only G5 answers that.
