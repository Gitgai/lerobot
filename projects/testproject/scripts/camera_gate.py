#!/usr/bin/env python3
"""Camera gate: capture one good frame from all three cameras and report health.

Run this before EVERY session. Three cameras or the run does not count.

WARMUP MATTERS (2026-08-05 lesson)
----------------------------------
The C270 top camera returns pure BLACK frames for the first ~1 second and only
stabilizes around 2 s. A gate that grabs the first successful read will declare
a perfectly healthy camera dead - that happened, and cost a diagnosis detour.
This script discards frames for `warmup_s` and reports mean brightness so a
genuinely dark frame is distinguishable from a not-yet-awake one.

Brightness guide (mean pixel value, 0-255):
    < 5      black - lens covered, or still warming up
    5 - 20   very dark - check lighting or aim
    > 20     normal

It also writes the frames so you can LOOK at them. A camera can be perfectly
healthy and still be aimed at the ceiling - only your eyes catch that.
"""

import argparse
import json
import time
from pathlib import Path

import cv2
import requests

PROJECT = Path(__file__).resolve().parents[1]


def grab_usb(device: str, warmup_s: float, width: int, height: int):
    """Open a V4L2 camera, discard frames for warmup_s, return the last one."""
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        return None, "could not open device"
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    deadline = time.time() + warmup_s
    frame = None
    reads = 0
    while time.time() < deadline:
        ok, f = cap.read()
        if ok:
            frame = f
            reads += 1
        time.sleep(0.02)
    cap.release()
    if frame is None:
        return None, f"no frames in {warmup_s}s"
    return frame, f"{reads} frames during warmup"


def grab_http(url: str, timeout_s: float):
    """Fetch one JPEG from the wrist proxy."""
    try:
        r = requests.get(url, timeout=timeout_s)
        r.raise_for_status()
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    import numpy as np

    arr = np.frombuffer(r.content, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return None, "response was not a decodable image"
    return frame, f"{len(r.content)} bytes"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=PROJECT / "artifacts" / "camera_gate")
    ap.add_argument("--warmup", type=float, default=3.0, help="seconds to discard per USB camera")
    args = ap.parse_args()

    cfg = json.loads((PROJECT / "config" / "so101.json").read_text())
    width = int(cfg.get("camera_width", 640))
    height = int(cfg.get("camera_height", 480))
    args.out.mkdir(parents=True, exist_ok=True)

    results = []

    for name, key in (("front", "front_camera_index"), ("top", "top_camera_index")):
        frame, note = grab_usb(cfg[key], args.warmup, width, height)
        results.append((name, frame, note))

    frame, note = grab_http(cfg.get("wrist_camera_url", "http://127.0.0.1:8092/frame"), 8.0)
    results.append(("wrist", frame, note))

    print(f"{'camera':8s} {'status':10s} {'size':11s} {'brightness':>10s}  note")
    all_ok = True
    for name, frame, note in results:
        if frame is None:
            print(f"{name:8s} {'DEAD':10s} {'-':11s} {'-':>10s}  {note}")
            all_ok = False
            continue
        bright = float(frame.mean())
        size = f"{frame.shape[1]}x{frame.shape[0]}"
        if bright < 5:
            status, ok = "BLACK", False
        elif bright < 20:
            status, ok = "very dark", True
        else:
            status, ok = "ok", True
        all_ok = all_ok and ok
        path = args.out / f"{name}.jpg"
        cv2.imwrite(str(path), frame)
        print(f"{name:8s} {status:10s} {size:11s} {bright:10.1f}  {note}")

    print(f"\nframes written to {args.out}")
    print("NOW LOOK AT THEM: front must face the robot, top must see the table")
    print("and the plate, wrist must see the gripper. A healthy camera pointed")
    print("at the ceiling passes every automated check and ruins the run.")
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
