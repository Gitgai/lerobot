#!/usr/bin/env python3
"""Compare FT4B gate images with the orange demonstration geometry."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def read_video_frame(path: Path, timestamp_s: float) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_s * 1000.0)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Cannot decode {path} at {timestamp_s:.3f}s")
    return frame


def orange_candidates(image: np.ndarray) -> list[dict]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Broad enough for both the C270 and wrist camera, then reject small clutter.
    mask = cv2.inRange(hsv, np.array([2, 95, 65]), np.array([35, 255, 255]))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    rows = []
    height, width = image.shape[:2]
    for idx in range(1, count):
        x, y, w, h, area = [int(v) for v in stats[idx]]
        if area < 180 or w < 12 or h < 12:
            continue
        cx, cy = [float(v) for v in centroids[idx]]
        rows.append({
            "x_px": round(cx, 2), "y_px": round(cy, 2), "area_px": area,
            "bbox": [x, y, w, h], "x_norm": round(cx / width, 5),
            "y_norm": round(cy / height, 5),
        })
    return sorted(rows, key=lambda row: row["area_px"], reverse=True)


def best_orange(image: np.ndarray) -> dict | None:
    # In this fixed front view the fruit starts in the lower-right table region.
    # Hough geometry separates the round fruit from the similarly coloured wood.
    gray = cv2.medianBlur(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 9)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=50,
        param1=80, param2=25, minRadius=20, maxRadius=60,
    )
    if circles is not None:
        height, width = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        yy, xx = np.ogrid[:height, :width]
        eligible = []
        for circle in circles[0]:
            cx, cy, radius = circle
            if cx <= 0.55 * width or cy <= 0.50 * height:
                continue
            interior = (xx - cx) ** 2 + (yy - cy) ** 2 <= (0.72 * radius) ** 2
            saturation = float(np.mean(hsv[:, :, 1][interior]))
            value = float(np.mean(hsv[:, :, 2][interior]))
            if saturation >= 70 and value >= 95:
                eligible.append((saturation + value + 0.4 * radius, circle))
        if eligible:
            _, (cx, cy, radius) = max(eligible, key=lambda item: item[0])
            x, y = max(0, round(cx - radius)), max(0, round(cy - radius))
            w = min(width - x, round(2 * radius))
            h = min(height - y, round(2 * radius))
            return {
                "x_px": round(float(cx), 2), "y_px": round(float(cy), 2),
                "radius_px": round(float(radius), 2), "bbox": [x, y, w, h],
                "x_norm": round(float(cx / width), 5), "y_norm": round(float(cy / height), 5),
                "method": "hough_circle",
            }
    candidates = orange_candidates(image)
    if not candidates:
        return None
    # The fruit is a compact, substantial orange component. Prefer large components
    # in the table region and penalize very elongated cable/wood highlights.
    ranked = []
    for row in candidates:
        _, _, w, h = row["bbox"]
        compact = min(w, h) / max(w, h)
        score = row["area_px"] * (0.35 + compact)
        ranked.append((score, row))
    return max(ranked, key=lambda value: value[0])[1]


def annotate(image: np.ndarray, label: str, orange: dict | None) -> np.ndarray:
    output = image.copy()
    cv2.rectangle(output, (0, 0), (output.shape[1], 34), (0, 0, 0), -1)
    cv2.putText(output, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
    if orange:
        x, y, w, h = orange["bbox"]
        cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 3)
        cv2.drawMarker(output, (round(orange["x_px"]), round(orange["y_px"])), (255, 0, 255), cv2.MARKER_CROSS, 22, 3)
    return output


def montage(images: list[np.ndarray], columns: int, cell_width: int = 320) -> np.ndarray:
    resized = []
    for image in images:
        scale = cell_width / image.shape[1]
        resized.append(cv2.resize(image, (cell_width, round(image.shape[0] * scale))))
    cell_height = max(image.shape[0] for image in resized)
    rows = (len(resized) + columns - 1) // columns
    canvas = np.full((rows * cell_height, columns * cell_width, 3), 28, np.uint8)
    for index, image in enumerate(resized):
        y, x = divmod(index, columns)
        canvas[y * cell_height:y * cell_height + image.shape[0], x * cell_width:(x + 1) * cell_width] = image
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(args.manifest.read_text())
    mapping = manifest["materialized"]["train"]["mapping"]
    episodes = pd.read_parquet(args.dataset / "meta/episodes/chunk-000/file-000.parquet")
    data = pd.read_parquet(args.dataset / "data/chunk-000/file-000.parquet")
    demo_start_states = np.stack([
        np.asarray(group.iloc[0]["observation.state"], dtype=float)
        for episode, group in data[data.episode_index < 25].groupby("episode_index", sort=True)
    ])
    demo_rows, demo_tiles, demo_wrist_tiles = [], [], []
    for entry in mapping:
        if entry["source_kind"] != "orange":
            continue
        ep = int(entry["output_episode"])
        meta = episodes.loc[episodes.episode_index == ep].iloc[0]
        file_idx = int(meta["videos/observation.images.front/file_index"])
        timestamp = float(meta["videos/observation.images.front/from_timestamp"])
        video = args.dataset / f"videos/observation.images.front/chunk-000/file-{file_idx:03d}.mp4"
        image = read_video_frame(video, timestamp)
        wrist_file_idx = int(meta["videos/observation.images.wrist/file_index"])
        wrist_timestamp = float(meta["videos/observation.images.wrist/from_timestamp"])
        wrist_video = args.dataset / f"videos/observation.images.wrist/chunk-000/file-{wrist_file_idx:03d}.mp4"
        wrist_image = read_video_frame(wrist_video, wrist_timestamp)
        orange = best_orange(image)
        row = {"kind": "demo", "output_episode": ep, "source_episode": int(entry["source_episode"]), "image": str(video), "timestamp_s": timestamp, "orange": orange}
        demo_rows.append(row)
        demo_tiles.append(annotate(image, f"demo src {entry['source_episode']} / out {ep}", orange))
        demo_wrist_tiles.append(annotate(wrist_image, f"demo src {entry['source_episode']} / out {ep}", None))

    gate_rows, gate_tiles, gate_wrist_tiles, gate_start_states = [], [], [], []
    trace_names = ["trial1_trace_run4", "trial2_trace", "trial3_trace"]
    for trial, trace_name in enumerate(trace_names, 1):
        trace = args.gate / trace_name
        image_path = trace / "frames/ep01_chunk001_front.jpg"
        wrist_path = trace / "frames/ep01_chunk001_wrist.jpg"
        image = cv2.imread(str(image_path))
        wrist_image = cv2.imread(str(wrist_path))
        if image is None:
            raise RuntimeError(f"Cannot read {image_path}")
        orange = best_orange(image)
        events = [json.loads(line) for line in (trace / "events.jsonl").read_text().splitlines()]
        start_state = np.asarray(next(row["state"] for row in events if row["kind"] == "observation" and row["chunk"] == 1), dtype=float)
        gate_start_states.append(start_state)
        state_distance = np.mean(np.abs(demo_start_states - start_state), axis=1)
        nearest_state_index = int(np.argmin(state_distance))
        row = {
            "kind": "gate", "trial": trial, "image": str(image_path), "orange": orange,
            "start_state": start_state.round(5).tolist(),
            "nearest_demo_state_output_episode": nearest_state_index,
            "nearest_demo_state": demo_start_states[nearest_state_index].round(5).tolist(),
            "nearest_demo_state_abs_difference": np.abs(demo_start_states[nearest_state_index] - start_state).round(5).tolist(),
            "nearest_demo_state_mean_abs_difference_deg": round(float(state_distance[nearest_state_index]), 5),
        }
        gate_rows.append(row)
        gate_tiles.append(annotate(image, f"gate trial {trial}", orange))
        gate_wrist_tiles.append(annotate(wrist_image, f"gate trial {trial}", None))

    valid_demo = [row for row in demo_rows if row["orange"]]
    gate_centres = np.array([[row["orange"]["x_norm"], row["orange"]["y_norm"]] for row in gate_rows if row["orange"]])
    demo_centres = np.array([[row["orange"]["x_norm"], row["orange"]["y_norm"]] for row in valid_demo])
    nearest = []
    for gate_row in gate_rows:
        if not gate_row["orange"]:
            continue
        point = np.array([gate_row["orange"]["x_norm"], gate_row["orange"]["y_norm"]])
        distances = np.linalg.norm(demo_centres - point, axis=1)
        order = np.argsort(distances)[:5]
        nearest.append({
            "trial": gate_row["trial"],
            "gate_orange": gate_row["orange"],
            "nearest_demonstrations": [
                {"source_episode": valid_demo[index]["source_episode"], "output_episode": valid_demo[index]["output_episode"], "normalized_distance": round(float(distances[index]), 5), "orange": valid_demo[index]["orange"]}
                for index in order
            ],
        })

    report = {
        "method": "HSV orange segmentation in the fixed front-camera image; normalized Euclidean centre distance is an image-space coverage measure, not a world-coordinate calibration.",
        "demonstrations_detected": len(valid_demo),
        "demonstrations_total": len(demo_rows),
        "demo_x_norm_range": [round(float(demo_centres[:, 0].min()), 5), round(float(demo_centres[:, 0].max()), 5)] if len(demo_centres) else None,
        "demo_y_norm_range": [round(float(demo_centres[:, 1].min()), 5), round(float(demo_centres[:, 1].max()), 5)] if len(demo_centres) else None,
        "gate_x_norm_range": [round(float(gate_centres[:, 0].min()), 5), round(float(gate_centres[:, 0].max()), 5)] if len(gate_centres) else None,
        "gate_y_norm_range": [round(float(gate_centres[:, 1].min()), 5), round(float(gate_centres[:, 1].max()), 5)] if len(gate_centres) else None,
        "nearest": nearest,
        "joint_names": JOINTS,
        "demo_start_state_min": demo_start_states.min(axis=0).round(5).tolist(),
        "demo_start_state_median": np.median(demo_start_states, axis=0).round(5).tolist(),
        "demo_start_state_max": demo_start_states.max(axis=0).round(5).tolist(),
        "demonstrations": demo_rows,
        "gates": gate_rows,
    }
    (args.output / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")
    cv2.imwrite(str(args.output / "demo_start_montage.jpg"), montage(demo_tiles, 5))
    cv2.imwrite(str(args.output / "gate_start_montage.jpg"), montage(gate_tiles, 3))
    cv2.imwrite(str(args.output / "wrist_start_montage.jpg"), montage(demo_wrist_tiles + gate_wrist_tiles, 5))
    print(json.dumps({key: report[key] for key in ("demonstrations_detected", "demonstrations_total", "demo_x_norm_range", "demo_y_norm_range", "gate_x_norm_range", "gate_y_norm_range", "nearest")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
