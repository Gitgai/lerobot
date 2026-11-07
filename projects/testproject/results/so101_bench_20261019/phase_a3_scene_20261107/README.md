# Phase A3 fixed scene and Phase B controlled trials

Date: 2026-11-07

The operator chose to keep the tray at its current position. `front_reference_current_tray.jpg` is therefore the
frozen scene reference. SIFT registration from successful U1 to that frame produced 140 inliers with 0.53-pixel
median error. `orange_marks_registered_current_tray.jpg` shows the transferred U1 orange centre as P0 and two
nearby diagnostic positions. The operator left the orange slightly below P0 and explicitly asked to continue
without another adjustment, so the accepted physical location is controlled but is not an exact U1 reproduction.

The arm start was read with torque disabled immediately before B1 and was within 0.15 degrees of U1. The model
server used fine-tune 3 `row3_all169_conservative_010000` on AI90 GPU 0 (RTX 5090), JPEG quality 85, no RTC, 20
executed actions per request and a 75-chunk cap. A no-robot dry request passed before motion. The full Rerun traces
are:

- `/home/gaikwad-prakash/bench_trace_ft3_phaseb1_orange_20261107`: acquisition failure; orange never lifted.
- `/home/gaikwad-prakash/bench_trace_ft3_phaseb2_orange_20261107`: success; lift by chunk 46 and release inside the
  tray by chunk 56.

Phase B currently stands at 1/2 acquisition and 1/2 end-to-end. A third unchanged repetition is required. B2 left
the orange in the tray, so the operator must return it to the same accepted table location before B3.
