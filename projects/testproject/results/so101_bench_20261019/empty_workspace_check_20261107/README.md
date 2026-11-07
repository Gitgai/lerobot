# Empty-workspace physical baseline check

Captured: 2026-11-07 12:35 IST  
Purpose: Phase A1 of the orange-to-tray reliability plan  
Policy motion: none

## Result

**Interim pass; physical fingertip comparison remains pending.**

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

Machine-readable readings are in `camera_report.json` and `motor_report.json`.
