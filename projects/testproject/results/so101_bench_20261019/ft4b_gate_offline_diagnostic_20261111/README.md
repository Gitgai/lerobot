# FT4B watched-gate offline diagnosis

Date: 2026-11-11

Scope: saved images, measured states and policy replay only; the robot and live cameras were not opened.

## Result

The 0/3 watched gate was run outside the demonstrated deployment geometry. Three independent measurements agree:

1. **Orange placement was outside the training cluster.** In the fixed 640×480 front view, all 25 training starts
   placed the orange centre at x=474.6–487.8 and y=329.4–352.2 pixels. Gate starts were:

   | Trial | Orange centre | Difference from demonstrated range |
   |---|---:|---|
   | 1 | (460.2, 343.8) | 14.4 px left; demonstrated y range |
   | 2 | (456.6, 309.0) | 18.0 px left and 20.4 px above |
   | 3 | (461.4, 317.4) | 13.2 px left and 12.0 px above |

   The measurement uses a Hough-circle fruit detector and is reproducible in `geometry.json`. Pixel position is an
   image-space coverage check, not a calibrated table coordinate.

2. **The scripted arm start was not the demonstrated arm start.** The largest difference is wrist roll:

   | State | Demonstration range | Demonstration median | Gate range |
   |---|---:|---:|---:|
   | wrist roll | −13.67° to −1.19° | −7.34° | +12.09° to +12.26° |
   | wrist flex | 77.45° to 78.86° | 78.42° | 79.21° |

   Gate wrist roll is at least 13.28° beyond every training start and about 19.5° from the training median. The
   nearest complete training start still differs by 18.29–18.46° on wrist roll. This rotates both the gripper and its
   wrist-camera view before the policy begins.

3. **The close approach differs visibly from the expert approaches.** The 25 expert pre-close wrist frames generally
   show the fruit deep between the two fingers. The gate frames show the fruit entering from a side or remaining near
   a fingertip. See `demo_preclose_wrist_montage.jpg` and `gate_preclose_wrist_montage.jpg`.

The front-camera field of view also changes across the gate starts relative to the demonstration montage: tray and arm
landmarks move in the image, especially in trials 2 and 3. This must be restored by matching the saved reference image
before another controlled comparison. No reliable millimetre displacement is claimed because the front camera has no
table-plane calibration.

## Checkpoint replay

Twelve saved observations were replayed three times each through checkpoints 6,000 and 9,000 with identical seeds,
20-action horizons and 15 inference steps. The checkpoints differ by only 0.448° mean action MAE across these cases
(largest case 0.672°). Checkpoint 9,000 is slightly closer to the historically recorded checkpoint-9,000 chunks:

| Checkpoint | Mean MAE versus recorded chunks |
|---|---:|
| 6,000 | 2.8278° |
| 9,000 | 2.6827° |

This is a stochastic replay consistency check, not a success metric. It provides no evidence that checkpoint 6,000
would correct the systematic physical offset, so a physical 6,000 trial is not justified.

## Decision and next gate

Do not retrain yet and do not run more trials from the +12° wrist-roll start. First restore the deployment conditions:

1. With the table empty and hands clear, move slowly to a demonstrated start pose. Use the demonstration median as the
   reference: `[-5.36, -104.44, 96.48, 78.42, -7.34, 58.51]` in joint order
   `[shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper]`.
2. Match the live front and wrist views to `demo_start_montage.jpg` and `wrist_start_montage.jpg`. Secure the cameras if
   their views move.
3. Place the orange in the demonstrated front-image region: centre x=475–488, y=329–352 in the restored 640×480 view.
4. Run three watched checkpoint-9,000 trials with all other settings unchanged.

If at least two of those three acquire and retain the orange, expand to ten matched trials. If the corrected gate still
fails acquisition, record corrective demonstrations from this exact standardized start and placement and train FT4C.
Only after the matched baseline is reliable should the dataset add wider placement coverage.

## Artifacts

- `geometry.json`: all detected centres and start-state comparisons.
- `checkpoint_replay.json`: exact 6,000/9,000 replay outputs and comparisons.
- `demo_start_montage.jpg`, `gate_start_montage.jpg`: front-view placement evidence.
- `wrist_start_montage.jpg`: demonstrated and gate wrist views at start.
- `demo_preclose_wrist_montage.jpg`, `gate_preclose_wrist_montage.jpg`: approach evidence.
- `scripts/audit_ft4b_gate_geometry.py`: reproducible geometry audit.
- `scripts/evaluate_ft4b_gate_replay.py`: read-only checkpoint replay.
