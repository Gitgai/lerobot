"""60-second teleoperation test: does the follower actually track the leader?

The static comparison in sync_check.py can only say the two arms AGREE about
angles while both are still. It cannot tell "correctly calibrated" apart from
"happens to be in a similar pose". Only driving the leader and watching the
follower answers that, so this moves the arm - deliberately, and bounded.

Configured EXACTLY as rec_esp.sh configures recording - in particular
max_relative_target is left at its default of None (uncapped), as lerobot's own
teleoperate and record scripts leave it. Setting a cap would have measured the
cap rather than the arms: it rate-limits the follower, and it forces an extra
Present_Position read per cycle ("slower fps expected", so_follower.py), so both
the tracking error and the lag would have been inflated by the instrument.

The real safeguard is the documented one: start with the two arms in a similar
pose. Torque is disabled on disconnect.
"""

import os
import time

import numpy as np

from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig
from lerobot.teleoperators.so_leader import SOLeader, SOLeaderTeleopConfig

def resolve_ports():
    """Ask arm_ports.py, the same resolver rec_esp.sh uses."""
    import subprocess
    out = subprocess.run(["python3", os.path.expanduser("~/arm_ports.py")],
                         capture_output=True, text=True).stdout
    got = {}
    for line in out.splitlines():
        if line.startswith("export "):
            k, _, v = line[len("export "):].partition("=")
            got[k] = v.strip()
    f, l = got.get("FOLLOWER_PORT"), got.get("LEADER_PORT")
    if not f or not l:
        raise SystemExit("  arm ports did not resolve - is an arm off the bus?\n" + out)
    return f, l


DURATION = 60.0
HZ = 30.0
JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

# Resolve ports the way rec_esp.sh does - by serial, never by number. The arms
# have renumbered three times today, and the follower has just moved to another
# physical port, so a hardcoded /dev/ttyACM0 would silently address the leader.
FOLLOWER_PORT, LEADER_PORT = resolve_ports()
print("  follower %s   leader %s" % (FOLLOWER_PORT, LEADER_PORT), flush=True)

robot = SOFollower(SOFollowerRobotConfig(port=FOLLOWER_PORT, id="my_so101_follower"))
teleop = SOLeader(SOLeaderTeleopConfig(port=LEADER_PORT, id="my_so101_leader"))

robot.connect()
teleop.connect()
print("  connected. MOVE THE LEADER ARM NOW - 60 seconds.", flush=True)

lead, foll, stamps = [], [], []
t0 = time.perf_counter()
next_beat = 0
try:
    while True:
        t = time.perf_counter() - t0
        if t >= DURATION:
            break
        cycle = time.perf_counter()

        obs = robot.get_observation()
        action = teleop.get_action()
        robot.send_action(action)

        lead.append([action[f"{j}.pos"] for j in JOINTS])
        foll.append([obs[f"{j}.pos"] for j in JOINTS])
        stamps.append(t)

        if int(t) // 10 > next_beat:
            next_beat = int(t) // 10
            print("  %ds..." % (next_beat * 10), flush=True)

        sleep = 1.0 / HZ - (time.perf_counter() - cycle)
        if sleep > 0:
            time.sleep(sleep)
except KeyboardInterrupt:
    print("  interrupted by operator", flush=True)
except Exception as exc:
    # A USB dropout raises here and, worse, makes the tidy disconnect below fail
    # too - which is how the follower was left holding torque last time. Report
    # it in one line rather than a wall of traceback, and still try to release.
    print("  ABORTED after %.1fs: %s: %s" % (time.perf_counter() - t0,
                                             type(exc).__name__, str(exc)[:80]), flush=True)
finally:
    for name, dev in (("follower", robot), ("leader", teleop)):
        try:
            dev.disconnect()
            print("  %s disconnected, torque off" % name, flush=True)
        except Exception as exc:
            print("  %s would NOT release: %s - retrying on a fresh handle"
                  % (name, type(exc).__name__), flush=True)
            try:
                from lerobot.motors.feetech import FeetechMotorsBus
                from lerobot.motors import Motor, MotorNormMode
                port = "/dev/ttyACM0" if name == "follower" else "/dev/ttyACM1"
                ms = {j: Motor(i + 1, "sts3215", MotorNormMode.RANGE_M100_100)
                      for i, j in enumerate(JOINTS)}
                b = FeetechMotorsBus(port=port, motors=ms)
                b.connect(handshake=False)
                b.disable_torque()
                b.disconnect()
                print("  %s torque released on the second attempt" % name, flush=True)
            except Exception as exc2:
                print("  %s STILL HOLDING TORQUE - power it down by hand (%s)"
                      % (name.upper(), type(exc2).__name__), flush=True)

if len(lead) < 30:
    print("\n  only %d cycles captured - too few to judge tracking." % len(lead))
    raise SystemExit(1)

L = np.array(lead)
F = np.array(foll)
print("\n  %d cycles in %.1fs (%.1f Hz)" % (len(L), stamps[-1], len(L) / stamps[-1]))
print("\n  joint            leader moved    tracking error      worst")
for i, j in enumerate(JOINTS):
    travel = L[:, i].max() - L[:, i].min()
    err = np.abs(L[:, i] - F[:, i])
    print("  %-14s %8.1f deg %12.1f deg %10.1f deg" % (j, travel, err.mean(), err.max()))

# lag: shift the follower back until it best matches the leader
big = max(range(6), key=lambda i: L[:, i].max() - L[:, i].min())
best, lag = -2, 0
for s in range(0, 16):
    a = L[:len(L) - s, big]
    b = F[s:, big]
    if a.std() < 1e-6 or b.std() < 1e-6:
        continue
    c = np.corrcoef(a, b)[0, 1]
    if c > best:
        best, lag = c, s
print("\n  most-moved joint: %s (%.0f deg of travel)" % (JOINTS[big], L[:, big].max() - L[:, big].min()))
print("  follower lags leader by %d cycles (%.0f ms), match %.3f" % (lag, lag * 1000.0 / HZ, best))
