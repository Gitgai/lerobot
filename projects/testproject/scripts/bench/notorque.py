"""CONTROL: hammer the follower's bus for 30 s with torque OFF.

Every torque-on run so far has died within ~1 s. Every read-only probe has
survived. This makes that contrast a measurement: the same read pattern as
voltrace.py, same rate, same port - the only difference is torque is never
enabled. If this survives 30 s the trigger is torque, not bus traffic.
"""

import os
import subprocess
import time

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
out = subprocess.run(["python3", os.path.expanduser("~/arm_ports.py")],
                     capture_output=True, text=True).stdout
port = [l.split("=", 1)[1].strip() for l in out.splitlines()
        if l.startswith("export FOLLOWER_PORT")][0]
motors = {j: Motor(i + 1, "sts3215", MotorNormMode.RANGE_M100_100) for i, j in enumerate(JOINTS)}
bus = FeetechMotorsBus(port=port, motors=motors)
bus.connect(handshake=False)
t0 = time.perf_counter()
n = 0
try:
    while time.perf_counter() - t0 < 30.0:
        bus.sync_read("Present_Voltage", normalize=False)
        bus.sync_read("Present_Load", normalize=False)
        bus.sync_read("Present_Position", normalize=False)
        n += 1
        time.sleep(0.05)
    print("  SURVIVED 30 s with torque OFF: %d read cycles, no dropout" % n)
except Exception as exc:
    print("  DIED at %.2fs with torque OFF: %s" % (time.perf_counter() - t0, type(exc).__name__))
finally:
    try:
        bus.disconnect()
    except Exception:
        pass
