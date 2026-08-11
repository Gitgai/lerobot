"""S4: variance-of-Laplacian sharpness over the evidence frames a run already wrote.

The client writes c%04d_{front,wrist}.jpg per chunk. Nothing has ever looked at
them for image QUALITY - only geometry was ever compared against sim. Sim renders
a pinhole camera: perfectly sharp, fixed focus, fixed exposure. A Pi camera on a
moving arm is the opposite, and the client grabs its observation immediately
after the 8-step motion burst - peak motion blur, peak autofocus hunt.

Low or wildly varying variance-of-Laplacian across a run means the policy was
fed blurred or focus-hunting frames. Free: runs on files already on disk.

    python frame_sharpness.py <dir-of-evidence-jpgs>
"""
import sys
from pathlib import Path

import cv2
import numpy as np

d = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
frames = sorted(d.glob("c*_*.jpg"))
if not frames:
    sys.exit(f"no c*_*.jpg evidence frames under {d}")

by_cam: dict[str, list] = {}
for f in frames:
    cam = f.stem.split("_", 1)[1]
    img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue
    by_cam.setdefault(cam, []).append(
        (f.name, cv2.Laplacian(img, cv2.CV_64F).var(), float(img.mean()))
    )

print(f"  {len(frames)} frames, {len(by_cam)} cameras\n")
print(f"  {'camera':<10}{'n':>5}{'sharp med':>12}{'sharp min':>12}{'blurred':>10}{'bright med':>12}")
for cam, rows in sorted(by_cam.items()):
    s = np.array([r[1] for r in rows])
    b = np.array([r[2] for r in rows])
    # <100 is the conventional blur threshold for 640x480 8-bit
    print(f"  {cam:<10}{len(rows):>5}{np.median(s):>12.1f}{s.min():>12.1f}"
          f"{100 * (s < 100).mean():>9.0f}%{np.median(b):>12.1f}")

print("\n  blurred% = frames under the conventional var-of-Laplacian < 100 threshold.")
print("  A high figure, or sharpness swinging run-to-run, means autofocus was live.")
print("  bright med near 0 means the sensor returned black - check it separately.")
for cam, rows in sorted(by_cam.items()):
    worst = sorted(rows, key=lambda r: r[1])[:3]
    print(f"\n  {cam} blurriest: " + ", ".join(f"{n} ({v:.0f})" for n, v, _ in worst))
