"""Fix the varied_corpus action-units bug, stats included.

THE BUG
-------
`single_arm_env_cfg.build_lerobot_frame()` writes:

    action            = raw   UNLESS dataset_cfg.action_align is set
    observation.state = convert_leisaac_action_to_lerobot(joint_pos)   ALWAYS

The corpus was generated with `action_align` unset, so state went through the
conversion and action did not: action is in RADIANS, state in motor units. The
eval client then applies its own motor->rad conversion to the policy's output,
shrinking it ~57x -> a frozen arm (4 mm of motion in 3,000 steps).

WHY OUT-OF-RANGE OUTPUT IS EXPECTED, NOT A BUG
----------------------------------------------
After conversion, elbow_flex and wrist_flex land outside the motor range. That
is faithful, not corruption:

  * the RAW action is already outside the USD joint limits before any
    conversion (-2.73 rad = -156 deg against an elbow limit of -100)
  * the MEASURED positions (recovered by inverting observation.state) are all
    in range - a position controller commanded past a stop clamps there
  * so the actions are TARGETS that exceed limits; the conversion carries that
    property across, it does not introduce it

The USD asset was checked directly (read_usd_joint_limits.py): all six joint
limits match leisaac's hardcoded table exactly, so the table is trustworthy.

DELIBERATELY NOT DONE: clamping the out-of-range targets. That would change the
data beyond a unit fix and is a modelling decision, not a bug fix. Make it
explicitly if you want it.

SAFETY: writes a NEW dataset directory; the original is never modified.
"""

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Transcribed VERBATIM from leisaac/assets/robots/lerobot.py:56-73 and verified
# against the USD asset itself. Copied rather than imported because that module
# pulls in isaaclab, which needs Isaac Sim running.
USD_JOINT_LIMITS = {
    "shoulder_pan": (-110.0, 110.0),
    "shoulder_lift": (-100.0, 100.0),
    "elbow_flex": (-100.0, 90.0),
    "wrist_flex": (-95.0, 95.0),
    "wrist_roll": (-160.0, 160.0),
    "gripper": (-10.0, 100.0),
}
MOTOR_LIMITS = {
    "shoulder_pan": (-100.0, 100.0),
    "shoulder_lift": (-100.0, 100.0),
    "elbow_flex": (-100.0, 100.0),
    "wrist_flex": (-100.0, 100.0),
    "wrist_roll": (-100.0, 100.0),
    "gripper": (0.0, 100.0),
}


def convert(action: np.ndarray) -> np.ndarray:
    """Port of leisaac convert_leisaac_action_to_lerobot: rad->deg, per-joint affine."""
    out = np.zeros_like(action)
    deg = action / np.pi * 180.0
    for i, joint in enumerate(USD_JOINT_LIMITS):
        j_lo, j_hi = USD_JOINT_LIMITS[joint]
        m_lo, m_hi = MOTOR_LIMITS[joint]
        out[:, i] = (deg[:, i] - j_lo) / (j_hi - j_lo) * (m_hi - m_lo) + m_lo
    return out


def stats_for(a: np.ndarray) -> dict:
    """Same statistic set LeRobot stores for a feature."""
    return {
        "min": a.min(0).tolist(),
        "max": a.max(0).tolist(),
        "mean": a.mean(0).tolist(),
        "std": a.std(0).tolist(),
        "count": [int(a.shape[0])],
        "q01": np.quantile(a, 0.01, axis=0).tolist(),
        "q10": np.quantile(a, 0.10, axis=0).tolist(),
        "q50": np.quantile(a, 0.50, axis=0).tolist(),
        "q90": np.quantile(a, 0.90, axis=0).tolist(),
        "q99": np.quantile(a, 0.99, axis=0).tolist(),
    }


SRC = Path("/home/kiran/.cache/huggingface/lerobot/local/varied_corpus")
DST = Path("/home/kiran/.cache/huggingface/lerobot/local/varied_corpus_fixed")

if DST.exists():
    sys.exit(f"refusing to overwrite {DST} - remove it first if you mean to redo this")

print(f"  copying {SRC.name} -> {DST.name} (original untouched)")
shutil.copytree(SRC, DST)

# ---- 1. the data ----
all_after = []
ep_slices = {}
for p in sorted(DST.glob("data/**/*.parquet")):
    df = pd.read_parquet(p)
    before = np.stack(df["action"].to_numpy())
    after = convert(before)
    df["action"] = list(after)
    df.to_parquet(p, index=False)
    all_after.append(after)
    for ep in df["episode_index"].unique():
        m = (df["episode_index"] == ep).to_numpy()
        ep_slices.setdefault(int(ep), []).append(after[m])
    print(f"  data: {p.name}  {len(df)} rows converted")

A = np.concatenate(all_after)

# ---- 2. global stats.json ----
sp = DST / "meta" / "stats.json"
st = json.loads(sp.read_text())
old_min = st["action"]["min"]
st["action"] = stats_for(A)
sp.write_text(json.dumps(st, indent=4))
print(f"\n  stats.json action.min  {np.round(old_min, 3).tolist()}")
print(f"                     ->  {np.round(st['action']['min'], 2).tolist()}")

# ---- 3. per-episode stats ----
for p in sorted(DST.glob("meta/episodes/**/*.parquet")):
    df = pd.read_parquet(p)
    for key, fn in (
        ("min", lambda a: a.min(0)),
        ("max", lambda a: a.max(0)),
        ("mean", lambda a: a.mean(0)),
        ("std", lambda a: a.std(0)),
        ("q01", lambda a: np.quantile(a, 0.01, 0)),
        ("q10", lambda a: np.quantile(a, 0.10, 0)),
        ("q50", lambda a: np.quantile(a, 0.50, 0)),
        ("q90", lambda a: np.quantile(a, 0.90, 0)),
        ("q99", lambda a: np.quantile(a, 0.99, 0)),
    ):
        col = f"stats/action/{key}"
        if col in df.columns:
            df[col] = [fn(np.concatenate(ep_slices[int(e)])).astype(np.float32) for e in df["episode_index"]]
    df.to_parquet(p, index=False)
    print(f"  per-episode stats: {p.name}  {len(df)} episodes updated")

print("\n  DONE. action now in motor units, stats regenerated at both levels.")
print("  Out-of-range targets on elbow_flex/wrist_flex are PRESERVED by design - see docstring.")
