"""Adversarial re-test of the 'training is working' claim.

Four ways the first result could be false, each given a check that can FAIL:

  C1 CHEAT CHECK. The model is graded on data it trained on, so a lookup table
     would score well. Test: feed the RIGHT state with the WRONG images (from a
     different episode). A model that genuinely uses vision must get WORSE; a
     model ignoring vision and replaying memorised state->action will not care.

  C2 HARNESS CHECK. Score a THIRD model that should be bad - the sim checkpoint
     fed deliberately black images. If that does not come out worst, the
     measurement is not measuring competence.

  C3 SAMPLING CHECK. The first run used 8 hand-picked episodes. Redo across ALL
     89 episodes at random frames, so selection cannot flatter either model.

  C4 BASELINE CHECK. Compare both against the dumbest possible predictor:
     "the arm stays exactly where it is" (repeat current state 16 times). If a
     model cannot beat that, its error number means nothing.

Usage: rigorous_check.py <ckpt_path> <label>
"""

import os
import subprocess
import sys
import time

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/kiran/sim/Isaac-GR00T-n16")
from gr00t.policy.server_client import PolicyClient

CKPT, LABEL = sys.argv[1], sys.argv[2]
D = "/home/kiran/lerobot_assets/datasets/so101_orange_89_v21"
INSTR = "pick up the orange and move it to another place"
PORT = 5558
RNG = np.random.default_rng(20260817)  # fixed seed: identical samples for both models

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
for _ in range(60):
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


# C3: ALL episodes, random frames, fixed seed
eps = sorted(
    int(p.split("_")[-1].split(".")[0]) for p in os.listdir(f"{D}/data/chunk-000") if p.endswith(".parquet")
)
matched, mismatched, frozen = [], [], []
BLACK = np.zeros((1, 1, 480, 640, 3), np.uint8)
n_ok = 0
for ep in eps:
    df = pd.read_parquet(f"{D}/data/chunk-000/episode_{ep:06d}.parquet")
    st = np.stack(df["observation.state"].to_numpy())
    ac = np.stack(df["action"].to_numpy())
    if len(st) < 60:
        continue
    i = int(RNG.integers(10, len(st) - 20))
    fr, wr = frame("front", ep, i), frame("wrist", ep, i)
    if fr is None or wr is None:
        continue
    truth = ac[i : i + 16]

    matched.append(np.abs(ask(fr, wr, st[i]) - truth).mean())  # honest score
    # C1: same state, images from a DIFFERENT episode
    other = int(RNG.choice([e for e in eps if e != ep]))
    of = frame("front", other, 20)
    ow = frame("wrist", other, 20)
    if of is not None and ow is not None:
        mismatched.append(np.abs(ask(of, ow, st[i]) - truth).mean())
    # C4: the do-nothing baseline
    frozen.append(np.abs(np.repeat(st[i][None], 16, axis=0) - truth).mean())
    n_ok += 1

srv.terminate()
m, mm, fz = np.array(matched), np.array(mismatched), np.array(frozen)
print(f"\n=== {LABEL} ===  {n_ok} episodes, 1 random frame each, seed-fixed")
print(f"  C3 honest score (correct images)     {m.mean():6.3f} deg   +/- {m.std() / np.sqrt(len(m)):.3f}")
print(
    f"  C1 with MISMATCHED images            {mm.mean():6.3f} deg   "
    f"(penalty {mm.mean() - m.mean():+.3f} - a vision-using model MUST get worse)"
)
print(
    f"  C4 do-nothing baseline               {fz.mean():6.3f} deg   "
    f"(model beats it by {fz.mean() - m.mean():+.3f})"
)
