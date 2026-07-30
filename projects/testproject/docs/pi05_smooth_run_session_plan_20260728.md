# Pi05 Smooth-Run Session Plan (smoke run + full attempt)

Last updated: 2026-07-28

This is the execution plan for the next robot session. It follows the first
successful grasp (2026-07-28) and the smoothness fixes implemented the same
day. Background:

```text
projects/testproject/docs/pi05_012000_first_successful_grasp_20260728.md
  (section 5: stutter root cause + the two fixes)
```

## 0. What This Session Answers

```text
1. Do the fixes work live? (JPEG observations + decoupled observation thread)
   Success = smooth ~30 Hz motion, chunk latency ~0.6 s.
2. Does smooth motion unlock the place/release phase?
   If yes: full task solved with the existing checkpoint.
   If no: the place failure is a DATA gap -> record place-heavy demos next.
```

The session is staged: pod patch (no robot) -> 30 s smoke run -> full attempt.
One sitting, ~30-40 min of pod time (~$0.30 at $0.50/hr).

## 1. Preconditions (verify before starting)

```text
pod started; get current IP/PORT from the RunPod Connect tab (they migrate)
user physically at the arm for both robot steps
laptop in its training position (it IS the front camera)
table cleared of non-training objects (no phone)
lights on
orange placed as in training
follower arm on /dev/ttyACM0 (serial 5B14114209)
camera devices verified:  v4l2-ctl --list-devices
  top   = C270 (by-id path already in config/so101.json)
  front = ACER built-in (by-id path already in config)
  wrist = Pi camera via laptop-side proxy
```

## 2. Step 1 - Pod Patch (no robot, one-time)

The pod's policy_server is old code and cannot decode JPEG observations yet.

```bash
# from the laptop repo root:
bash projects/testproject/scripts/runpod/apply_jpeg_decode_patch.sh <POD_IP> <POD_PORT>
# expect: "pod policy_server patched OK" (or "already patched" on rerun)
```

## 3. Step 2 - Services Up

```bash
# 1. wrist proxy (runs ON THE LAPTOP; SSHes to the Pi and serves 127.0.0.1:8092)
ssh raspi@192.168.1.14 'sudo systemctl stop timelapse.service'
cd projects/testproject && nohup .venv/bin/python tools/pi_wrist_proxy.py \
  --pi-host raspi@192.168.1.14 --pi-ip 192.168.1.14 > /tmp/wrist_proxy.log 2>&1 &
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8092/frame   # expect 200

# 2. policy server on the pod
ssh root@<POD_IP> -p <POD_PORT> -i ~/.ssh/runpod_ed25519 \
  'HF_HOME=/workspace/hf_cache nohup /workspace/venv312/bin/python -m lerobot.async_inference.policy_server --host=0.0.0.0 --port=8080 --fps=30 > /workspace/logs/policy_server_smooth_test.log 2>&1 &'

# 3. tunnel (keep running)
ssh -N -L 8080:localhost:8080 -p <POD_PORT> -i ~/.ssh/runpod_ed25519 root@<POD_IP>
```

## 4. Step 3 - Smoke Run (~30 s of motion, then stop)

Purpose: verify smoothness numbers only. Not trying to complete the task.
Gripper open (~40-55) anyway, in case it reaches quickly.

```bash
cd projects/testproject/scripts && ../.venv/bin/python async_client_3cam.py \
  --policy-type pi05 \
  --ckpt /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model \
  --chunk-size-threshold 0.85 \
  --max-relative-target null \
  --jpeg-quality 92 \
  --trace-dir ../artifacts/traces/smoke_smooth_$(date +%Y%m%d_%H%M%S)
# let it move ~30 s, then Ctrl-C (or kill the process)
```

PASS criteria (from the smoke trace, before proceeding):

```text
executed-action gap p95 < 0.1 s      (was ~2.4 s before the fixes)
chunk server->client latency < 800 ms (was ~1840 ms)
observations arriving every ~0.3-0.5 s
no motor-bus errors in the client output (threading check)
```

FAIL handling:

```text
latency still high      -> check the pod patch actually applied; check tunnel
stalls remain           -> read client output; the obs thread may be crashing;
                           fall back: drop --jpeg-quality (raw) to isolate
                           which fix misbehaves
bus errors / weird arm  -> stop immediately; the robot_lock needs review;
                           do NOT proceed to the full run
```

## 5. Step 4 - Full Attempt (only if smoke PASSES)

```text
reset: orange back to a training-like spot, arm to start pose,
       gripper opened to state ~40-55
```

Same client command with a fresh --trace-dir name (e.g. full_smooth_...).
Let it run through grasp -> lift -> carry -> place. Stop when the orange is
placed and released, or when it clearly loops (>~700 actions like last time).

## 6. Step 5 - Wrap Up (always)

```bash
# stop client (Ctrl-C), then:
pkill -f pi_wrist_proxy
ssh raspi@192.168.1.14 'sudo systemctl start timelapse.service'
# stop tunnel; stop policy server or just stop the pod from the console
```

Then analyze the traces (same method as before: executed-action gaps, gripper
close/hold, chunk latency) and write the results doc.

## 7. Decision Tree After The Full Attempt

```text
grasp + place succeed:
  -> task solved with existing checkpoint 012000. Document. Optionally do
     2-3 repeat runs for a success rate before calling it reliable.

grasp succeeds, place still fails (smooth motion, good latency):
  -> place failure is a DATA gap (focus windows emphasized grasping).
     Next project: record 15-25 place-emphasis demos, build a place-focus
     dataset, fine-tune from 012000, gate offline (on the POD environment,
     never the laptop), then re-test.

grasp now fails (regression vs yesterday):
  -> compare the new trace against yesterday's successful one
     (official_async_3cam_012000_fixed_20260728_021800) - same analysis
     method; suspect the changed variables first (jpeg, obs cadence 0.3 s,
     threading), and fall back one fix at a time.
```

## 7b. SESSION RESULTS (2026-07-29)

Smoke run: PASS decisively.

```text
action-gap p95 33 ms (was ~2400) | 23.3 Hz (was 2.2) | latency 974 ms (was 1839)
trace: smoke_smooth_20260729_000607
```

Full attempts: NO grasp secured this session. Root causes found, in order of
discovery (each with trace evidence):

```text
1. Smoke run object was an ONION, not the orange (user confirmed) - model
   approached but missed: partial generalization to unseen objects noted.
2. Orange placement off-distribution (nestled against the arm bracket) in the
   first full attempt: 18 misses. placement_comparison.png.
3. CHUNK-CYCLING failure mode discovered: at obs cadence 0.3-0.4 s, fresh
   chunks interrupt closes in progress; grip-and-release loops. Calmed by
   obs_min_interval 0.8-1.5 s (our client's knob, not a lerobot default).
4. TOP CAMERA HAD PHYSICALLY MOVED since the successful run (closer/lower) -
   biased spatial reading, systematic too-high/lateral misses in every
   attempt. Confirmed by user's phone videos (fingers at orange crown, not
   equator). Fixed by re-aiming to match reference; verified.
   -> NEW STANDING GATE: before every session, capture the top camera and
   visually match it against the successful run's first frame
   (official_async_3cam_012000_fixed_20260728_021800/images/top first jpg).
5. SPEED: arm runs ~2x demo speed with occasional 70-114 unit single-step
   snaps (training max 6.5). Mechanism confirmed in official code: actions
   whose timestep expired in transit are discarded on arrival
   (robot_client aggregation), so ~60% of every chunk is skipped at ~1 s
   latency and the arm fast-forwards. This IS lerobot-default behavior under
   high latency; max_relative_target=None (uncapped) is the official
   follower default. User chose to keep pure defaults.
```

Final attempt (fixed camera, clean scene, defaults): the closest miss of the
day - contact, strong close, partial lift, orange slipped out; then retry
loop. Trace: final_attempt_* of 2026-07-29.

Session verdict:

```text
The smoothness fixes work and are permanent wins. Live grasping with this
checkpoint is highly sensitive to (a) exact top-camera pose, (b) object
placement, (c) execution speed vs demo speed. Success rate with 012000
across all live attempts so far: 1 grasp+carry (2026-07-28) in ~7 tries.
```

Recommended next steps, in order:

```text
1. Camera-reference gate before every run (now standing).
2. Attack the speed/latency properly WITHIN official designs: investigate
   lerobot's RTC (real-time chunking, rtc_config in PI05Config) - built
   exactly for high-latency serving; or find a lower-latency GPU (nearer
   region / local).
3. If grasp reliability stays poor after speed is fixed: record 15-25 fresh
   demos (grasp emphasis + place emphasis + slight camera-pose variation for
   robustness) and fine-tune from 012000.
```

## 8. Standing Rules (unchanged)

```text
three cameras verified before every run; stale /dev/videoN numbers are the
  known trap - use v4l2-ctl --list-devices
gripper open 40-55 at start - closed-ish starts trigger false grasps
official LeRobot client/server only; trace always enabled
no commits of traces/artifacts; docs-only commits
user present at the arm for all robot motion
```
