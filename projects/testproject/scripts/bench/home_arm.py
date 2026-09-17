"""Drive the follower to the pose every training episode starts from.

Every one of the 30 episodes begins with the arm parked at its home posture. A
trial that starts somewhere else asks the model for a situation it has never
seen at t=0, so the first actions mean nothing.

Moves in small interpolated steps over ~5 seconds rather than commanding the
target directly - the arm is 35 degrees away and a single command would make it
lunge.
"""

import json
import os
import subprocess
import time

import numpy as np

from lerobot.motors import Motor, MotorCalibration, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.utils.constants import HF_LEROBOT_CALIBRATION, ROBOTS

J = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
# median pose across all 30 episodes' start/end - they are the same pose
HOME = {"shoulder_pan": -2.6, "shoulder_lift": -104.3, "elbow_flex": 96.7,
        "wrist_flex": 78.4, "wrist_roll": -0.7, "gripper": 48.9}
SECONDS = 5.0
HZ = 30.0

out = subprocess.run(["python3", os.path.expanduser("~/arm_ports.py")],
                     capture_output=True, text=True).stdout
port = [l.split("=", 1)[1].strip() for l in out.splitlines() if l.startswith("export FOLLOWER_PORT")][0]
raw = json.load(open(os.path.join(HF_LEROBOT_CALIBRATION, ROBOTS, "so_follower", "my_so101_follower.json")))
calib = {k: MotorCalibration(**v) for k, v in raw.items()}
bus = FeetechMotorsBus(port=port,
                       motors={j: Motor(i + 1, "sts3215", MotorNormMode.DEGREES) for i, j in enumerate(J)},
                       calibration=calib)
bus.connect(handshake=False)
start = {j: bus.read("Present_Position", j) for j in J}
print("  moving to home over %.0f s" % SECONDS)
bus.enable_torque()
n = int(SECONDS * HZ)
for k in range(1, n + 1):
    a = k / n
    for j in J:
        bus.write("Goal_Position", j, start[j] + a * (HOME[j] - start[j]))
    time.sleep(1.0 / HZ)
time.sleep(1.0)
final = {j: bus.read("Present_Position", j) for j in J}
bus.disable_torque()
bus.disconnect()
print("  joint            target     reached    off by")
worst = 0.0
for j in J:
    d = final[j] - HOME[j]
    worst = max(worst, abs(d))
    print("  %-14s %8.1f %10.1f %9.1f" % (j, HOME[j], final[j], d))
print("\n  worst joint error %.1f deg - %s" % (worst, "at home" if worst < 6 else "NOT at home"))
print("  torque released")
