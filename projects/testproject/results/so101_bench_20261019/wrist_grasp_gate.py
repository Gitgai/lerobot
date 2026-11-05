#!/usr/bin/env python3
"""Measure orange alignment relative to the marked SO-101 fingertips.

This tool is vision-only: it never connects to the robot.  A PASS means that
the live image is close to the one verified centre grasp.  It is a necessary
pre-close condition, not permission to enable automatic reset by itself.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


LEFT_TIP_ROI = (80, 50, 300, 310)
RIGHT_TIP_ROI = (360, 30, 620, 300)
DEFAULT_REFERENCE = Path(__file__).parent / (
    "reset/calibration_evidence/tray_closed_loop_success_20261105/"
    "01_final_open_wrist.jpg"
)


class DetectionError(RuntimeError):
    pass


def orange_blob(image: np.ndarray) -> tuple[np.ndarray, float]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([3, 100, 70]), np.array([28, 255, 255]))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 1000:
            continue
        _, _, width, height = cv2.boundingRect(contour)
        perimeter = cv2.arcLength(contour, True)
        aspect = min(width, height) / max(width, height)
        fill = area / (width * height)
        circularity = 4 * math.pi * area / (perimeter * perimeter) if perimeter else 0
        # At the raised tray pose, orange-coloured wood can touch an image edge
        # and form a component larger than the fruit.  The real orange remains
        # compact and nearly round in both raised and final approach views.
        if aspect >= 0.65 and fill >= 0.5 and circularity >= 0.45:
            candidates.append(contour)
    if not candidates:
        raise DetectionError("orange not found")
    contour = max(candidates, key=cv2.contourArea)
    moments = cv2.moments(contour)
    if moments["m00"] == 0:
        raise DetectionError("orange contour has zero area")
    centre = np.array(
        [moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]],
        dtype=float,
    )
    return centre, float(cv2.contourArea(contour))


def black_tip(image: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = roi
    hsv = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([179, 255, 105]))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, _, stats, centres = cv2.connectedComponentsWithStats(mask)
    candidates = []
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        if 250 <= area <= 1000 and 15 <= width <= 40 and 15 <= height <= 45:
            candidates.append((int(area), centres[index] + [x0, y0]))
    if not candidates:
        raise DetectionError(f"marked fingertip not found in ROI {roi}")
    return max(candidates, key=lambda item: item[0])[1].astype(float)


def measure(image: np.ndarray) -> dict:
    orange, orange_area = orange_blob(image)
    left = black_tip(image, LEFT_TIP_ROI)
    right = black_tip(image, RIGHT_TIP_ROI)
    span = float(np.linalg.norm(right - left))
    if not 250 <= span <= 400:
        raise DetectionError(f"implausible fingertip span {span:.1f}px")
    along = (right - left) / span
    normal = np.array([-along[1], along[0]])
    midpoint = (left + right) / 2
    relative = np.array([(orange - midpoint) @ along, (orange - midpoint) @ normal])
    return {
        "orange_px": orange.round(2).tolist(),
        "orange_area_px": round(orange_area, 1),
        "left_tip_px": left.round(2).tolist(),
        "right_tip_px": right.round(2).tolist(),
        "tip_midpoint_px": midpoint.round(2).tolist(),
        "tip_span_px": round(span, 2),
        "orange_in_finger_frame_px": relative.round(2).tolist(),
    }


def evaluate(image: np.ndarray, reference: np.ndarray, tolerance: float) -> dict:
    live = measure(image)
    ref = measure(reference)
    error = np.asarray(live["orange_in_finger_frame_px"]) - np.asarray(
        ref["orange_in_finger_frame_px"]
    )
    passed = bool(np.all(np.abs(error) <= tolerance))
    return {
        "result": "PASS" if passed else "REJECT",
        "safe_to_close": passed,
        "provisional_single_success_reference": True,
        "tolerance_each_axis_px": tolerance,
        "finger_frame_error_px": error.round(2).tolist(),
        "live": live,
        "reference": ref,
        "note": "PASS is necessary but still requires watched close, stall, lift and carry proof.",
    }


def annotate(image: np.ndarray, result: dict) -> np.ndarray:
    output = image.copy()
    live = result["live"]
    left = tuple(np.rint(live["left_tip_px"]).astype(int))
    right = tuple(np.rint(live["right_tip_px"]).astype(int))
    orange = tuple(np.rint(live["orange_px"]).astype(int))
    midpoint = tuple(np.rint(live["tip_midpoint_px"]).astype(int))
    colour = (0, 200, 0) if result["safe_to_close"] else (0, 0, 255)
    cv2.line(output, left, right, (255, 200, 0), 2)
    for point in (left, right):
        cv2.circle(output, point, 8, (255, 200, 0), 2)
    cv2.circle(output, midpoint, 7, (255, 0, 255), 2)
    cv2.circle(output, orange, 10, colour, 3)
    error = result["finger_frame_error_px"]
    cv2.putText(
        output,
        f"{result['result']} finger-frame error {error}",
        (15, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        colour,
        2,
        cv2.LINE_AA,
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--tolerance", type=float, default=14.0)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--annotated", type=Path)
    args = parser.parse_args()

    image = cv2.imread(str(args.image))
    reference = cv2.imread(str(args.reference))
    if image is None or reference is None:
        raise SystemExit("could not read live image or reference image")
    try:
        result = evaluate(image, reference, args.tolerance)
    except DetectionError as error:
        result = {"result": "ERROR", "safe_to_close": False, "error": str(error)}
    text = json.dumps(result, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n")
    if args.annotated and "live" in result:
        args.annotated.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.annotated), annotate(image, result))
    return 0 if result.get("safe_to_close") else 2


if __name__ == "__main__":
    raise SystemExit(main())
