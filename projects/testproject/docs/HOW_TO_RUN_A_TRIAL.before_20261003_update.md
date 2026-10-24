# How to run a trial (SO-101 arm) — plain guide + exact commands

For a human or an agent picking this up. The TOP is the simple workflow; the lower
sections are the exact commands, per model, plus the gotchas that bit us.

---

## The workflow in 5 steps (what a "trial" is)

```text
1. START   run ONE command that tells the arm to do the task (pick the orange, put it on the plate).
2. RUNS    the arm moves. The command runs in the background (shows "running"); you wait.
           NOTE: you can't watch it live today — the program holds both cameras while it runs.
3. DONE    you get a "finished" notice.
4. CHECK   look at a front-camera PHOTO of where the orange + arm ended up, plus the saved
           numbers (did the gripper close? lift? release?). Decide: did it place the orange?
5. RESET   send the arm back to its rest pose (home). A *successful* run should return by
           itself; you home it manually after an unfinished/stopped run.
```

## The rig (two computers)

```text
AI90  kiran@192.168.194.220          the GPU box. Runs the policy "brain" (server). Big GPU.
Acer  gaikwad-prakash@192.168.194.228 the arm + cameras. Trial client runs here.
link  ZeroTier network between them (~345 ms).
power follower MUST be ~7.4V (STS3215 servos). At 5V it throws voltage faults. Physical supply.
```

---

## A) GR00T trial (our model) — the simple one

GR00T has a turnkey script. The brain usually already runs on AI90 (port 5555).

```text
# 1. (AI90) start the brain if it is down:
RECOV_CKPT=6000 python3 ~/srv_wrap_recov.py        # serves checkpoint-6000 on :5555

# 2. (Acer) one command per trial — homes the arm, then runs the policy:
~/home_and_trial.sh <N>        # <N> = any trial number, e.g. 801

# evidence lands in:  ~/so101_trials/trial_<N>/   (trace.jsonl, client.log, result.json, frames)
```

## B) pi05 trial (Codex's model) — three pieces

pi05 has no turnkey script; it is a custom launcher. Needs a server + a tunnel + the client.

```text
# 1. (AI90) start the pi05 brain. It is loopback-only + has a 15-MINUTE lifetime, so start it
#    right before the trial. Make a FRESH-output-dir copy each time (the script refuses to reuse
#    an existing output dir, and we must not delete old evidence):
D=/home/kiran/sim/pi05-fullft-orange50-20260922
sed 's/raw_physical_trial/raw_physical_trial_<FRESH>/g' "$D/fullft10k_trial_server.py" > "$D/server_<FRESH>.py"
env PYTHONPATH=/home/kiran/sim/pi05-official-20260922/orange50_30k_deployment_check_20260922/server_dependencies \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
    /home/kiran/sim/pi05-official-20260922/.venv/bin/python -u "$D/server_<FRESH>.py"   # waits ~60s, prints "ready"

# 2. (AI90) open a reverse tunnel so the Acer reaches the brain on its own loopback:
ssh -N -o ExitOnForwardFailure=yes -R 127.0.0.1:18088:127.0.0.1:8085 gaikwad-prakash@192.168.194.228

# 3. (Acer) run the client (fresh output dir again). It does a NO-ARM check first, then moves the arm:
cd ~/Documents/ChatGPT/Lerobot
sed 's/fullft10k_raw_trial_20260924/fullft10k_raw_trial_<FRESH>/' run_fullft10k_raw_trial.py > run_<FRESH>.py
./.venv-official-client-061/bin/python run_<FRESH>.py

# evidence lands in:  ~/Documents/ChatGPT/Lerobot/fullft10k_raw_trial_<FRESH>/live/
#   (observation_*.npz per step, events.jsonl, result.json)
```

---

## CHECK the result (step 4)

```text
- result.json      -> status, commands_sent, and why it stopped
- grip numbers     -> from the trace/observations: did gripper CLOSE (~<20), LIFT, then RELEASE (>50)?
                      close-early-then-release = a real grasp; closed-on-air (~13) or never-closed = miss
- front snapshot   -> where the orange + arm ended up; is the orange IN the plate?
- VERDICT: trust the WRIST camera / your eyes, not an auto-detector (it false-positives on wood grain).
```

Grab a front snapshot AFTER the run (camera is free then) with a warm-up read:

```text
(Acer) open /dev/v4l/by-id/usb-046d_C270_... with OpenCV, read ~45 frames (warm-up), save the last.
```

## STOP / HOME (step 5)

```text
stop   pkill -TERM the client  -> releases torque (arm goes limp/safe)
home   python3 ~/home_arm.py   (if the bus glitches with "no status packet", run
       ~/clear_overload.py then retry home — up to ~3x)
```

---

## GOTCHAS (things that WILL bite you)

```text
- BUS FLAKY: first access often fails "no status packet" -> run clear_overload.py to warm it, retry.
- pi05 SERVER 15-MIN LIFETIME: it self-expires. Start it right before the trial; relaunch per run.
- pi05 IS DETERMINISTIC (seed 0): same orange position => identical result. To learn anything new,
  MOVE the orange between runs.
- FRESH OUTPUT DIRS: both server and client refuse to overwrite an existing output dir (exist_ok=False).
  Use a new <FRESH> name each run. Do NOT delete previous evidence to reuse a name.
- CAMERA BUSY DURING A RUN: the client holds both cameras, so you cannot snapshot mid-run. Snapshot AFTER.
- SECURITY: the pi05 transport is gRPC+pickle on loopback -> keep it TUNNELED, never bind it to the network.
- GRIPPER OVERLOAD: lerobot's configure() resets the gripper to a cautious limit (Overload_Torque=25)
  on every connect, which trips "overload" (status 32) on a hard clamp. We PATCHED the pi05 client's
  lerobot (.venv-official-client-061/.../so_follower.py, gripper block -> 1000/500/80; backup .bak_20260927)
  so pi05 runs overload-free. Restore the .bak to revert. GR00T's separate venv is NOT patched.
- POWER reverts: the gripper protection + any servo-limit tweak revert to factory on a power cycle;
  the 7.4V supply is physical (check it if voltage faults return).
```

## Current status (2026-10-03)

Both hardware walls solved (power 7.4V, gripper overload). pi05 10k RUNS the full policy on the
arm but does not grasp yet — the motion is sequential/jerky (no RTC). Next step: add smooth motion
(RTC) to the pi05 client. See `pi05_first_arm_and_power_fix_20260927.md` for the full story.
