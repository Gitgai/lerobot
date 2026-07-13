# Raspberry Pi Zero 2W Camera Plan for LeRobot

## 1. Goal

Use the Raspberry Pi Zero 2W camera as an extra camera for the SO-101 LeRobot arm, without modifying the existing PiSnap/PiPics project.

The important rule:

```text
PiSnap stays untouched.
Robot camera stream is separate.
```

## 2. Current PiSnap Setup

Your existing PiSnap/PiPics Raspberry Pi setup already does this:

```text
Pi camera
  -> rpicam-still
  -> saves JPG files every few seconds
  -> PiPics FastAPI server serves saved images
```

Existing PiSnap/PiPics pieces:

```text
timelapse.service
pipics.service
/home/raspi/timelapse/
http://PI_IP:8000
```

This is good for timelapse/gallery work, but it is not ideal for robot control because robot control needs fresh camera frames continuously.

## 3. What We Will Not Touch

We will not edit or delete:

```text
PiSnap GitHub repo
pipicsserver GitHub repo
timelapse_loop.sh
pipics_server/server.py
pipics.service
timelapse.service
existing timelapse images
existing PiSnap app logic
```

## 4. What We Add Separately

Create a new separate folder on the Raspberry Pi:

```text
/home/raspi/lerobot_camera_stream/
```

This folder is only for LeRobot camera streaming.

Example contents later:

```text
robot_camera_server.py
requirements.txt
README.md
```

It will run on a different port:

```text
PiSnap/PiPics server:     http://PI_IP:8000
LeRobot camera stream:   http://PI_IP:8090
```

## 5. Important Camera Conflict

The Pi has one physical camera.

If PiSnap timelapse and LeRobot camera stream both use the camera at the same time, one may fail or become slow.

So the safe workflow is:

```bash
sudo systemctl stop timelapse.service pipics.service
# start robot camera stream
# use LeRobot / Pi05
sudo systemctl start timelapse.service pipics.service
```

This pauses PiSnap camera capture, but does not modify PiSnap.

## 6. Camera Role

Recommended camera layout:

```text
Laptop/USB camera          = front camera
Raspberry Pi Zero 2W camera = side/top/wrist camera
```

For Pi05, a second camera may help because one laptop camera does not give enough 3D information about the orange and gripper.

## 7. First Test Workflow

Step 1: Find Raspberry Pi IP.

```bash
ping raspberrypi.local
```

or use the known IP address.

Step 2: SSH into the Pi.

```bash
ssh raspi@PI_IP
```

Step 3: Pause only the timelapse service.

```bash
sudo systemctl stop timelapse.service
```

Step 4: Create a separate robot camera folder.

```bash
mkdir -p ~/lerobot_camera_stream
cd ~/lerobot_camera_stream
```

Step 5: Run a separate camera stream server.

We will choose the simplest stable option after checking what is installed on the Pi:

```text
Option A: rpicam-based MJPEG stream
Option B: Python snapshot/MJPEG server
Option C: mjpg-streamer
```

Step 6: Test from laptop browser.

```text
http://PI_IP:8090
```

or:

```text
http://PI_IP:8090/stream
```

Step 7: Test from laptop OpenCV.

```python
cv2.VideoCapture("http://PI_IP:8090/stream")
```

Step 8: Add it to our LeRobot/Pi05 test as an extra camera input.

## 8. Quality Settings

Start simple:

```text
Resolution: 640x480
FPS: 10-15 if stable
Lighting: bright and even
```

Do not chase high resolution first. Stable FPS is more useful for robot control.

## 9. Why This Helps

The current Pi05 tests with one laptop camera showed:

```text
arm moves
orange is visible
gripper is visible
but grasp is not reliable
```

Likely reason:

```text
Pi05 needs better visual geometry.
One camera view is not enough.
```

Adding the Pi camera may give a better side/top/wrist view so the model can better understand where the gripper is relative to the orange.

## 10. Success Criteria

We know this step is working when:

```text
PiSnap project remains unchanged
Pi camera stream opens in browser
OpenCV can read the stream from laptop
LeRobot/Pi05 script can record both cameras
Pi05 test video shows clearer object/gripper positioning
```

## 11. My Recommendation

Use the Raspberry Pi Zero 2W camera before spending more time on the ESP32-CAM.

Reason:

```text
Pi camera is usually more stable than ESP32-CAM
Pi has better networking and Python support
Pi stream is easier to integrate with LeRobot
```

Keep ESP32-CAM as a later experiment.

## 12. Current Live Wrist Stream

The current working wrist-camera path is:

```text
Raspberry Pi camera
  -> rpicam-vid live MJPEG stream on tcp://192.168.1.10:8892
  -> local laptop proxy tools/pi_wrist_proxy.py
  -> http://127.0.0.1:8092/frame
```

This replaced the older "latest saved PiSnap JPG" proxy.

Why:

```text
Old path scanned /home/raspi/timelapse for every frame.
That folder had many JPG files, so each frame could be several seconds stale.

New path keeps one rpicam-vid stream open.
The local proxy keeps the newest frame in memory.
The /frame endpoint returns in a few milliseconds.
```

Start the local wrist proxy:

```bash
cd /home/prakash-gaikwad/PrakashProjects/testproject
python3 -u tools/pi_wrist_proxy.py
```

For a background run:

```bash
cd /home/prakash-gaikwad/PrakashProjects/testproject
setsid python3 -u tools/pi_wrist_proxy.py > /tmp/pi_wrist_live_proxy.log 2>&1 < /dev/null &
```

Check status:

```bash
curl http://127.0.0.1:8092/status
```

Good status:

```text
"ok": true
"last_frame_age_seconds": less than 1.0
```

Important:

```text
PiSnap/PiPics must be paused while the live wrist stream is running,
because the Raspberry Pi has only one physical camera.
```

## 13. Saved Local Camera Links

These are the local browser links we are using for the current multi-camera setup:

```text
Top camera proxy page:   http://127.0.0.1:8094/
Top camera JPEG frame:   http://127.0.0.1:8094/frame
Top camera status:       http://127.0.0.1:8094/status

Logitech live-view page: http://127.0.0.1:8093/tools/c270_live_view.html
Pi wrist proxy page:     http://127.0.0.1:8092/
Pi wrist JPEG frame:     http://127.0.0.1:8092/frame
Pi wrist status:         http://127.0.0.1:8092/status
```

Current camera roles:

```text
Top   = Logitech C270 direct OpenCV / LeRobot camera
Front = laptop camera
Wrist = Raspberry Pi camera through Pi wrist proxy
```

Current known camera behavior:

```text
Front laptop camera:
  direct OpenCV capture works.

Top Logitech C270:
  direct LeRobot OpenCVCamera works.
  use /dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0.
  use MJPG and warmup_s=3.
  first cold one-shot frames can be black, so do not use single immediate frame capture as the test.
  the older browser proxy is only a fallback, not the preferred LeRobot path.

Wrist Raspberry Pi camera:
  live rpicam proxy works.
  use http://127.0.0.1:8092/frame.
```
