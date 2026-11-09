#!/usr/bin/env python3
"""Replay a bench trace through the read-only shadow grasp verifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "results/so101_bench_20261019"))

from shadow_grasp_verifier import ShadowGraspVerifier  # noqa: E402


def rgb(path: Path):
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(path)
    return image[:, :, ::-1].copy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trace = args.trace.expanduser().resolve()
    verifier = ShadowGraspVerifier()
    transitions = []
    final_by_episode = {}
    observations = 0
    for line in (trace / "events.jsonl").open():
        event = json.loads(line)
        if event.get("kind") != "observation":
            continue
        result = verifier.update(
            event["ep"], event["chunk"],
            rgb(trace / event["images"]["front"]),
            rgb(trace / event["images"]["wrist"]),
            event["state"],
        )
        observations += 1
        final_by_episode[str(event["ep"])] = verifier.episode_summary()
        if result["transition"]:
            transitions.append(result)
    document = {
        "trace": str(trace),
        "observations": observations,
        "final_phase_by_episode": final_by_episode,
        "transitions": transitions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n")
    print(json.dumps(document["final_phase_by_episode"], indent=2))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
