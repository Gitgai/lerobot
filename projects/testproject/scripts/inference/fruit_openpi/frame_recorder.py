"""Lossless frame/observation recorder. No robot imports or hardware writes.

Camera timestamps are host postprocessing timestamps, not exposure timestamps.
Bounded background queue; missing coverage is counted, never silently hidden.
"""

import json
import queue
import threading
import time
from collections import Counter
from pathlib import Path

import cv2


class FrameRecorder:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.pending = queue.Queue(maxsize=180)
        self.lock = threading.Lock()
        self.counts = Counter()
        self.sequences = Counter()
        self.error = None
        self.closed = False
        self.started_ns = time.monotonic_ns()
        self.stream = (self.root / "events.jsonl").open("x", buffering=1)
        self.workers = [
            threading.Thread(target=self._write_loop, name=f"frame-recorder-{i}") for i in range(3)
        ]
        for worker in self.workers:
            worker.start()
        self.event(
            "recording_started",
            timestamp_semantics="host monotonic after image postprocessing; not exposure time",
            image_format="lossless PNG RGB source",
            queue_capacity=180,
        )

    def _submit(self, event, images=None):
        event = dict(event, monotonic_ns=time.monotonic_ns(), unix_ns=time.time_ns())
        with self.lock:
            if self.closed:
                return
            try:
                self.pending.put_nowait((event, images or {}))
                self.counts["enqueued"] += 1
            except queue.Full:
                self.counts["dropped_" + event["kind"]] += 1
                if self.counts["dropped_" + event["kind"]] == 1:
                    print(
                        "RECORDING WARNING: queue full; missing "
                        + event["kind"]
                        + " coverage will be counted",
                        flush=True,
                    )

    def event(self, kind, **data):
        self._submit(dict(kind=kind, **data))

    def frame(self, camera, image):
        with self.lock:
            index = self.sequences[camera]
            self.sequences[camera] += 1
        self._submit(
            {"kind": "camera_frame", "camera": camera, "frame_id": index},
            {f"frames/{camera}/{index:08d}.png": image.copy()},
        )

    def observation(self, obs):
        with self.lock:
            index = self.sequences["observation"]
            self.sequences["observation"] += 1
        raw = obs.observation
        paths = {k: f"observations/{index:08d}_{k}.png" for k in ("front", "wrist")}
        self._submit(
            {
                "kind": "observation",
                "observation_id": index,
                "step": obs.get_timestep(),
                "observation_unix": obs.get_timestamp(),
                "task": raw.get("task"),
                "state": {k: float(v) for k, v in raw.items() if k.endswith(".pos")},
                "images": paths,
            },
            {paths[k]: raw[k].copy() for k in paths},
        )

    def attach_camera(self, camera, name):
        if name not in ("front", "wrist"):
            raise ValueError("Only front/wrist recording configured")
        original = camera._postprocess_image

        def record_after_postprocess(raw):
            image = original(raw)
            self.frame(name, image)
            return image

        camera._postprocess_image = record_after_postprocess

    def check(self):
        if self.error:
            raise RuntimeError("Frame recording failed: " + self.error)

    def _write_loop(self):
        while True:
            item = self.pending.get()
            if item is None:
                break
            event, images = item
            if self.error:
                with self.lock:
                    self.counts["discarded_after_error"] += 1
                continue
            try:
                for relative, rgb in images.items():
                    path = self.root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if not cv2.imwrite(
                        str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 0]
                    ):
                        raise OSError("Cannot save " + str(path))
                event["saved_paths"] = list(images)
                with self.lock:
                    self.stream.write(json.dumps(event) + "\n")
                    self.counts["saved_" + event["kind"]] += 1
                    self.counts["saved_images"] += len(images)
            except Exception as exc:
                self.error = repr(exc)

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
        for _worker in self.workers:
            self.pending.put(None)
        for worker in self.workers:
            worker.join()
        self.stream.close()
        result = {
            "counts": dict(self.counts),
            "seen": dict(self.sequences),
            "error": self.error,
            "elapsed_s": (time.monotonic_ns() - self.started_ns) / 1e9,
            "complete": self.error is None and not any(k.startswith("dropped_") for k in self.counts),
        }
        (self.root / "summary.json").write_text(json.dumps(result, indent=2))
        print("RECORDING_SUMMARY " + json.dumps(result), flush=True)
        self.check()
