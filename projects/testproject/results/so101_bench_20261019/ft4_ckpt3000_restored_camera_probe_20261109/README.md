# FT4 checkpoint 3,000: restored-camera small-orange row

Date: 2026-11-09  
Result: **1/5 (20%)**
Execution: 20 actions per request, 30 Hz, 75-request cap, return to start

The front camera was restored to the controlled overhead view and checked before movement. The tray occupied the
upper-left of the frame, the arm was upper-centre and the fixed small orange was unobstructed below the gripper.

| Trial | Result | Acquisition | Delivery | Mean request latency |
| --- | --- | --- | --- | ---: |
| T1 | fail | offset contact; close without retained lift | none | 1,140 ms |
| T2 | fail | passed/closed to the side of the orange | none | 1,131 ms |
| T3 | success | secure close around chunks 37–38 | released in tray by chunk 47 | 1,177 ms |
| T4 | fail | secure grasp and carry | orange ended on table immediately in front of tray | 1,186 ms |
| T5 | fail | centred close without retained lift | none | 1,180 ms |

The restored camera removed the view mismatch but did not make acquisition repeatable. Three of five trials failed
before a retained lift. One obtained a real grasp and carry but failed at release, and one completed the task.

## Offline verifier check

The existing fixed wrist-image pre-close detector was applied without retuning to one reviewed frame from each
trial. A pre-close frame was labelled eligible when the later trace proved a real grasp, even if delivery later
failed. It allowed both real grasps (T3 and T4), blocked T1 and T2, and incorrectly allowed T5. Agreement was
**4/5**: positive eligibility **2/2**, failed-acquisition blocking **2/3**.

This result demonstrates why an image-centering check cannot be the only motor gate. T5 looked centred before the
fingers closed but did not retain the orange. Retrospective post-close evidence separates the cases:

| Trial | Pre-close check | Orange follows short lift | Orange remains in tray | Verified stage |
| --- | --- | --- | --- | --- |
| T1 | block | no | n/a | acquisition failure |
| T2 | block/unknown | no | n/a | acquisition failure |
| T3 | allow | yes | yes | success |
| T4 | allow | yes | no | release failure |
| T5 | allow (false positive) | no | n/a | acquisition failure |

The next implementation should run these checks prospectively in shadow mode: require plausible pre-close geometry,
then confirm that the orange moves with the fingers during a short lift, and finally confirm that it remains inside
the tray after release. These results validate the check sequence offline; they do not yet establish a safe live
action gate.

## Shadow implementation

The bench client now has `--shadow-grasp-verifier`. When enabled, it records a read-only state machine alongside the
normal trace and exposes it in the Rerun viewer. It detects close transitions from measured gripper motion, requires
two plausible wrist observations plus a stable closed aperture and arm motion for retained lift, then checks the
orange centre against the fixed overhead tray region when the gripper reopens. It has no robot/action method and its
return value is never consulted by the dispatch loop.

Replay over all five trials produced the reviewed stage verdicts exactly: T1/T2/T5 acquisition failure, T3 success
and T4 delivery failure. The full stateful verifier averaged **11.79 ms per observation** over the 300-observation
T2–T5 trace. This is a calibration replay on the same evidence used to build the thresholds, not held-out accuracy.
The next requirement is a prospective watched row with the verifier enabled and the policy unchanged.

Artifacts:

- `verification/preclose_labels.csv`: reviewed labels and source frames.
- `verification/preclose_measurements.csv`: detector decisions and measurements.
- `verification/annotated/`: detector overlays.
- `verification/shadow_replay_T1.json` and `shadow_replay_T2_T5.json`: complete state-machine replay results.
- `key_frames/`: acquisition, carry and release evidence.
- Raw T1 trace: `/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_small_orange_restoredcam_20261109_t3`.
- Raw T2–T5 trace: `/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_small_orange_restoredcam_20261109_t2_t5`.
