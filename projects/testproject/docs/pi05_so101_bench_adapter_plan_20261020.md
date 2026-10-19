# R3a — Serving adapter: the public π0.5 (VLASH stack) behind the bench client's Zenoh protocol, verified WITHOUT the arm

Date: 2026-10-20. Status: **DONE 2026-10-19 — no Zenoh adapter was needed (see §"simplification found while building"); the W0 wrapper serves the bench client directly; bench trial 1 ran (G5 started).** Parent: pi05_so101_real_base_audit_plan_20261019.md (R3).

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

## 2026-10-19 — simplification found while building: no Zenoh adapter may be needed
The wrapper IS a LeRobot gRPC async policy server. Any LeRobot-0.4.x async client — the stock
`lerobot.async_inference.robot_client`, or the small bench_client.py in results/so101_bench_20261019/ — can drive the
real arm against it directly over ZeroTier (AI90 192.168.194.220:8080). The Zenoh route is only needed if the
operator's existing bench client must be kept. The wrapper now sets its reply-pickle module layout from the client's
own request, so LeIsaac (0.4.2 layout) and stock 0.4.x clients both work. Bench quick-start (operator at the Acer):
  1. from the Acer: `nc -vz 192.168.194.220 8080` (or `python -c "import socket;print(socket.create_connection(('192.168.194.220',8080),5))"`)
  2. a LeRobot 0.4.x env with lerobot[feetech], grpcio, opencv; copy bench_client.py; `--dry-run` first (reads cameras +
     arm, queries the policy, moves nothing; prints state vs first action per chunk)
  3. then `--episodes 1 --max-chunks 90`, non-pipelined, per-step clamp 8° / gripper 15, q or ESC stops.
  Wrapper on AI90 records every frame it receives (RECORD_EVERY=1) under results/so101_bench_20261019/frames/.

## Build order (agreed 2026-10-20)
W0 the shared policy wrapper (A1 below) → R2 closed-loop sim gate (R plan) → R3a transport adapter + G1/G3/G4
→ R3 bench. R2 goes before the transport work because it is the cheapest closed-loop evidence and a bad
result there means a plumbing bug to fix before anything else.

## Build record — policy wrapper (W0), 2026-10-20
- scripts/so101_base_policy_server.py: subclass of LeRobot 0.4.1's gRPC PolicyServer with LeIsaac's pickle
  module aliases; loads the VLASH π0.5 once, maps front→base_0_rgb / wrist→left_wrist_0_rgb / six .pos → state,
  bypasses LeRobot's pre/post-processors (VLASH normalises itself); unit so101-base-server, GPU 1, :8080.
- LeIsaac's client connected and exchanged policy instructions on the first attempt.
- Gotcha 3: `compile_model=True` (the author's bench setting) RETRACES on every call in this loop — 415 s per
  call, i.e. unusable — so the wrapper serves EAGER (137 ms/call). For the bench, compile would have to be
  made shape-stable (fixed prompt tokenisation, static shapes) or left off; in sim it does not matter.

## The adapter (on AI90, ~1 day)
```text
A1  a policy wrapper the draft server can load: type "vlash_pi05" → VLASH PI05Policy (author's patches,
    empty_cameras=1, compiled) exposing predict_action_chunk(obs[, delay, prefix]); slot mapping
    front→base_0_rgb, wrist→left_wrist_0_rgb; state/action 6-D as recorded; chunk 50 → return 20
A2  Client mode — DEFINITIONS LOCKED 2026-10-20 (operator):
      NON-PIPELINED (stop-and-wait): execute the whole chunk, stop, send the observation, wait for the
               reply, execute. No overlap, no guessing at the join. Latency costs TIME (duty = chunk /
               (chunk + round trip)), not correctness, on a STATIC bench; it also makes the arm stop-start.
      PIPELINED: send the next request while actions remain, timed to arrive before the current chunk
               runs out; the arm never stops, but the new chunk was planned from an earlier observation
               and without knowing what the arm did since → the join is a GUESS unless the model is told
               the committed actions. That is what RTC (guided or trained) does.
      RULE: pipelined only WITH RTC; without RTC we run non-pipelined. R3 default = NON-PIPELINED.
      EVIDENCE: in LIBERO, executing the whole chunk before asking again scored 198/200 vs 199/200 for
      replan-every-5 (L6b, 2026-10-20) — the stop-and-wait pattern costs no success in a static scene.
      ACCEPTED COST (operator 2026-10-20): the non-pipelined client will be slower and stop-start; that is
      fine for R3 — we are testing whether the task gets done, not how smoothly. Success criterion and the
      time cap are set for a stop-and-wait arm (see R3 protocol); speed is recorded, not judged.
      The word "pipelined" is reserved for the definition above and not used loosely elsewhere.
      RTC inside the adapter: guided RTC (LeRobot's prefix-conditioned denoising) only if VLASH's sampler
      exposes its loop cleanly — a later step, not R3's first run.
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
                      the operator to run one command) → true end-to-end latency per call and jitter; for the
                      NON-PIPELINED client this gives the duty cycle = 667 ms / (667 + RTT) and the wall time per
                      attempt — a speed cost, not a correctness cliff (L6's cliff applies to clients that keep
                      moving during the wait, i.e. pipelined without RTC).
G2b closed loop, sim  the same policy wrapper drives the LeIsaac orange task for 50+50 seeded episodes
                      (R2 in the R plan): compounding error, grasp timing, release — the step the replay
                      cannot test; the corpus holds ~200 LeIsaac orange episodes, so this is in-distribution
G4  fault cases       dropped frame, stale delay hint, client reconnect → server stays up, timing logged
G5  the bench         20 trials, NON-PIPELINED (A2), frames recorded server-side (R3 proper).
                      STARTED 2026-10-19: trial 1 ran from the Acer over ZeroTier, median 0.92 s per call,
                      FAIL (reach OK, grasp beside the fruit) — record in results/so101_bench_20261019/bench_runs.md.
                      G1/G2/G4 were not run: the live dry run from the Acer (real cameras, real state, policy
                      output within 1–2 units of the pose) and the trial itself covered what they would have shown.
```
Outputs: results/so101_bench_adapter_20261020/{g1_loopback.json, g2_openloop_ep*.json, g3_remote_acer.json}
and a run record here. Cost: ~1 day build + 2 h verification; GPU 0 (9 GB) while serving.

## What it will and will not tell us
WILL  the bridge works end to end at the real latency, before anyone stands at the arm;
      whether the public model's actions on OUR frames track OUR recorded demonstrations.
WON'T whether it picks the orange. Open-loop agreement is necessary, not sufficient — only G5 answers that.
