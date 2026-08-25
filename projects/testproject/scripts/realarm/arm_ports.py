"""Resolve the SO-101 arms by SERIAL NUMBER, not by /dev/ttyACM* name.

Why: an EMI dropout on 2026-08-25 made both arms re-enumerate; the follower
came back as ttyACM2 instead of ttyACM0. A command hard-coded to ttyACM0 then
either fails, or - far worse - silently addresses the WRONG ARM. Serials are
burned into the controllers and never change.

Usage:  eval $(python arm_ports.py)   ->  exports FOLLOWER_PORT / LEADER_PORT
"""
import glob
import subprocess

FOLLOWER_SERIAL = "5B14114209"
LEADER_SERIAL = "5B14029688"


def serial_of(dev: str) -> str:
    out = subprocess.run(["udevadm", "info", "-q", "property", "-n", dev],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("ID_SERIAL_SHORT="):
            return line.split("=", 1)[1]
    return ""


ports = {serial_of(d): d for d in sorted(glob.glob("/dev/ttyACM*"))}
f = ports.get(FOLLOWER_SERIAL, "")
l = ports.get(LEADER_SERIAL, "")
print(f"export FOLLOWER_PORT={f}")
print(f"export LEADER_PORT={l}")
if not f:
    print("echo '  WARNING: follower not on the bus'")
if not l:
    print("echo '  WARNING: leader not on the bus'")
