# Pi05 Live Deployment Mismatch Investigation Plan

Last updated: 2026-07-28

Active plan. Supersedes the retrain plan (on hold) and the offline comparison
plan (answered). Evidence basis:

```text
projects/testproject/docs/pi05_012000_pod_evidence_correction_20260728.md
```

## 1. The Question

```text
012000 predicts close/hold/lift correctly on training-style focus frames
(pod evidence, gripper corr 0.83, better than 003000 on every joint).
The same checkpoint failed twice on the real arm:
  trace 230756: no strong close at all near the orange
  trace 233341: strong close only at t=0-84 (too early), open near the orange
Why does a model that grasps correctly offline fail live?
```

Candidate explanations, in current likelihood order:

```text
A. Live observations differ from training observations
   (camera geometry/angles, camera key mapping top/front/wrist, image
   resolution/format, start pose, start gripper state)
B. Live state drifts off-distribution and the policy cannot recover
   (compounding error: small early deviations lead to states never seen in
   the 89 training episodes)
C. Live serving path alters observations or actions
   (policy server processing, chunk switching, timing/latency)
```

## 2. Phase 0 - Pod Prerequisites

```text
1. Repair the migrated venv (interpreter died with the old container):
     install uv on the pod, then: uv python install 3.12.13
     verify: /workspace/venv312/bin/python -V  -> 3.12.13
     (site-packages on /workspace are intact; do NOT reinstall packages)
2. Do NOT update /workspace/lerobot. It is the training-era code (e40b58a8)
   and the only environment proven to replay this checkpoint correctly.
3. Disk cleanup per user decision 2026-07-28: keep only restart 009000 and
   012000 checkpoints on the pod; expert 003000 archived to the laptop at
   projects/testproject/artifacts/checkpoints/pi05_orange49_plus_grasp_focus_expert/003000/;
   logs and compare outputs archived at
   projects/testproject/artifacts/pod_archive_20260728/.
4. Pod costs $0.50/hr while running. Stop it between work sessions;
   /workspace persists.
```

## 3. Phase 1 - Trace Replay (the decisive experiment, no robot)

The two failure traces recorded the observations the live policy server
received. Replay them through 012000 on the pod, in the training-era
environment, and compare with the chunks the server returned live.

```text
inputs: projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_230756
        projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_233341
        (upload the observation payloads to the pod)
method: for each traced observation, run the saved pre/post processors +
        predict_action_chunk with 012000, same as the July 22 comparison
        script; compare with the live-returned chunk stored in the trace
```

Interpretation:

```text
offline(trace obs) == live chunks (within sampling noise):
  -> the model answered its inputs faithfully; the INPUTS are the problem
  -> go to Phase 2 (input comparison)

offline(trace obs) != live chunks:
  -> the live serving path altered something
  -> inspect policy server processing, versions, dtype, chunk handling (C)
```

Secondary check in the same run: for trace observations near the orange,
does 012000 predict close when given those images? If it never closes on
live images but closes on training images, the images differ in a way that
matters (strong evidence for A).

## 4. Phase 2 - Input Comparison (laptop, free)

Compare traced live observations against training frames, feature by feature:

```text
images:
  camera key mapping: does live "top" look like training "top", etc.
    (a swapped top/front mapping would explain a lot and is cheap to check)
  geometry: camera positions/angles/crops vs training views
  format: resolution, color order, exposure
state:
  start gripper state: live vs training start (~40-55 open expected)
  full start pose vector vs training episode starts
  wrist_flex trajectory divergence point: when does live state leave the
    training distribution? (earlier analysis: live wrist_flex ~-1 vs demo ~91)
task:
  exact task string equality between live client and dataset
timing:
  observation->chunk->execution latency; how many actions execute per chunk
  before a new chunk arrives (fresh-obs rate vs training fps)
```

Output: a table of concrete mismatches, each marked fixable-by-setup vs
needs-data/training.

## 3b. Phase 1 Results (2026-07-28: trace replay on pod, training-era env)

All 58 traced observations from both failure runs were replayed through 012000
on the pod GPU. Artifacts: /workspace/trace_replay/*/replayed_chunks.jsonl
(copies in local scratch; summary below).

RESULT 1 - the serving path is CLEARED:

```text
Replay reproduces the live chunks. Examples (live vs replay, different noise):
  230756 obs0: live first gripper 30.6 vs replay 30.4
  233341 obs0: live first gripper -4.0 vs replay -3.7 (the instant full close)
The live policy server faithfully computed what the model says for its inputs.
Explanation C (serving path alters things) is eliminated.
```

RESULT 2 - the model DOES intend to grasp, but plans the close in the part of
the chunk that async execution never runs:

```text
Run 230756, near-orange observations (obs 21-24):
  predicted min gripper 29-46, located at chunk offsets 43-49 of 50.
With chunk_size_threshold=0.5 and 1.4 s latency, roughly only the first ~25
actions of each chunk execute before replacement. Offsets 40+ NEVER run.
So the close was perpetually postponed: hover -> stale obs -> new chunk with
close again at the tail -> hover. Matches the live outcome exactly
(422 executed actions, zero strong close).
```

RESULT 3 - the early-close of run 233341 is a start-state effect:

```text
Start gripper state was 21.2 (nearly closed). Given that state, the model
immediately predicts full close (-4 at offset 0) - reproduced in replay.
The model conditions strongly on the current gripper state: "already mostly
closed" reads as "grasp in progress, finish closing".
```

CAUSAL STORY (complete, all evidence consistent):

```text
The model is fine. Two deployment defects caused both failures:
1. Chunk latency (1.4 s) + threshold 0.5 starves the queue, stutters the arm,
   and discards the chunk tails where the model schedules the close.
2. A partially-closed start gripper triggers a false "finish the grasp" close.
```

Phase 3 fix set (needs user approval for the config change):

```text
- raise chunk_size_threshold to ~0.85 so a new chunk is requested ~1.5 s
  before the queue drains (> 1.4 s latency): continuous 30 Hz motion, no
  starvation, observations converge, the planned close migrates to the chunk
  head where it actually executes
- start with the gripper open (state ~40-55), per the existing checklist
- start the Pi wrist proxy (port 8092) - port 8000 is now a timelapse server
- room lights on; re-verify top/front framing before the run
- CAMERA IDENTITY (user-confirmed 2026-07-28, do not trust old device numbers):
    top   = Logitech C270 HD WEBCAM (external USB; was /dev/video0, is
            /dev/video4 as of 2026-07-28 - numbers move between boots/replugs)
    front = laptop built-in camera (ACER FHD User Facing; owns /dev/video0-3
            as of 2026-07-28)
    wrist = Raspberry Pi camera via wrist proxy (raspi@192.168.1.14)
  Before every live run: `v4l2-ctl --list-devices`, then point the config at
  the C270 node for top and an ACER node for front. Stale numbers from an old
  manifest would feed the model the wrong views silently.
  Webcams need warmup for auto-exposure (top used warmup_s: 3) - first frames
  after opening are dark; this is normal, not a broken camera.
- Camera check result 2026-07-28 (with lights on, correct devices):
    top (C270 @ /dev/video4): WORKS, framing close to training, but an iPhone
      was lying in the field of view - clear the table of non-training objects
    front (laptop built-in): WORKS but currently faces the USER. The laptop
      must be physically placed in its training position facing the robot and
      table before the run - the laptop IS the front camera.
    wrist (Pi): verified, matches training framing.
  Contact sheet: artifacts/pod_archive_20260728/camera_check_final_20260728.png
```

## 4b. Phase 2 Findings (2026-07-28, from the two failure traces + live cameras)

Checked and CLEARED:

```text
camera key mapping: correct. Live top/front/wrist match training top/front/wrist
  (contact sheet: artifacts/pod_archive_20260728/camera_comparison_train_vs_live.png)
camera geometry: broadly matches training framing; live images slightly dimmer
task string: identical to dataset ("pick up the orange and move it to another place")
start arm pose: all joints within training start ranges in both runs
camera hardware today: laptop top/front capture OK (room was dark at check
  time - re-verify framing with lights on), Pi wrist capture OK and matches
  training framing. Pi note: port 8000 now runs a timelapse server, NOT the
  wrist proxy (proxy script expects port 8092); wrist proxy must be started
  before any live run.
```

FINDINGS (mismatches, in severity order):

```text
1. CHUNK LATENCY STARVES THE ACTION QUEUE  (severe, quantified)
   server->client chunk latency: median 1392 ms, p90 1540 ms, max 6505 ms
   client requests a new chunk at chunk_size_threshold=0.5 -> when 25 actions
   (0.83 s at 30 fps) remain. 0.83 s < 1.4 s latency -> queue drains to 0
   every cycle.
   Measured effect: executed-action interval median 0.033 s but p95 ~1.05 s;
   effective execution ~9 Hz vs 30 Hz training; queue_size min 0 in both runs.
   The arm moved in a stutter: ~0.8 s motion, ~0.5-1 s freeze, repeat. Every
   chunk was computed from an observation ~1.4+ s stale by the time its
   actions ran. Training demos were continuous 30 Hz - the policy never saw
   stop-start dynamics or stale-observation states.

2. START GRIPPER STATE LOWER THAN TRAINING MEAN  (moderate)
   run 230756 start gripper: 28.6 | run 233341: 21.2 | training mean: 39.1
   (both technically inside the training min/max range, but 21.2 is nearly
   closed; run 233341 - which started most-closed - is the run that "closed"
   immediately at t=0-84)
```

Implication for Phase 3: the latency mismatch is fixable with official knobs
(e.g. raising chunk_size_threshold so chunks are requested ~1.5 s before the
queue empties, and/or reducing server inference latency); the start gripper
must be opened to ~40-55 before starting. Any config change needs user
approval per standing rules.

## 5. Phase 3 - Corrected Live Re-Test (only after Phases 1-2)

One real-arm run fixing every mismatch found, under the standing gates:

```text
official LeRobot async, three cameras (top /dev/video0, front /dev/video2,
wrist /dev/video6 via Pi bridge), robot.max_relative_target=null, read-only
trace enabled, arm in original-episode start pose, gripper visibly open
(first observed gripper state ~40-55)
```

If it still fails with verified-matching inputs, the remaining explanation is
distribution drift (B) - then the fix IS training-side (e.g., more varied
demos, noise-augmented starts), and the retrain plan comes off hold with a
different goal than "train longer".

### 5b. Runbook (prepared 2026-07-28, all prep verified)

Prep already done and verified:

```text
config/so101.json updated: top/front cameras now use stable /dev/v4l/by-id
  paths (C270 = top, ACER built-in = front), wrist_camera_url =
  http://192.168.1.14:8092/frame
scripts/async_client_3cam.py extended with --policy-type and --trace-dir
  passthrough (was hardcoded to act, no tracing)
dry-run (--print-only) verified: correct devices, pi05, threshold 0.85,
  max_relative_target null, trace enabled
pi_wrist_proxy.py deployed to raspi@192.168.1.14:/home/raspi/
cameras visually verified against training views (top/front/wrist all match;
  laptop repositioned; table cleared)
follower arm present on /dev/ttyACM0 (serial 5B14114209)
```

Test-time sequence:

```bash
# 1. Pi: free the camera and start the wrist proxy (timelapse restarts after)
ssh raspi@192.168.1.14 'sudo systemctl stop timelapse.service && nohup python3 /home/raspi/pi_wrist_proxy.py > /tmp/wrist_proxy.log 2>&1 &'
curl -s -o /dev/null -w "%{http_code}\n" http://192.168.1.14:8092/frame   # expect 200

# 2. Pod (verify IP/port from RunPod Connect tab first - pods migrate):
ssh root@<POD_IP> -p <POD_PORT> -i ~/.ssh/runpod_ed25519 \
  'HF_HOME=/workspace/hf_cache nohup /workspace/venv312/bin/python -m lerobot.async_inference.policy_server --host=0.0.0.0 --port=8080 --fps=30 > /workspace/logs/policy_server_fixed_test.log 2>&1 &'

# 3. Laptop: SSH tunnel (keep running)
ssh -N -L 8080:localhost:8080 -p <POD_PORT> -i ~/.ssh/runpod_ed25519 root@<POD_IP>

# 4. Physical setup: orange placed as in training, arm in start pose,
#    GRIPPER OPENED so its state reads ~40-55, lights on, table cleared.

# 5. Client (laptop):
cd projects/testproject/scripts && ../.venv/bin/python async_client_3cam.py \
  --policy-type pi05 \
  --ckpt /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model \
  --chunk-size-threshold 0.85 \
  --max-relative-target null \
  --trace-dir ../artifacts/traces/official_async_3cam_012000_fixed_$(date +%Y%m%d_%H%M%S)

# 6. After the run: restart the Pi timelapse
ssh raspi@192.168.1.14 'sudo systemctl start timelapse.service'
```

Success criteria for this run:

```text
first traced observation gripper state in 40-55
executed-action p95 interval < 0.1 s (no starvation stalls; was ~1.05 s)
strong close (<=25) executed near the orange
pick/lift achieved, or if not: trace analysis per Phase 1 method
```

## 6. Side Track (optional, laptop): Fix Local Replay

The laptop cannot currently gate checkpoints (newer lerobot code breaks this
checkpoint's replay). Two options, low priority:

```text
1. Pin a laptop venv to lerobot e40b58a8 for replay/gating only.
2. Bisect upstream between e40b58a8 and current main to find the breaking
   change; report upstream if it is a real backward-compat bug.
```

Until fixed, all offline gating runs on the pod, in the training-era env.

## 7. Standing Rules (unchanged)

```text
No real-arm runs before Phases 1-2 produce findings, unless the user
explicitly approves a diagnostic run.
No 2-camera evaluations as clean results.
Official LeRobot defaults; no custom movement scripts without approval.
No committing artifacts; no tokens anywhere.
```
