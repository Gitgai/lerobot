"""Log the follower's supply voltage right up to the instant its USB dies.

Hypothesis under test: the follower's board browns out when its servos draw
current, dropping off the USB bus. If that is right the voltage will collapse in
the last samples before the error. If the voltage is steady and the port dies
anyway, the fault is the cable or the board, not the supply.

Torque is enabled but NO movement is commanded - the arm is told to hold exactly
where it already is. If it still browns out while merely holding, that is the
strongest possible evidence for power, because nothing is being asked of it.
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
print("  follower on %s" % port, flush=True)

motors = {j: Motor(i + 1, "sts3215", MotorNormMode.RANGE_M100_100) for i, j in enumerate(JOINTS)}
bus = FeetechMotorsBus(port=port, motors=motors)
bus.connect(handshake=False)

hold = bus.sync_read("Present_Position", normalize=False)
print("  holding current pose, nothing will move", flush=True)
bus.enable_torque()
for j, v in hold.items():
    bus.write("Goal_Position", j, int(v), normalize=False)

t0 = time.perf_counter()
log = []
try:
    while time.perf_counter() - t0 < 30.0:
        v = bus.sync_read("Present_Voltage", normalize=False)
        ld = bus.sync_read("Present_Load", normalize=False)
        t = time.perf_counter() - t0
        log.append((t, min(v.values()) / 10.0, max(x & 0x3FF for x in ld.values())))
        time.sleep(0.05)
except Exception as exc:
    print("  DIED at %.2fs: %s: %s" % (time.perf_counter() - t0,
                                       type(exc).__name__, str(exc)[:70]), flush=True)
finally:
    try:
        bus.disable_torque()
        bus.disconnect()
        print("  torque released", flush=True)
    except Exception:
        print("  could not release torque through this handle", flush=True)

print("\n  last 20 samples before the end:")
print("    time    volts   peak load")
for t, v, l in log[-20:]:
    print("    %5.2fs %6.1fV %8d" % (t, v, l))
if log:
    vs = [v for _, v, _ in log]
    print("\n  voltage: started %.1fV, lowest %.1fV, ended %.1fV over %d samples"
          % (vs[0], min(vs), vs[-1], len(vs)))
