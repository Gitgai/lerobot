# L6 — Does inference latency change the policy's success? (LIBERO, time-faithful mode, delay sweep)

Date: 2026-10-16/17. Status: **building; sweep to run on AI90 (GPU 0, LoRA 20k server on :8007).**
Supersedes the first version of this doc (sim on the Acer, policy on AI90), dropped 2026-10-17
after discussion: a frozen-time simulator cannot show a latency effect at any distance, and the
real operating latency is already known.

## The question
Serving π0.5 from AI90 to a robot elsewhere costs **300-500 ms per call end to end (operator's
measured figure, inference included)**. Does that delay change what the policy achieves? The
standard LIBERO protocol cannot answer it: the simulator pauses while the policy thinks, so every
row so far assumes an infinitely fast brain. A simulator's job is to stand in for the world, and
time is part of the world — so we give the loop a time-faithful mode and sweep the delay.

## Design (l2_eval_openpi.py --latency-mode realtime, added 2026-10-17)
- Control runs at 20 Hz (LIBERO: one env.step = 50 ms). A query issued at step tq with injected
  delay D arrives at step tq + ceil(D/50 ms). The world keeps stepping in between.
- Query cadence unchanged: every 5 steps (openpi's replan_steps), at most one request outstanding.
- While waiting, the arm executes what is left of the previous chunk; if that runs out it HOLDS
  (zero position/rotation deltas, gripper command unchanged). Holds are counted (n_hold).
- On arrival the new chunk is adopted from index d ("skip": actions whose time has passed are
  dropped — what a timestamped async client does). "replay" (execute stale actions from 0) is
  available as a flag, not used in the main sweep.
- Delay is INJECTED, deterministic; the real local call time (~60 ms) is spent but not counted,
  so rows depend only on D. At D = 0 the mode reduces exactly to the frozen protocol (gate G1).
- openpi has no RTC; LoRA 20k policy (our best, 199/200 frozen), Spatial, layouts 0-19, n=200/row.

## Sweep and pre-registered reading
D (ms):  0 (gate)  100  250  500  1000       d (steps): 0 2 5 10 20
- G1: D=0 realtime within the CI of frozen 199/200 (97.2-99.9) → mode is faithful; else stop.
- Operating point 300-500 ms: the 250 and 500 rows bracket it.
- 500 ms = 10 steps = the whole 10-step chunk: with "skip" nothing of a chunk is usable on
  arrival → expected to collapse (every step a hold). 1000 ms likewise. Reporting them states the
  plain-chunking limit; they are not a prediction about RTC.
- Readings: success vs D (curve + knee), holds per episode, steps to success. Rows go in their own
  table (different protocol) — NEVER pooled with the benchmark rows.
- Follow-up when the orange/LeIsaac stage runs with LeRobot: the same sweep with RTC on (guided),
  which is what RTC exists for; the difference between the curves is what RTC buys back.

## How
results/pi05_libero_20261010/l6_delay_sweep.sh — systemd user unit l6-delay-sweep; server unit
l6-remote-server (serve_policy.py, LoRA 20k, GPU 0, :8007). Outputs
L6_delay{D}ms_lora20k_spatial_n200/{per_episode.jsonl,summary.json}; log l6_delay_sweep.log.
Cost: ~10 min per row locally (holds make episodes hit the 230-step cap → ~15 min) → ~1.2 h.
