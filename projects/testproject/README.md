# Robot Arm Learning Project

This project is for building a leader/follower robot arm setup and using LeRobot to evaluate, collect, and train robot manipulation policies.

## Current Status

We have already evaluated pretrained policies in simulation:

- `lerobot/pi05_libero_finetuned` on LIBERO Object: `99/100`, or `99%`
- `lerobot/pi05_libero_finetuned` on LIBERO Spatial: `97/100`, or `97%`
- `lerobot/pi05_libero_finetuned` on LIBERO Goal: `96/100`, or `96%`

`LIBERO 10` was attempted twice on the 16 GB RAM Brev L4 instance, but the instance became unhealthy during startup/loading. The next retry should use a larger VM with at least 32 GB system RAM.

## Local Results

Videos copied locally:

- `/data/downloads/pi05_libero_object_tasks_0to9_10eps/`
- `/data/downloads/pi05_libero_spatial_tasks_0to9_10eps/`
- `/data/downloads/pi05_libero_goal_tasks_0to9_10eps/`

## Documentation

- [Simulator Evaluation](docs/simulator_evaluation.md)
- [Brev L4 Setup](docs/brev_l4_setup.md)
- [LIBERO Results](docs/libero_results.md)
- [Robot Hardware Plan](docs/robot_hardware_plan.md)
- [Leader/Follower Workflow](docs/leader_follower_workflow.md)

## Main Goal

Build a leader/follower robot arm setup, collect demonstrations, and train/evaluate robot manipulation policies using LeRobot.

The recommended path is:

1. Build and verify the follower arm.
2. Build and verify the leader arm.
3. Make teleoperation reliable.
4. Record simple demonstrations.
5. Train ACT first.
6. Evaluate ACT on the real robot.
7. Try SmolVLA fine-tuning after the hardware and dataset are stable.

