#!/usr/bin/env python3
"""Read-only Rerun guide for placing the tray at a table-registered target."""

from __future__ import annotations

import argparse
import json
import signal
import time
from pathlib import Path

import cv2
import numpy as np
import rerun as rr
import rerun.blueprint as rb


def parse_point(value: str) -> np.ndarray:
    point = np.asarray([float(part) for part in value.split(",")], dtype=np.float32)
    if point.shape != (2,):
        raise argparse.ArgumentTypeError("point must be x,y")
    return point


def descriptors(image: np.ndarray, mask: np.ndarray, sift: cv2.SIFT):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return sift.detectAndCompute(gray, mask)


def transform_from_matches(base_kp, base_desc, current_kp, current_desc, ratio=0.72):
    if base_desc is None or current_desc is None:
        raise RuntimeError("no descriptors")
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(base_desc, current_desc, k=2)
    good = [first for first, second in pairs if first.distance < ratio * second.distance]
    if len(good) < 8:
        raise RuntimeError(f"only {len(good)} feature matches")
    source = np.float32([base_kp[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
    destination = np.float32([current_kp[match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
    transform, inliers = cv2.findHomography(source, destination, cv2.RANSAC, 2.0)
    if transform is None or int(inliers.sum()) < 6:
        raise RuntimeError("feature transform rejected")
    return transform, len(good), int(inliers.sum())


def map_point(point: np.ndarray, transform: np.ndarray) -> np.ndarray:
    return cv2.perspectiveTransform(point.reshape(1, 1, 2), transform)[0, 0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", default="/dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--tray-centre", type=parse_point, required=True)
    parser.add_argument("--target", type=parse_point, required=True)
    parser.add_argument("--tolerance-px", type=float, default=4.0)
    parser.add_argument("--web-port", type=int, default=9118)
    parser.add_argument("--grpc-port", type=int, default=9884)
    parser.add_argument("--status", type=Path, default=Path("/tmp/so101_tray_placement_status.json"))
    args = parser.parse_args()

    baseline = cv2.imread(str(args.baseline))
    if baseline is None:
        raise SystemExit(f"could not read baseline {args.baseline}")
    height, width = baseline.shape[:2]
    sift = cv2.SIFT_create(nfeatures=3000, contrastThreshold=0.01)

    table_mask = np.zeros((height, width), dtype=np.uint8)
    table_mask[285:, :] = 255
    table_mask[120:, 450:] = 255
    tray_mask = np.zeros((height, width), dtype=np.uint8)
    tray_mask[30:300, 80:325] = 255
    base_table_kp, base_table_desc = descriptors(baseline, table_mask, sift)
    base_tray_kp, base_tray_desc = descriptors(baseline, tray_mask, sift)

    blueprint = rb.Blueprint(
        rb.Horizontal(
            rb.Spatial2DView(origin="camera/top", name="Live tray guide"),
            rb.Vertical(
                rb.TextDocumentView(origin="status", name="Tray status"),
                rb.TimeSeriesView(origin="offset", name="Target offset (pixels)"),
            ),
        ),
        collapse_panels=True,
    )
    rr.init("SO-101 tray placement guide")
    rr.serve_web(open_browser=False, web_port=args.web_port, grpc_port=args.grpc_port, default_blueprint=blueprint)

    cap = cv2.VideoCapture(args.camera, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        raise SystemExit(f"could not open {args.camera}")

    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    frame_index = 0
    started = time.monotonic()
    try:
        while running:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            frame_index += 1
            if frame_index < 45:
                continue
            annotated = frame.copy()
            record = {"ready": False, "time": time.time()}
            try:
                current_table_kp, current_table_desc = descriptors(frame, table_mask, sift)
                current_tray_kp, current_tray_desc = descriptors(frame, tray_mask, sift)
                table_transform, table_matches, table_inliers = transform_from_matches(
                    base_table_kp, base_table_desc, current_table_kp, current_table_desc
                )
                tray_transform, tray_matches, tray_inliers = transform_from_matches(
                    base_tray_kp, base_tray_desc, current_tray_kp, current_tray_desc
                )
                target = map_point(args.target, table_transform)
                tray = map_point(args.tray_centre, tray_transform)
                error = tray - target
                distance = float(np.linalg.norm(error))
                ready = distance <= args.tolerance_px
                colour = (0, 255, 0) if ready else (0, 0, 255)
                tray_px = tuple(np.rint(tray).astype(int))
                target_px = tuple(np.rint(target).astype(int))
                cv2.circle(annotated, target_px, 15, (0, 255, 0), 3)
                cv2.circle(annotated, tray_px, 12, colour, 3)
                cv2.arrowedLine(annotated, tray_px, target_px, (0, 255, 255), 3, tipLength=0.25)
                label = "READY - STOP MOVING" if ready else f"MOVE TRAY dx={-error[0]:+.0f}, dy={-error[1]:+.0f}px"
                cv2.putText(annotated, label, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.72, colour, 2, cv2.LINE_AA)
                record.update(
                    ready=ready,
                    tray_px=tray.round(2).tolist(),
                    target_px=target.round(2).tolist(),
                    error_px=error.round(2).tolist(),
                    distance_px=round(distance, 2),
                    table_matches=table_matches,
                    table_inliers=table_inliers,
                    tray_matches=tray_matches,
                    tray_inliers=tray_inliers,
                )
                status = (
                    f"{'READY — stop moving the tray' if ready else 'Adjust the whole tray'}\n\n"
                    f"Tray centre: `{tray[0]:.1f}, {tray[1]:.1f}` px  \n"
                    f"Table-registered target: `{target[0]:.1f}, {target[1]:.1f}` px  \n"
                    f"Move: `dx={-error[0]:+.1f}, dy={-error[1]:+.1f}` px  \n"
                    f"Distance: **{distance:.1f} px** (ready at <= {args.tolerance_px:.1f} px)\n\n"
                    "Red circle follows the tray. Green circle is fixed to the table.  \n"
                    "Camera only. The robot is disconnected."
                )
                rr.log("offset/x_px", rr.Scalars(float(error[0])))
                rr.log("offset/y_px", rr.Scalars(float(error[1])))
                rr.log("offset/distance_px", rr.Scalars(distance))
            except Exception as error:
                status = f"Tracking error: `{error}`\n\nStop moving until tracking returns. Camera only."
                cv2.putText(annotated, "TRACKING ERROR - STOP", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 255), 2)
                record["error"] = str(error)

            encoded_ok, encoded = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if encoded_ok:
                rr.set_time("elapsed", duration=time.monotonic() - started)
                rr.log("camera/top", rr.EncodedImage(contents=encoded.tobytes(), media_type="image/jpeg"))
                rr.log("status", rr.TextDocument(status, media_type="text/markdown"))
                args.status.write_text(json.dumps(record, indent=2) + "\n")
            time.sleep(0.2)
    finally:
        cap.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
