# Read-only wrist pre-close diagnostic — calibration report

Date: 2026-11-07  
Policy evidence: fine-tune 3 orange trials O1, R2, R3, R5, U1, AH1-AH6 and AI1  
Safety status: offline and read-only; no robot connection and no action modification

## Result

The initial detector agrees with all 12 manually reviewed calibration frames:

| reviewed class | detector result | agreement |
|---|---|---:|
| successful grasp pose | eligible | 5/5 |
| failed grasp pose | ineligible or unknown | 7/7 |
| total | correct gate decision on the calibration set | 12/12 |

This is not a validation accuracy claim. The thresholds were selected using these same reviewed frames, there is no
held-out set yet, and one frame per trial does not establish temporal reliability.

## Measured cause in adaptive trial AI1

AI1 used 20-action coarse execution, switched to five-action execution at chunk 24 and returned to 20-action
recovery at chunk 76. The server continued predicting 20 actions throughout.

At chunk 23 the green-orange fruit looked laterally plausible between the fingers, but its detected wrist-camera
centre was approximately `(335, 344)` in the 640×480 image. It was below the reviewed effective grasp band and too
deep toward the gripper palm. The five selected successful closes had centres around:

```text
O1  (381, 201)
R2  (305, 224)
R3  (298, 164)
R5  (317, 215)
U1  (362, 177)
```

The failed fruit continued moving downward in the wrist view rather than into the contact region. The gripper later
closed without securing it, and the 20-action recovery made empty closes after the fruit left the wrist view.

The action trace also shows that five-action execution delayed some planned closes. At AI1 chunks 36-37, the full
prediction reached its tighter gripper values around action indices 16-17, while the first five actions stayed near
the open value. By chunk 38 a close entered the first five actions, so truncation delayed but did not fully suppress
the close. The decisive remaining error was spatial depth, not action horizon alone.

## Prototype

[`analyze_wrist_grasp_geometry.py`](../../../scripts/analyze_wrist_grasp_geometry.py) performs these read-only steps:

1. Resize the wrist image to the policy-input resolution, 640×480.
2. Detect bright, saturated circular candidates using a Hough transform.
3. Select the strongest candidate using saturation, brightness and radius.
4. Compare its normalized centre and radius with the reviewed grasp band.
5. Return `eligible`, `ineligible` or `unknown`.

The fixed band is expressed in normalized image coordinates. It is appropriate only for this fixed wrist-camera
mount, isolated orange task and current gripper geometry. It is not a general object detector.

`unknown` is a blocking result. AH1, AH2, AH4 and AH6 are gross misses in which occlusion or partial visibility
prevents a confident circle estimate. A future gate must never convert uncertainty into permission to close.

## Artifacts

- `preclose_labels.csv`: reviewed calibration labels and reasons.
- `preclose_measurements.csv`: detector output and measurements.
- `samples/`: the 12 exact wrist policy-input frames used for calibration.
- `annotated/`: per-frame diagnostic overlays.
- `annotated_montage.jpg`: one-page visual review of all calibration decisions.

Reproduce the measurements from the `projects/testproject` environment with:

```bash
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python \
  scripts/analyze_wrist_grasp_geometry.py \
  results/so101_bench_20261019/preclose_diagnostic_20261107/preclose_labels.csv \
  --output results/so101_bench_20261019/preclose_diagnostic_20261107/preclose_measurements.csv \
  --annotated-dir results/so101_bench_20261019/preclose_diagnostic_20261107/annotated
```

## Decision

Do not enable an action gate yet. Before motor commands can depend on this diagnostic:

1. Label separate pre-close frames from additional successful and failed trials as a held-out set.
2. Require the same decision over at least two consecutive observations.
3. Verify that every held-out successful close remains eligible.
4. Run shadow mode during controlled trials after the empty-workspace and restored-start checks.
5. Treat `ineligible` and `unknown` as hold-and-reobserve conditions with at most two retries.

This detector can prevent a visibly bad close. It cannot generate the missing correction that moves the gripper
from a bad depth to a good one. Corrective demonstrations and a new fine-tuned checkpoint remain necessary if
hold-and-replan does not produce an eligible pose.

## Held-out Phase B check

After the thresholds were fixed, six separate frames from controlled trials BCTRL1-BCTRL3 were reviewed under
`heldout_phase_b/`. The gate agreed with all six physical outcomes: B2 c43, the sole close that produced a stable
lift and delivery, was `eligible`; one failed close was `ineligible`; and four failed, partly occluded edge views were
`unknown`. Because `unknown` blocks closing, all five failed closes would have been stopped.

This small selected-frame result supports continuing to shadow mode, but it does not justify action gating. It has
only one positive example and does not establish prospective or consecutive-frame reliability. See
`heldout_phase_b/README.md` and `heldout_phase_b/annotated_montage.jpg`.
