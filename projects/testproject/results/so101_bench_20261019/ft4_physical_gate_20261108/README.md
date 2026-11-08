# Fine-tune 4 checkpoint 2,000 watched physical gate

Date: 2026-11-08  
Checkpoint: `ft4_orange_matchbox_corrective_20261108/checkpoints/002000/pretrained_model`  
Result: **1 complete orange-to-tray success in 3 controlled trials (33.3%)**

## Fixed settings

- AI90 RTX 5090, gRPC port 8081;
- overhead C270 plus AK wrist camera;
- instruction `pick up the orange and place it on the plate`;
- 20 executed actions per policy request at 30 Hz;
- 75-request cap and scripted return to the recorded start;
- central-area manual orange placement and fixed tray;
- full local trace streamed through the Rerun follower.

## Results

| Trial | Result | Median request latency | Minimum measured gripper | Observation |
|---|---|---:|---:|---|
| 1 | Fail | 1.235 s | 19.9 | Orange entered both fingers and the gripper closed, but it was not secured or lifted |
| 2 | Fail | 1.262 s | 17.4 | Approach was offset; repeated closes remained outside the right finger |
| 3 | **Success** | 1.257 s | 25.2 | Closed by about chunk 15, airborne by 18, released in the tray by 24, returned by about 40 |

Trial 3 was stopped after chunk 44 because the task and policy return were already complete. The client then restored
the exact recorded start pose. This is counted as success rather than an abort.

One preceding forward-right exploratory failure is excluded from the 1/3 score because its placement did not match
the controlled central protocol.

## Reading

Checkpoint 2,000 is deployable and can execute the full learned task, but acquisition is not repeatable. The failed
trials closed more tightly than the successful trial, showing that a low gripper value alone is not evidence of a
secure grasp. The useful distinction is visual centring followed by an immediate retained lift.

This gate does not justify a ten-trial success claim or the 90% target. Compare the successful and failed close
windows, then run checkpoint 3,000 through the same three-trial watched gate before choosing the candidate for the
matched ten-trial row.

Machine-readable details, source log paths and trace paths are in `gate_summary.json`.
