# G485 Serving Bring-Up Plan (replace RunPod with the RTX 5090)

Created: 2026-08-05
Status: PLAN - not yet executed
Related: `agent_handoff_pi05_20260803.md` (project state),
`pi05_generalization_roadmap_20260802.md` (what the runs are FOR)

Goal: serve checkpoint 012000 from the G485 box (RTX 5090, USA) to the robot
(laptop + arm + 3 cameras, India), retire RunPod, and reach the first real
experiment - the subtask-switching probe - without repeating Era 1.

---

## 0. Verified Starting State (checked 2026-08-05)

```text
G485 (kiran@192.168.194.158, hostname kiran-G485, USA)
  GPU ................. RTX 5090, 32 GB VRAM, driver 595.84, idle
  CPU / RAM ........... 24 cores, 61 GB (54 GB free)
  disk ................ 1.8 TB, 1.7 TB free
  checkpoint .......... ~/lerobot_assets/checkpoints/pi05_012000  (8.8 GB) OK
  training-era code ... ~/lerobot_assets/lerobot_trainingera @ e40b58a8 OK
                        (exactly the commit the checkpoint was trained on)
  venv ................ ~/lerobot_assets/lerobot_trainingera/.venv OK
  RTC server adapter .. APPLIED (4 hits for _init_rtc_from_env/_rtc_inference_kwargs)
  JPEG decode patch ... *** MISSING *** <- the one real blocker
  policy server ....... NOT running (an earlier "running" report was a
                        pgrep self-match on our own SSH command string)

LAPTOP (gaikwad-prakash, India)
  follower arm ........ OK - 6 motors, model 777, 0.00 deg drift, no serial glitch
  leader arm .......... NOT CONNECTED (needed for Stage 2 recording, not for this plan)
  top camera C270 ..... OK 640x480 MJPG
  wrist camera ........ OK - Pi back on LAN at 192.168.1.28 (was .15), 52 KB frames
  front camera ........ BLOCKED - /dev/video0 held by Chrome
  venv ................ CPU torch, editable lerobot - client only, correct

LINK (India <-> USA over ZeroTier, path is DIRECT not relayed)
  RTT ................. ~255 ms (physics; not fixable)
  throughput .......... ~1 MB/s (Indian broadband upload is the limit)
  implication ......... JPEG observations are MANDATORY. Raw 2.77 MB would
                        take ~3 s per observation = unusable.
```

---

## Phase 1 - Server-side prep on G485

### 1.1 Apply the JPEG decode patch (BLOCKER)

The existing script `scripts/runpod/apply_jpeg_decode_patch.sh` is hardcoded
for the pod (`root@ip -p port`, `/workspace/lerobot`, runpod key). Generalize
it, or run the same two steps manually against G485:

```bash
G485=kiran@192.168.194.158
AI=/home/kiran/lerobot_assets/lerobot_trainingera/src/lerobot/async_inference

# 1. ship the codec module the server needs
scp src/lerobot/async_inference/image_codec.py $G485:$AI/image_codec.py

# 2. patch policy_server.py to decompress incoming observations
#    (same anchors as the pod patch: the `from .configs import
#     PolicyServerConfig` import, and the `pickle.loads(received_bytes)` line)
```

```text
Idempotent - the patch checks for 'decompress_observation_images' and exits if
already present. It writes a .bak once. VERIFY after:
  ssh $G485 "grep -c decompress_observation_images $AI/policy_server.py"   -> >0
```

### 1.2 Confirm the venv can import the server

```bash
ssh $G485 '~/lerobot_assets/lerobot_trainingera/.venv/bin/python -c \
  "import lerobot, torch; print(lerobot.__file__); print(torch.__version__, torch.cuda.is_available())"'
```

```text
Expect: path under lerobot_trainingera/src/lerobot   <- pinned code, NOT a
        pip-installed lerobot, and NOT the laptop's newer code
        torch with cuda True
```

### 1.3 Decide network exposure

The client must reach the server over ZeroTier at `192.168.194.158:8080`.

```text
Bind: --host=0.0.0.0  (server listens on all interfaces incl. ZeroTier)
Check firewall on G485:  sudo ufw status
  If ufw is active, allow 8080 ON THE ZEROTIER INTERFACE ONLY:
    sudo ufw allow in on ztugarqtxd to any port 8080 proto tcp
  Do NOT open 8080 to the public internet - the server accepts pickled
  payloads and must only be reachable over the private ZeroTier network.
```

---

## Phase 2 - Start the server and prove connectivity

```bash
# ON G485 (keep in a screen/tmux so it survives the SSH session)
cd ~/lerobot_assets/lerobot_trainingera
RTC_ENABLE=1 RTC_EXEC_HORIZON=35 \
  .venv/bin/python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 --port=8080 --fps=30
```

```text
Gate 2a - server is listening:
  ssh $G485 'ss -tlnp | grep 8080'                       -> a LISTEN line
Gate 2b - reachable from the laptop:
  timeout 5 bash -c "echo > /dev/tcp/192.168.194.158/8080" && echo REACHABLE
Gate 2c - keep RTC_EXEC_HORIZON=35. The latency it compensates for is now
  geography, not a pod. Do not tune it in the same session as anything else.
```

Note: no SSH tunnel. ZeroTier already provides the private path, and the
tunnel was our single most frequent failure (died 3x in one evening).
Client flag becomes `--server 192.168.194.158:8080`.

---

## Phase 3 - OFFLINE TRUST EXAM (do not skip - this is the Era 1 gate)

**Nothing moves the robot until the new serving stack reproduces known-good
behavior.** A month was lost to a stack that looked healthy and was not.

We have recorded, known-good sessions on the laptop, e.g.
`artifacts/traces/probe_onion_134916` (62 stalled squeezes, 30 carry samples,
the best carry in project history) with `observations.jsonl`, saved images,
and `action_chunks.jsonl`.

```text
Method: replay recorded observations to the G485 server and compare the
returned chunks against the chunks recorded that day.

IMPORTANT subtlety: pi05 is a FLOW-MATCHING model - it samples noise, so
outputs are stochastic. Do NOT expect bit-identical actions. Compare:
  per-joint mean and range of the chunk        (must sit in the same band)
  gripper command trajectory shape             (close/open at similar phase)
  correlation of mean trajectory vs recorded   (target: high, >0.8)
  no NaN/inf, no collapse to a constant        (Era 1's failure signature was
                                                collapse to dataset-median ~40-41)
Repeat the same observation 3x to see the spread from sampling alone; the
run-to-run spread sets the noise floor for judging the comparison.

PASS  -> proceed to Phase 4
FAIL  -> STOP. Do not touch the robot. Suspect, in order: wrong code version,
         patch mis-applied, checkpoint mismatch, processor/normalizer missing.
```

---

### Why not test in a SIMULATOR on G485 instead? (asked 2026-08-05)

Reasonable instinct - the 5090 could run a sim, and no robot means no risk.
Checked, and it does not work for THIS checkpoint:

```text
1. There is NO SO-101 environment in lerobot. Registered envs are aloha,
   pusht, libero, libero_plus, metaworld, robocasa, robotwin, robomme,
   vlabench, isaaclab_arena, gym_manipulator. None model our arm.
2. Even if one existed, 012000 is fine-tuned on REAL images from OUR three
   cameras at OUR viewpoints. A simulator renders a different visual world.
   The policy would be judged on images it has never seen - the real-to-sim
   gap - so any behavior observed would say nothing about the real robot.
   Failure in sim would not mean the stack is broken; success would not mean
   it works.
3. The thing sim would give us - "exercise the stack without the robot" -
   Phase 3 already does BETTER, by replaying REAL recorded observations from
   a known-good session and comparing against known-good outputs.

Where sim IS legitimately useful, and stays on the table:
  - dry-running the Phase 6 subtask-switching WRAPPER logic (mutable task
    string, watcher thread) against a mock robot - no simulator needed, a
    replay/mock harness is enough and is faster to build.
  - future work with a policy TRAINED in that sim (e.g. the LIBERO pi05
    checkpoints), which is a different project, not a test of 012000.
```

## Phase 4 - Camera gate (laptop side)

```text
4a. Release the front camera: close the Chrome tab holding /dev/video0.
    Verify: no process in /proc/*/fd holds /dev/video*
4b. Start the wrist proxy (Pi is now 192.168.1.28, NOT .15):
      ./.venv/bin/python tools/pi_wrist_proxy.py \
        --pi-host raspi@192.168.1.28 --pi-ip 192.168.1.28
    Free the Pi camera first: sudo systemctl stop timelapse.service pipics.service
    Restore those services after the session.
4c. Capture one frame from EACH of the three cameras and LOOK at them:
      front faces the robot? top sees the table AND the plate? wrist not black?
4d. Confirm config/so101.json front path still resolves (device numbering
    shifts when USB devices are added - it resolved to /dev/video0 today).
```

Three cameras or the run does not count. This rule is not negotiable.

---

## Phase 5 - Smoke run (30-60 s, measure the link, judge nothing else)

Purpose: prove the end-to-end path and MEASURE the rates. Not a behavioral test.

```bash
cd projects/testproject/scripts
../.venv/bin/python async_client_3cam.py --policy-type pi05 \
  --task "pick up the orange and move it to another place" \
  --ckpt /home/kiran/lerobot_assets/checkpoints/pi05_012000 \
  --server 192.168.194.158:8080 \
  --chunk-size-threshold 0.85 --max-relative-target null \
  --jpeg-quality 92 --trace-dir ../artifacts/traces/g485_smoke_$(date +%H%M%S)
```

```text
Then score the trace immediately:
  ./.venv/bin/python scripts/analyze_grasp_from_trace.py artifacts/traces/g485_smoke_*

GATE: obs rate >= 0.8/s. Below that the policy is steering on stale images and
      ANY behavioral conclusion is void (this invalidated two runs on 08-02).
EXPECT: worse than the pod-era 1.5-2 obs/s is possible - each observation is
      ~190 KB over a ~1 MB/s link (~190 ms) plus 255 ms RTT plus 153 ms
      inference. If obs rate lands below 0.8/s, do NOT proceed to Phase 6;
      go to Phase 5b.
```

### 5b. If the link is too slow (contingency, only if Phase 5 fails the gate)

Options in order of preference, ONE AT A TIME, each re-validated by Phase 3:

```text
1. Lower JPEG quality 92 -> 80. Smaller payload, mild image change.
2. Client-side downscale before sending. pi05 resizes every image to 224x224
   internally (modeling_pi05.py:1180, DEFAULT_IMAGE_SIZE=224), so we are
   shipping ~6x more pixels than the model uses. Big win, but it changes the
   resize chain the model sees -> MUST pass the Phase 3 exam before robot use.
3. Accept a lower control rate and raise RTC_EXEC_HORIZON to match.
Never change two of these at once.
```

---

## Phase 6 - First real experiment: the subtask-switching probe

Only after Phases 3-5 pass. Full rationale in the handoff doc, Section 9.

```text
WHY: Physical Intelligence released only pi05's low-level half; the high-level
brain that decodes subtask text was never released. We emulate it from the
laptop. Verified feasible by code reading: the task string is re-read and
re-tokenized on EVERY inference, no caching, so it can change mid-episode.

WHAT: start "pick up the onion"; when the live stall test says the onion is
held, switch the task string to "put the onion on the plate".
TRIGGER: commanded gripper < 22 AND measured > commanded + 10 AND measured in
  25-36, sustained ~2 s (3-4 observations). Plus a manual override key.
BUILD: RobotClient takes the task ONCE into both loops (robot_client.py:581-586)
  -> needs a subclassed wrapper with a mutable current_task and a watcher
  thread; the watcher must wrap robot.send_action (line 424) to capture the
  COMMANDED gripper width (self.latest_action is only an index).
SCENE: onion at its PRACTICED spot, plate elsewhere. We are isolating the goal
  question, NOT re-testing position generalization.
OUTCOME either way is informative:
  no change -> the place skill is genuinely absent; only Stage 2 data fixes it
  any plate-directed motion -> P6 failed partly on PROMPT STRUCTURE, and
    subtask-style strings become standard in how we run AND how we record.
```

---

## Phase 7 - Retire RunPod (only after the checkpoint is safe)

```text
PRECONDITION: checkpoint 012000 must exist in TWO places before anything is
deleted. Today it is on G485 (8.8 GB) and on a stopped pod whose address now
refuses connections. Treat the pod copy as already unreliable.
7a. Pull a second copy to the laptop (or an external disk) from G485.
7b. Verify it: file count + sizes + a checksum comparison, not just "it copied".
7c. Only then release pod resources, and delete the lingering network volume
    (silent_coffee_tick, 10 GB, EU-RO-1, ~$0.70/mo).
```

---

## Abort Criteria (stop and diagnose, do not push through)

```text
Phase 3 exam fails ................ never touch the robot; wrong stack
obs rate < 0.8/s .................. infrastructure, not behavior; Phase 5b
actions NaN / collapse to constant . the Era 1 signature; stop immediately
arm serial glitches return ........ note frequency; hardware watch item
any two variables changed at once . invalidate the run and redo it
```

## What Must NOT Change In This Bring-Up

```text
RTC_EXEC_HORIZON=35, chunk-size-threshold 0.85, jpeg-quality 92,
max-relative-target null, 640x480 cameras, three cameras, official lerobot
defaults. The recipe is frozen so that if behavior differs from the pod era,
the SERVER MOVE is the only suspect.
```

## Time And Cost

```text
Phase 1-2  ~30 min   (patch + start + gates)
Phase 3    ~30 min   (offline exam; no robot, no risk)
Phase 4    ~15 min   (cameras; needs Chrome closed)
Phase 5    ~10 min   (smoke + rate measurement)
Phase 6    ~30 min   (build the wrapper) + ~15 min robot time
Phase 7    ~30 min   (copy + verify + release)
Cost: $0. This is the point of the move.
```
