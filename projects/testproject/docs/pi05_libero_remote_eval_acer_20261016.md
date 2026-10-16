# L6 — LIBERO evaluation with the simulator on the Acer and the policy on AI90 (over ZeroTier)

Date: 2026-10-16. Status: **AI90 side UP (server unit l6-remote-server, port 8007); Acer side
BLOCKED on SSH access (AI90's key is not authorised on the Acer) — operator action below.**

## What and why
Same LoRA policy (lora_libero_20261010 step 20000, our best: 199/200 local), same evaluation loop
(l2_eval_openpi.py, their convention, logged), same 200 episodes (Spatial, layouts 0-19, seed 7,
replan 5 of 10, 230-step cap) — but the SIMULATOR runs on the Acer laptop in India and every
policy call crosses ZeroTier to AI90's GPU 0 in New Jersey. Two things it tells us that the local
rows cannot: (1) the policy's success rate is unchanged by remote serving (it should be: the sim
waits for each action chunk, so latency cannot change outcomes), (2) the real per-call latency
of serving a π0.5 policy across the internet — the number that matters for the arm-side plan
(O3: real arm with RTC on, policy possibly remote). An earlier attempt of this kind (a loopback
server on AI90 started 2026-10-16 04:34Z from the laptop, folder openpi-full-benchmark-20261016)
never received a client; no record exists of what failed on the Acer side.

## Pre-registered reading
success: within the n=200 interval of the local 199/200 (CI 97.2-99.9) → "remote serving does
not change the policy". Latency: report median and p95 of (a) network round trip, (b) server
compute (~60 ms locally), (c) end-to-end per call; and wall-clock per episode vs local (~2-5 s).
Anything outside → investigate, do not pool with local rows.

## How (both halves are scripts in results/pi05_libero_20261010/)
AI90: `l6-remote-server` systemd user unit — serve_policy.py, LoRA 20k, GPU 0, port 8007, binds
      0.0.0.0 (reachable at 192.168.194.220:8007 over ZeroTier). Log: l6_remote_server.log.
Acer: `l6_acer_bootstrap.sh` — uv + Python 3.12 venv, LIBERO (same fork/pin as AI90's probe
      venv), openpi-client (copied from AI90's openpi checkout), MuJoCo with EGL/OSMesa; then
      `l6_acer_run.sh` — l2_eval_openpi.py --host 192.168.194.220 --port 8007 --suite
      libero_spatial --trials-per-task 20 --row lora20k_remote_acer, results copied back to
      AI90 results/L6_lora20k_remote_acer_spatial_n200/.
Output per episode adds: rtt_ms (TCP ping to AI90 at episode start), infer_s per call.

## Operator action needed (one-time)
On the Acer, authorise AI90's key so I can drive the laptop side:
  mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '<AI90 pubkey, see chat>' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
Then say "key added". Alternative: run l6_acer_bootstrap.sh and l6_acer_run.sh yourself on the Acer.

## Gates
G1 Acer reachable + SSH works. G2 LIBERO env renders one frame on the Acer (CPU/EGL). G3 one
episode end-to-end (policy call returns 10×7 chunk). G4 n=200. Each gate logged in l6_acer.log.

## Cost
Acer: CPU-only sim, ~1-2 GB venv + ~1 GB LIBERO assets. AI90: GPU 0 ~9 GB for the server.
Per call ~0.3 s network + 0.06 s compute → ~5× slower episodes than local: ~1-1.5 h for 200.
