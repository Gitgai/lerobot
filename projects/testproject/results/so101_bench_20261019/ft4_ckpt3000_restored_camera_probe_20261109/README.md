# FT4 checkpoint 3,000: restored-camera small-orange probe

Date: 2026-11-09  
Result: **0/1**  
Execution: 20 actions per request, 30 Hz, 75-request cap, return to start

The front camera was restored to the controlled overhead view and checked before movement. The tray occupied the
upper-left of the frame, the arm was upper-centre and the orange was unobstructed below the gripper.

The policy reached the orange, contacted it with an offset approach and pushed it right. It later closed around the
orange edge but did not retain it through lift; the gripper reopened and the arm moved away. There was no transport
or tray release. Mean request latency across 75 requests was 1,140 ms (median 1,181 ms; maximum 1,393 ms).

This probe shows that restoring the camera removes the low/side-view confound but does not by itself fix acquisition.
Further blind checkpoint trials are paused pending shadow-mode validation of pre-close centring, retained lift and
tray-release checks.

Raw trace: `/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_small_orange_restoredcam_20261109_t3`
