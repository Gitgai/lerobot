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

### Cartesian centre-path test with the tray removed

After the contact, the operator moved the tray and orange clear of the original approach area. The arm was manually
lifted while torque was off, its actual pose was read, and it was folded home without crossing the tray. We then
used the official SO-101 URDF to solve a Cartesian vertical path from the verified centre hover. The path contains
seven poses at 5 mm increments from 0 to 30 mm. Its nominal horizontal drift is below 0.01 mm. This also quantified
why the rejected joint-space estimate was unsafe: it raised the tool by only about 4.7 mm, then the next interpolated
move swept about 9 mm sideways.

The replacement approach was tested in empty workspace:

1. unfold at pan 0 to the 30 mm raised joint shape;
2. rotate pan to 77.2 degrees only at full clearance;
3. descend through the 5 mm Cartesian waypoints;
4. reverse the waypoints to ascend;
5. rotate pan back to 0 at full clearance and fold home.

The physical descent completed without reversal or a large lateral sweep. Horizontal FK error stayed below 4.8 mm
on descent and 2.56 mm on ascent. Load-dependent elbow lag was about 1 to 3.3 degrees, so the lowest measured pose
remained about 6.7 mm above the verified hover. The arm then returned home, torque was disabled, and the jog server
exited.

The reproducible solver is `results/so101_bench_20261019/generate_tray_cartesian_path.py`; its official URDF and
generated record are under `reset/kinematics/`. The JSON deliberately contains
`"approved_for_tray_use": false`. This test validates the path shape in empty workspace; it does not validate the
tray rim clearance, a contact-height descent, or an orange grasp. `--reset-between` therefore remains disabled.

The first tray-present high pass started at an absolute URDF tool z of 31.39 mm, which is 27.81 mm above the
verified hover z of 3.58 mm. The pan rotation completed without contact, and the measured tray centre changed by only 0.5 pixel, from
`(152.5,129.5)` to `(152.0,129.5)`. However, the elbow relaxed during rotation and reduced tool height to 26.4 mm.
That is only 22.82 mm above hover and violates the 30 mm clearance requirement, so no descent was attempted. The arm reversed the same pan path,
folded home, powered off and disconnected. The guarded jog server now provides `goto_zguard MIN_Z_MM q0,...,q5`,
which reads the live joints during the move and stops as soon as FK tool height falls below the specified minimum.
The next high pass must use an absolute-z guard of 33.5 mm and maintain about 30 mm above hover for the complete
rotation. Its before, raised, over-tray and after frames plus measurements are stored under
`reset/calibration_evidence/tray_high_clearance_20261105/`.

The next run extended the nominal path to 40 mm. Elbow compensation at pan 0 produced an actual absolute tool z
of 44.73 mm, or 41.15 mm above verified hover. The guarded pan completed at 40.33 mm absolute z, maintaining
36.75 mm above hover and passing the 33.5 mm live guard. This validates the high lateral pan path.

The open gripper then descended through the Cartesian waypoints. At the nominal 20 mm waypoint, measured joints
placed the tool at `[68.37,-127.87,18.60]` mm: 15.02 mm above hover with 5.25 mm horizontal error. The descent was
stopped because it exceeded the 5 mm limit. No close was attempted. The tray contour centroid remained stable to
0.2 pixel, but the orange shifted about 13.6 pixels while the open gripper was near it. The descent is therefore
rejected even though the 40 mm high pan passed.

The error exposed an open-loop limitation in the jog mover: it advanced an internal commanded position and allowed
the measured joints to finish as much as 2 degrees away. The server now has `goto_closed`, which reads the real
joints after every step, adds bounded load compensation, and requires every arm joint to be within 0.5 degree. It
refuses initial corrections over 5 degrees and stops if compensation exceeds 5 degrees. It passed a no-motion
home-pose test and correctly refused an oversized test correction.
The next descent must use `goto_closed` for every waypoint and retain the 5 mm horizontal FK stop rule. Evidence is
stored under `reset/calibration_evidence/tray_guarded_40mm_20261105/`.

The closed-loop tray-present retry reduced horizontal error at the nominal 20 mm waypoint from 5.25 mm to 0.76 mm.
At the nominal 10 mm waypoint with pan 77.2 degrees, horizontal error was 0.25 mm, but the wrist view showed the
fixed fingertip touching or nearly touching the orange. The arm retreated to 20 mm before lateral alignment.
Pan 79.9 degrees moved the fixed finger farther into the fruit image, while pan 70 degrees visually centred the
shifted orange between both open fingers. The arm then descended in 5 mm Cartesian steps and split the final prior
centre-approach move into four measured substeps.

The final open approach looked symmetric, but a close command of 15 reached 15.1 rather than stalling in the
accepted 16–26 orange hold range. The wrist image showed one finger against the orange and a gap to the opposite
finger. The miss was reopened immediately and the arm reversed every waypoint, passed the height-guarded pan away,
returned home, powered off and disconnected. The orange shifted about 9.2 pixels during the attempt. No grasp was
accepted and the descent remains blocked. This shows that the midpoint between open fingertips is not the jaw
centre after closure; closing kinematics or a measured closed-jaw midpoint offset must be included in alignment.
Evidence is under `reset/calibration_evidence/tray_closed_loop_descent_20261105/`.

A final watched retry used pan 74.5 degrees so the orange began closer to the fixed fingertip, plus a 40 mm guarded
high pan, 5 mm Cartesian descent waypoints, 0.5-degree measured-joint tolerance, and the four approach substeps.
The close-on-stall routine stopped at 21.9, inside the accepted 16–26 orange hold range. Both black fingertip marks
were visibly on opposite sides of the orange. The orange then followed a lift and a 3-degree sideways carry, proving
the grasp. The arm returned along the same measured path, released the orange inside the tray, ascended through all
5 mm waypoints, passed the 33.5 mm height-guarded pan away, folded home, disabled torque and disconnected.

This verifies the guarded Cartesian centre path for the orange position used in that attempt. It does not approve
automatic reset: `left`, `right`, `near`, and `far` descents remain unverified, and `bench_reset.py` does not yet
execute this Cartesian/closed-loop path. The generated JSON therefore retains `"approved_for_tray_use": false`.
Proof frames and measurements are in `reset/calibration_evidence/tray_closed_loop_success_20261105/`.

The guarded tray-left retry placed the orange near top-camera coordinate `(128,165)` and reused the verified
40 mm high path. The initial 62.3 degree pan left the fruit about 56 pixels toward one finger in the final wrist
view. Watched probes at the 20 mm checkpoint bracketed the alignment: 57 degrees over-corrected at the final
approach, while interpolation to 59 degrees placed the orange within about 5 pixels of the jaw midpoint. This
matched the successful centre reference within measurement error, and neither the tray nor fruit moved during the
descent.

The close was rejected. `close_on_stall` reached 2.2 instead of the accepted 16--26 hold range, and the fruit was
not retained. More importantly, the elbow reading changed from 83.6 to 93.9 degrees during the close. The current
routine copies each newly measured arm pose into the next gripper command, so it follows arm drift rather than
holding the five approach joints. The arm reopened, recovered to the known approach pose, reversed every 5 mm
waypoint, passed the 33.5 mm guarded pan away, returned home, disabled torque and disconnected. Tray-left remains
unverified. Before another physical retry, the close routine must lock the original five arm-joint targets while
stepping the gripper; only then can the remaining grasp-depth error be measured. The jog server now implements
that hold with bounded feedback compensation and a 5 degree drift abort/reopen, but it still requires a home-pose
physical check before another tray approach. Evidence is under
`reset/calibration_evidence/tray_left_guarded_alignment_miss_20261105/`.

The revised close first passed a home-pose no-object test: it reached 2.2 with 0.0 degree arm drift, reopened to
44.6, then powered off normally. A watched left retry then repeated the guarded 40 mm path. Because the orange had
settled slightly deeper in the tray, the 20 mm wrist checkpoint selected pan 57.7 degrees; the final open view was
within about 15 pixels of the successful centre alignment. The corrected close held the arm to 1.3 degrees maximum
drift, proving that the controller defect was fixed, but it still closed to 2.1 and did not retain the fruit. The
fingers passed below or along the fruit and shifted it about 23 pixels deeper in the tray. The arm reopened, reversed
the measured path, used the guarded pan away, returned home and powered off.

This isolates the remaining tray-left failure to grasp depth/front-to-back geometry on the sloped tray surface.
Another pan correction cannot solve it. The next attempt requires an offline-generated, collision-checked
left-specific approach below the current centre-derived final pose; no deeper live probing is allowed. Evidence is
under `reset/calibration_evidence/tray_left_guarded_hold_miss_20261105/`.

The deeper path was then generated offline from the rejected left endpoint. It preserved Cartesian x/y and pan,
lowered tool z in six 1 mm steps, limited the largest commanded joint change to 0.758 degrees, and kept the deepest
tool point 1.425 mm above the verified centre-hover tool z. Empty-tray watched runs at pan 57.7 and 60.7 degrees
completed every depth step, reversed the same path, and produced no visible tray contact or shift. These checks did
not approve the path for automatic reset; they only authorized one watched grasp at the matching 60.7-degree
placement.

In that watched grasp, both the 20 mm checkpoint and deepest wrist frame showed the orange between the open black
finger tips. The close controller held arm drift to 0.7 degrees, but the gripper reached 5.9, below the accepted
16--26 hold range. The fingers passed beside the orange and shifted it from approximately `(139,143)` to
`(142,178)` in the top camera. The arm reopened immediately, reversed all six depth steps and every verified
Cartesian waypoint, panned away above the 33.5 mm guard, returned home, disabled torque, and disconnected.

This rejects additional vertical depth as the next solution. Six more millimetres were mechanically safe at this
placement but did not create a hold. The next candidate must be a small lateral Cartesian correction derived from
the deepest wrist image, generated offline and checked first with an empty tray. Tray-left and automatic reset remain
unapproved. Evidence is under
`reset/calibration_evidence/tray_left_pan607_deeper_hold_miss_20261105/`; the generated path is
`reset/kinematics/tray_left_deeper_path.json`.

The next offline generator used the measured wrist response from the earlier 57--59 degree bracket: increasing pan
by 2 degrees moved the orange about 25 wrist pixels left. From the deeper miss it generated a bounded 60.7--65.2
degree lateral arc in 0.5 degree steps. The largest predicted horizontal tool translation was 11.345 mm and tool z
remained constant. A watched empty-tray run completed the full arc and reverse with the gripper open, no visible
contact, and no tray shift.

For the matching watched grasp, the orange started near `(137,150)`. At the deepest 60.7-degree pose it was about
25 pixels toward the fixed finger; the measured response selected a 63.2-degree command. The arm settled at 63.0
degrees and the wrist image showed approximately 3 pixels of offset with symmetric finger clearance. Despite this
corrected lateral alignment, `close_stall` reached only 7.4 with 1.4 degrees maximum arm drift. The fingers again
missed the usable grasp plane and shifted the orange about 28 pixels toward the near side of the tray. The arm
reopened, reversed the lateral and vertical paths, used the guarded pan away, returned home, disabled torque, and
disconnected.

This resolves lateral centring as the leading error. Pan 63.0 degrees centred the orange, but the fruit remained
about 48 wrist pixels away from the vertical location seen in the verified centre grasp. The next candidate must
translate the gripper in the front/back Cartesian direction while retaining the verified depth and pan. It must be
generated offline and pass an empty-tray clearance run before another grasp. Evidence is under
`reset/calibration_evidence/tray_left_lateral_empty_dry_20261105/` and
`reset/calibration_evidence/tray_left_lateral_hold_miss_20261105/`; the generated lateral path is
`reset/kinematics/tray_left_lateral_path.json`.

The proposed front/back path then passed an empty-tray open-gripper sweep from -12 to +12 mm, but its watched
alignment exposed two design errors before any close was issued. First, the marked orange position
`(135.7,137.2)` was only 15.6 pixels from the calibrated tray centre, inside the reset script's 31.5-pixel
`centre` region; it should have used the already verified centre path rather than a left path. Second, the
position-only IK changed wrist flex by -11.4 degrees over the -12 mm branch, rotating the camera and jaws. Wrist y
improved from 118.7 to 149.1 pixels, but wrist x ended 68.3 pixels away from the successful reference. The arm
retreated without closing, returned home and disabled torque.

The user's 20 mm wrist-body clearance was satisfied in this attempt. At the lowest candidate, the wrist-link and
gripper-body origins were approximately 136.4 and 87.8 mm above the table frame; only the jaw-tip frame descended
to 5 mm. Fixed tray-border patches shifted by less than 1.3 pixels, so wrist/tray contact was not the alignment
failure. The current HSV tray detector nevertheless returned no tray under the live lighting because its mask
fragmented below the configured contour area. Full measurements and the replacement design are in
`docs/so101_tray_pickup_root_cause_20261105.md` and
`reset/calibration_evidence/tray_left_front_back_alignment_rejected_20261105/`.

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

The 2026-11-05 left retries established that sequential pan, vertical-depth and front/back corrections do not form
a repeatable grasp controller. Do not continue the position-only front/back path. Keep the verified centre pickup
for placements inside the centre classifier radius. For true off-centre placements, preserve tool orientation and
solve both wrist-image axes together using a local two-axis Cartesian image Jacobian. The pre-close gate must use
the orange relative to both black finger marks. Repair and validate the live tray detector before any reset test.

Place the orange in the tray at `left`, `right`, `near`, and `far`. For each position:

1. reuse the verified 40 mm high transit, 33.5 mm live height guard, 5 mm Cartesian waypoint spacing and
   closed-loop joint correction; the failed 1 cm joint-space estimate and open-loop descent must not be reused;
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

### Watched centre-path replay gate rejection

The next live replay correctly selected the verified centre path for a centre-class overhead placement at `(137.2,137.5)`. At the final open pose, however, the wrist orange centre was `(267.6,144.5)` compared with the successful reference `(325.2,165.8)`. The `(-57.6,-21.3)` pixel error put the fruit too close to the left jaw. The pre-close gate rejected the attempt before contact; the orange and tray remained fixed, and the arm returned home with torque off. Therefore the centre path is now an approach seed rather than unconditional close permission. A wrist-relative two-axis correction is required for centre and off-centre placements alike.

### Reusable wrist-relative pre-close gate

`results/so101_bench_20261019/wrist_grasp_gate.py` now detects the orange and both black fingertip marks, expresses the orange in the coordinate frame formed by the two marks, and compares that measurement with the verified successful centre grasp. It does not connect to or move the robot. With the provisional 14-pixel per-axis acceptance window, it passes the verified success at `[0.0,0.0]`, rejects the watched centre replay at `[-51.92,-31.01]`, and rejects a known close-beside frame. `test_wrist_grasp_gate.py` preserves those three regression cases. This gate is necessary before a close but does not replace stall, lift and sideways-carry proof.

### Empty-tray two-axis wrist Jacobian probe

The open gripper replayed the verified centre path and tested two independent local movements: a 1-degree pan probe (about 2.8 mm lateral travel) and a 2 mm radial probe. The radial probe preserved tool z and pitch exactly by holding the shoulder-lift, elbow-flex and wrist-flex sum at 59.4 degrees. Both probes returned to the baseline pose. Two unoccluded tray-border patches measured less than 0.6 pixel displacement, and no contact occurred. The arm returned home with torque off. These movements are approved only for the live open-gripper image-response measurement; closing remains blocked until the wrist gate passes.

### Live two-axis wrist response

With the orange returned to the tray, the centre baseline measured `[-23.63,+8.96]` pixels relative to the verified grasp. A +1-degree pan probe measured `[-27.89,+7.61]`; a +2 mm fixed-pitch radial probe measured `[-18.42,+16.36]`. This yields the local Jacobian columns `[-4.26,-1.35]` pixels/degree and `[+2.605,+3.70]` pixels/mm. The unconstrained zero-error solve was rejected as too large for a local model. The smallest grid candidate that reaches the provisional ±14-pixel gate is approximately -1.84 degrees pan plus +0.69 mm radial, predicting `[-13.994,+13.997]`. Because the negative-pan endpoint was outside the completed empty-tray test, the arm retreated without closing. The candidate must pass one empty-tray combined-path check before use with the fruit.

### Empty-tray combined correction validation

The minimum predicted gate correction `[-1.84 degrees pan,+0.69 mm radial]` was tested as one fixed-pitch, fixed-z move from the centre baseline. The candidate joint pose was `[72.66,-63.7444,82.9341,40.2103,0.0,37.0]`. Unoccluded tray-border patches shifted at most 0.46 pixel, and no contact occurred. The arm returned home with torque off. This pose is approved for one watched open-gripper orange alignment check; a close remains conditional on a fresh wrist gate pass.

### Fixed combined correction rejected on the next placement

After the orange was manually returned to the tray, the previously validated combined pose measured `[-34.31,-0.27]` pixels and failed the ±14-pixel wrist gate. No close occurred; the arm returned home with torque off. The orange's new physical placement differed enough that the correction computed from the prior baseline was stale. This rules out storing one corrected centre endpoint. Runtime alignment must capture a fresh baseline for each placement, solve a bounded correction using the measured Jacobian, and operate inside a separately cleared correction envelope.

### Bounded runtime correction envelope

A final empty-tray validation sampled 48 open-gripper poses across pan 69.5–79.5 degrees and radial offsets -4 to +4 mm, using 1-degree and 1 mm boundary steps. The radial solutions held tool z and pitch fixed. Camera-frame jitter was removed using the stationary orange on the table; tray patches with phase-response below 0.3 were ignored. Across 67 valid patch observations, maximum tray-relative movement was 1.581 pixels and no contact was observed. The arm returned home with torque off. This envelope is approved for runtime open-gripper correction after a fresh baseline image; closing still requires a fresh wrist gate pass.

### Adaptive correction rejected outside the local envelope

On the next fresh placement, the centre baseline measured `[-75.89,+0.41]` pixels. The best solution inside the cleared ±5-degree/±4 mm envelope still predicted `[-44.17,+21.96]`; the unconstrained linear solve requested about -23.0 degrees pan and -8.5 mm radial travel, which is invalid for a local model and unsafe at tray-floor height. No correction or close occurred, and the arm returned home with torque off. This establishes that the cleared envelope is a final-refinement region, not a whole-tray acquisition controller. The next implementation must coarse-align at a raised collision-safe pose using overhead and wrist vision, then descend vertically and apply the local gate/refinement.

### Raised coarse alignment descent transfer rejected

The raised wrist servo reached its requested finger-frame target with only `[+2.38,-4.06]` pixels residual at the collision-safe pose. Two watched open-gripper descents then tested whether that alignment transferred to grasp height. Replaying the verified descent's joint deltas ended at `[-14.76,-50.78]` pixels relative to the successful final reference and failed the ±14-pixel gate. A Cartesian vertical descent held tool x/y fixed and ended with a 426.85-pixel fingertip span; manual measurement placed the orange at `[+16.59,+61.05]` pixels in the finger frame rather than the reference `[-27.62,-5.30]`. The gate rejected both paths, no close occurred, the orange stayed fixed, and the arm returned home with torque off.

This proves that one raised image target plus an assumed descent transform is insufficient. Wrist-camera scale and fruit-to-fingertip geometry change substantially with wrist posture during descent. The next implementation must use one fixed, pitch-controlled Cartesian descent and calibrate its raised-to-final image transfer from multiple open-gripper samples, or localize the fruit in table coordinates with the overhead camera and reserve the cleared final wrist envelope for small refinement only.

### Empirically corrected raised target for the joint-delta descent

The joint-delta probe's measured high-to-final transfer implied a new raised finger-frame target of `[-21.05,-30.71]` pixels. A watched high-only correction moved radially outward 13.56 mm at 43.58 mm tool height while preserving wrist pitch, then applied -2.87 degrees of additional pan. The final raised measurement was `[-25.48,-37.07]`, only `[-4.43,-6.36]` pixels from the requested target. The gripper stayed open, no descent or close occurred, the orange stayed fixed, and the arm returned home with torque off.

This validates the raised image target but does not validate its floor endpoint. The generated joint-delta endpoint lies outside the cleared final ±4 mm correction region. Before using it with the orange, remove the orange while keeping the tray fixed and replay the complete path open-gripper, inspecting clearance at every waypoint. Only after that empty-tray pass may the orange be restored for a gated grasp attempt.

### Empirical joint-delta path empty-tray clearance pass

With the orange removed and the tray left fixed, the gripper replayed the complete empirically corrected path open at 37. Top frames were captured at every descent waypoint; wrist frames were checked at modeled tool heights of 18, 13, 8, 3.4 and 9.5 mm. Neither jaw nor the wrist body contacted the tray floor or rim. The exact path then reversed to the raised pose and returned home.

Before/after home-view phase correlation measured tray-rim movement of 0.076 pixels on the left, 0.085 pixels on the bottom and 0.039 pixels on the right, all with responses above 0.92. The tray therefore remained stationary. This exact open-gripper path is cleared for one watched orange replay. Closing still requires a fresh wrist gate pass followed by accepted stall, lift and sideways-carry proof.

### Empirical path live replay rejected at the final gate

The orange was restored to `(151.94,147.59)`, only 3.17 top-camera pixels from the calibrated `(154,150)` target. The arm replayed the exact empty-tray-cleared path with the gripper open. At the final endpoint, the wrist gate measured `[+9.48,+50.21]` pixels relative to the verified grasp and rejected the close. The local Jacobian would require approximately -7.82 degrees pan and -16.42 mm radial movement; the best point inside the cleared ±5-degree/±4 mm envelope still predicts `[-22.24,+28.66]` and fails the gate. No close or contact occurred, the orange remained fixed, and the arm reversed the cleared path and returned home with torque off.

This rules out a constant raised-to-final image transfer even when overhead placement is tightly controlled. The next correction must be measured at multiple heights. A new final-depth branch from this exact cleared endpoint must first pass an empty-tray clearance test; only then may multi-height wrist feedback use it with the fruit.

### Final-depth correction branch empty-tray clearance pass

With the orange removed, the arm replayed the cleared empirical approach to its final endpoint, then tested the correction inferred from the rejected live gate: -7.817 degrees pan in one-degree steps followed by -16.422 mm radial movement in two-millimetre fixed-height, fixed-pitch steps. Tool z remained 9.49 mm and the gripper stayed open at 37. Top images were captured after every new step and wrist images at the pan endpoint, 8 mm radial point and final endpoint. No floor or rim contact was observed. The exact branch and complete approach reversed successfully, and the arm returned home with torque off.

The top camera had shifted as a whole between sessions by several pixels, and flexed slightly during the run. After subtracting global table-image motion, maximum tray-relative movement was about 1.52 pixels, inside the previously accepted 1.581-pixel limit. The compensated current placement target is `(157.56,141.78)` rather than yesterday's `(154,150)`. This exact correction branch is cleared for one watched orange replay; closing remains conditional on a fresh wrist gate pass.

### Final-depth correction live replay rejected: local Jacobian cannot be extrapolated

The orange was restored to `(159.74,147.14)`, 5.78 pixels from the compensated placement target. The arm replayed the cleared approach and the complete -7.817-degree/-16.422-mm final-depth branch with the gripper open. At the endpoint, the wrist gate measured `[+101.64,-41.56]` pixels relative to the verified grasp, a severe overshoot on both axes. No close occurred, the orange remained fixed, and the entire route reversed to home with torque off.

This establishes that the measured two-column wrist Jacobian is valid only for small local refinement. It must never again be extrapolated to a large correction. Further work must use small bounded moves, capture a fresh wrist measurement after each move, and repeat at several descent heights. Every height-specific correction region must be empty-tray cleared before fruit use.

### Multi-height bounded correction test: safe rejection with lateral residual

After the top-camera mount was secured, four stationary frames measured only 0.02--0.09 pixel of motion. With the orange removed, bounded correction envelopes of plus or minus 1 degree pan and plus or minus 2 mm radial motion were checked at modeled tool heights of 43.6, 33.2, 23.0, 13.0 and 9.5 mm. The gripper stayed open. The complete descent and return produced no observed contact; unobstructed tray regions moved about 0.3--0.7 pixel relative to the table, with the least reliable rim patch still below the previously accepted 1.5-pixel limit.

The orange was then restored at `(163.30,146.28)`, 7.3 pixels from the compensated overhead target. At 43.6 mm, local +1 degree pan and +2 mm radial probes were measured rather than extrapolated. The combined bounded offset produced intermediate errors of `[-4.71,-15.26]` pixels at 43.6 mm, `[+0.89,-12.20]` at 33.2 mm and `[+9.29,-9.33]` at 23.0 mm against the provisional height targets. At 13.0 mm the +2 mm radial path was on the boundary at `[+14.13,-5.04]`; reducing radial offset to +1 mm moved the image in the opposite direction and was undone.

The arm continued open along the empty-tray-cleared route to the real final grasp gate. The initial final error was `[+19.60,+28.49]` pixels. Fresh measurements were taken while stepping radial offset from +2 mm to -2 mm. At -2 mm the depth error improved to +9.17 pixels, but lateral error remained +22.62 pixels, so the close was rejected. The orange changed only 0.46 overhead pixel and the tray remained fixed. The route was reversed, the arm returned home, torque was disabled and the controller disconnected.

This test shows that multi-height feedback prevents blind descent and corrects the depth component, but the current final lateral envelope is too narrow for this approach seed. The next live attempt is blocked until an empty-tray test clears the approximately +5 degree additional final pan indicated by the measured lateral residual, or the approach seed is replaced by an overhead-camera table-coordinate solution. Repeating the current path or extending the correction without an empty-tray check is not useful.

### Additional final pan corridor cleared with empty tray

The orange was removed without moving the tray. The arm replayed the bounded multi-height approach with +1 degree pan and +2 mm radial offset, crossed the already cleared final radial range to -2 mm, then increased final pan from 64.9 to 70.2 degrees in one-degree-or-smaller steps. Top frames were captured after every pan step and wrist frames at both corridor endpoints. No jaw, wrist-body, tray-floor or rim contact was observed.

At the 70.2-degree endpoint, phase correlation measured about 0.43 pixel of tray-relative movement while the arm was present. After reversing the exact pan, radial and approach route and folding home, three unobstructed tray regions moved only 0.20--0.31 pixel relative to the stationary table references. The arm returned home, torque was disabled and the controller disconnected. The exact final pan corridor from 64.9 through 70.2 degrees at the -2 mm radial endpoint is cleared for one watched live scan. Each one-degree live step still requires a fresh wrist measurement; closing remains conditional on the real final ±14-pixel gate.

### Fourteen-pixel final gate rejected after false-positive empty close

With the orange restored at `(159.62,142.79)`, only 2.3 overhead pixels from the calibrated target, the arm replayed the cleared multi-height route and scanned the final radial and pan corridors. At pan 65.9 degrees and radial offset -2 mm, the old final gate reported error `[+13.17,-0.07]` pixels and passed because both axes were inside its provisional ±14-pixel window. The guarded close then reached 2.1 rather than the verified 16--26 hold range. The right jaw contacted the orange while the left jaw remained clear, pushing the fruit about 31.6 overhead pixels deeper in the tray. No lift or transport was attempted. The gripper reopened, the exact route reversed, the arm returned home and torque was disabled.

The old gate was too permissive: its lateral error was close to the 14-pixel boundary even though the depth error matched the successful reference. The final tolerance is now ±5 pixels per axis. Fingertip detection also selects the black component nearest each verified fingertip position instead of the largest eligible component, because black wrist hardware entered the right-tip ROI during the final radial scan. The verified success passes at `[0,0]`; the new false-positive regression frame rejects at `[+13.17,-0.07]`; the earlier centre replay and known miss remain rejected. Five regression tests pass. The cleared final pan scan may be repeated once with the tighter gate; closing is forbidden outside ±5 pixels on either axis.

### Tight wrist-image match still missed: require successful-pose geometry

The orange was restored at `(159.37,138.81)`, 3.47 overhead pixels from the calibrated target. The arm replayed the cleared route and scanned radial offset to -2 mm, then pan through the cleared corridor. One-degree pan samples bracketed the tightened gate: 67.9 degrees measured `[+5.50,+4.99]` pixels and 68.9 degrees measured `[-10.27,+2.38]`. A smaller cleared step to 68.25 degrees measured `[+1.84,+4.63]`, passed the ±5-pixel image gate, and closely matched the successful reference in orange area and fingertip span. Nevertheless, the guarded close reached 2.2 rather than the verified 16--26 hold range. The right jaw contacted the fruit while the left jaw remained clear; no lift was attempted. The gripper reopened, the route reversed, the arm returned home and torque was disabled.

Forward kinematics identifies the missing condition. The verified successful final pose `[74.5,-64.6,83.2,40.8,0]` places the modeled tool at `[77.438,-139.234,11.003]` mm. The image-matched failed pose `[68.2476,-52.3275,79.5066,32.221,0]` places it at `[96.284,-144.006,9.490]` mm. The failed pose is about `[+18.846,-4.772,-1.513]` mm away despite having essentially the same pitch sum and a near-identical wrist image. The current camera-relative 2D gate is therefore necessary but not sufficient for closing.

The joint-delta/multi-height approach seed is blocked for further live closes. The next solution must stay near the verified successful joint and Cartesian geometry, use overhead tray-relative localization to adjust that pose, and apply the wrist image gate only as final refinement. A future close must require both the tightened ±5-pixel image gate and a bounded Cartesian/joint-pose guard around the verified successful grasp. No further live close is permitted from the current `[68.25,-52.33,79.51,32.22]` family of endpoints.

### Successful-pose close interlock

`tray_grasp_pose_guard.py` now implements the missing independent 3-D condition. The reference is the verified successful arm pose `[74.5,-64.6,83.2,40.8,0]`, whose modeled tool position is `[77.438,-139.234,11.003]` mm. A pose passes only when its Cartesian distance is at most 3 mm and every arm joint is within 3 degrees of that reference. The known image-matched failure is rejected at about 19.5 mm Cartesian distance and 12.3 degrees maximum joint error.

The jog server disables the unguarded `close_stall` command. The only tray-close command is now `close_stall_guarded /absolute/path/to/fresh_wrist_image.jpg`. It requires, in order: a wrist image no more than five seconds old, the successful-pose 3-D gate, the tightened ±5-pixel wrist-image gate, and a second pose check after image processing. Only then can the existing drift-limited close execute. Nine offline regression tests pass across the wrist and pose gates.

This change prevents recurrence of the measured failure; it does not yet make auto-reset operational. The next physical step is an **empty-tray** replay based on the successful centre-pose branch. The orange must be removed while the tray stays taped in place. No close will be issued during that test. If the open gripper reaches and repeats the successful geometry without tray contact, one orange may be returned to the fixed centre pocket for a single guarded grasp. Five consecutive successful grasp-and-return cycles are required before enabling automatic reset.

### Successful-pose empty-tray replay passed

With the orange removed to the table and the taped tray left empty, the arm unfolded at pan 0, reached the 40 mm raised shape with measured-joint feedback, and rotated over the tray through the 33.5 mm absolute-height guard. Its measured height after the high pan was 38.44 mm. It then descended through every 5 mm Cartesian waypoint and the four small final approach steps used by the verified successful grasp. The gripper remained open at 37 and no close command was issued.

At the final endpoint the measured pose was `[74.3,-64.6,83.6,41.0,0,37]`. The new 3-D gate passed it at 2.473 mm Cartesian distance and 0.4 degree maximum joint error from the successful reference. Top and wrist frames showed no finger, wrist-body, tray-floor or rim contact. The exact route was reversed, the high pan-away again used the 33.5 mm guard, and the arm folded home with torque disabled.

Before/after phase correlation measured the tray at only `[+0.108,-0.020]` pixels relative to two stationary table patches. The tray therefore remained fixed. Evidence is under `reset/calibration_evidence/tray_success_pose_empty_clearance_20261106/`. The successful-pose branch is now cleared for one watched centre-orange grasp using `close_stall_guarded` with a newly captured wrist frame. Automatic reset remains disabled until that grasp succeeds and five consecutive complete grasp-and-return cycles pass.

### First successful-pose live replay rejected safely

The orange was placed at top-camera coordinate `[160.58,144.17]`, corresponding to the previously drawn green target near `[158,142]`. The arm replayed the exact successful-pose branch with the gripper open. At the final endpoint, measured q was `[74.5,-64.6,83.3,41.0,-0.4,37]`; the 3-D guard passed at 1.013 mm Cartesian distance and 0.4 degree maximum joint error.

The fresh wrist frame independently rejected the close at `[-88.72,-37.81]` pixels relative to the verified grasp. The orange was far toward the left jaw in the wrist view. No close command was sent and no grasp was attempted. The route reversed, the arm returned home, torque was disabled, and the orange moved only about 3.1 overhead pixels.

This result invalidates the `[158,142]` absolute overhead target. The camera geometry changed between the verified success and the current session, so an old absolute pixel coordinate cannot define the tray pickup point. Mapping the verified successful orange coordinate `[151,121.5]` through the clear old and current tray bounds gives a provisional current tray-relative target near `[173,116]`: about 12 pixels right and 28 pixels upward from the tested placement. This target may be used for one more gated replay, but closing remains conditional on both independent gates. Evidence is under `reset/calibration_evidence/tray_success_pose_guarded_live_20261106/`.

### Tray-relative target replay improved alignment but remained low

The next measured placement was `[172.85,122.77]`: horizontally aligned with the new `[173,116]` target but still 6.77 pixels low. The successful-pose replay again passed the independent 3-D gate at 1.372 mm Cartesian distance and 0.5 degree maximum joint error. Wrist error improved substantially from `[-88.72,-37.81]` to `[-22.16,-12.90]` pixels, confirming that the tray-relative correction moved in the correct direction, but the ±5-pixel gate still rejected. No close occurred. The orange moved only 0.177 overhead pixel, the route reversed, and the arm returned home with torque disabled.

The remaining placement adjustment is `[−0.02,−6.78]` top-camera pixels: essentially straight upward by about 0.85 cm to `[173,116]`. The observed improvement predicts that this final placement should bring the wrist measurement close to the tightened gate. Evidence is under `reset/calibration_evidence/tray_success_pose_guarded_live_target3_20261106/`.

`live_orange_placement_guide.py` replaces repeated still-image placement instructions. It is camera-only and never connects to the robot. The Rerun dashboard overlays the detected orange centre, `[173,116]` target, correction arrow, live x/y/distance plots and a green `READY — HANDS CLEAR` message inside a three-pixel placement window. It also writes the latest machine-readable measurement to `/tmp/so101_orange_placement_status.json`. This live guide should be used for the remaining calibration and for verifying a future physical tray pocket.

### Two-axis target solved; wrist edge-blob detector corrected

Three measured top-placement/wrist-error pairs produced a well-conditioned 2-D local mapping (condition number 2.48). Solving it moved the current target to approximately `[177.80,115.37]`. The live guide placed the orange at `[179.24,115.20]`, 1.45 pixels away. The next successful-pose replay passed the 3-D guard at 2.399 mm Cartesian distance and 0.4 degree maximum joint error.

The first wrist evaluation was invalid because `orange_blob` selected an orange-coloured table component touching the lower-left image edge at `[71.63,397.44]`. The actual fruit was clearly visible between the jaws at `[328.54,167.12]`. `wrist_grasp_gate.py` now selects the compact orange candidate nearest the verified fruit position when used in the fixed final wrist geometry; top-camera callers retain largest-blob behaviour. A new regression test covers this exact frame, and all ten wrist/pose tests pass.

The corrected evaluation of the saved final frame is `PASS` at `[-0.37,+4.99]` pixels, inside the tightened ±5-pixel window. Both independent pre-close gates therefore passed for this placement. No close occurred in this replay because the false rejection had already caused a safe retreat. One repeat of the unchanged placement is permitted for a live guarded close. Evidence is under `reset/calibration_evidence/tray_success_pose_guarded_live_target5_20261106/`.

The first repeat correctly refused the external-frame close: during the approximately 3.8-second C270 startup/capture, load-dependent elbow drift moved the modeled tool 6.740 mm from the successful reference, beyond the 3 mm pose limit. The fruit was untouched and the route reversed safely. This proves that a fresh file timestamp alone does not synchronize image and joint state.

`vision_calib_jog_server.py` now provides `close_stall_live /absolute/evidence.jpg`. It first restores the successful pose with measured-joint feedback, then continuously compensates all five arm joints while the wrist camera warms for 45 frames. It saves the final frame, checks the synchronized 3-D pose, applies the corrected ±5-pixel wrist gate, immediately rechecks pose, and only then calls the drift-limited close. The old unsynchronized command remains guarded but is no longer the operating path. Ten offline gate tests and compilation pass. The unchanged placement may be replayed once with this synchronized close.

The first synchronized attempt also refused safely. Camera reads completed faster than the loaded elbow settled, leaving 5.622 mm Cartesian error after warm-up. The fruit was untouched. The command now performs a second measured-joint alignment while the camera is already open, clears the prior frame, then captures ten post-correction frames while continuing 30 Hz pose compensation. This directly synchronizes the evaluated frame with the pose that must pass the 3 mm guard.

The post-warmup realignment attempt also refused at 5.915 mm Cartesian error. The measured elbow settled about 1.1 degrees away from the successful reference after the capture loop reset the load-compensation bias. No close occurred in any of these attempts. The orange and tray were not grasped, and the arm returned home with torque disabled.

This route is now blocked. `LIVE_CLOSE_APPROVED` is `False`, so `close_stall_live` refuses before motion. The next controller must retain the approximately 3–4 degree elbow compensation learned by measured-joint alignment instead of reinitializing its bias during image capture. It must pass an empty-tray hold-and-capture test at less than 3 mm Cartesian error across repeated captures. A shallow physical orange pocket at the solved tray-relative location is also required so placement does not depend on hand positioning. No further same-arm auto-reset grasp should run until both conditions are satisfied.

### Persistent load compensation and empty-tray qualification

The controller fix is implemented but has not yet been qualified on the physical arm. `load_compensated_hold.py` owns the incremental five-joint compensation calculation. `align_closed_loop` now returns its learned bias, the camera warm-up continues from that bias, the post-warmup realignment starts from the accumulated bias, and the synchronized-frame loop continues from the same value. The former `bias.fill(0.0)` reset is removed. Thirteen offline pose, vision and compensation tests pass.

`hold_capture_test /absolute/evidence.jpg` provides the qualification path. It follows the same alignment, warm-up, realignment, synchronized capture and 3-D pose gate as the live close, but it cannot close the gripper. `LIVE_CLOSE_APPROVED` remains `False`. With the tray empty and fixed at its marked position, run five hold captures. Every capture must pass with Cartesian distance at or below 3 mm, and no contact or tray displacement is allowed. Any failure resets the five-run count and keeps live close blocked. After the arm is returned home and torque is disabled, record the five results together in a new evidence directory.

The first empty-tray qualification stopped on test 2. Test 1 passed at 0.991 mm Cartesian distance and 0.279 degree maximum joint error, retaining approximately -3.90 degrees of elbow command compensation. Test 2 safely rejected at 3.271 mm and 0.396 degree. Tests 3--5 did not run, no close occurred, and no contact was observed. The route was reversed, the arm returned home, torque was disabled and the controller disconnected. Before/after phase correlation measured only `[-0.072,-0.155]` pixels of tray motion before table-reference subtraction.

This exposed two remaining controller boundaries. Each separate `hold_capture_test` call still began with zero compensation, and the 0.5-degree alignment exit condition could satisfy its joint test while missing the 3 mm Cartesian limit. `LoadCompensationState` now retains the learned five-joint bias across repeated commands. Capture alignment uses a 0.25-degree tolerance, and the synchronized phase can continue for up to 40 frames, exiting early only when the independent Cartesian/joint pose gate passes. Fourteen offline tests pass. The revised controller still requires a fresh five-pass empty-tray qualification; live close remains blocked.

The second qualification confirmed cross-command memory but stopped on test 3. Tests 1 and 2 passed at 1.279 mm and 0.404 mm. Their retained elbow compensation increased from -4.10 to -4.61 degrees. Test 3 refused before capture when compensation reached the unchanged 5-degree safety ceiling. No close or contact occurred; tests 4--5 did not run. The route was reversed, the arm returned home, torque was disabled and the controller disconnected.

The remaining defect is integral windup on encoder-scale residuals. The joint observations resolve at approximately 0.1 degree, so repeatedly integrating those small errors across otherwise successful captures can grow the command bias without improving pose. `compensated_arm_command` now applies a 0.15-degree deadband before integration while still returning the raw error for monitoring. The 5-degree compensation ceiling remains unchanged. Fifteen offline tests, including 100 repeated deadband updates, must pass before the next empty-tray qualification.

The deadband controller passed the complete empty-tray qualification. Five consecutive synchronized hold captures measured 1.229, 1.229, 1.645, 1.229 and 0.083 mm Cartesian distance from the verified successful grasp pose, all below the 3 mm limit. Maximum joint errors were 0.273, 0.273, 0.360, 0.273 and 0.132 degrees. The gripper remained open, no close command was issued and no contact was observed. The route was reversed, the arm returned home, torque was disabled and the controller disconnected. Tray motion relative to the two table references was only `[+0.112,-0.094]` pixels.

The loaded-pose controller requirement is now satisfied. `LIVE_CLOSE_APPROVED` remains `False`: the remaining prerequisite is a shallow physical orange locator at the solved tray-relative target so the reset placement is mechanically repeatable. Install and overhead-verify that locator before one guarded fruit grasp. Automatic reset remains disabled until the locator, guarded grasp, lift, return and five complete cycles pass.

### Black-cross manual target and rejected guarded approach

The solved overhead target was marked on the tray with a small black cross. The live guide verified the orange at `[176.84,116.92]`, 1.83 pixels from target `[177.7967,115.3657]`. This established a repeatable manual visual reference but did not mechanically constrain the fruit. The close command was changed to a default-disabled, process-local one-shot authorization: `SO101_ENABLE_ONE_LIVE_CLOSE=1` grants one attempt, and the authorization is consumed before synchronized capture begins.

The arm followed the cleared route with the gripper open and reached `[74.5,-64.6,83.6,40.8,0,37]`. The wrist gate rejected before close with an impossible `[-303.79,+179.77]` pixel error. Inspection of the saved frame showed the black cross between the open fingers but no orange. A fresh top frame after retreat showed the orange on the lower-left table outside the tray. Because the live guide had verified the orange immediately before the run, the open approach displaced it and it rolled out of the tray. No close or grasp occurred. The route was reversed, the arm returned home, torque was disabled and the controller disconnected.

This is direct evidence that the pen mark cannot replace the planned shallow physical locator. Do not repeat the guarded approach from a freely rolling orange. Install a low-profile ring or three shallow stops at the black cross, confirm that they do not intersect the cleared finger paths, then repeat overhead placement verification and one one-shot guarded approach. Live close remains disabled by default.

### One secured-orange diagnostic disproved the overhead-centroid target

The orange was mechanically secured over the black cross and the live top-camera guide measured its centre at `[176.43,114.72]`, only 1.51 pixels from the solved target `[177.7967,115.3657]`. The arm replayed the cleared successful-pose route and reached measured q `[74.4,-64.6,82.9,40.9,0,37]` with the gripper open. The process-local one-shot close authorization was then consumed by a synchronized wrist capture.

The wrist gate rejected at `[-22.53,-17.57]` pixels against the verified grasp reference, outside the ±5-pixel limit, so the gripper did not close. The exact route was reversed, the arm returned home, torque was disabled and the controller disconnected. A fresh top frame after the attempt measured the orange at `[176.47,115.09]`, 1.36 pixels from the same target. The secured fruit therefore did not move during the approach.

This isolates the remaining error: matching the irregular orange's 2-D top-camera blob centre does not reproduce its verified wrist-frame grasp alignment. Fruit orientation, height and viewpoint change its apparent centre, so further hand placement to the same pixel target cannot solve this reliably. This was the single agreed diagnostic repeat. Do not continue pixel chasing. The next auto-reset design must mechanically constrain the fruit's 3-D pose, or estimate its 3-D grasp point and adjust the final pose with vision. Evidence is under `reset/calibration_evidence/tray_secured_manual_mark_guarded_grasp_20261106/`.

### No-locator fallback: final-pose software correction is outside the cleared envelope

No material was available for a passive tray locator. The secured-orange wrist error `[-22.53,-17.57]` was therefore checked against the measured local Jacobian and the empty-tray-cleared final refinement envelope of ±1 degree pan and ±2 mm radial travel. The unconstrained zero-error solution requests approximately -3.070 degrees pan and +3.629 mm radial travel. The best point inside the cleared envelope is its `[-1 degree,+2 mm]` boundary and still predicts `[-13.06,-8.82]` pixels, outside the ±5-pixel close gate.

`bounded_wrist_correction.py` now performs this read-only check and returns `REFUSE_LOCAL_EXTRAPOLATION` for the current attempt. Three offline tests pass. This prevents the previously disproved large local-Jacobian extrapolation from being tried again. With no locator, automatic same-arm reset remains paused; near-term policy evaluation should use manual placement. A software-only reset requires a new raised, multi-height visual-servo calibration before any further fruit close.
