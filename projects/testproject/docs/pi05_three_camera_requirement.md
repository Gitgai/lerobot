# Pi05 Three-Camera Requirement

Last updated: 2026-07-19

This document records the current decision:

```text
We will not treat a two-camera run as a valid Pi05 pick-orange evaluation.
The correct evaluation requires top, front, and wrist cameras.
```

This is not about being strict for no reason. The current observed failure is near the end of the task:

```text
reach toward orange works
touch/push sometimes works
center gripper around orange is weak
close and lift are not reliable
```

The wrist camera is exactly the view that can help the policy see close-range gripper/object alignment. Removing it would create a weaker test and could lead us to the wrong conclusion.

## 1. Required Camera Inputs

For the intended official Pi05 evaluation, the robot must provide:

```text
top camera
front camera
wrist camera
robot joint state
task text
```

The camera requirement is:

```text
top   = normal LeRobot/OpenCV-readable camera
front = normal LeRobot/OpenCV-readable camera
wrist = normal LeRobot/OpenCV-readable camera
```

Preferred Linux form:

```text
/dev/videoX
```

The camera must be readable by official LeRobot `OpenCVCamera` with:

```text
width = 640
height = 480
fps = 30
```

## 2. What Is Not Acceptable For Main Evaluation

Do not use these as the main Pi05 evaluation setup:

```text
top + front only
duplicating one camera into top/front/wrist
missing wrist camera padded by the model
ESP32 serial/JTAG device as camera
Raspberry Pi TCP stream directly if official LeRobot rejects width/height/FPS validation
custom camera adapter before official camera options are exhausted and approved
```

Reason:

```text
Those setups do not prove whether the intended three-camera policy can solve the task.
They are camera/infrastructure experiments, not final Pi05 behavior evidence.
```

## 3. Accepted Wrist Camera Solutions

### Option A: Small USB UVC Wrist Camera

This is the preferred clean solution.

Requirement:

```text
USB camera appears as /dev/videoX
v4l2-ctl reports Video Capture
OpenCV can read frames
official LeRobot robot_client can connect it as wrist
```

Why:

```text
No stream bridge.
No Raspberry Pi camera service.
No ESP32 firmware issue.
No custom script.
Most compatible with official LeRobot.
```

### Option B: Fixed v4l2loopback Wrist Device

This keeps the Raspberry Pi camera, but only if the local loopback behaves like a real capture camera.

Requirement:

```text
/dev/video6 reports Video Capture
OpenCV can open /dev/video6
OpenCV can read 640x480 RGB frames
official LeRobot robot_client can use /dev/video6 as wrist
```

Current blocker:

```text
/dev/video6 reports Video Output only.
OpenCV cannot read it as a camera.
```

### Option C: ESP32 Only If It Becomes UVC

The currently connected ESP32 is not acceptable as a wrist camera because the laptop sees it as:

```text
/dev/ttyACM1
Espressif USB JTAG/serial debug unit
```

That is a serial/JTAG device, not a camera.

ESP32 becomes acceptable only if it is flashed/configured so Ubuntu sees it as:

```text
/dev/videoX
```

and `v4l2-ctl` reports:

```text
Video Capture
```

## 4. Gate Before Any Pi05 Evaluation

Do not run the main Pi05 official evaluation until this gate passes:

```text
top camera readable
front camera readable
wrist camera readable
all three precheck images saved
official robot_client connects all three cameras
RunPod policy_server ready
official defaults preserved
```

If any camera is missing:

```text
stop
fix camera
do not run Pi05 evaluation
do not fine-tune based on that failed setup
```

## 5. How To Label Non-Compliant Tests

If a non-three-camera test is ever run for infrastructure debugging, label it clearly:

```text
camera_infrastructure_test_only
not a Pi05 pick-orange evaluation
not valid evidence for final model behavior
```

Do not use such a run to decide:

```text
whether Pi05 can grasp
whether the model needs fine-tuning
whether the dataset is sufficient
whether close-range correction episodes are required
```

## 6. Current Next Action

Current correct next action:

```text
Get or fix a wrist camera that appears as a normal /dev/videoX capture camera.
```

Preferred path:

```text
mount a small USB UVC camera on the wrist
verify it appears as /dev/videoX
save top/front/wrist precheck images
then run official LeRobot three-camera async evaluation
```
