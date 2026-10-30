#!/usr/bin/env python3
"""Follow a bench_client.py --trace-dir journal in Rerun. Read-only."""
import argparse, json, time
from collections import deque
from pathlib import Path

import cv2
import rerun as rr
import rerun.blueprint as rb

JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")


def table(actions):
    lines = ["| step | " + " | ".join(JOINTS) + " |",
             "|---:|" + "---:|" * len(JOINTS)]
    lines += ["| " + str(i) + " | " + " | ".join(f"{v:.2f}" for v in row) + " |"
              for i, row in enumerate(actions)]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("trace", type=Path)
    ap.add_argument("--connect", required=True)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    root = a.trace.expanduser().resolve()
    journal = root / "events.jsonl"
    rr.init("SO-101 fine-tune live trial — " + root.name)
    rr.connect_grpc(a.connect)
    rr.send_blueprint(rb.Blueprint(rb.Vertical(
        rb.TextDocumentView(origin="status", name="Live trial status"),
        rb.Horizontal(rb.Spatial2DView(origin="camera/front", name="Front policy input"),
                      rb.Spatial2DView(origin="camera/wrist", name="Wrist policy input")),
        rb.Tabs(
            rb.TextDocumentView(origin="prediction", name="Predicted 20-action chunk"),
            rb.TextDocumentView(origin="dispatch", name="Executed actions"),
            rb.TextDocumentView(origin="state", name="Measured joints"),
            rb.Vertical(rb.TimeSeriesView(origin="timing", name="Policy request latency"),
                        rb.TimeSeriesView(origin="progress", name="Episode / chunk progress"), name="Timing"),
            rb.Tabs(*[rb.TimeSeriesView(origin=f"joints/{j}", name=j) for j in JOINTS], name="Joint plots")),
        rb.TimePanel(timeline="elapsed")), collapse_panels=True))

    offset = 0; origin = None; last_seen = time.monotonic(); latest = {}; sends = deque(maxlen=20)
    counts = {"observations": 0, "predictions": 0, "sends": 0}; done = False
    while True:
        rows = []
        if journal.exists():
            with journal.open() as f:
                f.seek(offset)
                while len(rows) < 2000:
                    line = f.readline()
                    if not line or not line.endswith("\n"): break
                    rows.append(json.loads(line)); offset = f.tell()
        for e in rows:
            ns = e["monotonic_ns"]; origin = ns if origin is None else origin
            elapsed = (ns - origin) / 1e9; rr.set_time("elapsed", duration=elapsed)
            last_seen = time.monotonic(); kind = e["kind"]; latest[kind] = e
            if kind == "observation":
                counts["observations"] += 1
                for cam in ("front", "wrist"):
                    p = (root / e["images"][cam]).resolve()
                    if not p.is_relative_to(root): raise ValueError("image outside trace")
                    data = p.read_bytes()
                    rr.log(f"camera/{cam}", rr.EncodedImage(contents=data, media_type="image/jpeg"))
                for j, value in zip(JOINTS, e["state"]): rr.log(f"joints/{j}/measured", rr.Scalars(value))
                rr.log("progress/chunk", rr.Scalars(e["chunk"])); rr.log("progress/episode", rr.Scalars(e["ep"]))
                rr.log("state", rr.TextDocument("Measured before request\n\n" + "\n".join(
                    f"{j}: {v:.2f}" for j, v in zip(JOINTS, e["state"])) +
                    "\n\nCamera stale counts: " + json.dumps(e.get("camera_stale", {}))))
            elif kind == "action_chunk_received":
                counts["predictions"] += 1
                rr.log("timing/latency_ms", rr.Scalars(1000 * e["latency_s"]))
                rr.log("prediction", rr.TextDocument(
                    f"Episode {e['ep']}, chunk {e['chunk']} — {1000*e['latency_s']:.0f} ms\n\n" + table(e["actions"]),
                    media_type="text/markdown"))
                for row in e["actions"]:
                    for j, value in zip(JOINTS, row): rr.log(f"joints/{j}/predicted", rr.Scalars(value))
            elif kind == "action_dispatched":
                counts["sends"] += 1
                sends.append(e)
                for j, value in zip(JOINTS, e["sent"]): rr.log(f"joints/{j}/sent", rr.Scalars(value))
                lines = ["Latest 20 commands returned by `send_action`.", "",
                         "| ep | chunk | step | gripper | clamped |", "|---:|---:|---:|---:|:---:|"]
                lines += [f"| {x['ep']} | {x['chunk']} | {x['action_index']} | {x['sent'][5]:.2f} | {x['clamped']} |" for x in sends]
                rr.log("dispatch", rr.TextDocument("\n".join(lines), media_type="text/markdown"))
            elif kind == "trace_closed": done = True

        phase = "waiting for trace"; ep = "–"; chunk = "–"; latency = "–"
        phase_events = {
            "countdown": lambda x: f"countdown: {x['seconds_left']} s",
            "episode_started": lambda x: "trial running",
            "episode_ended": lambda x: "episode ended: " + str(x["result"]),
            "return_started": lambda x: "returning to start",
            "return_ended": lambda x: "returned to start",
            "trace_closed": lambda x: "trace closed" if x.get("complete") else "trace closed incomplete",
        }
        present = [(e["monotonic_ns"], kind, e) for kind, e in latest.items() if kind in phase_events]
        if present:
            _, kind, event = max(present)
            phase = phase_events[kind](event)
        if "episode_started" in latest: ep = latest["episode_started"]["ep"]
        if "observation" in latest: ep = latest["observation"]["ep"]; chunk = latest["observation"]["chunk"]
        if "action_chunk_received" in latest: latency = f"{1000*latest['action_chunk_received']['latency_s']:.0f} ms"
        rr.reset_time()
        rr.log("status", rr.TextDocument(
            f"{phase}\nEpisode: {ep}   Chunk: {chunk}   Latest latency: {latency}\n"
            f"Observations: {counts['observations']}   predictions: {counts['predictions']}   sends: {counts['sends']}\n"
            f"No new trace event for {time.monotonic()-last_seen:.1f} s\n\n"
            "Read-only viewer. Images are the exact inputs recorded before each policy request. "
            "Predicted values are model output; sent values include the client safety clamp."), static=True)
        rr.get_global_data_recording().flush()
        drained = journal.exists() and offset == journal.stat().st_size
        if done and drained or (a.once and drained): break
        if not rows: time.sleep(.15)
    rr.disconnect()


if __name__ == "__main__": main()
