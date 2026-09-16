"""How far must the follower travel to reach the leader's pose, right now?

Read-only: torque is never enabled, nothing is commanded. Positions are
normalised through each arm's own calibration, which is the space the teleop
loop works in - comparing raw servo counts would be meaningless because the two
arms have different calibrated ranges (that is why the gripper looked 818 units
apart in the static check and it meant nothing).
"""

import json
import os

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.utils.constants import HF_LEROBOT_CALIBRATION, ROBOTS, TELEOPERATORS

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def load(kind, folder, dev_id, port):
    path = os.path.join(HF_LEROBOT_CALIBRATION, folder, kind, dev_id + ".json")
    with open(path) as fh:
        raw = json.load(fh)
    from lerobot.motors import MotorCalibration
    calib = {k: MotorCalibration(**v) for k, v in raw.items()}
    norm = MotorNormMode.DEGREES
    motors = {j: Motor(i + 1, "sts3215", norm) for i, j in enumerate(JOINTS)}
    bus = FeetechMotorsBus(port=port, motors=motors, calibration=calib)
    bus.connect(handshake=False)
    pos = {j: bus.read("Present_Position", j) for j in JOINTS}
    bus.disconnect()
    return pos


import subprocess
out = subprocess.run(["python3", os.path.expanduser("~/arm_ports.py")],
                     capture_output=True, text=True).stdout
ports = {}
for line in out.splitlines():
    if line.startswith("export "):
        k, _, v = line[len("export "):].partition("=")
        ports[k] = v.strip()

foll = load("so_follower", ROBOTS, "my_so101_follower", ports["FOLLOWER_PORT"])
lead = load("so_leader", TELEOPERATORS, "my_so101_leader", ports["LEADER_PORT"])

print("  joint            leader   follower   the follower must move")
worst = 0.0
for j in JOINTS:
    d = lead[j] - foll[j]
    worst = max(worst, abs(d))
    flag = "   <-- BIG" if abs(d) > 20 else ""
    print("  %-14s %7.1f %10.1f %12.1f deg%s" % (j, lead[j], foll[j], d, flag))
print("\n  largest gap: %.1f degrees" % worst)
print("  At teleop start the follower is commanded straight to the leader's pose,")
print("  so this whole gap is crossed in ONE step at full torque.")
