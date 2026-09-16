"""Report torque state on the follower and release it.

The sync test died on a USB dropout, so SOFollower.disconnect() never ran and
its disable_torque never reached the servos. Torque lives in the servo's own
register and the servos keep their external supply, so it survives the board
re-enumerating: the arm can still be stiff and holding position.
"""

from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors import Motor, MotorNormMode

NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
motors = {n: Motor(i + 1, "sts3215", MotorNormMode.RANGE_M100_100) for i, n in enumerate(NAMES)}
bus = FeetechMotorsBus(port="/dev/ttyACM0", motors=motors)
bus.connect(handshake=False)

print("  joint            torque  load  volts")
for n in NAMES:
    vals = []
    for reg in ("Torque_Enable", "Present_Load", "Present_Voltage"):
        try:
            vals.append(bus.read(reg, n, normalize=False))
        except Exception:
            vals.append(None)
    t, l, v = vals
    lm = (l & 0x3FF) if isinstance(l, int) else "?"
    vs = "%.1f" % (v / 10.0) if isinstance(v, int) else "?"
    print("  %-14s %6s %5s %5sV" % (n, "ON" if t else "off", lm, vs))

bus.disable_torque()
print("\n  torque disabled on all six joints - arm is free to move by hand")
bus.disconnect()
