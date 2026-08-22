"""Score a checkpoint on the 10 HELD-OUT episodes it never trained on.

This is the screening step before spending real-arm time. Unlike the earlier
40%-checkpoint probe, these episodes were excluded from training, so a good
score here means generalisation rather than memorisation.

Three numbers, because one is not enough to trust:

  HONEST      correct images, correct state -> what the model actually does.
  MISMATCHED  correct state, images from a DIFFERENT episode. A model that
              uses its eyes MUST get worse. If this is ~0, the model is blind
              and the honest score is just state-replay.
  DO-NOTHING  the dumbest predictor: "hold the current pose for 16 steps".
              A model that cannot beat this has learned nothing useful.

Each variant is scored on ITS OWN camera build of the same episodes, because
that is what it will see when served.

Usage: probe_holdout.py <ckpt> <label> <side|top>
"""

import json
import os
import subprocess
import sys
import time

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/kiran/sim/Isaac-GR00T-n16")
from gr00t.policy.server_client import PolicyClient

CKPT, LABEL, VARIANT = sys.argv[1], sys.argv[2], sys.argv[3]
ROOT = "/home/kiran/lerobot_assets/datasets"
D = f"{ROOT}/so101_orange_89_v21" + ("_topfront" if VARIANT == "top" else "")
INSTR = "pick up the orange and move it to another place"
PORT = 5559
RNG = np.random.default_rng(20260818)  # fixed: both variants see identical frames

HOLDOUT = json.load(open(f"{ROOT}/holdout_episodes.json"))["holdout"]

srv = subprocess.Popen(
    [
        "/home/kiran/sim/Isaac-GR00T-n16/.venv/bin/python",
        "-u",
        "-m",
        "gr00t.eval.run_gr00t_server",
        "--model_path",
        CKPT,
        "--embodiment-tag",
        "NEW_EMBODIMENT",
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    env={**os.environ, "HF_HUB_OFFLINE": "1"},
)
for _ in range(72):
    if f":{PORT}" in subprocess.run(["ss", "-tln"], capture_output=True, text=True).stdout:
        break
    time.sleep(5)
time.sleep(5)
client = PolicyClient(host="127.0.0.1", port=PORT)


def frame(cam, ep, idx):
    cap = cv2.VideoCapture(f"{D}/videos/chunk-000/observation.images.{cam}/episode_{ep:06d}.mp4")
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, f = cap.read()
    cap.release()
    return cv2.cvtColor(cv2.resize(f, (640, 480)), cv2.COLOR_BGR2RGB)[None, None] if ok else None


def ask(fr, wr, state):
    s = np.asarray(state, dtype=np.float32)
    ch, _ = client.get_action(
        {
            "video": {"front": fr, "wrist": wr},
            "state": {"single_arm": s[:5][None, None], "gripper": s[5:6][None, None]},
            "language": {"annotation.human.task_description": [[INSTR]]},
        }
    )
    return np.concatenate([ch["single_arm"][0], ch["gripper"][0]], axis=1)


honest, mismatched, nothing = [], [], []
for ep in HOLDOUT:
    df = pd.read_parquet(f"{D}/data/chunk-000/episode_{ep:06d}.parquet")
    st = np.stack(df["observation.state"].to_numpy())
    ac = np.stack(df["action"].to_numpy())
    if len(st) < 60:
        continue
    for i in np.linspace(10, len(st) - 20, 6, dtype=int):  # 6 points spread through each episode
        i = int(i)
        fr, wr = frame("front", ep, i), frame("wrist", ep, i)
        if fr is None or wr is None:
            continue
        truth = ac[i : i + 16]
        honest.append(np.abs(ask(fr, wr, st[i]) - truth).mean())
        other = int(RNG.choice([e for e in HOLDOUT if e != ep]))
        of, ow = frame("front", other, 20), frame("wrist", other, 20)
        if of is not None and ow is not None:
            mismatched.append(np.abs(ask(of, ow, st[i]) - truth).mean())
        nothing.append(np.abs(np.repeat(st[i][None], 16, axis=0) - truth).mean())

srv.terminate()
h, m, n = np.array(honest), np.array(mismatched), np.array(nothing)
print(f"\n=== {LABEL} ===  {len(h)} samples from {len(HOLDOUT)} HELD-OUT episodes")
print(f"  HONEST      {h.mean():6.3f} deg  +/- {h.std() / np.sqrt(len(h)):.3f}")
print(f"  MISMATCHED  {m.mean():6.3f} deg   penalty {m.mean() - h.mean():+.3f}  (must be clearly positive)")
print(f"  DO-NOTHING  {n.mean():6.3f} deg   model beats it by {n.mean() - h.mean():+.3f}")
json.dump(
    {
        "label": LABEL,
        "variant": VARIANT,
        "n": len(h),
        "honest": float(h.mean()),
        "mismatched": float(m.mean()),
        "nothing": float(n.mean()),
    },
    open(f"/home/kiran/lerobot_assets/probes/holdout_{VARIANT}.json", "w"),
    indent=2,
)
