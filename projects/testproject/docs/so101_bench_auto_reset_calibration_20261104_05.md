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
