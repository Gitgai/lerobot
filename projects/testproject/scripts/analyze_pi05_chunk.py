#!/usr/bin/env python3
"""Analyze a Pi05 dry-run action chunk and report whether it looks like a grasp.

Reads the CSV produced by `pi05_faithful_chunk_test.py --dry-run`:
  columns: phase, action_index, <motor>.pos ...
  phase "before"     -> robot state before any action (action_index = -1)
  phase "dry_chunk"  -> the full chunk of policy actions (action_index 0..N-1)

It prints, with no robot motion required:
  - per-joint trajectory summary (start -> first -> last, min/max, total range)
  - an ASCII sparkline of each joint across the chunk
  - a plain-language read on whether the chunk shows an approach + gripper-close
    signature, or is mostly reorientation.

This is evidence, not a verdict. It separates measured facts from interpretation.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

SO101_MOTORS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

# Joints that move the gripper through space (an "approach" uses these).
POSITION_JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex"]

SPARK = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float]) -> str:
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return SPARK[0] * len(values)
    out = []
    for v in values:
        idx = int((v - lo) / (hi - lo) * (len(SPARK) - 1))
        out.append(SPARK[idx])
    return "".join(out)


def load(path: Path) -> tuple[dict[str, float], dict[str, list[float]]]:
    before: dict[str, float] = {}
    chunk: dict[str, list[float]] = {m: [] for m in SO101_MOTORS}
    with path.open() as f:
        for row in csv.DictReader(f):
            if row["phase"] == "before":
                before = {m: float(row[f"{m}.pos"]) for m in SO101_MOTORS}
            elif row["phase"] in ("dry_chunk", "policy_action"):
                # "dry_chunk": full 50-action dry run. "policy_action": the raw policy
                # actions from an executed faithful test (lets us re-read old evidence).
                for m in SO101_MOTORS:
                    chunk[m].append(float(row[f"{m}.pos"]))
    return before, chunk


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action_log", type=Path, help="CSV from --dry-run")
    args = parser.parse_args()

    before, chunk = load(args.action_log)
    n = len(chunk[SO101_MOTORS[0]])
    if n == 0:
        raise SystemExit("No dry_chunk rows found in the CSV.")

    print(f"PI05 CHUNK ANALYSIS  ({n} actions)")
    print(f"source: {args.action_log}")
    print()

    # ---- Per-joint facts ----
    print(f"{'motor':<14}{'before':>9}{'first':>9}{'last':>9}{'min':>9}{'max':>9}{'range':>9}   trajectory")
    print("-" * 96)
    ranges: dict[str, float] = {}
    for m in SO101_MOTORS:
        vals = chunk[m]
        b = before.get(m, float("nan"))
        rng = max(vals) - min(vals)
        ranges[m] = rng
        print(
            f"{m:<14}{b:>9.2f}{vals[0]:>9.2f}{vals[-1]:>9.2f}"
            f"{min(vals):>9.2f}{max(vals):>9.2f}{rng:>9.2f}   {sparkline(vals)}"
        )
    print()

    # ---- Interpretation (facts -> read) ----
    approach_range = max(ranges[m] for m in POSITION_JOINTS)
    approach_total = sum(ranges[m] for m in POSITION_JOINTS)
    grip = chunk["gripper"]
    grip_net = grip[-1] - grip[0]
    grip_range = ranges["gripper"]
    # A grasp usually shows the gripper move one way (open/settle) then reverse (close).
    grip_min_i = grip.index(min(grip))
    grip_max_i = grip.index(max(grip))
    grip_reversal = abs(grip_max_i - grip_min_i) < n - 1 and grip_range > 2.0
    wrist_roll_range = ranges["wrist_roll"]

    print("READ (measured facts -> interpretation):")
    print(
        f"  position-joint motion across chunk: max {approach_range:.1f} deg, total {approach_total:.1f} deg"
    )
    print(
        f"  gripper: net {grip_net:+.1f} deg, range {grip_range:.1f} deg, min@{grip_min_i} max@{grip_max_i}"
    )
    print(f"  wrist_roll range: {wrist_roll_range:.1f} deg")
    print()

    signals = []
    if approach_range > 10.0:
        signals.append("position joints move meaningfully -> approach motion PRESENT")
    else:
        signals.append("position joints barely move -> approach motion WEAK/ABSENT")
    if grip_range > 2.0 and grip_reversal:
        signals.append("gripper moves then reverses -> possible OPEN-then-CLOSE (grasp) signature")
    elif grip_range > 2.0:
        signals.append("gripper moves but does not clearly reverse -> partial gripper action")
    else:
        signals.append("gripper barely moves -> NO grasp/close action in this chunk")
    if wrist_roll_range > 60.0:
        signals.append("large wrist_roll swing -> significant reorientation in this chunk")

    for s in signals:
        print(f"  - {s}")
    print()

    looks_like_grasp = approach_range > 10.0 and grip_range > 2.0 and grip_reversal
    if looks_like_grasp:
        print("SUMMARY: chunk CONTAINS an approach + gripper-close signature. Worth a closed-loop run.")
    elif approach_range > 10.0:
        print(
            "SUMMARY: chunk shows approach motion but no clear gripper close. Inconclusive -> closed-loop test."
        )
    else:
        print(
            "SUMMARY: chunk is mostly reorientation, little approach/close. Weak. Still confirm with closed-loop."
        )
    print()
    print("NOTE: one open-loop chunk is ~1.5-2 s. Pi05 is meant to run CLOSED-LOOP and correct")
    print("over many chunks, so this is a screen, not a verdict. Test 2 (closed-loop) is the verdict.")


if __name__ == "__main__":
    main()
