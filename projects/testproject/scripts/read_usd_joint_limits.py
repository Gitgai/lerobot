"""Read the SO-101 follower's ACTUAL joint limits out of the USD asset.

Why: leisaac's SO101_FOLLOWER_USD_JOINT_LIMLITS is a hardcoded transcription
(assets/robots/lerobot.py:56). Applying it to the varied_corpus action column
put elbow_flex and wrist_flex OUTSIDE the motor range, while the other four
joints landed cleanly. Either the corpus actions are not what we think, or the
table has drifted from the asset it claims to describe. This checks the asset.
"""
from pxr import Usd, UsdPhysics

USD_PATH = "/home/kiran/sim/leisaac-src/assets/robots/so101_follower.usd"

# leisaac/assets/robots/lerobot.py:56-63, verbatim
HARDCODED = {
    "shoulder_pan": (-110.0, 110.0),
    "shoulder_lift": (-100.0, 100.0),
    "elbow_flex": (-100.0, 90.0),
    "wrist_flex": (-95.0, 95.0),
    "wrist_roll": (-160.0, 160.0),
    "gripper": (-10.0, 100.0),
}

stage = Usd.Stage.Open(USD_PATH)
if stage is None:
    raise SystemExit(f"could not open {USD_PATH}")

found = {}
for prim in stage.Traverse():
    if not prim.IsA(UsdPhysics.RevoluteJoint) and not prim.IsA(UsdPhysics.PrismaticJoint):
        continue
    joint = UsdPhysics.RevoluteJoint(prim) if prim.IsA(UsdPhysics.RevoluteJoint) else UsdPhysics.PrismaticJoint(prim)
    lo = joint.GetLowerLimitAttr().Get()
    hi = joint.GetUpperLimitAttr().Get()
    found[prim.GetName()] = (lo, hi, prim.GetTypeName())

print(f"  joints found in the USD: {len(found)}\n")
print(f"  {'joint (USD prim)':<24}{'USD limit':<26}{'hardcoded table':<22}{'agree?'}")
for name, (lo, hi, typ) in sorted(found.items()):
    key = next((k for k in HARDCODED if k in name.lower()), None)
    hard = HARDCODED.get(key)
    if lo is None or hi is None:
        verdict = "no limit authored"
        usd = "(none)"
    else:
        usd = f"({lo:.1f}, {hi:.1f})"
        if hard is None:
            verdict = "not in table"
        else:
            verdict = "yes" if (abs(lo - hard[0]) < 1 and abs(hi - hard[1]) < 1) else "*** DIFFERS ***"
    print(f"  {name:<24}{usd:<26}{str(hard) if hard else '-':<22}{verdict}")
