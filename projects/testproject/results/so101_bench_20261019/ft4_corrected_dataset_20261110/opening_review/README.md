# FT4 opening-frame visual review

Reviewed the front streams for all 30 accepted orange episodes and all five matchbox episodes. Wrist streams were
also checked for representative orange episodes 1, 6, 12, and 30. The contact sheets are under `all_35/`.

## Findings

- In 34/35 accepted episodes, the object is already placed and the robot remains at the start pose until expert movement begins.
- Orange episode 6 includes a human moving the orange from the tray to the table. The retained start begins after the hand has cleared.
- Wrist views remain stationary during the removed static/setup interval and begin changing with the expert reach.

The derivative retains five frames (0.167 seconds at 30 Hz) immediately before the first arm-command displacement of at least 3 degrees. Original source episodes are unchanged.

## Task instruction

The derivative uses the exact instruction stored by the original recording:

`pick up the orange and place it on the plate`

## Training status

Dataset preparation and audit are complete. Training was not started.

## Padding correction found during recheck

The first derivative added 25 shortened approach-through-lift entries. A deeper loader review found that PI05 trains
on 50 future actions and averages loss over episode-end padding without masking it. A shortened entry ending during
transport would therefore teach an artificial repeated terminal action. That derivative was rejected before
training. The corrected dataset contains only 29 complete, naturally ending training entries and six complete held-out
entries. No phase-window duplication remains.
