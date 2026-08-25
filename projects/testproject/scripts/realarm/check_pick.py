"""Is each episode a REAL pick, or did it start with the orange already held?

Matters because a crashed attempt can leave the orange in the gripper; the next
attempt would then show 'holding' from frame 0 without any pick being performed.
Such an episode teaches the policy nothing about grasping.
"""
import glob, os
import numpy as np, pandas as pd

D = os.path.expanduser("~/plate_demos")
df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{D}/data/**/*.parquet", recursive=True))])
print(f"  {'ep':>3} {'first hold':>11} {'held':>6} {'grip min':>9}   interpretation")
good = []
for ep in sorted(df["episode_index"].unique()):
    e = df[df["episode_index"] == ep]
    st = np.stack(e["observation.state"].to_numpy())
    ac = np.stack(e["action"].to_numpy())
    gap = st[1:, 5] - ac[:-1, 5]
    shut = ac[:-1, 5] < 30
    held = (gap > 2) & shut
    if held.sum() < 30:
        print(f"  {int(ep):>3} {'-':>11} {int(held.sum()):>6} {ac[:,5].min():>9.1f}   NO GRASP")
        continue
    first = int(np.where(held)[0][0])
    if first < 20:
        print(f"  {int(ep):>3} {first:>11} {int(held.sum()):>6} {ac[:,5].min():>9.1f}   ALREADY HOLDING - discard")
    else:
        print(f"  {int(ep):>3} {first:>11} {int(held.sum()):>6} {ac[:,5].min():>9.1f}   real pick")
        good.append(int(ep))
print(f"\n  REAL usable demos: {len(good)}  -> episodes {good}")
