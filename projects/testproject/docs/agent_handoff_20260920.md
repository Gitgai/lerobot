# Agent handover — SO-101 orange pick-and-place via GR00T N1.6 (2026-09-20)

Written for the next agent picking up this rig. Self-contained. Companion detail:
`EVAL_VIZ_AND_RECOVERY.md` sec 7-9 (the eval story), `PLAN.md` (top = current
state), `MACHINES.md` / `MODELS.md` (inventory). Memories that matter are listed
at the end.

---

## TL;DR

The task is: SO-101 arm picks an orange off the table and places it on a plate,
driven by a GR00T N1.6 policy served on the NJ GPU box and executed on the arm in
Pune over ZeroTier. The best model (`n16_recovery_v1/checkpoint-6000`) eliminated
the old "hover" failure but places only ~3/7 (RTC) / 5/10 (sequential) — the same
rate. **This session proved the control loop and the network are NOT the ceiling;
the ceiling is grasp-and-release precision, plus a marginal 5.4 V follower supply.**

**Do next, in order:**

1. **Fix the follower power to ~7.4 V** (measured 5.4 V; physical fix). Cheapest
   lever, likely cause of the "clamp-stall" failures.
2. **Re-run a scored set** of checkpoint-6000 WITH `--rtc` at 7.4 V = the true rate.
3. If still low, **record precise-grasp demos** (clean early close + decisive
   release over the plate) and fold them in. NOT more descent demos.

Do NOT: move the GPU / add a Mumbai node (network is fine), touch the RTC loop
(it's proven), retrain past ~6000 steps on this data (12k overfits the hold), or
trust the automated orange detector (wood-grain false positives — verify by eye /
wrist cam).

---

## The rig

```text
kiran-AI90        NJ, RTX 5090 (32 GB). THE POLICY SERVER runs here. This is where
                  the agent (you) runs. ZeroTier IP 192.168.194.220.
Acer laptop       Pune. gaikwad-prakash@192.168.194.228 (ZeroTier). THE ARM +
                  CAMERAS are here. All trial scripts run here over SSH.
link              ZeroTier, DIRECT, ~345 ms round-trip (verified in every RTC
                  trace). This is the same regime that produced 9/10 in Aug.
```

Arm: SO-101 follower (Feetech STS3215 servos, 7.4 V nominal). Cameras: a front
camera (table view) + a wrist camera (looks straight down; DECIDES placement when
the plate is at the front camera's frame edge). Devices are resolved at runtime by
`~/arm_ports.py` (serial port) and `~/camfind.py` (camera indices) — do not
hard-code them.

---

## Current model + the number

```text
served now   n16_recovery_v1 / checkpoint-6000   (pid on AI90 port 5555, RECOV_CKPT=6000)
             path: /home/kiran/lerobot_assets/checkpoints/n16_recovery_v1/n16_recovery_v1/checkpoint-6000
lineage      fine-tune of n16_new30_v1/checkpoint-6000 on 30 recovery + 30 base episodes
rate         PLACE 3/7 with --rtc (2026-09-20); 5/10 sequential (2026-09-18). Same within noise.
checkpoint-3000  0/5 (worse) — do not use.
baseline     orange_pick_baseline_v1 = n16_real79_side/checkpoint-10000 = 9/10 (Aug, the target)
base 5/10    n16_new30_v1/checkpoint-6000 (pre-recovery; hovered when it failed)
```

Datasets on AI90 under `/home/kiran/lerobot_assets/datasets/`: `new30_merged`
(30 eps v2.1), `recovery30_v21` (30), `new30_plus_recov30` (60, stats regenerated).
GR00T trains on LeRobot v2.1 (per-episode files), not v3.0.

---

## What this session established (2026-09-20)

### 1. RTC works and is ~5x faster (demo tempo) — but doesn't fix placement

`--rtc` (depth-2 pipelined client: 2 sockets + staleness guard) was OFF in every
eval this month; it is the loop the 9/10 baseline used. Re-tested this session:

```text
             run time   chunks   peak arm speed   median speed   rtt
RTC (702)     68.7 s     337       133 deg/s        4.8 deg/s     348 ms
SEQ (604)    294.2 s     322        27 deg/s        0.2 deg/s     632 ms
```

RTC finishes in 69 s vs 294 s, peak joint speed ~5x higher = demo tempo restored.
Gates passed: G0 dry 95.4% duty, G1 motion 85-86% duty. **But the scored rate did
not move (3/7).** The loop was necessary, not sufficient.

### 2. The grip trace is the outcome oracle — release, not grasp, is the tell

```text
trial  grip-min @ frac   final   outcome    read
702 v   15.6 @ 0.38       70.4    PLACE      closed EARLY, then RELEASED (final high)
705 v   13.4 @ 0.38       60.0    PLACE      closed early, released
707 v   17.8 @ 0.72       54.5    PLACE      closed, released
703 x   59.2 @ 0.99       59.2    no-grasp   gripper NEVER closed (min ~59 = open)
704 x   64.3 @ 0.99       64.5    no-grasp   never closed
706 x   16.7 @ 0.97       16.9    STALL      closed LATE, stayed CLAMPED (never released)
708 x   15.2 @ 0.93       15.2    STALL      closed late, clamped, orange pinned at table
```

Every SUCCESS ends with the gripper reopened over the plate (final 54-70). Every
FAILURE either never closes (703/704, min ~60) or closes and stays clamped
(706/708, final 15-17). grip-min ~22 = orange secured; ~13-14 = closed on air;
68+ = never closed.

### 3. Two failure modes, both grasp-execution

```text
no-grasp     (703, 704)  gripper never closes
clamp-stall  (706, 708)  closes but never lifts/releases; orange pinned at table
```

708 was re-run with a 120 s window (708b): the arm closed at frac 0.65 but stayed
clamped (final 17.7) and never lifted — a TRUE stall, not a timeout. More time did
not help.

### 4. Undervoltage: follower at 5.4 V (nominal 7.4 V)

Measured 2026-09-20 with `~/voltrace.py`. LIFTING the grasped orange is the
highest-torque moment; the clamp-stalls (grasped, could not lift) fit an
undervolted-servo signature. NOT a hard block — 702/705/707 lifted+placed at 5.4 V
— so it is MARGINAL, with the lift as the marginal-failure point. Raising to 7.4 V
and re-running is the cleanest single test to confirm/deny it.

---

## What is NOT the problem (ruled out this month, with evidence)

```text
network latency   direct ZeroTier ~345 ms rtt = the 9/10 regime. No GPU move needed.
RTC loop off      now ON and verified (was the real cause of the crippled 31%-duty evals).
diffusion steps   already at the minimum of 4 (num_inference_timesteps).
image payload     256 px / 640x480 is a minor knob, not the ceiling.
orange position   same positions gave both outcomes -> execution inconsistency, not OOD.
```

The only remaining levers are POWER (physical) and GRASP-PRECISION DATA.

---

## How to run everything

### Policy server (AI90 — usually already up)

```bash
# check it's listening
ss -ltnp | grep 5555
# (re)start on a chosen recovery checkpoint (3000|6000):
RECOV_CKPT=6000 python3 ~/srv_wrap_recov.py
```

Serving now: pid on 5555, RECOV_CKPT=6000, up since 2026-09-19. It's a ZMQ REQ/REP
service binding 0.0.0.0:5555; transport is msgpack (safe, no pickle) + JPEG q92.

### One scored trial (Acer)

```bash
ssh gaikwad-prakash@192.168.194.228 '~/home_and_trial.sh <N>'
```

`home_and_trial.sh` homes with retry (calls `clear_overload.py` + `home_arm.py` up
to 3-4x to clear latched Feetech errors) then runs `run_trial.sh <N>`, which calls
`n16_realarm_client.py --policy_host=192.168.194.220 --policy_port=5555
--jpeg_quality=92 --rtc=true` under `timeout 300`. Output per trial:

```text
"chunks <N>  grip min <g>@c<chunk>(frac <f>)  final <g>"   <- the outcome oracle
~/trial_<N>_frames/     per-chunk front+wrist JPEGs
~/trial_<N>_trace.jsonl per-chunk state/action/rtt/grip
~/trial_<N>_sheet.jpg   front(top)+wrist(bottom) contact sheet (trial_sheet.py)
```

Score by eye from the sheet + wrist cam (NOT the auto detector). A place = the
wrist cam shows the orange over the plate AND the gripper reopens (final grip 54-70).

### Check follower voltage (Acer)

```bash
ssh gaikwad-prakash@192.168.194.228 'python3 ~/voltrace.py'
```

### Re-analyze traces for grip + speed (either box; script in scratchpad + Acer ~/)

```bash
python3 ~/rtc_analyze.py   # on the Acer, prints the table in section 2 above
```

---

## Key files

### AI90 (this box)

```text
~/srv_wrap_recov.py                  policy server launcher (RECOV_CKPT env, ignores SIGSTKFLT)
~/rtc_analyze.py                     trace -> grip/speed/rtt table (verified this session)
/home/kiran/lerobot_assets/checkpoints/n16_recovery_v1/.../checkpoint-{3000,6000}
/home/kiran/lerobot_assets/datasets/{new30_merged,recovery30_v21,new30_plus_recov30}
.../projects/testproject/configs/leisaac_so101_gr00t_config.py   registers NEW_EMBODIMENT
.../projects/testproject/scripts/gr00t_patches/launch_finetune.py  training entry (writes LINEAGE/TASKS)
```

### Acer (arm side, all in ~)

```text
home_and_trial.sh   home-with-retry then run_trial.sh
run_trial.sh        the trial (now passes --rtc=true)
n16_realarm_client.py  eval client; _rtc_loop() is the real-arm path (gated by --rtc)
clear_overload.py   toggles TorqueEnable to clear a latched gripper OVERLOAD (id 6)
home_arm.py         homing
voltrace.py         read bus voltage
trial_sheet.py      build the front+wrist contact sheet
arm_ports.py / camfind.py   resolve serial port + camera indices at runtime
tidy.sh             sweep trial_* into ~/runs/, delete regenerable scratch
```

Trials are archived under `~/runs/trials/<N>/{frames,trace.jsonl,sheet.jpg,log}`;
the RTC set (701-708, 708b) is still loose in `~/trial_70*` at time of writing.

---

## Gotchas & lessons (this session's corrections — do not repeat them)

- **The auto orange detector is unreliable** (locks onto wood grain; misreads the
  plate at the front-cam frame edge). Score placement by eye + the WRIST camera +
  the grip trace (final 54-70 = released). The operator's first-hand knowledge of
  episodes they teleoperated outranks any detector. (memory: verify-detector-against-ground-truth)
- **Check `--rtc` is ON before blaming the network.** A client flag defaulting to
  off looks exactly like a slow link in the timing. This cost a wrong "need a
  Mumbai GPU" conclusion. (memory: rtc-pipeline-for-grasp)
- **Power is MARGINAL, not dead.** Don't call 5.4 V a hard blocker — trials
  succeed at it. It's a candidate for the LIFT (highest torque) specifically.
- **Read the trace/frames before naming an outcome.** "empty-table flailing",
  "never grasped", "RTC isn't fast" were all wrong first reads, corrected by the
  data. Grip final + the sheet settle it.
- **Homing trips the gripper OVERLOAD (id 6) intermittently** at 5.4 V; that's why
  `home_and_trial.sh` retries with `clear_overload.py`. Likely eased by 7.4 V.
- **Don't train past ~6000 steps on this dataset** — 12k overfits the "hold" state
  (carries the orange home without releasing).
- **Meet on the Acer can grab the C270** wrist cam; close the tab if a camera is busy.

---

## Open questions for the next agent

1. Does 7.4 V remove the clamp-stalls (706/708 pattern)? (the #1 test)
2. What is checkpoint-6000's true rate with --rtc AND 7.4 V, over 10 scored runs?
3. Left-far reach is thin in the data (a known 9/10-baseline residual) — do the
   no-grasp fails (703/704) cluster there? (check start-frame positions vs outcome)
4. Would a small set of precise-grasp demos (clean early close + decisive release)
   move the rate, given the descent is already reliable?

---

_Handover written 2026-09-20 by the session that ran the RTC re-test. All numbers
in this doc are recomputed from the trace files, not from memory._
