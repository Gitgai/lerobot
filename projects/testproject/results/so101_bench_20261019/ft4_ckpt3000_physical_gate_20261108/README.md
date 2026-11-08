# Fine-tune 4 checkpoint 3,000 watched physical gate

Date: 2026-11-08  
Checkpoint: `ft4_orange_matchbox_corrective_20261108/checkpoints/003000/pretrained_model`  
Result: **1 complete orange-to-tray success in 3 controlled trials (33.3%)**

## Fixed settings

The protocol matched checkpoint 2,000: AI90 GPU 0 on port 8081, two cameras, exact orange instruction, 20 executed
actions per request at 30 Hz, 75-request cap, central placement, Rerun trace, and scripted return to start.

## Results

| Trial | Result | Median latency | Minimum gripper | Observation |
|---|---|---:|---:|---|
| 1 | **Success** | 1.237 s | 19.9 | Recovered late, secured the orange around chunks 67–68, and released it in the tray at the cap |
| 2 | Fail | 1.249 s | 21.6 | Passed the orange open, stretched beyond it, then closed over empty table |
| 3 | Fail | 1.221 s | 18.0 | Centred and closed repeatedly but never retained the orange through lift |

## Comparison and decision

Checkpoint 2,000 scored **2/6 (33.3%)** and checkpoint 3,000 scored **1/3 (33.3%)**. Checkpoint 3,000 therefore did
not improve the observed end-to-end rate. Its success also required a late recovery and used the entire cap.

Neither candidate advances to the matched ten-trial row. The next useful work is the offline close-window comparison
and a revision focused on centring plus retained lift before collecting more blind repetitions.

Machine-readable details and source trace paths are in `gate_summary.json`.
