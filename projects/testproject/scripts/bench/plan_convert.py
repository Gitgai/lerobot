"""Plan the v3.0 -> v2.1 conversion with trimming. WRITES NOTHING.

Prints, per episode: its frame range in the packed source videos, whether it
ends at the rest posture, where it would be cut, and which source video file(s)
hold its frames - because an episode that straddles a file boundary needs
different handling and must not be discovered halfway through a write.
"""

import glob
import json
import os

import av
import numpy as np
import pandas as pd

SRC = "/data/lerobot_datasets"
REST_J = [1, 2, 3]          # shoulder_lift, elbow_flex, wrist_flex
# "Ends at rest" means two things, and the SECOND is the one that matters:
#   HOME_TOL - the arm is roughly at its home posture (loose: catches an episode
#              that ended mid-air, e.g. still holding the fruit at lift +31)
#   STILL    - the arm is genuinely motionless over the last second
# A 2.0 deg tolerance alone was too tight: 10eps_final ep4 sat frozen for its
# last 10 seconds with the wrist 2.27 deg from where other episodes left it, and
# was refused despite being a perfectly good ending. Parked is the criterion;
# home position is only the sanity check.
HOME_TOL = 5.0
STILL_DEG = 0.2             # max joint movement over the final second
SAFETY_S = 3.0
FPS = 30.0

SETS = [
    ("so101_pick_test_c270_wrist_10eps_final",    True,  "pick up the orange and place it on the plate"),
    ("so101_pick_test_c270_wrist_10eps_adjusted", True,  "pick up the orange and place it on the plate"),
    ("so101_pick_test_c270_wrist_tomato_10eps",   False, "pick up the tomato and place it on the plate"),
]
CAMS = ["front", "wrist"]


def video_files(d, cam):
    """Source video files in order, with the global frame range each covers."""
    vs = sorted(glob.glob("%s/%s/videos/observation.images.%s/**/*.mp4" % (SRC, d, cam), recursive=True))
    out, n = [], 0
    for v in vs:
        with av.open(v) as c:
            k = c.streams.video[0].frames or sum(1 for _ in c.decode(c.streams.video[0]))
        out.append((v, n, n + k - 1))
        n += k
    return out


def rest_cut(st):
    """Frame to cut at, or None if the episode does not end parked at home."""
    canon = np.array(CANON)
    if np.any(np.abs(st[-1, REST_J] - canon) > HOME_TOL):
        return None                                    # ended somewhere else
    if len(st) > 30 and np.abs(np.diff(st[-30:], axis=0)).max() > STILL_DEG:
        return None                                    # still moving at the end
    at = np.all(np.abs(st[:, REST_J] - canon) <= HOME_TOL, axis=1)
    i = len(st) - 1
    while i > 0 and at[i - 1]:
        i -= 1
    return min(len(st), i + int(SAFETY_S * FPS))


# canonical rest pose from every episode's final frame
finals = []
for d, _, _ in SETS:
    ps = sorted(glob.glob("%s/%s/data/**/*.parquet" % (SRC, d), recursive=True))
    df = pd.concat([pd.read_parquet(p) for p in ps])
    col = "observation.state" if "observation.state" in df.columns else "action"
    finals += [np.stack(g[col].values)[-1] for _, g in df.groupby("episode_index")]
CANON = np.median(np.array(finals), axis=0)[REST_J]
print("  canonical rest pose (lift, elbow, wrist_flex): %s\n  home tol +/-%.1f deg, must be still to within %.1f deg over the last second\n"
      % (np.round(CANON, 1), HOME_TOL, STILL_DEG))

plan = {}
for d, do_trim, task in SETS:
    ps = sorted(glob.glob("%s/%s/data/**/*.parquet" % (SRC, d), recursive=True))
    df = pd.concat([pd.read_parquet(p) for p in ps]).reset_index(drop=True)
    col = "observation.state" if "observation.state" in df.columns else "action"
    vf = {c: video_files(d, c) for c in CAMS}
    print("  === %s ===" % d.replace("so101_pick_test_c270_wrist_", ""))
    print("     trim: %s   task: %r" % ("YES" if do_trim else "no (kept whole)", task))
    for c in CAMS:
        print("     %-5s source videos: %s" % (c, ", ".join("%s[%d..%d]" % (os.path.basename(v), a, b) for v, a, b in vf[c])))
    print("     ep  rows   global range      ends at rest   keep   cut   spans files?")
    eps = []
    for ep, g in df.groupby("episode_index"):
        st = np.stack(g[col].values)
        a, b = int(g.index[0]), int(g.index[-1])
        cut = rest_cut(st) if do_trim else len(st)
        rest_ok = rest_cut(st) is not None
        if cut is None:
            cut = len(st)                     # refuse: keep whole
        span = any(sum(1 for v, x, y in vf[c] if not (b < x or a > y)) > 1 for c in CAMS)
        eps.append({"ep": int(ep), "a": a, "b": b, "rows": len(st), "keep": int(cut),
                    "rest_ok": bool(rest_ok), "span": bool(span)})
        print("     %2d %5d  %6d..%-6d  %-12s %5d %5d   %s"
              % (ep, len(st), a, b, "yes" if rest_ok else "NO -> REFUSE",
                 cut, len(st) - cut, "YES" if span else "no"))
    plan[d] = {"trim": do_trim, "task": task, "eps": eps}
    print("     total rows %d -> %d\n" % (sum(e["rows"] for e in eps), sum(e["keep"] for e in eps)))

json.dump({"canon": CANON.tolist(), "sets": plan}, open("/tmp/convert_plan.json", "w"), indent=1)
tb = sum(e["rows"] for s in plan.values() for e in s["eps"])
ta = sum(e["keep"] for s in plan.values() for e in s["eps"])
refuse = sum(1 for s in plan.values() for e in s["eps"] if not e["rest_ok"])
spans  = sum(1 for s in plan.values() for e in s["eps"] if e["span"])
print("  PLAN: %d -> %d frames (%.0f%% removed).  refused: %d.  episodes spanning 2 video files: %d"
      % (tb, ta, 100.0*(tb-ta)/tb, refuse, spans))
