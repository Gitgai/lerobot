# FT4B checkpoint 9,000 watched orange gate

Dates: 2026-11-10 to 2026-11-11  
Checkpoint: `ft4b_orange_corrected_20261110/checkpoints/009000/pretrained_model`  
Result: **0 complete orange-to-tray successes in 3 controlled trials**

## Fixed settings

AI90 GPU 0 on port 8081, exact recorded instruction `pick up the orange and place it on the plate`, two fresh 640×480 cameras, 20 executed actions per request at 30 Hz, 75-request cap, same right-front orange placement, Rerun trace, and scripted return to the recorded start pose.

| Trial | Result | Median latency | Minimum gripper | Observation |
|---|---|---:|---:|---|
| 1 | Fail | 1.184 s | 33.5 at chunk 47 | Reached immediately, arrived beside the orange, pushed/followed it rightward, no retained grasp |
| 2 | Fail | 1.154 s | 36.6 at chunk 48 | Orange stayed outside one finger; repeated partial closes beside it, no lift |
| 3 | Fail | 1.143 s | 44.6 at chunk 55 | Reached immediately, passed beside the opposite side, no meaningful close or retention |

## Decision

Checkpoint 9,000 does not advance to the ten-trial gate. The corrected training removed the earlier long idle-start failure: all three trials began purposeful reaching promptly. It did not correct the dominant acquisition error. In all three trials the orange remained outside the two-finger opening when the gripper arrived, so later closing and recovery motions could not establish a grasp.

The next evidence-bearing step is an offline pre-close comparison of these three traces against the accepted demonstrations, using camera-space orange centre versus the two marked fingertips and predicted versus executed lateral/depth motion. Do not collect another blind row before identifying whether the repeated offset comes from deployed camera geometry, starting placement coverage, or learned action targeting.

The first three local launch attempts in this directory are void setup attempts: two local background processes were cleaned up before countdown and one policy connection failed before countdown because Qwen occupied GPU 0. None sent a policy action and none counts in the gate. The counted trials are `trial1_run4`, `trial2`, and `trial3`.
