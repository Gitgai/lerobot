#!/usr/bin/env python3
"""Read-only orange grasp-pose diagnostic for reviewed wrist-camera frames.

This is a calibration tool, not an action gate. It detects a bright, saturated,
roughly circular fruit candidate and checks whether its normalized centre and
radius fall inside the reviewed grasp band. Missing or ambiguous detections are
reported as ``unknown`` and must never be treated as eligible by a future gate.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np


WIDTH, HEIGHT = 640, 480
X_BAND = (220 / WIDTH, 480 / WIDTH)
Y_BAND = (90 / HEIGHT, 310 / HEIGHT)
RADIUS_BAND = (70 / HEIGHT, 180 / HEIGHT)


def detect(image_path: Path) -> dict[str, object]:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(image_path)
    image = cv2.resize(image, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    gray = cv2.medianBlur(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 9)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=80,
        param1=80,
        param2=35,
        minRadius=60,
        maxRadius=180,
    )
    yy, xx = np.ogrid[:HEIGHT, :WIDTH]
    candidates: list[dict[str, float]] = []
    for x, y, radius in ([] if circles is None else circles[0]):
        mask = (xx - x) ** 2 + (yy - y) ** 2 <= (0.72 * radius) ** 2
        saturation = float(np.mean(hsv[:, :, 1][mask]))
        value = float(np.mean(hsv[:, :, 2][mask]))
        if saturation < 90 or value < 180:
            continue
        candidates.append(
            {
                "x": float(x),
                "y": float(y),
                "radius": float(radius),
                "saturation": saturation,
                "value": value,
                "score": saturation + value + 0.7 * radius,
            }
        )
    if not candidates:
        return {"status": "unknown", "reason": "no confident fruit circle", "image": image}

    best = max(candidates, key=lambda candidate: candidate["score"])
    x_norm = best["x"] / WIDTH
    y_norm = best["y"] / HEIGHT
    radius_norm = best["radius"] / HEIGHT
    inside = (
        X_BAND[0] <= x_norm <= X_BAND[1]
        and Y_BAND[0] <= y_norm <= Y_BAND[1]
        and RADIUS_BAND[0] <= radius_norm <= RADIUS_BAND[1]
    )
    return {
        **best,
        "x_norm": x_norm,
        "y_norm": y_norm,
        "radius_norm": radius_norm,
        "status": "eligible" if inside else "ineligible",
        "reason": "inside reviewed grasp band" if inside else "outside reviewed grasp band",
        "image": image,
    }


def annotate(result: dict[str, object], destination: Path, expected: bool) -> None:
    image = result["image"].copy()
    x1, x2 = round(X_BAND[0] * WIDTH), round(X_BAND[1] * WIDTH)
    y1, y2 = round(Y_BAND[0] * HEIGHT), round(Y_BAND[1] * HEIGHT)
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 255), 2)
    if "x" in result:
        centre = (round(result["x"]), round(result["y"]))
        cv2.circle(image, centre, round(result["radius"]), (255, 0, 255), 3)
        cv2.circle(image, centre, 5, (0, 0, 255), -1)
    colour = (0, 180, 0) if result["status"] == "eligible" else (0, 0, 220)
    text = f"detector={result['status']} expected={'eligible' if expected else 'blocked'}"
    cv2.putText(image, text, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour, 2, cv2.LINE_AA)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination), image, [cv2.IMWRITE_JPEG_QUALITY, 92])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path, help="CSV with sample, image_path and expected_eligible")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--annotated-dir", type=Path)
    args = parser.parse_args()

    label_path = args.labels.resolve()
    rows = list(csv.DictReader(label_path.open()))
    output_rows = []
    for row in rows:
        image_path = Path(row["image_path"])
        if not image_path.is_absolute():
            image_path = label_path.parent / image_path
        expected = row["expected_eligible"].strip() == "1"
        result = detect(image_path)
        predicted = result["status"] == "eligible"
        output_rows.append(
            {
                **row,
                "detector_status": result["status"],
                "correct_for_gate": int(predicted == expected),
                "x": "" if "x" not in result else f"{result['x']:.1f}",
                "y": "" if "y" not in result else f"{result['y']:.1f}",
                "radius": "" if "radius" not in result else f"{result['radius']:.1f}",
                "saturation": "" if "saturation" not in result else f"{result['saturation']:.1f}",
                "value": "" if "value" not in result else f"{result['value']:.1f}",
                "detector_reason": result["reason"],
            }
        )
        if args.annotated_dir:
            annotate(result, args.annotated_dir / f"{row['sample']}.jpg", expected)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(output_rows[0])
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)

    positives = [r for r in output_rows if r["expected_eligible"] == "1"]
    negatives = [r for r in output_rows if r["expected_eligible"] == "0"]
    positive_pass = sum(r["detector_status"] == "eligible" for r in positives)
    negative_block = sum(r["detector_status"] != "eligible" for r in negatives)
    print(f"positive eligible: {positive_pass}/{len(positives)}")
    print(f"negative blocked or unknown: {negative_block}/{len(negatives)}")
    print(f"calibration agreement: {positive_pass + negative_block}/{len(output_rows)}")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
