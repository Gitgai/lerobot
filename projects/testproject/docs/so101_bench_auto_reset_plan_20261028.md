# Bench auto-reset: the arm puts the orange back on the table between trials (scripted, not the policy)

Date: 2026-10-28. Status: **PROPOSED — awaiting go.** Operator's idea (2026-10-28): "pick the orange from the plate and
put it back on the table at a different location so we can perform the next trial."
Parent: R3/R5 bench protocol (pi05_so101_real_base_audit_plan_20261019.md, pi05_so101_lora_on_top_plan_20261019.md);
record: results/so101_bench_20261019/bench_runs.md. Client: results/so101_bench_20261019/bench_client.py.

## Why
A trial row today needs a person at the table every 60–90 s to move the orange out of the tray and place it again.
On 2026-10-26 that cost six void trials (orange/tomato left in the tray → the model correctly did nothing) and
limited us to rows of five. The next thing we need is a 20-trial orange row per model for a real confidence
interval (3/5 today spans ~19–88 %); 20 trials at one command, placements varied by the machine, is what makes
that cheap and reproducible across models (base, fine-tune 3, later rows 1/2).

## Decision: a SCRIPTED reset, not the policy
```text
scripted joint-space routine   RECOMMENDED. Same mechanism the client already uses to return the arm to start
                               (slow, per-step clamped move to a joint target); more waypoints. Deterministic,
                               loggable, model-independent — identical for every model we compare.
the policy with a reversed     NOT relied on. "pick up the orange and place it on the table" never appears in the
instruction                    169 training episodes; on Isaac the model treats an orange already on the plate
                               as a finished task and stays at rest (rows B2–B5, C1, 2026-10-26). One curiosity
                               trial at most, logged as off-protocol.
```

## The routine (joint space, LeRobot units: degrees, gripper 0–100)
Waypoints are taken from REAL poses, not invented: the September plate demos (20 episodes, tray at the arm's
right) and the fine-tune's own successful releases on 2026-10-26.
```text
measured anchors (pan, lift, elbow, wrist_flex, wrist_roll, gripper)
  release over the tray, September demos, median of 20:  [-76, -32,  61,  58,  -6, 36]   (std pan 18, lift 22)
  release over the tray, fine-tune 3 row E trial 1:       [-57,  -3,  34,  60, -13, 41]
  held orange, row E trials 1/3/5:  gripper 16–26 when holding (tomato 28–32); fully shut on air = 2–7
  rest / start pose:                                       [  0, -99,  97,  75,   2, 41]
```
Sequence (every leg is a clamped move, ≤ 1.5°/step on arm joints and ≤ 3/step on the gripper at 30 Hz, i.e. the
same speed as the existing return-to-start):
```text
R0  preconditions   arm at start pose (read it); tray in its taped position; gripper open (≥ 40)
R1  above tray      [T_pan, T_lift_high, T_elbow_high, T_wflex, T_wroll, 45]   — hover ~8 cm above the tray centre
R2  descend         same pan/roll, lift/elbow lowered to the tray floor height minus the orange radius
R3  close           gripper → 10 over 1 s; read back; HOLD if 16 ≤ reading ≤ 30 (orange between the jaws),
                    MISS if < 12 (shut on air) or > 34 (blocked)
R4  retry on MISS   open, lift 3 cm, shift pan ±8° toward the tray's far side (two alternates), repeat R2–R3 once
                    each; if still MISS → open, go to start, print RESET FAILED, stop the row (operator places)
R5  lift            lift/elbow back to the R1 hover with the gripper held
R6  carry           pan to the chosen table slot (see grid), hover height
R7  lower + open    descend to table height + orange radius, gripper → 45, dwell 0.5 s
R8  retreat         lift 5 cm, return to start pose; re-read: gripper ≥ 40, joints within 2° of start
R9  verify          grab a front frame; the orange must NOT be inside the tray's pixel box (the detector from the
                    September recovery work, position-free plate oval + centroid test) and MUST be on the table
                    region; on failure → RESET FAILED, stop the row
```
Calibration session (one-off, with the operator at the bench, ~30 min): tape the tray outline on the table; jog
the arm to the tray centre at the floor and record T_*; jog to each of the grid slots and record S_i; store them in
results/so101_bench_20261019/reset_waypoints.json with the date and a photo. Re-calibrate whenever the tray or
the camera moves (the client refuses to run a reset if the waypoint file's tray photo differs from the live
frame by more than a threshold — a cheap guard against the 2026-10-19 "camera moved" repeat).

## Placement grid (where the orange goes back)
Pre-registered, 10 slots in the arm's reachable fan, left-front to right-front, two depths; the row visits them in
a fixed shuffled order written into the log so every model sees the same 20 placements (10 slots × 2 rounds):
```text
depth near (~12 cm from the base plate):  pan −40, −20, 0, +20, +40
depth far  (~22 cm):                       pan −35, −17, 0, +17, +35
```
Slots inside the tray's footprint are excluded automatically from the calibration. The slot list is the same for
every model row; the base's trials 6–16 were hand-placed and stay as they are.

## Integration with the client
`bench_client.py --reset-between --waypoints reset_waypoints.json --slots 0..9x2`:
- after each episode and the return-to-start, run R0–R9; log one JSON line per reset (slot, gripper readings at R3,
  retries, verify result, wall time) to the same --out file with "event": "reset"; reset chunks are NEVER counted
  as trial chunks and no policy call is made during a reset
- a trial starts only after a reset reports OK (or the operator placed by hand on a RESET FAILED)
- `--max-chunks 75` stays the trial cap; the reset has its own 40 s budget
- ESC/q still stops everything; the first run of any session is `--reset-dry-run`: the full routine with the
  gripper held open at 45 and R2/R7 stopping 3 cm high, nothing is touched

## Safety and limits
- blind joint-space grasp: it will miss an orange that rolled to the tray's rim → that is what R4's retry and R9's
  verify are for; a failed reset stops the row, it never guesses on
- the tray must not move: taped position + photo check; the camera must not move: same check
- the orange only (tomato/onion rows stay hand-placed: different diameters change R2's height)
- first live resets with the operator at the switch, as for every new arm behaviour on this bench
- no change to the policy server, the protocol fruit, the instruction, or the chunk cap — the reset is bench
  plumbing, not part of the trial

## Verification before it runs a row (pre-registered)
```text
V1  dry run, gripper open, 3 cm high                       no contact, joints within 2° of each waypoint
V2  3 live resets, operator watching                       3/3 HOLD at R3, orange on the chosen slot, R9 OK
V3  10 live resets across all slots, no trials             ≥ 9/10 OK; any RESET FAILED stops and is read
V4  one 5-trial fine-tune-3 orange row with --reset-between  trial results agree with hand-placed rows; resets
                                                           logged; zero void trials
```
Then the 20-trial rows: fine-tune 3 first, then the base (both at 75 chunks), then rows 1/2 if wanted.

## Cost
~1 h to write (sequence + verify + log), 30 min calibration at the bench, 20 min V1–V3. Saves a person-minute per
trial afterwards and removes the void-trial failure mode.

## Outputs
results/so101_bench_20261019/reset_waypoints.json (+ tray photo), reset events inside the row's .jsonl, a
reset_log.md with V1–V4 and any RESET FAILED cases, and the 20-trial rows in bench_runs.md.
