import numpy as np
import pandas as pd

df = pd.read_parquet("/home/gaikwad-prakash/esp_orange/data/chunk-000/file-000.parquet")
st = np.stack(df["observation.state"].values)
grip, lift = st[:, 5], st[:, 1]
print("  %d rows.  gripper %.1f..%.1f   shoulder_lift %.1f..%.1f"
      % (len(df), grip.min(), grip.max(), lift.min(), lift.max()))

rng = grip.max() - grip.min()
ci = np.where(grip < grip.min() + 0.25 * rng)[0]
runs = [r for r in np.split(ci, np.where(np.diff(ci) != 1)[0] + 1) if len(r) >= 15] if len(ci) else []
if not runs:
    print("  no sustained closure (>=15 frames) found")
else:
    g0, g1 = int(runs[0][0]), int(runs[0][-1])
    print("  first sustained closure: frames %d-%d  (%.1fs held)" % (g0, g1, (g1 - g0) / 30.0))
    print("  shoulder_lift at closure: %.1f   (Aug-20 successes closed at -28)" % lift[g0])
    print("  APPROACH WINDOW = frames %d-%d" % (max(0, g0 - 60), g0))
    print("WINDOW %d %d %d" % (max(0, g0 - 60), g0, g1))
