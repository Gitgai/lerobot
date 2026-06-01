# Simulator Evaluation

This document records the simulator work completed before moving into physical robot hardware.

## VLABench

We tested the idea of evaluating `lerobot/smolvla_vlabench` in VLABench.

Findings:

- The checkpoint is trained for VLABench-style simulation.
- It expects three camera inputs, robot state, and a 7D action output.
- It is not directly suitable for an SO-101 style physical arm.
- The VLABench run had action mismatch/debugging problems and poor task success, so we moved to LIBERO.

Conclusion:

VLABench is useful as a simulator target for that checkpoint, but it was not the best path for our immediate goal.

## LIBERO

LIBERO became the main simulator benchmark because LeRobot has a working pretrained policy for it:

- Policy: `lerobot/pi05_libero_finetuned`
- Simulator: LIBERO
- Task suites tested: Object, Spatial, Goal

This worked well and produced videos and success metrics.

## RoboCasa

RoboCasa was tested separately on Jetson Orin Nano.

What worked:

- Installed RoboCasa in a separate environment.
- Downloaded lightweight assets.
- Created a `CloseFridge` environment.
- Reset the environment.
- Rendered a smoke-test frame.

What did not happen yet:

- Full `lerobot/smolvla_robocasa` policy evaluation on Jetson.

Reason:

- Jetson CUDA PyTorch worked best in Python 3.10.
- Newer LeRobot RoboCasa evaluation expects Python 3.12.
- Python 3.12 CUDA PyTorch on Jetson was the blocker.

Conclusion:

Use Orin for simulator smoke tests and simple robotics workloads. Use cloud GPU for full pretrained policy evaluation.

