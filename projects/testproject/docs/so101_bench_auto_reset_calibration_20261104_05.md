# SO-101 bench auto-reset live calibration record and runbook

Dates: 2026-11-04 and 2026-11-05

Branch: `codex/record-row-n-20261030`

Design plan: [`so101_bench_auto_reset_plan_20261028.md`](so101_bench_auto_reset_plan_20261028.md)

Authoritative waypoints: `results/so101_bench_20261019/reset/reset_waypoints.json`

## Outcome

The scripted orange auto-reset now has:

- a verified start pose;
- a verified tray-centre pickup, lift, sideways carry and release;
- ten verified table placement slots, numbered 0 through 9;
- a hover and low placement pose for every slot;
- a final overhead-camera centroid for every slot;
- visual evidence for the later calibrations and a commit-by-commit audit trail;
- safe return-to-home paths and torque-off completion after each calibration session.

The system is not ready for unattended `--reset-between` operation yet. Only the tray centre has been verified.
The tray `left`, `right`, `near`, and `far` descents are still derived estimates. They must be calibrated, then the
pre-registered V1-V3 reset tests must pass. This block is stored in the waypoint file itself:

```text
PARTIAL LIVE CALIBRATION 2026-11-04/05 — tray-centre pickup and table slots 0-9 verified;
off-centre tray descents remain unverified; do not run --reset-between yet
```

## Why live calibration was necessary

The first waypoint draft was derived from September demonstrations. That data gave useful directions, a motion
envelope, and candidate regions, but it could not provide reliable contact poses on the current bench. The camera
scale and angle had changed, the teleoperated demonstrations used many redundant joint configurations, and no
episode contained an orange pickup from the tray in the current layout. Donor poses for a single target could be
30-70 degrees apart.

We therefore retained the derived values as provenance (`px_september`, donor names and spread) and replaced the
operational fields (`px`, `hover`, and `place`) with measurements made on the live arm. A waypoint was accepted
only after a real pickup, lift, sideways carry, low release, retreat, and final camera measurement.

## Bench configuration used

```text
arm                 SO-101 follower on /dev/ttyACM0 during this session
top camera          Logitech C270, /dev/video4 during this session
wrist camera        /dev/video6 during this session
image size          640 x 480
pixel scale         8.0 px/cm in reset_waypoints.json
start pose          [0.4, -104.4, 96.5, 78.3, -8.2, 45.0]
orange close target 15
typical hold stall  17.2-18.8 during the accepted slot calibrations
open gripper        45
slot separation     at least 75 px (about 9.4 cm at 8 px/cm)
```

Device numbers are session-specific. Future runs must identify cameras by hardware/name as described in
`MACHINES.md`; `/dev/video4` and `/dev/video6` are a record of this session, not permanent identities.

The tops of both gripper fingers were marked black near their tips. Those marks made the finger edges visible in
the wrist image and made it possible to judge whether the orange lay between the jaws or against the outside of a
finger.

## Guarded jog process

Calibration used `results/so101_bench_20261019/vision_calib_jog_server.py`. The process connected without changing
the existing motor calibration and accepted commands through `~/vision_calib_jog_cmd`; it wrote measured joint
state and the result of each move to `~/vision_calib_jog_state.json`.

The server enforced the motion envelope observed in the 169 demonstrations, plus the existing five-degree margin.
It interpolated slowly at 30 Hz, clamping each arm joint to 0.6 degrees per step and the gripper to 1.5 units per
step. Gripper protection registers were checked at startup:

```text
Max_Torque_Limit    500
Protection_Current 250
Overload_Torque     25
```

The command set was deliberately small:

```text
goto p,l,e,wf,wr,g   slow absolute six-joint move
delta joint,value    small correction to one joint
grip value           change only the gripper
read                 save current measured state
off                  disable torque
quit                 disconnect and exit
```

Every session ended at the standard start pose, followed by `off` and `quit`. The operator kept hands clear while
the arm moved. When the orange rolled outside a reachable region, the arm stopped and the operator repositioned it
only after the motion had ended.

## Camera capture and measurement

The C270 produces roughly 25-30 blank or undecodable frames when a new capture process opens. We acquired at least
50 top-camera frames and 35 wrist-camera frames, then used the last valid frame. The common ffmpeg messages
`unable to decode APP fields` and `EOI missing, emulating` did not invalidate the final decoded frame.

The wrist camera answered the alignment and grasp questions:

1. Are both black finger tips visible around the fruit?
2. Is the orange centred deeply enough that closing will not push it sideways?
3. After closing, is the fruit still between both fingers?

The overhead camera answered the placement questions. Final orange centroids used a tight HSV mask, normally hue
4-22 with saturation at least 145. The measurement was taken after the arm moved clear or returned home. Wood grain
can satisfy a broad orange mask, so we selected a component only inside the expected orange region and checked its
area and bounding box. A detector result was never accepted without the source image.

## Acceptance procedure used for every slot

Each accepted slot followed the same evidence chain:

1. **Start safely.** Confirm the arm at the standard start pose, gripper open, orange stationary, cameras fresh.
2. **Approach above the source.** Move through the known collision-free home/intermediate path, then to the source
   slot hover and low pickup pose. The proposed 1 cm raised tray transit is blocked: its joint-space estimate still
   brushed and moved the tray on 2026-11-05. Before any further tray approach, remove the tray and validate the full
   end-effector swept path in Cartesian space with at least 3 cm clearance. Simultaneous joint interpolation must
   not be described or used as a vertical descent.
3. **Align with the wrist image.** Adjust pan or reach in small increments until the orange is between both marked
   fingers. Being visually close in the top camera was insufficient.
4. **Close without crushing.** Command gripper 15. A stall around 17-19 supported a hold but did not prove one.
5. **Prove the grasp.** Lift, then pan approximately five degrees sideways. Accept only when the orange visibly
   follows and the original table point becomes empty. A plausible gripper stall alone was never accepted.
6. **Probe the new target while elevated.** Move toward a free table region and inspect both cameras.
7. **Lower using a known geometry.** Reuse or interpolate between verified hover/place offsets. Keep the fruit held
   while measuring the candidate overhead position.
8. **Check spacing before release.** Compute Euclidean distance from the candidate centroid to every accepted slot.
   Reject candidates below 75 pixels. We usually sought additional margin because the fruit can roll after opening.
9. **Release and retreat.** Open to 45, confirm the fruit separates from the jaws, lift the open gripper, and follow
   the collision-free path back to start.
10. **Measure the settled fruit.** Use a clean overhead frame after retreat. Recompute every distance from this final
    centroid; the settled point, rather than the held point, is authoritative.
11. **Record and protect the result.** Save the hover/place targets, measured release pose, centroid, distances,
    checks and evidence directory in `reset_waypoints.json`; preserve the previous JSON as
    `reset_waypoints.pre_slotN_calib_20261105.json`.
12. **Validate and publish.** Run JSON parsing, `py_compile` on `bench_reset.py`, and `git diff --check`; commit and
    push the result. Disable torque before ending the session.

## Safe home path used

The accepted placements span both sides of the arm. Returning directly from an extended pose could cross the base
or table. The retreat therefore used a raised slot hover and the following measured intermediate poses before the
standard start pose:

```text
[-18.5, -20.2, 18.8, 50.5, -5.2, 45]
[-9.7,  -59.9, 51.5, 46.0, -4.8, 45]
[-5.5, -103.8, 93.5, 42.2, -1.6, 45]
[ 0.0, -104.1, 97.0, 78.2, -8.0, 45]
```

Servo readback sometimes stopped two to five degrees short under load. The actual state was always read after a
move; contact and release decisions used the camera view and measured state rather than assuming the requested
target had been reached exactly.

## Accepted table waypoints

Joint order is `[shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper]`. Pixel coordinates are
the final settled orange centroid in the 640x480 overhead image. “Nearest” is measured against the final set of ten
slots, not only against slots that existed at the moment of calibration.

| Slot | Final px | Hover | Place | Nearest final slot |
| ---: | ---: | --- | --- | --- |
| 0 | (471.0, 397.5) | `[-30.9, -13.7, 27.5, 46.0, -11.2, 45]` | `[-30.7, 9.8, 30.0, 32.4, -11.1, 45]` | S1, 82.7 px |
| 1 | (407.1, 345.0) | `[-16.3, -9.1, 42.8, 32.8, -20.9, 45]` | `[-16.2, 1.8, 43.8, 18.5, -22.1, 45]` | S0, 82.7 px |
| 2 | (591.7, 410.9) | `[-49.5, 14.0, 20.0, 34.0, -17.0, 45]` | `[-49.5, 23.0, 20.0, 21.0, -17.0, 45]` | S0, 121.4 px |
| 3 | (454.3, 205.8) | `[-60, -35, 60, 48, -20, 45]` | `[-60, -24, 61, 34, -20, 45]` | S4, 96.8 px |
| 4 | (519.5, 277.3) | `[-60, -35, 60, 48, -20, 45]` | `[-60, -5, 61, 25, -20, 45]` | S5, 87.5 px |
| 5 | (594.7, 232.6) | `[-75, 0, 30, 45, -18, 45]` | `[-75, 15, 25, 30, -18, 45]` | S4, 87.5 px |
| 6 | (292.0, 414.4) | `[-5, 0, 30, 45, -18, 45]` | `[-5, 15, 25, 30, -18, 45]` | S7, 111.9 px |
| 7 | (308.7, 303.8) | `[-10, -41, 65, 48, -18, 45]` | `[-10, -30, 66, 34, -18, 45]` | S8, 82.7 px |
| 8 | (228.1, 285.5) | `[16, -41, 65, 48, -18, 45]` | `[16, -30, 66, 34, -18, 45]` | S7, 82.7 px |
| 9 | (152.8, 333.0) | `[25, -10, 50, 40, -18, 45]` | `[25, 0, 40, 30, -18, 45]` | S8, 89.0 px |

The minimum final spacing is 82.7 pixels. At the configured 8 px/cm, that is about 10.3 cm.

## Slot-by-slot record

### Tray centre

The tray centre was calibrated first. The orange was centred using the midpoint between the closed-jaw marks, then
lifted and carried 2.6 degrees sideways before being released back into the tray. The hold reading was 22.2. The
accepted values are:

```text
tray centre px  (150.0, 143.5)
hover           [77.2, -68.4, 86.8, 42.4, 0.0, 45]
centre descend  [79.9, -64.6, 83.2, 40.8, -0.2, 37]
```

This proves only the centre. The other four descent entries remain unverified.

### Slots 0 and 1

Slots 0 and 1 established the live camera scale and two usable pickup/release geometries. Both were aligned with
the wrist camera, grasped, lifted, returned and released. Their metadata is stored directly in the waypoint JSON;
the accepted commits are `99d7e1243` and `cf17788f0`.

### Slot 2

Slot 2 established the rule that a gripper reading is not proof of a grasp. The first record was rejected because
the orange did not visibly leave the table. A retry produced a real grasp and a 25-degree carry, but the release
settled only 33.2 pixels from Slot 0, so that endpoint was also rejected. A compensated release overshot to the
far-right boundary and was rejected. The orange was recovered and the final point `(591.7,410.9)` was accepted at
121.4 pixels from Slot 0. The full correction history remains in `failed_calibration_20261104`,
`successful_grasp_retry_20261104`, and `compensated_release_20261105` in the JSON.

### Slots 3 and 4

Slot 3’s first release settled about 51-55 pixels from Slots 0 and 1. It was recovered and moved to
`(454.3,205.8)`. Slot 4’s first endpoint was about 71 pixels from Slot 3 and was likewise rejected; the compensated
place geometry produced `(519.5,277.3)`. These trials established that spacing must be checked after settling.

### Slot 5

Two apparent pickups closed behind the orange; the carry check exposed both failures. A later verified grasp
released only 63.5 pixels from Slot 4 and was rejected. During recovery the orange was pushed to the far-right
camera boundary, so the operator returned it to a reachable point after the arm stopped. The retry produced a
verified grasp and the accepted point `(594.7,232.6)`.

### Slot 6

Slot 6 used the same radial geometry as Slot 5 with a different pan. The orange was visibly carried from Slot 5,
then placed at `(292.0,414.4)`. This clean transfer confirmed that a family of verified reach geometries could be
reused across pan angles when the camera still verified the result.

### Slot 7

Slot 7 began at Slot 6. The pickup needed a pan correction from -5 to -10 before the orange sat between both jaws.
Several held target probes were rejected because lowering moved the orange too close to Slot 6. Interpolation toward
the Slot 3 low-table geometry produced a safe held target. The clean final point was `(308.7,303.8)`, 106.7 pixels
from Slot 1 and 111.9 pixels from Slot 6 at the time of acceptance.

### Slot 8

Slot 8 moved into the left-middle workspace. A first low target around `(234,308)` had almost no margin over the
75-pixel rule, so pan was increased and the endpoint moved farther left. After release, the normal folded home pose
partly hid the orange. The arm was rotated while folded and high to obtain an unobstructed top frame, then returned
to standard home. The accepted point was `(228.1,285.5)`.

### Slot 9

Slot 9 used a pose interpolated between the verified Slot 8 and Slot 6 reach geometries to reach the remaining
lower-left region. The orange was held near `(143.8,352.1)`, then rolled about 21 pixels during retreat and settled
at `(152.8,333.0)`. We stored the settled point. It remained 89.0 pixels from Slot 8, so it passed.

### Tray-left descent attempt

The first off-centre tray calibration used an orange at top-camera coordinate `(122.0,160.0)`, 28 pixels left
and 16.5 pixels below the verified tray centre. The reset classifier labelled this placement `left`.

The verified centre hover was used as the safe entry pose. Pan probes found the orange near the jaw midpoint, but
two early closes at approximately `[69.0,-64.6,86.4,41.5,-0.2,37.1]` and
`[59.4,-64.6,86.6,41.5,-0.1,37.1]` closed beside the fruit and pushed it. Both were rejected.

The retry tested wrist roll at -15 and +15 degrees. Roll changed the overhead approach orientation but did not fix
the front-to-back contact mismatch seen by the wrist camera. Reducing wrist flex from about 42 to 31 degrees moved
the fixed fingertip farther down the orange's side. At pan 62.3, shoulder -63.4, elbow 96.5, wrist flex 31.8 and
roll 14.8, both marked fingertips appeared on opposite sides of the fruit. The gripper still closed to 10.1 rather
than stalling in the known orange hold range. A larger lift and a 3.3-degree sideways carry left the orange at the
same tray coordinate, proving that the fingers had slipped around the upper surface rather than grasped it.

No tray-left waypoint was accepted. The arm returned through the raised tray pose, centre hover and folded-pan
retreat to standard home, after which torque was disabled. `left` remains in `unverified_descents`, and
`--reset-between` remains blocked.

The next tray-left attempt should first use the empty tray to establish the deepest collision-free path at the left
slope. The orange should then be approached from above that path with the fingers below its widest section before
closing. This avoids repeating lateral pan corrections when the real failure is insufficient grasp depth.

A later raised-transit retry also failed. The arm moved from a proposed raised centre pose near
`[76.9,-72.0,93.1,43.5,-0.2,44.8]` toward the verified centre hover. Although this was intended as a 1 cm higher,
vertical-only approach, it was only a joint-space estimate. The interpolated path brushed the tray and displaced
its centre by approximately 23 pixels left and 40 pixels upward. Motion stopped immediately; torque was disabled
at the current pose and the server exited without a return move. This path is rejected and must not be replayed.

## Lessons that changed the procedure

1. **A stall reading is supporting evidence, not grasp proof.** The fingers can close beside or behind an orange
   and still report a plausible value. Lift plus sideways carry is the decisive check.
2. **The wrist camera determines acquisition quality.** The overhead view can make a jaw look centred while the
   orange is outside one finger. The black tip marks made this visible.
3. **Measure after release and retreat.** Several fruits shifted or rolled. The held coordinate is useful for
   control, but the settled coordinate defines the slot.
4. **Reject overlaps immediately.** Slot 2, Slot 3, Slot 4 and Slot 5 all produced plausible releases that were too
   close to earlier positions. Keeping the 75-pixel rule prevented an attractive but unusable grid.
5. **Reuse geometry, then verify.** Verified hover/place offsets sped up later slots, but camera checks remained
   mandatory because pan and fruit shape changed the final image position.
6. **Camera visibility is part of calibration.** For Slot 8, the arm was safely rotated at folded home height to
   expose the orange before measurement. An occluded detector result would not have been reliable.
7. **Do not accept inferred waypoints as live waypoints.** The demonstration-derived candidates were valuable
   starting points but differed substantially from the current camera and table geometry.
8. **Keep a recoverable audit trail.** Every risky correction preserved the previous JSON, evidence images and a
   separate commit. Failed endpoints were recorded instead of silently overwritten.
9. **Tray-wall slope changes grasp depth.** A fruit can appear centred between the marked tips and still slip out
   during lift if the fingers contact above its widest section. Off-centre tray pickup needs a verified depth path,
   not only pan and roll alignment.

## Evidence and commit trail

Later-slot evidence is under:

```text
results/so101_bench_20261019/reset/calibration_evidence/slot2_compensated_20261105/
results/so101_bench_20261019/reset/calibration_evidence/slot3_20261105/
...
results/so101_bench_20261019/reset/calibration_evidence/slot9_20261105/
results/so101_bench_20261019/reset/calibration_evidence/tray_left_failed_20261105/
```

Each directory contains some or all of: start frame, aligned top/wrist frames, carry proof, held target, released
frame and clean final top frame. The JSON contains the evidence directory for each accepted slot.

```text
f9be01fd4  Calibrate tray-center orange pickup
99d7e1243  Calibrate table slot zero
cf17788f0  Calibrate table slot one
0d9b423aa  Initial slot-two record
40e74d185  Reject unsuccessful slot-two calibration
39bb45e13  Record verified slot-two grasp retry
f40b66b28  Calibrate compensated table slot two
4863331db  Calibrate table slot three
522ff916f  Calibrate table slot four
505a87652  Calibrate table slot five
828a6c9e8  Calibrate table slot six
23bf81aa4  Calibrate table slot seven
06f239fb9  Calibrate table slot eight
733411c2f  Calibrate table slot nine
```

## Remaining plan

### 1. Calibrate all off-centre tray descents

Place the orange in the tray at `left`, `right`, `near`, and `far`. For each position:

1. keep tray approaches blocked until a Cartesian/swept-volume path has been measured with the tray removed and
   verified with at least 3 cm clearance; the failed 1 cm joint-space estimate must not be reused;
2. align using both cameras and the black finger marks;
3. close on the orange and record the stall;
4. prove the grasp with a lift and small sideways carry;
5. return and release into the tray;
6. record the accepted descend pose and evidence;
7. update `unverified_descents` in the tray calibration metadata.

Do not derive the four poses by applying a pan offset alone: the tray rim and camera perspective change the needed
reach and height.

### 2. Run the pre-registered reset validation

```text
V1  full dry run, gripper open, contact legs 3 cm high    no contact; every waypoint and return path valid
V2  three watched live resets                            3/3 real holds, placements and R9 checks
V3  ten reset-only cycles across all slots               at least 9/10; stop and inspect every failure
V4  one five-trial fine-tune-3 row with reset-between    zero void trials; reset events logged separately
```

The first `--reset-between` command may be issued only after the off-centre descents and V1-V3 pass. V4 is the
first policy-integrated test. After V4, run the fixed 20-placement sequence for fine-tune 3 and then the base model.

### 3. Recalibration triggers

Repeat the relevant calibration if any of these changes:

- top or wrist camera position;
- tray location or orientation;
- arm base position;
- gripper fingers or black alignment marks;
- fruit size or object type;
- table height;
- motor calibration or follower arm.

This waypoint set is for the single orange used in the calibration. Tomato, capsicum, pen and other objects require
separate pickup height, hold-range and placement validation.
