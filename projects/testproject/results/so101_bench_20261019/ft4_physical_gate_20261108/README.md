# Fine-tune 4 checkpoint 2,000 watched physical gate

Date: 2026-11-08  
Checkpoint: `ft4_orange_matchbox_corrective_20261108/checkpoints/002000/pretrained_model`  
Result: **2 complete orange-to-tray successes in 6 controlled trials (33.3%)**

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
| 4 | Fail | 1.219 s | 23.7 | Offset close pushed the orange right; it was never secured or lifted |
| 5 | **Success** | 1.188 s | 20.6 | Secure grasp by about chunk 29; released in the tray by 38 and remained there through 55 |
| 6 | Fail | 1.193 s | 14.8 | Repeated offset closes; orange stayed on the table and no transport began |

Trial 3 was stopped after chunk 44 because the task and policy return were complete. Trial 5 completed delivery by
chunk 38. A hand removed the orange at chunk 56 after completion but before the cap; that intervention is visible in
the trace and is recorded rather than mistaken for policy behavior. The completed delivery remains a success.

One preceding forward-right exploratory failure is excluded from the 2/6 score because its placement did not match
the controlled central protocol.

## Reading

Checkpoint 2,000 can execute the full learned sequence, but acquisition is not repeatable. Three of four failures
were offset closes beside the orange, and one centred close did not retain the fruit through lift. The failures often
closed more tightly than the successes, so gripper value alone does not prove a grasp. Visual centring and a retained
lift distinguish the successful trials.

At 2/6, further repetitions of checkpoint 2,000 are unlikely to change the candidate decision. Run checkpoint 3,000
through the same watched three-trial gate. Only the stronger candidate should proceed to a matched ten-trial row.

Machine-readable details, source log paths and trace paths are in `gate_summary.json`.
