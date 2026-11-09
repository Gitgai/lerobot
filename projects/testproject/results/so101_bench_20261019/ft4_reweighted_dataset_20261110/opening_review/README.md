# FT4 opening-frame visual review

Reviewed the front and wrist streams for orange source episodes 1, 6, 12, and 30. These cover short, typical, and longest automatically identified openings.

## Findings

- Episode 1: orange is already placed; the robot remains at the start pose until expert movement begins.
- Episode 6: the opening includes a human moving the orange from the tray to the table. The retained start begins after the hand has cleared.
- Episode 12: orange is already placed; the robot remains at the start pose until expert movement begins.
- Episode 30: orange is already placed; the robot remains at the start pose until expert movement begins.
- Wrist views remain stationary during the removed static/setup interval and begin changing with the expert reach.

The derivative retains five frames (0.167 seconds at 30 Hz) immediately before the first arm-command displacement of at least 3 degrees. Original source episodes are unchanged.

## Task instruction

The derivative uses the exact instruction stored by the original recording:

`pick up the orange and place it on the plate`

## Training status

Dataset preparation and audit are complete. Training was not started.
