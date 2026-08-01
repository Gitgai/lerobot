# RTC Live Sessions: First Grasp+Lift+Carry Under Real-Time Chunking

Last updated: 2026-08-01

Follow-up to `pi05_rtc_backport_plan_20260731.md` (gates were green offline).
This doc records the first two LIVE runs with the RTC-enabled trusted server.

## 1. Session Prerequisites That Bit Us First (all fixed)

```text
FRONT CAMERA IDENTITY THEFT: after a laptop reboot, the ACER's single by-id
name silently jumped from its RGB camera to its INFRARED sensor (GREY
640x360@15) - explaining a whole evening of "camera stuck at 360" mystery.
The ACER exposes TWO cameras (RGB video2/3, IR video4/5) but only ONE by-id
pair. FIX (permanent): config now uses the port-anchored by-path name
  /dev/v4l/by-path/pci-0000:00:14.0-usb-0:5:1.0-video-index0  (RGB)
Front camera also now forces fourcc MJPG (record_3cam_demos.cameras_arg).

WRIST RIBBON: went electrically dead (detected=0) after heavy sessions;
powered-off reseat revived it. "no cameras available" = electrical;
"failed to acquire / pipeline in use" = alive but busy (timelapse/pipics/
our own proxy).

POD MIGRATIONS: SIX during this project so far, one mid-session. Migrated
pods come back RUNNING (billing). Standing rule: after any migration, check
and re-stop. Balance drains explained ($7 + $1.4 + $0.5 evenings).
```

## 2. Run 1 - RTC with default execution_horizon=10

```text
trace: rtc_live_20260731_231941 (3106 actions, 135 s)
RTC confirmed active in server log.
Motion: median step 1.29 / p95 6.46 / max 60.6 (demos: 0.88/3.25/6.5).
Better than pre-RTC (max 70-114) but seams survived.
Behavior: repeated REAL grips (75 of 281 obs with fingers at orange width,
one ~8 s hold) but never lift-while-holding; releases at table level nudged
the orange progressively out of position. User video IMG_9356.MOV confirms.
Diagnosis: execution_horizon (10 steps ~ 0.33 s) << inference delay
(~30 steps ~ 1 s): RTC only protected a third of the gap; chunk switches
during the grip->lift transition still wavered the grip.
```

## 3. Run 2 - RTC with execution_horizon=35 (the fix)

```text
trace: rtc_h35_* of 2026-08-01 (~1338 actions)
Attempt 1: close on air, clean fast retry.
Attempt 2 (~28 s in): textbook grasp (cmd 5, fingers pinned at 28 = orange
width) -> LIFT WHILE HOLDING (shoulder_lift crossed 0 to -22 with grip
pinned; 6 HOLDING-AND-LIFTED observations - FIRST TIME EVER) -> carried
upward -> orange slipped out around lift -40..-59 as the grip command eased
(4 -> 29 -> 42) -> model returned to start pose and waited (clean self-reset).

Motion (best ever): median 1.26 / p95 4.60 / oversized-steps 3.44%
(vs 4.99% at h10, ~5% pre-RTC). p95 is approaching demo scale.
```

## 4. Where This Leaves The Task

```text
SOLVED: reach, precise grasp acquisition (2-for-2 real grips tonight),
grip->lift transition, smooth near-demo motion, fast purposeful retries.
REMAINING: grip force eases during the carry -> object slips before place.
Next investigation: is the easing (a) demo-faithful behavior (demos also
ease toward place - but with the orange lower) executed at the wrong height,
(b) RTC prefix carrying stale "release-phase" actions, or (c) marginal grip
physics. Start by comparing carry-phase gripper commands: demos vs this
trace at matched lift values.
```

## 4b. Carry-Slip Analysis Result (2026-08-01, offline)

```text
Demos vs tonight's h35 carry, at matched heights:
  demo grip COMMAND during carry: ~23-25 at all heights
  tonight's command: 0.8-24 (matched or TIGHTER than demos)
  -> the model does NOT under-squeeze; force imitation is faithful.
  demo FINGER WIDTH while holding: 32.8   tonight: 28
  -> the held object was ~5 units narrower than in training.
USER CONFIRMED: tonight's orange is NOT the demo fruit (smaller).
Verdict: fruit-size mismatch. Demo-level force on a narrower grip is
marginal -> mid-carry slips. July 28's success survived only because the
model happened to command extra-tight (5-17) throughout.
Fixes: (1) use a demo-sized orange (width ~31-34 when held) - zero cost;
(2) later, record demos with 2-3 fruit sizes so the model learns
"squeeze until secure" instead of "squeeze to 23".
Live predictor for runs: grip width >=31 should survive carry; <=28 slips.
```

## 4c. Five-Run Reliability Attempt (2026-08-01) - ABORTED, host congestion

```text
Run 1 (bigger orange): two grips (widths 30 and 33 - the 33 matching demo
geometry exactly), lift begun, lost during 5-11 s chunk latency spikes.
Diagnosis: pod host load average 10+ (noisy neighbors post-migration #6);
GPU itself fine (~0.5-0.6 s inference). Latency 5.7 s median makes RTC
protection (1.2 s) irrelevant - run annulled, count postponed.
Action: terminate this pod chain; deploy fresh from the volume page (new
host lottery) before the real five-run count.
```

## 5. Next Session Plan

```text
1. Reliability first: 3-5 runs with the h35 recipe (server env:
   RTC_ENABLE=1 RTC_EXEC_HORIZON=35). Count grips / lifts / carries / places.
2. Carry-phase gripper analysis (section 4) from tonight's trace vs demos.
3. If slips persist and analysis points at demo-faithful easing at wrong
   height: place-emphasis demos + fine-tune becomes the path (train on NEW
   lerobot code per the code-pairing rule, gaining native RTC).
Standing gates unchanged (camera reference match, orange placement, open
gripper, user present). Run recipe = section 3 of the smooth-run plan doc
+ RTC env vars, front camera by-path node.
```
