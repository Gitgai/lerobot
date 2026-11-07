# Empty-workspace physical baseline check

Captured: 2026-11-07 12:35 IST  
Purpose: Phase A1 of the orange-to-tray reliability plan  
Policy motion: none

## Result

**Failed mount-stability acceptance; robot motion remains paused.**

The orange and tray were removed before capture. Both cameras produced fresh, changing 640x480 frames. All six
motors were readable with torque disabled, zero reported load, 7.2-7.3 V supply and 32-33 C temperature. The
`my_so101_follower` calibration file was present and its SHA-256 was recorded.

The top frame shows a clear swept area, a visibly separated gripper and no obvious loose arm part. The wrist frame
is overexposed around the gripper and shows only one black fingertip mark clearly; the other marked tip is outside
or occluded by the bright edge from this camera angle. Therefore the opening itself is confirmed, but exact
finger-height equality and parallelism cannot be established from these fixed views. Camera-mount rigidity under
light cable motion also requires a physical check; a still image alone cannot establish it.

## Recorded motor state

| Motor | Raw position | Torque | Load magnitude | Voltage | Temperature |
|---|---:|---:|---:|---:|---:|
| shoulder_pan | 2053 | off | 0 | 7.3 V | 32 C |
| shoulder_lift | 890 | off | 0 | 7.2 V | 33 C |
| elbow_flex | 3093 | off | 0 | 7.3 V | 32 C |
| wrist_flex | 2891 | off | 0 | 7.2 V | 33 C |
| wrist_roll | 1994 | off | 0 | 7.2 V | 33 C |
| gripper | 2166 | off | 0 | 7.3 V | 32 C |

The gripper calibration range is 1371-2834. Raw position 2166 is the baseline reading for the visibly separated
configuration shown here. It must not be interpreted as proof that the gripper is closed.

## Camera identity and current settings

- Front: Logitech C270, serial `FC7A6780`, stable by-id device, 640x480 YUYV at 30 fps, automatic exposure,
  brightness 128, contrast 32, saturation 32.
- Wrist: AK-Camera, serial `JV`, stable by-id device, 640x480 YUYV at 30 fps, automatic exposure, brightness 0,
  contrast 4, saturation 100.
- Consecutive-frame mean absolute differences were 2.60 for front and 1.80 for wrist; hashes also differed. Both
  streams were fresh during the capture.

## Remaining A1 check

Keep the arm unpowered and the table empty. Lightly test both camera mounts and the wrist cable for movement. An
additional viewpoint or a safe inspection pose is needed if exact tip-height and parallelism measurements are
required; do not alter the fixed policy cameras merely to obtain that view. Do not restore the U1 start pose until
the mount and cable check passes.

## Post-touch check

After the operator lightly checked the camera mounts and wrist cable, fresh frames were captured. Both black
fingertip marks were visible in the new wrist frame, confirming that the gripper was open and separated. The front
camera's stable table regions moved consistently by approximately 1-2 pixels horizontally and 2 pixels vertically:

| Front-camera region | X shift | Y shift | Phase response |
|---|---:|---:|---:|
| lower table | -2.17 px | -1.90 px | 0.83 |
| left table | -0.90 px | -2.22 px | 0.92 |
| lower-left table | -1.92 px | -2.18 px | 0.83 |

A second settled capture reproduced the same displacement, so this was not temporary vibration. A persistent
2-pixel shift is material for the 3-5-pixel visual tolerances used by the placement and grasp gates. The front
camera mount must be secured before selecting the new reference image.

The unpowered arm also drifted during the touch check: raw shoulder lift changed by -50 counts, wrist roll by +75,
shoulder pan by +19 and wrist flex by +11. The gripper changed by only -4 counts. Because the wrist camera moves
with the arm, the wrist-mount comparison is inconclusive and is not classified as a mount failure.

Machine-readable readings are in `camera_report.json`, `motor_report.json`, `mount_stability_report.json`, and
`motor_report_post_touch.json`.

## Secured-mount retest

After the front mount was tightened, two consecutive reference frames were initially stable to less than 0.01
pixel. A second light-touch test then displaced the front view persistently by 3.7-4.1 pixels horizontally:

| Front-camera region | X shift | Y shift | Phase response |
|---|---:|---:|---:|
| whole frame | +4.08 px | -0.08 px | 0.95 |
| lower table | +3.72 px | +0.14 px | 0.84 |
| left table | +3.87 px | +0.64 px | 0.83 |
| lower-left table | +3.67 px | +0.40 px | 0.80 |

The agreement across independent table regions and the high responses identify a real rigid image translation, not
auto-exposure noise. Tightening the existing attachment was insufficient. The camera head/hinge and cable require
rigid restraint and strain relief before another reference is accepted.
