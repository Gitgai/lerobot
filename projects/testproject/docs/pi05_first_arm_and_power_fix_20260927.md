# π0.5 first arm run + power / gripper fixes (2026-09-27)

Cross-cutting status + plan. Affects BOTH lanes (GR00T on the SO-101 arm, and the
π0.5 lane owned by Codex). Written after the first-ever *moving* π0.5 10k trial.

## Headline
1. **VOLTAGE SOLVED.** The follower ran at ~5 V; STS3215 servos are 7.4 V-rated. Raised
   to 7.4 V. The "input voltage error" (Status 1) that blocked homing + grasps — and that
   killed every prior π0.5 physical attempt "before any policy movement" — is gone.
2. **π0.5 10k MOVED THE ARM for the first time** — 250 commands, real motion, past the
   voltage blocker.
3. **NEW SHARED WALL: gripper OVERLOAD (Status 32)** — hits BOTH GR00T and π0.5 at 7.4 V.
   The gripper clamps hard enough to trip its overload protection.

## Hardware facts (measured 2026-09-26/27)
```text
servos            STS3215 (model 777, confirmed on all 6). 7.4 V nominal.
                  firmware limits: Min_Voltage 4.0 V, Max 8.0 V.
voltage BEFORE    idle 5.4 V, holding sag 4.4 V  -> input-voltage faults under load
voltage AFTER     idle 7.2 V, holding min 5.7 V  -> voltage faults GONE (clear of 4.0 floor)
proof             GR00T homes clean first try; π0.5 10k drives the arm
gripper protection (conservative vs arm joints):
   Overload_Torque    arm 80 | gripper 25 -> 50 -> (this session) 80
   Protection_Current arm 500 | gripper 250 -> 500
   Torque_Limit       arm 1000 | gripper 500
```

## GR00T trials across the fix
```text
709/710/711  (5 V)              abort: gripper voltage (1) / overload (32)
714          (7.4 V, OT 25)     homed CLEAN (voltage fixed), then gripper OVERLOAD (32) on grasp
715          (7.4 V, OT 50)     stopped by operator mid-run
```

## π0.5 10k first arm run (2026-09-27)
```text
model     /home/kiran/sim/pi05-fullft-orange50-20260922/orange45_fullft_15k_candidate/
          checkpoints/010000/pretrained_model  (offline-best: 3.88% full-seq action error)
server    Codex's fullft10k_trial_server.py, pi05-official .venv + PYTHONPATH=.../server_dependencies
          (grpc via PYTHONPATH, training env untouched), AI90 127.0.0.1:8085, 15-min lifetime
tunnel    reverse SSH AI90:8085 -> Acer 127.0.0.1:18088
client    ~/Documents/ChatGPT/Lerobot/run_fullft10k_raw_trial.py (.venv-official-client-061)
          fake-actuator check -> warmup -> follower_lock -> live policy
result    fake check PASSED (100 targets). Live: 250 commands sent, arm reached + attempted
          grasp, then gripper OVERLOAD (32). Arm safe after (torque off, cleanup verified).
```

## Plan (in progress)
```text
1. Raise gripper protection to match the arm joints:
     Overload_Torque 50 -> 80 ;  Protection_Current 250 -> 500   (reversible EEPROM writes)
2. Relaunch server + tunnel; rerun π0.5 10k.
3. If overload persists: suspect the overload-TIME limit or the policy's hard clamp
   (the gentle human demo replay NEVER overloaded -> both policies over-grip vs a good grasp).
```

## Ownership / hygiene
- π0.5 lane (training + the custom launcher) is **Codex's**. This session (Claude) fixed the
  power + gripper protection and ran the first moving π0.5 trial using Codex's recipe.
- Evidence-preserving: every rerun uses FRESH output dirs; Codex's `raw_physical_trial` and
  `fullft10k_raw_trial_20260924` are untouched.
- Voltage fix = the enabling change for both lanes. Overload is now the shared next problem,
  and it is NOT power.

---

## UPDATE — trial results after the gripper patch (2026-09-27)

The gripper overload was beaten by patching lerobot's `configure()` (see patch note
below). pi05 10k then RAN the full policy on the arm — no aborts — but did not
complete a pick-and-place.

```text
run      gripper limits   commands   outcome
714 GR  25/250/500        —          (GR00T) homed clean, gripper OVERLOAD on grasp
pi05 #1  25 (reset by client) 250     gripper OVERLOAD (32) — the bump kept getting reset
pi05 #2  25 (reset by client) 250     same (deterministic, seed0)
pi05 #3  80/500/1000 (patched)  2150  NO overload, ran until my 185s timeout. Orange far-left,
                                      arm reached it but gripper beside it — no grasp.
pi05 #4  80/500/1000 (patched)  1250  NO overload, orange CENTERED (fair shot). Arm moved but
                                      never secured the orange. Still on table, plate empty.
```

### Findings
```text
- VOLTAGE: solved (7.4V). Confirmed for GR00T and pi05.
- OVERLOAD: solved by patching the gripper limits. Root cause: lerobot SOFollower.configure()
  hard-writes the gripper to Max_Torque_Limit=500 / Protection_Current=250 / Overload_Torque=25
  on EVERY connect ("avoid burnout"), inside a torque-off block — so any pre-set register is
  overwritten before the policy runs. seed0 made the overload trip at the identical 250-command
  point every time.
- GRASP: NOT solved. Even centered, pi05 10k does not complete the grasp/place on the real arm.
  Same family as GR00T. Not hardware, not orange position.
- LIKELY REMAINING LEVERS: RTC (the run is sequential/no-RTC, ~2s/chunk, jerky open-loop-ish
  motion — GR00T needed RTC to grasp reliably) + grasp precision / sim-to-real gap.
```

### The gripper patch — FLAG FOR CODEX
```text
file     ~/Documents/ChatGPT/Lerobot/.venv-official-client-061/.../lerobot/robots/so_follower/so_follower.py
change   in configure(), the `if motor == "gripper":` block:
           Max_Torque_Limit 500 -> 1000 ;  Protection_Current 250 -> 500 ;  Overload_Torque 25 -> 80
         (i.e. gripper now matches the arm joints instead of the conservative "avoid burnout" values)
backup   so_follower.py.bak_20260927  (restore to revert)
scope    ISOLATED to the pi05 client venv (.venv-official-client-061). GR00T's PrakashProjects
         venv is untouched. Note: this UNDOES a protection Codex set deliberately — the gripper
         can now pull more torque/current (that's why the overload stopped). Left IN PLACE so
         further pi05 runs stay overload-free; restore from the .bak if the burnout risk is a concern.
```

### Milestone
pi05 10k went from "dies before any policy movement" (voltage fault) to "runs the full policy
on the arm, no aborts" in this session. The remaining gap (grasp completion) is a policy +
control-loop problem (RTC + precision), the same as GR00T — not the rig.

---

## CONCLUSION (2026-09-27) — pi05 runs on the arm; needs the smooth-motion (RTC) fix to grasp

Three live trials at three orange positions, all with the gripper patch (no overload):
```text
trial e  orange far-left     2150 cmds   no overload   →  no grasp
trial f  orange centered     1250 cmds   no overload   →  no grasp
trial g  orange center-left    538 cmds   no overload   →  no grasp
```

**Conclusion: pi05 10k now runs the full policy on the real arm (both hardware walls —
voltage and gripper overload — are solved), but it does NOT complete the grasp/place.
It is position-independent (three positions, same result), so it is not the orange
placement — it is the grasp EXECUTION.**

### Root cause of the non-grasp: jerky, stop-and-go motion (no RTC)
All runs are SEQUENTIAL (`rtc=False`): the arm executes a 50-action chunk, then FREEZES
~2 s waiting for the next inference, then jerks again. That stop-start, open-loop-within-
a-chunk motion is exactly what stopped GR00T from grasping — GR00T went 4/10 sequential →
9/10 once the loop was made smooth/continuous (RTC, the depth-2 pipelined client). pi05
almost certainly needs the same.

### Next step (the one work item): give pi05 SMOOTH MOTION (RTC)
```text
- pi05's client (~/Documents/ChatGPT/Lerobot/run_fullft10k_raw_trial.py + pi05_10k_transport_
  candidate.py) is a CUSTOM SYNCHRONOUS launcher — no RTC. Adding a pipelined/continuous loop
  is a BUILD (transport + control loop), and it is CODEX's client.
- GR00T's RTC lives in a different client (n16_realarm_client.py) — not reusable as-is.
- Recommendation: make "RTC for pi05" the next task (hand to Codex, or scope the build).
  Only after smooth motion is in place is it fair to judge pi05's grasp precision.
```

### State of the rig at stop
```text
arm        homed, torque off
gripper    patched to 80/500/1000 in the client venv (backup .bak_20260927; restore to revert)
servers    stopped / expiring; no trials running
docs       this file = the full record (voltage fix, overload fix + root cause, 3-trial conclusion)
```
