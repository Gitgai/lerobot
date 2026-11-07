# Empty-workspace physical baseline check

Captured: 2026-11-07 12:35 IST  
Purpose: Phase A1 of the orange-to-tray reliability plan  
Policy motion: none

## Result

**Interim pass; physical fingertip comparison remains pending.**

The orange and tray were removed before capture. Both cameras produced fresh, changing 640x480 frames. All six
motors were readable with torque disabled, zero reported load, 7.2-7.3 V supply and 32-33 C temperature. The
`my_so101_follower` calibration file was present and its SHA-256 was recorded.

The top frame shows a clear swept area and no obvious loose arm part. The wrist frame is overexposed around the
gripper and shows only one black fingertip mark clearly. The top crop also cannot separate the two marks because
the gripper is nearly closed in the current resting pose. Therefore finger-height equality, parallelism and opening
symmetry have not yet been demonstrated. Camera-mount rigidity under light cable motion also requires a physical
check; a still image alone cannot establish it.

## Recorded motor state

| Motor | Raw position | Torque | Load magnitude | Voltage | Temperature |
|---|---:|---:|---:|---:|---:|
| shoulder_pan | 2053 | off | 0 | 7.3 V | 32 C |
| shoulder_lift | 890 | off | 0 | 7.2 V | 33 C |
| elbow_flex | 3093 | off | 0 | 7.3 V | 32 C |
| wrist_flex | 2891 | off | 0 | 7.2 V | 33 C |
| wrist_roll | 1994 | off | 0 | 7.2 V | 33 C |
| gripper | 2166 | off | 0 | 7.3 V | 32 C |

The gripper calibration range is 1371-2834. Raw position 2166 is approximately +8.7 on the calibrated -100 to
+100 range, which explains why the fingertips overlap in this view; this is a reading, not a gripper-zero test.

## Camera identity and current settings

- Front: Logitech C270, serial `FC7A6780`, stable by-id device, 640x480 YUYV at 30 fps, automatic exposure,
  brightness 128, contrast 32, saturation 32.
- Wrist: AK-Camera, serial `JV`, stable by-id device, 640x480 YUYV at 30 fps, automatic exposure, brightness 0,
  contrast 4, saturation 100.
- Consecutive-frame mean absolute differences were 2.60 for front and 1.80 for wrist; hashes also differed. Both
  streams were fresh during the capture.

## Remaining A1 check

With the arm still unpowered and the table empty, open the gripper enough that both marked tips are separated.
Capture fresh front and wrist frames, compare tip height and finger parallelism, and lightly test both camera mounts
and the wrist cable for movement. Do not restore the U1 start pose until this check passes.

Machine-readable readings are in `camera_report.json` and `motor_report.json`.
