#!/usr/bin/env python3
"""Replay saved chunk-1 observations through FT4 checkpoint 3000 without robot access."""

import argparse
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np


FIRST = Path("/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_regular_orange10_row2f_20261109")
REST = Path("/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_regular_orange10_row2_remaining7_20261109")
TRIALS = {
    2: (FIRST, 2, "late_reach"),
    3: (FIRST, 3, "success"),
    5: (REST, 2, "no_engagement"),
    7: (REST, 4, "no_engagement"),
    8: (REST, 5, "no_engagement"),
    9: (REST, 6, "no_engagement"),
    10: (REST, 7, "extremely_late_reach"),
}
BENCH = Path(__file__).parents[1] / "bench_client.py"


def load_bench():
    spec = importlib.util.spec_from_file_location("saved_bench_client", BENCH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_trial(root, ep, chunk):
    observation = None
    historical = None
    for line in (root / "events.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row.get("ep") != ep or row.get("chunk") != chunk:
            continue
        if row.get("kind") == "observation":
            observation = row
        elif row.get("kind") == "action_chunk_received":
            historical = np.asarray(row["actions"], dtype=np.float32)
    if observation is None or historical is None:
        raise RuntimeError(f"missing ep{ep} chunk{chunk} in {root}")
    images = {}
    for name in ("front", "wrist"):
        bgr = cv2.imread(str(root / observation["images"][name]), cv2.IMREAD_COLOR)
        if bgr is None:
            raise RuntimeError(f"could not read {name} image")
        images[name] = np.ascontiguousarray(bgr[:, :, ::-1])
    return np.asarray(observation["state"], dtype=np.float32), images, historical


def metrics(actions, state):
    shoulder_unfold = float(np.max(actions[:, 1] - state[1]))
    elbow_unfold = float(np.max(state[2] - actions[:, 2]))
    score = max(shoulder_unfold, elbow_unfold)
    return {
        "shoulder_unfold_deg": shoulder_unfold,
        "elbow_unfold_deg": elbow_unfold,
        "reach_score_deg": score,
        "purposeful_reach": score >= 15.0,
        "gripper_min_deg": float(np.min(actions[:, 5])),
        "first_action": actions[0].round(4).tolist(),
        "last_action": actions[-1].round(4).tolist(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="192.168.194.220:8081")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--case", action="append", default=[], help="trial:chunk; default is chunk 1 for every trial")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("report.json"))
    args = parser.parse_args()
    bench = load_bench()
    act = bench.grpc_client(args.server, 20)
    rows = []
    cases = [(int(text.split(":")[0]), int(text.split(":")[1])) for text in args.case]
    if not cases:
        cases = [(trial, 1) for trial in TRIALS]
    for trial, chunk in cases:
        root, ep, outcome = TRIALS[trial]
        state, images, historical = load_trial(root, ep, chunk)
        historical_metrics = metrics(historical, state)
        for repeat in range(1, args.repeats + 1):
            prediction = act(images["front"], images["wrist"], state, "Grab oranges and place into plate.")
            rows.append({
                "trial": trial,
                "chunk": chunk,
                "historical_outcome": outcome,
                "repeat": repeat,
                "state": state.tolist(),
                "historical": historical_metrics,
                "replay": metrics(prediction, state),
                "historical_replay_mae": float(np.mean(np.abs(prediction - historical))),
                "timing_ms": act.last_timing,
            })
    groups = []
    for trial, chunk in cases:
        group = [row for row in rows if row["trial"] == trial and row["chunk"] == chunk]
        scores = [row["replay"]["reach_score_deg"] for row in group]
        groups.append({
            "trial": trial,
            "chunk": chunk,
            "historical_outcome": group[0]["historical_outcome"],
            "historical_chunk": group[0]["historical"],
            "replays": len(group),
            "purposeful_reach_replays": sum(row["replay"]["purposeful_reach"] for row in group),
            "reach_score_median_deg": float(np.median(scores)),
            "reach_score_range_deg": [float(np.min(scores)), float(np.max(scores))],
        })
    report = {
        "scope": "Saved chunk-1 camera images and measured state only; no robot or live cameras opened.",
        "checkpoint": "FT4 checkpoint 3000",
        "repeats_per_observation": args.repeats,
        "purposeful_reach_definition": "Within the 20 predicted actions, shoulder lift unfolds or elbow flex unfolds by at least 15 degrees from the saved state.",
        "groups": groups,
        "rows": rows,
    }
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({"repeats_per_observation": args.repeats, "groups": groups}, indent=2))


if __name__ == "__main__":
    main()
