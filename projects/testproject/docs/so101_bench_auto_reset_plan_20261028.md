# Bench auto-reset: the arm puts the orange back on the table between trials (scripted, not the policy)

Date: 2026-10-28. Status: **PROPOSED, reviewed and amended 2026-10-28 (gaps section) — awaiting go to build.** Operator's idea (2026-10-28): "pick the orange from the plate and
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
R0b LOOK FIRST      grab a front frame; detect the tray outline and the orange centroid (the position-free
                    detector from the September recovery work); map the orange's pixel offset from the tray
                    centre to one of 5 calibrated descent poses (centre, near, far, left, right of the tray centre).
                    No orange found in the tray → RESET FAILED (nothing to reset; the operator places).
R1  above tray      hover ~8 cm above the chosen descent pose, gripper 45
R1b correct         re-read joints; if any joint is > 2° off the waypoint, one short correcting move (the
                    return-to-start was seen to stop 3–5° short on 2026-10-19/20 — a height error at R2)
R2  descend         to the chosen descent pose (tray floor height minus the orange radius); R1b again
R3  close           close in 2-unit steps at 30 Hz and STOP when the reading stops changing for 5 steps (never
                    drive to a fixed target — a held orange stops the jaws at 16–26, driving on bruises it);
                    HOLD if the stall reading is 16–30, MISS if < 12 (shut on air) or > 34 (blocked)
R4  retry on MISS   open, lift 3 cm, LOOK again (R0b: the miss may have moved the orange), descend to the new
                    pose; at most 2 retries; still MISS → open, go to start, RESET FAILED, stop the row
R5  lift            lift/elbow back to the R1 hover with the gripper held
R6  carry           pan to the chosen table slot (see grid), hover height
R7  lower + open    descend to table height + orange radius, gripper → 45, dwell 0.5 s
R8  retreat         lift 5 cm, return to start pose; re-read: gripper ≥ 40, joints within 2° of start
R9  verify          grab a front frame: (a) the orange centroid is within ±3 cm (in calibrated pixels) of the chosen
                    slot — not merely "outside the tray", a drop during the carry must be caught; (b) the tray
                    outline is within 1 cm of its calibrated position (a brushed tray invalidates every waypoint);
                    (c) the arm is at start. Any failure → RESET FAILED, stop the row. Before/after frames of every
                    reset are saved; the operator can overrule the detector from them.
```
Calibration session (one-off, with the operator at the bench, ~30 min): tape the tray outline on the table; jog
the arm to the tray centre at the floor and record T_*; jog to each of the grid slots and record S_i; store them in
results/so101_bench_20261019/reset_waypoints.json with the date and a photo. Re-calibrate whenever the tray or
the camera moves (the client refuses to run a reset if the waypoint file's tray photo differs from the live
frame by more than a threshold — a cheap guard against the 2026-10-19 "camera moved" repeat).

## Placement grid (where the orange goes back) — DECIDED 2026-10-28 with the operator
Where the orange is placed decides how hard the test is, so it is set on purpose, not by the script's reach.
```text
MAIN row (the 20-trial number)   placements drawn from WHERE OUR DEMONSTRATIONS PUT THE ORANGE: the start-of-episode
                                 orange position is read from the overhead frame of each of the 60 September
                                 episodes (same camera as the bench) and the front frame of the 109 August ones;
                                 the 2-D distribution is binned into 10 cells covering its central 90 %; each cell
                                 = one slot (its centre, in calibrated joint space). 10 slots × 2 rounds = 20, in a
                                 fixed shuffled order written to the log — the SAME 20 for every model
                                 (fine-tune 3, base, rows 1/2). Measures: how well the model does the task it
                                 was taught. Comparable with the hand-placed rows of 2026-10-26, which sat in
                                 this area.
WIDE row (separate, labelled)    10 slots across the whole reachable fan (two depths, pan −40…+40), run only after
                                 the main row and reported on its own line. Measures: generalisation beyond the
                                 taught area. Never pooled with the main row.
excluded                         slots inside the tray's footprint; slots closer than 6 cm to the base plate
```
The demonstration-area extraction is a 20-minute script over the recordings (detector + camera-to-table map from
the calibration photo) and its output (a scatter plot + the 10 cells) goes into the plan before V1 runs.

DONE 2026-10-28 (scripts/demo_placement_area.py → results/so101_bench_20261019/reset/demo_placement_area.{json,jpg}):
the orange was found in the first overhead frame of 55 of the 60 September episodes; the tray stood on the arm's
RIGHT (the bench layout) in 44 of them, on the left in 16 (the recovery set moved it). Using the 37 demos with the
tray on the right and the orange on the table, 10 k-means slots (overhead pixels, 640×480; demos per slot):
```text
S0 (47,296) 4   S1 (71,164) 5   S2 (156,312) 1   S3 (34,459) 1   S4 (37,409) 4
S5 (98,388) 8   S6 (211,423) 5  S7 (244,372) 2   S8 (377,386) 3  S9 (506,386) 4
```
= the left half of the table and the front edge, 5–25 cm from the base, which is also where Sunday's hand placements
were. The joint-space hover/place pose for each slot is recorded at the calibration session. Motion envelope from
the 169 training episodes (reset/motion_envelope.json): pan −111…84, lift −105…83, elbow −92…97, wrist_flex
−100…103, wrist_roll −75…91, gripper 2…88 (+5° margin).

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
- MOTION ENVELOPE: every reset waypoint and every interpolated step must lie inside the per-joint min/max seen in
  the 169 training episodes (plus 5°); a leg that would leave it is refused before it starts. This is the guard for
  unattended rows, where ESC on the Acer terminal is the only other stop besides the power switch.
- lighting: the overhead frame's brightness drifted across 2026-10-26 (frame mean 96 → 162); the verify
  detector's colour thresholds are checked on both ends of that range before V1, and every verify saves its frame
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

## Gaps found on review (2026-10-28) and how the plan now covers them
```text
blind grasp vs an orange anywhere in the tray   → R0b looks first and picks the descent pose from the orange's position
squeezing a soft fruit to a fixed target        → R3 stops on stall, never drives past the hold reading
a drop during the carry reported as OK          → R9 requires the orange within ±3 cm of the slot
the arm brushing the tray                       → R9 checks the tray outline every reset; taped + photo at calibration
moves landing 3–5° short                        → R1b correcting move before every contact leg
placements that test the untaught table         → MAIN row on the demonstration area; WIDE row separate (operator's decision)
nobody watching unattended resets               → motion envelope from the training data; frames saved; detector overrulable
```

## Build record
```text
2026-10-28  GO from the operator. Built, not yet run on the arm:
            results/so101_bench_20261019/bench_reset.py        R0–R9 as a class (look / move-with-correction /
                                                               close-on-stall / verify / envelope guard); raises
                                                               ResetFailed, the client stops the row on it
            bench_client.py --reset-between --waypoints --slots --reset-dry-run   (resets logged as "event": "reset"
                                                               lines in the row's .jsonl; never counted as chunks)
            reset/reset_waypoints.TEMPLATE.json                 slots' pixel targets + envelope filled; joint-space
                                                               hover/place/descend poses are null until calibration
            reset/demo_placement_area.{json,jpg}, reset/motion_envelope.json
            copied to the Acer (~/bench_client.py, ~/bench_reset.py). Compiles; no live test yet.
NEXT        calibration session at the bench (operator + me, ~30 min): tape the tray, photo, jog to the tray
            centre/near/far/left/right at floor height and the hover above, then to each of the 10 slots (hover +
            place) — record with --home-to-style moves and the joint readback; write reset_waypoints.json; then V1.
```

## Cost
~2 h to write (sequence + look/verify + envelope + log) + 20 min for the demonstration-area extraction, 30 min calibration at the bench, 20 min V1–V3. Saves a person-minute per
trial afterwards and removes the void-trial failure mode.

## Outputs
results/so101_bench_20261019/reset_waypoints.json (+ tray photo), reset events inside the row's .jsonl, a
reset_log.md with V1–V4 and any RESET FAILED cases, and the 20-trial rows in bench_runs.md.
