# Fine-tune 4 controlled close-window diagnosis

Date: 2026-11-09  
Scope: nine controlled small/medium citrus trials from fine-tune 4 checkpoints 2,000 and 3,000  
Safety: offline and read-only; the later shifted-camera large-citrus trials are excluded

## Outcome

The physical comparison contains three successes and six failures:

| Failure class | Count | Trials |
|---|---:|---|
| Offset approach or pass-by | 3 | 2k T2, 2k T4, 3k T2 |
| Visually centred close without retained lift | 3 | 2k T1, 2k T6, 3k T3 |
| Complete delivery | 3 | 2k T3, 2k T5, 3k T1 |

The policy can complete reach, lift, transport and release. Its unresolved problem is establishing and confirming a
load-bearing grasp.

## Held-out wrist-detector result

The fixed detector from `preclose_diagnostic_20261107` was applied without changing its thresholds:

| Reviewed outcome | Detector result |
|---|---:|
| Successful grasp labelled eligible | 3/3 |
| Failed grasp blocked or unknown | 3/6 |
| Total agreement | 6/9 |

Three failed closes were false permits:

- 2k T2: the fruit centre fell inside the broad image band even though one finger did not enclose it;
- 2k T6: the fruit looked centred, but the tight close did not survive lift;
- 3k T3: the fruit again looked centred, but no retained lift occurred.

This rejects a pre-close centre check as a motor gate in its current form. A 2D fruit centroid cannot prove that both
finger contact surfaces enclose the fruit, that the fingers are at the correct height, or that the grasp carries load.

## Measured gripper behavior

Successful closes produced a sustained contact aperture before transport:

- 2k T3: 25.2 at the selected close, then 27.3–29.2 while the fruit was retained;
- 2k T5: 21.1–20.6 across the close and initial lift;
- 3k T1: approximately 28.9 across chunks 68–72 before tray approach.

Two centred failures closed more tightly and immediately reopened:

- 2k T6: 14.8 at chunk 48, then 25.4 and 39.1;
- 3k T3: 18.0 at chunk 61, then 28.0 and 37.0.

The 2k T1 failure remained near 20 without a lift, so aperture alone is also insufficient. The verifier must combine
pre-close geometry, measured contact behavior and visual evidence that the fruit moves with the gripper during a
short lift.

Median request latency was 1.188–1.262 seconds across these trials and does not separate success from failure.

## Object and camera confounds

Checkpoint 2,000 trials 1–3 used the larger green-yellow citrus and scored 1/3. Its later three small-orange trials
also scored 1/3. Checkpoint 3,000 scored 1/3 on the small orange. The checkpoint comparison therefore remains tied,
but the six-trial checkpoint-2,000 headline combines two fruit appearances.

The subsequent large-citrus experiments used a visibly shifted, lower front-camera view. They are exploratory and
must not be merged into this controlled comparison. `camera_reference_vs_current.jpg` shows the mismatch.

## Decision and next implementation

1. Restore the documented overhead front-camera view before any further policy comparison.
2. Use one fixed small orange and the same marked start region.
3. Keep the pre-close detector in shadow mode as a blocker for gross misses.
4. Add a read-only post-close verifier requiring all of:
   - two consecutive plausible pre-close observations;
   - a nonempty, stable gripper-contact plateau after closing;
   - a short lift in which the fruit moves with the fingers and leaves the table.
5. If verification fails, reopen and request one new observation/replan; do not begin transport.
6. Validate the combined verifier prospectively on controlled trials before allowing it to alter motor commands.

More blind repetitions of checkpoints 2,000 or 3,000 are paused until the camera is restored and this verifier is
implemented in shadow mode.

## Artifacts

- `labels.csv`: reviewed FT4 close-window labels;
- `measurements.csv`: unchanged fixed-detector output;
- `close_state_windows.csv`: joint and gripper windows around each selected close;
- `annotated_montage.jpg`: visual detector review;
- `camera_reference_vs_current.jpg`: controlled versus shifted front-camera geometry.
