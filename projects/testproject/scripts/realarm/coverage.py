"""Where was the orange actually placed in each recorded demo?

The runbook requires the agent to MEASURE this rather than trust the label -
the Phase 0 session had region labels drift silently mid-session.
Bands (front-camera x): operator-RIGHT 60-183 | MIDDLE 183-369 | operator-LEFT 369-500
"""
import glob, os
import cv2, numpy as np, pandas as pd

D = os.path.expanduser("~/plate_demos")
meta = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{D}/meta/episodes/**/*.parquet", recursive=True))])
REAL = [0, 2, 4, 5, 7, 8, 9, 10, 11]   # episodes that are genuine picks

def band(x):
    if x < 183: return "operator-RIGHT"
    if x <= 369: return "MIDDLE"
    return "operator-LEFT"

counts = {}
print(f"  {'ep':>3}{'orange x':>10}   band")
for _, r in meta.iterrows():
    ep = int(r["episode_index"])
    if ep not in REAL: continue
    fi = int(r["videos/observation.images.front/file_index"])
    v = f"{D}/videos/observation.images.front/chunk-000/file-{fi:03d}.mp4"
    cap = cv2.VideoCapture(v); ok, fr = cap.read(); cap.release()
    if not ok: print(f"  {ep:>3}   unreadable"); continue
    hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (5,150,70), (22,255,255))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9,9), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m)
    if n < 2 or stats[1:, cv2.CC_STAT_AREA].max() < 400:
        print(f"  {ep:>3}   no orange found"); continue
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x = int(cent[i][0]); b = band(x)
    counts[b] = counts.get(b, 0) + 1
    print(f"  {ep:>3}{x:>10}   {b}")
print("\n  COVERAGE so far:")
for b, target in (("MIDDLE", 8), ("operator-RIGHT", 8), ("operator-LEFT", 4)):
    print(f"    {b:15s} {counts.get(b,0)} of {target}")
