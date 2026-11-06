#!/usr/bin/env python3
"""Read-only live top-camera guide for tray-relative orange placement."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import time

import cv2
import numpy as np
import rerun as rr
import rerun.blueprint as rb

from wrist_grasp_gate import DetectionError, orange_blob


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", default="/dev/video4")
    parser.add_argument("--target", default="173,116")
    parser.add_argument("--tolerance-px", type=float, default=3.0)
    parser.add_argument("--connect", required=True)
    parser.add_argument("--status", type=Path, default=Path("/tmp/so101_orange_placement_status.json"))
    args = parser.parse_args()
    target = np.asarray([float(value) for value in args.target.split(",")], dtype=float)
    if target.shape != (2,):
        raise SystemExit("--target must be x,y")

    rr.init("SO-101 orange placement guide")
    rr.connect_grpc(args.connect)
    rr.send_blueprint(
        rb.Blueprint(
            rb.Horizontal(
                rb.Spatial2DView(origin="camera/top", name="Live placement guide"),
                rb.Vertical(
                    rb.TextDocumentView(origin="status", name="Placement status"),
                    rb.TimeSeriesView(origin="offset", name="Target offset (pixels)"),
                ),
            ),
            collapse_panels=True,
        )
    )

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
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
    started = time.monotonic()
    frame_index = 0
    try:
        while running:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            frame_index += 1
            # Let the C270 finish its blank/auto-exposure startup frames.
            if frame_index < 45:
                continue
            annotated = frame.copy()
            cv2.circle(annotated, tuple(np.rint(target).astype(int)), 9, (0, 255, 0), 3)
            cv2.drawMarker(
                annotated,
                tuple(np.rint(target).astype(int)),
                (0, 255, 0),
                cv2.MARKER_CROSS,
                25,
                3,
            )
            record = {"ready": False, "target_px": target.tolist(), "time": time.time()}
            try:
                centre, area = orange_blob(frame)
                error = centre - target
                distance = float(np.linalg.norm(error))
                ready = distance <= args.tolerance_px
                colour = (0, 255, 0) if ready else (0, 0, 255)
                cv2.circle(annotated, tuple(np.rint(centre).astype(int)), 10, colour, 3)
                cv2.arrowedLine(
                    annotated,
                    tuple(np.rint(centre).astype(int)),
                    tuple(np.rint(target).astype(int)),
                    (0, 255, 255),
                    3,
                    tipLength=0.25,
                )
                label = "READY - HANDS CLEAR" if ready else f"move dx={-error[0]:+.1f}, dy={-error[1]:+.1f} px"
                cv2.putText(annotated, label, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, colour, 2, cv2.LINE_AA)
                record.update(
                    ready=ready,
                    orange_px=centre.round(2).tolist(),
                    error_px=error.round(2).tolist(),
                    distance_px=round(distance, 2),
                    orange_area_px=round(area, 1),
                )
                rr.log("offset/x_px", rr.Scalars(float(error[0])))
                rr.log("offset/y_px", rr.Scalars(float(error[1])))
                rr.log("offset/distance_px", rr.Scalars(distance))
                status = (
                    f"{'READY — hands clear' if ready else 'Adjust orange'}\n\n"
                    f"Orange centre: `{centre[0]:.2f}, {centre[1]:.2f}` px  \n"
                    f"Target: `{target[0]:.2f}, {target[1]:.2f}` px  \n"
                    f"Error: `{error[0]:+.2f}, {error[1]:+.2f}` px  \n"
                    f"Distance: **{distance:.2f} px** (ready at <= {args.tolerance_px:.1f} px)\n\n"
                    "Camera only. The robot is disconnected."
                )
            except DetectionError as error:
                status = f"Orange detection error: `{error}`\n\nCamera only. The robot is disconnected."
                cv2.putText(annotated, "ORANGE NOT DETECTED", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                record["error"] = str(error)

            ok, encoded = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if ok:
                rr.set_time("elapsed", duration=time.monotonic() - started)
                rr.log("camera/top", rr.EncodedImage(contents=encoded.tobytes(), media_type="image/jpeg"))
                rr.log("status", rr.TextDocument(status, media_type="text/markdown"))
                args.status.write_text(json.dumps(record, indent=2) + "\n")
            # Five visual updates per second are enough for hand placement.
            time.sleep(0.2)
    finally:
        cap.release()
        rr.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
