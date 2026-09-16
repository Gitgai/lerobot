#!/usr/bin/env python3
"""Find the robot's cameras by NAME, not by device number.

The indices move on every reboot or replug - the OV4689 has been /dev/video4
and /dev/video6 on consecutive days, and the C270 took the number it vacated.
A script that hard-codes numbers will silently feed the front view into the
wrist slot, which would poison a whole recording session.

Prints shell assignments:
    WRIST_CAM=/dev/videoN
    FRONT_CAM=/dev/videoN
"""
import glob
import re
import subprocess
import sys

WANT = {"wrist": "AK-Camera", "front": "C270"}


def card_name(dev):
    try:
        out = subprocess.run(["v4l2-ctl", "-d", dev, "--info"],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return None
    m = re.search(r"Card type\s*:\s*(.+)", out)
    return m.group(1).strip() if m else None


def can_capture(dev):
    try:
        out = subprocess.run(["v4l2-ctl", "-d", dev, "--list-formats"],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return False
    return "MJPG" in out


found = {}
for dev in sorted(glob.glob("/dev/video*")):
    name = card_name(dev)
    if not name or not can_capture(dev):
        continue
    for role, needle in WANT.items():
        if role not in found and needle.lower() in name.lower():
            found[role] = (dev, name)

missing = [r for r in WANT if r not in found]
for role, (dev, name) in found.items():
    print(f"{role.upper()}_CAM={dev}")
    print(f"# {role}: {name}", file=sys.stderr)
if missing:
    for r in missing:
        print(f"# MISSING {r} camera (looking for '{WANT[r]}')", file=sys.stderr)
    sys.exit(1)
