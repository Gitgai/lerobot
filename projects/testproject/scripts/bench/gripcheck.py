from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors import Motor, MotorNormMode

NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
motors = {n: Motor(i + 1, "sts3215", MotorNormMode.RANGE_M100_100) for i, n in enumerate(NAMES)}
bus = FeetechMotorsBus(port="/dev/ttyACM0", motors=motors)
bus.connect(handshake=False)
print("  joint            pos   load   volts   temp")
for n in NAMES:
    row = []
    for reg in ("Present_Position", "Present_Load", "Present_Voltage", "Present_Temperature"):
        try:
            row.append(bus.read(reg, n, normalize=False))
        except Exception:
            row.append(None)
    p, l, v, t = row
    vs = "%.1f" % (v / 10.0) if isinstance(v, int) else "?"
    # Present_Load: bit 10 is direction, lower 10 bits are magnitude (0-1000)
    lm = (l & 0x3FF) if isinstance(l, int) else None
    print("  %-14s %5s %6s %6sV %5s" % (n, p, lm, vs, t))
bus.disconnect()
