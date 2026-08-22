#!/usr/bin/env python3
"""Score a Phase-0 reliability sweep: turn N runs into a SUCCESS RATE.

Reports, per run and in aggregate:
    placed      how many of the three oranges reached the plate (the task)
    lift        per-orange peak height gain - THE metric that separates a real
                grasp from closing on air. Real grasp ~0.16-0.20 m; a false
                "grasp" (proximity + gripper closed, no contact) ~0.003 m.
    placeSteps  total steps any put_*_to_plate term was True
    firstPlace  step index of the first successful place (pace of the policy)

Why lift and not the predicate: mdp.orange_grasped is
    distance(object, ee_frame[1]) < 0.05  AND  gripper_joint < 0.60
which is proximity AND closure - no contact, no force, no lift. A policy that
parks beside the orange and closes on air scores True indefinitely. Object
displacement is what makes the predicate evidence.

Usage:  python3 scripts/phase0_score_sweep.py [logs/phase0]
"""

import csv
import statistics
import sys
from pathlib import Path

ORANGES = (1, 2, 3)


def score(path: Path) -> dict | None:
    rows = list(csv.DictReader(open(path)))
    if not rows:
        return None
    out = {"name": path.stem, "steps": len(rows), "lifts": [], "placed": 0, "place_steps": 0}
    first = None
    for n in ORANGES:
        z = [float(r[f"o{n}_z"]) for r in rows]
        out["lifts"].append(max(z) - z[0])
        key = f"put_orange00{n}_to_plate"
        hits = [i for i, r in enumerate(rows) if r.get(key) == "1"]
        if hits:
            out["placed"] += 1
            out["place_steps"] += len(hits)
            first = hits[0] if first is None else min(first, hits[0])
    out["first_place"] = first
    d = [float(r["d_min"]) for r in rows]
    out["closest"] = min(d)
    return out


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "logs/phase0")
    runs = [s for s in (score(p) for p in sorted(root.glob("*.csv"))) if s]
    if not runs:
        print(f"no runs found in {root}")
        return

    print(f"{'run':22s} {'steps':>6s} {'placed':>7s} {'lifts (m)':>26s} {'placeSteps':>11s} {'1stPlace':>9s}")
    for r in runs:
        lifts = "[" + ", ".join(f"{v:.3f}" for v in r["lifts"]) + "]"
        fp = str(r["first_place"]) if r["first_place"] is not None else "-"
        print(
            f"{r['name']:22s} {r['steps']:>6d} {r['placed']:>5d}/3 {lifts:>26s} {r['place_steps']:>11d} {fp:>9s}"
        )

    placed = [r["placed"] for r in runs]
    full = sum(1 for p in placed if p == 3)
    any_place = sum(1 for p in placed if p > 0)
    total = len(runs)
    # A lift over 0.10 m cannot be produced by closing on air; it is a real grasp.
    real_grasps = sum(1 for r in runs for v in r["lifts"] if v > 0.10)

    print(f"\n{'=' * 78}")
    print(f"RUNS: {total}")
    print(f"  full task (3/3 placed) : {full}/{total}  = {100 * full / total:.0f}%")
    print(f"  placed at least one    : {any_place}/{total}  = {100 * any_place / total:.0f}%")
    print(f"  oranges placed         : {sum(placed)}/{3 * total} = {100 * sum(placed) / (3 * total):.0f}%")
    print(f"  real grasps (lift>0.10): {real_grasps}/{3 * total}")
    if total > 1:
        print(
            f"  placed per run         : mean {statistics.mean(placed):.2f}, stdev {statistics.stdev(placed):.2f}"
        )
    firsts = [r["first_place"] for r in runs if r["first_place"] is not None]
    if firsts:
        print(f"  first place at step    : min {min(firsts)}, max {max(firsts)}")
        print(f"  -> a run shorter than ~{max(firsts)} steps would have MISSED a success")


if __name__ == "__main__":
    main()
