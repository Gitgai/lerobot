import sys
from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors import Motor, MotorNormMode

NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
for port in sys.argv[1:]:
    motors = {n: Motor(i + 1, "sts3215", MotorNormMode.RANGE_M100_100)
              for i, n in enumerate(NAMES)}
    bus = FeetechMotorsBus(port=port, motors=motors)
    try:
        bus.connect(handshake=False)
        found = [i for i in range(1, 8) if bus.ping(i) is not None]
        print("  %s: motors responding %s" % (port, found if found else "NONE"))
        bus.disconnect()
    except Exception as e:
        print("  %s: ERROR %s: %s" % (port, type(e).__name__, str(e)[:90]))
