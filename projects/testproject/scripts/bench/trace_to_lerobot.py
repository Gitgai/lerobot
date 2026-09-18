"""Build a LeRobotDataset from a policy-eval trial (frames + run_trace.jsonl),
so the trial can be replayed in `lerobot-dataset-viz` (rerun) like any recording.

WHY: the GR00T eval client dumps per-chunk JPEGs + a JSON trace instead of a
LeRobotDataset (the policy runs through a separate server, off LeRobot's native
record path). The trace ALREADY carries the full 6-joint observation.state and
the executed action, so no re-recording is needed - just repackage.

Usage:  trace_to_lerobot.py <trial_frames_dir> <trace.jsonl> <out_root> <repo_id>
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from lerobot.datasets.lerobot_dataset import LeRobotDataset

JOINTS = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos",
          "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]
frames_dir, trace_path, out_root, repo_id = sys.argv[1:5]
frames_dir = Path(frames_dir)

rows = [json.loads(l) for l in open(trace_path) if l.strip()]
# effective cadence from the trace timestamps -> fps (rounded, >=1)
ts = np.array([r["t"] for r in rows])
dt = np.median(np.diff(ts)) if len(ts) > 1 else 0.5
fps = max(1, round(1.0 / dt))
print("  %d trace rows, median dt %.3f s -> fps %d" % (len(rows), dt, fps))

features = {
    "observation.state": {"dtype": "float32", "shape": [6], "names": JOINTS},
    "action":            {"dtype": "float32", "shape": [6], "names": JOINTS},
    "observation.images.front": {"dtype": "video", "shape": [480, 640, 3], "names": ["h", "w", "c"]},
    "observation.images.wrist": {"dtype": "video", "shape": [480, 640, 3], "names": ["h", "w", "c"]},
}
root = Path(out_root)
import shutil
if root.exists():
    shutil.rmtree(root)
ds = LeRobotDataset.create(repo_id=repo_id, fps=fps, features=features, root=root,
                           robot_type="so101_follower", use_videos=True)

TASK = "pick up the orange and place it on the plate"
kept = 0
for r in rows:
    c = r["chunk"]
    ff = frames_dir / ("c%04d_front.jpg" % c)
    wf = frames_dir / ("c%04d_wrist.jpg" % c)
    if not (ff.exists() and wf.exists()):
        continue
    front = cv2.cvtColor(cv2.imread(str(ff)), cv2.COLOR_BGR2RGB)
    wrist = cv2.cvtColor(cv2.imread(str(wf)), cv2.COLOR_BGR2RGB)
    if front is None or wrist is None:
        continue
    state = np.array([r["state"][j] for j in JOINTS], dtype=np.float32)
    act = r.get("action0") or r["state"]
    action = np.array([act[j] for j in JOINTS], dtype=np.float32)
    ds.add_frame({
        "observation.state": state,
        "action": action,
        "observation.images.front": front,
        "observation.images.wrist": wrist,
        "task": TASK,
    })
    kept += 1
ds.save_episode()
ds.finalize()
print("  wrote %d frames -> %s" % (kept, root))
print("  visualize:  lerobot-dataset-viz --repo-id %s --root %s --episode-index 0" % (repo_id, root))
