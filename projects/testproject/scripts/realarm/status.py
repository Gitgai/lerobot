"""One-line-per-demo report: is it a real pick, and which band was it in?
Auto-detects real episodes rather than relying on a hand-maintained list."""
import glob, os
import cv2, numpy as np, pandas as pd

D = os.path.expanduser("~/plate_demos")
df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{D}/data/**/*.parquet", recursive=True))])
meta = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{D}/meta/episodes/**/*.parquet", recursive=True))])

def band(x):
    return "operator-RIGHT" if x < 183 else ("MIDDLE" if x <= 369 else "operator-LEFT")

counts, real = {}, []
last = None
for ep in sorted(df["episode_index"].unique()):
    e = df[df["episode_index"] == ep]
    st = np.stack(e["observation.state"].to_numpy()); ac = np.stack(e["action"].to_numpy())
    gap = st[1:,5] - ac[:-1,5]; shut = ac[:-1,5] < 30
    held = (gap > 2) & shut
    if held.sum() < 30:
        last = f"ep {int(ep)}: NO GRASP (gripper only reached {ac[:,5].min():.0f}, needs <30)"; continue
    first = int(np.where(held)[0][0])
    if first < 20:
        last = f"ep {int(ep)}: DISCARD - already holding at start"; continue
    r = meta[meta["episode_index"] == ep].iloc[0]
    fi = int(r["videos/observation.images.front/file_index"])
    cap = cv2.VideoCapture(f"{D}/videos/observation.images.front/chunk-000/file-{fi:03d}.mp4")
    ok, fr = cap.read(); cap.release()
    b = "?"
    if ok:
        hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
        m = cv2.inRange(hsv, (5,150,70), (22,255,255))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9,9), np.uint8))
        n, lab, stt, cent = cv2.connectedComponentsWithStats(m)
        if n > 1 and stt[1:, cv2.CC_STAT_AREA].max() >= 400:
            i = 1 + int(np.argmax(stt[1:, cv2.CC_STAT_AREA])); b = band(int(cent[i][0]))
    real.append(int(ep)); counts[b] = counts.get(b, 0) + 1
    last = f"ep {int(ep)}: GOOD - real pick, {int(held.sum())} frames held, {b}"
print(f"  {last}")
print(f"  total usable: {len(real)}")
for b, t in (("MIDDLE",8), ("operator-RIGHT",8), ("operator-LEFT",4)):
    print(f"    {b:15s} {counts.get(b,0)} of {t}")
