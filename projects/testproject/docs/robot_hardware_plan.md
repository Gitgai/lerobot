# Robot Hardware Plan

This is the detailed plan for building the leader/follower robot arm setup.

## Goal

Build two robot arms:

- Leader arm: moved by hand by the human.
- Follower arm: receives commands and repeats the leader motion.

After teleoperation works, use LeRobot to record demonstrations and train a policy.

## Guiding Principle

Do not start with training. Start with reliable hardware.

The order should be:

1. Hardware moves safely.
2. Motors report correct positions.
3. Calibration is repeatable.
4. Leader controls follower smoothly.
5. Cameras and robot state record cleanly.
6. Only then collect demonstrations.
7. Train ACT first.
8. Try larger vision-language-action models later.

## Hardware Components

Prepare these for each arm:

- Arm frame and joints
- Motors/servos
- Motor controller boards
- Power supply
- USB or serial connection
- Mounting base
- Gripper
- Emergency power switch
- Cable management

For the full learning setup:

- One or more RGB cameras
- Stable camera mounts
- A table/workspace
- Objects for simple tasks
- Local machine or Jetson/Orin for robot control
- Cloud GPU for heavier training if needed

## Workspace Setup

Use a simple, repeatable table layout.

Recommended workspace:

- Arm bolted or clamped to the table
- Camera fixed in one position
- Good lighting
- Plain background
- Object positions marked with tape
- Robot power switch reachable by hand

Avoid changing the table setup between data collection sessions. Robot learning is sensitive to camera angle, lighting, and object placement.

## Safety Checklist

Before powering the follower arm:

- Verify the power supply voltage.
- Verify the power supply current limit.
- Check that motors are connected in the right order.
- Check that no cable can catch in a joint.
- Keep the arm away from your face and hands during first motion.
- Start with low speed and low torque if supported.
- Keep an emergency stop or power switch nearby.

Before running any learned policy:

- Test in a clear workspace.
- Remove sharp, heavy, or fragile objects.
- Limit action range if possible.
- Be ready to cut power.

## Phase 1: Build The Follower Arm

The follower arm is the real robot that moves.

Tasks:

1. Assemble the frame.
2. Install each motor.
3. Connect motor cables cleanly.
4. Connect controller board.
5. Connect power.
6. Verify that the computer detects the controller.
7. Move one joint at a time.
8. Confirm joint direction.
9. Confirm joint limits.
10. Confirm gripper open/close.

Acceptance test:

```text
Each joint can move independently, slowly, and in the expected direction.
The gripper opens and closes.
The arm can return to a known home position.
```

## Phase 2: Build The Leader Arm

The leader arm is moved by hand. It should report joint positions, not fight the human.

Tasks:

1. Assemble the leader frame.
2. Install motors or encoders.
3. Configure the leader arm for low torque/passive movement if supported.
4. Read joint positions from the computer.
5. Move each joint by hand and verify position values change.
6. Confirm joint ordering matches the follower.
7. Confirm gripper input maps to follower gripper.

Acceptance test:

```text
Moving the leader by hand produces smooth, correct joint readings.
Joint 1 on leader maps to joint 1 on follower, and so on.
```

## Phase 3: Calibration

Calibration is one of the most important steps.

Goals:

- Define joint zero positions.
- Define joint limits.
- Make leader and follower agree.
- Save calibration files.

Recommended process:

1. Put both arms in the same physical home pose.
2. Record raw joint positions.
3. Save offsets.
4. Move leader joint 1 and check follower joint 1.
5. Repeat for every joint.
6. Test gripper open/close mapping.
7. Save calibration.
8. Power cycle and verify calibration still works.

Acceptance test:

```text
After restart, both arms still agree in home pose and teleoperation direction.
```

## Phase 4: Teleoperation

Teleoperation means the leader controls the follower in real time.

Start simple:

1. Move only one joint.
2. Move two joints.
3. Move all joints slowly.
4. Add gripper.
5. Add speed smoothing.
6. Add workspace limits.

Good teleoperation should feel:

- Smooth
- Predictable
- Not delayed too much
- Safe near joint limits

Acceptance test:

```text
You can use the leader arm to move the follower to a target object, close the gripper, lift the object slightly, and put it down.
```

## Phase 5: Camera Setup

Start with one camera before adding more.

Recommended first camera:

- Fixed third-person camera
- Shows the full arm, gripper, and workspace
- Does not move during data collection

Optional second camera:

- Wrist camera or side camera

Camera checklist:

- Image is sharp.
- Gripper is visible.
- Target objects are visible.
- Lighting is stable.
- No strong shadows.
- Camera does not shake.

Acceptance test:

```text
A human can watch the camera feed and understand what the robot is doing.
```

## Phase 6: First Demonstration Tasks

Choose very simple tasks first.

Good first tasks:

- Move gripper to a colored block.
- Pick up one block.
- Move block from left to right.
- Put block into a bowl.
- Open and close gripper near an object.

Avoid first:

- Complex insertion
- Soft objects
- Transparent objects
- Heavy objects
- Cluttered scenes
- Long multi-step tasks

## Phase 7: Data Collection

Record short, clean demonstrations.

Start with:

```text
Task: pick up one block and place it in a marked area
Episodes: 20-50
Camera: one fixed RGB camera
Policy target: ACT
```

Each demonstration should include:

- Camera frames
- Robot joint state
- Action commands
- Task name
- Success/failure label if possible

Data quality rules:

- Keep successful demos.
- Save failures separately.
- Do not mix different camera positions in one dataset.
- Do not change object types halfway through a dataset.
- Keep episode length consistent.

Acceptance test:

```text
You can replay a recorded episode and see synchronized video, state, and action data.
```

## Phase 8: Train ACT First

ACT is the recommended first training policy for your own robot.

Why ACT first:

- Easier to train than large VLA models.
- Faster iteration.
- Better for debugging hardware and data issues.
- Less compute-hungry.

First training target:

```text
Policy: ACT
Task: one simple pick-and-place task
Dataset size: 20-50 good demonstrations
```

Only after ACT works should we try SmolVLA fine-tuning.

## Phase 9: Evaluate On The Robot

Evaluation should be structured.

Example:

```text
Task: pick block and place in marked area
Trials: 20
Success metric: object ends inside target area
```

Track:

- Number of successes
- Number of failures
- Failure reason
- Video of each run
- Whether the robot needed human intervention

Failure categories:

- Did not reach object
- Reached object but missed grasp
- Grasped but dropped object
- Moved to wrong place
- Hit joint limit
- Camera/object not visible
- Unsafe motion

## Phase 10: Improve

Improve one thing at a time.

Possible improvements:

- More demos
- Better camera angle
- Better lighting
- Cleaner object placement
- Slower teleoperation
- Better calibration
- More consistent task reset
- More focused dataset

Do not change hardware, task, camera, and model all at once. Change one variable, test, then decide.

## Recommended Milestones

Milestone 1:

```text
Follower arm moves safely under direct control.
```

Milestone 2:

```text
Leader arm readings are correct.
```

Milestone 3:

```text
Leader controls follower smoothly.
```

Milestone 4:

```text
One camera records clear video.
```

Milestone 5:

```text
20 successful demonstrations recorded.
```

Milestone 6:

```text
ACT policy trained.
```

Milestone 7:

```text
ACT policy succeeds on at least 50% of simple real robot trials.
```

Milestone 8:

```text
Dataset and setup are stable enough to try SmolVLA fine-tuning.
```

