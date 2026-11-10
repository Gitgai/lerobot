# FT4B corrected held-out checkpoint comparison

Date: 2026-11-10

The three corrected FT4B checkpoints were evaluated on 101 fixed next-ten-action probes from all six held-out complete episodes (84 orange and 17 matchbox). This is an offline imitation ranking, not a robot success rate.

| Checkpoint | All MAE | Orange MAE | Orange arm MAE | Gripper MAE | Step-10 gripper agreement |
|---|---:|---:|---:|---:|---:|
| 3,000 | 3.2546 | 3.2574 | 3.5571 | 1.7108 | 100% |
| 6,000 | 3.1957 | **3.1764** | **3.4739** | 1.6421 | 100% |
| **9,000** | **3.1875** | 3.1769 | 3.4787 | **1.6279** | 100% |

Checkpoint 9,000 ranks first overall and has the lowest gripper error. Checkpoint 6,000 is effectively tied on orange and has a slightly lower orange arm-joint error. Select 9,000 for the first three watched orange trials and retain 6,000 as the immediate backup.

The evaluator was updated to decode ordered multi-file camera streams; the earlier version assumed one MP4 per camera and stopped before checkpoint inference. Exact output is in `holdout.json`.
