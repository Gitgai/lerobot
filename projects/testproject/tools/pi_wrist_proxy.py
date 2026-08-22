#!/usr/bin/env python3
"""Live Raspberry Pi wrist-camera proxy for LeRobot/Pi05.

This serves a fast local JPEG endpoint at http://127.0.0.1:8092/frame.

The old version of this tool scanned the PiSnap timelapse folder for the
newest JPG on every request. That was too slow for robot control. This version
keeps one live rpicam-vid stream open and serves the newest decoded frame from
memory.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8092
DEFAULT_PI_HOST = "raspi@192.168.1.5"
DEFAULT_PI_IP = "192.168.1.5"
DEFAULT_PI_STREAM_PORT = 8892
WIDTH = 640
HEIGHT = 480
FPS = 10


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pi Wrist Live Camera</title>
  <style>
    :root {
      --bg: #11161b;
      --panel: #1a2128;
      --text: #eef4f8;
      --muted: #9eb0c0;
      --ok: #86efac;
      --warn: #facc15;
      --accent: #7dd3fc;
    }
    body {
      margin: 0;
      padding: 24px;
      min-height: 100vh;
      background: #11161b;
      color: var(--text);
      font-family: system-ui, sans-serif;
    }
    .wrap { max-width: 1100px; margin: 0 auto; display: grid; gap: 16px; }
    .panel {
      background: var(--panel);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 10px;
      padding: 18px;
    }
    h1 { margin: 0 0 6px; font-size: 1.4rem; }
    p { margin: 0; color: var(--muted); }
    code { color: var(--accent); }
    .status { display: flex; gap: 12px; flex-wrap: wrap; color: var(--muted); }
    .status strong { color: var(--text); }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    img {
      display: block;
      width: 100%;
      border-radius: 8px;
      background: #0b0f13;
      min-height: 280px;
      object-fit: contain;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <h1>Pi Wrist Live Camera</h1>
      <p>Pi05 wrist-camera URL: <code>http://127.0.0.1:8092/frame</code></p>
    </div>
    <div class="panel status">
      <div><strong>Status:</strong> <span id="status">checking...</span></div>
      <div><strong>Frame age:</strong> <span id="age">-</span></div>
      <div><strong>Frames:</strong> <span id="frames">-</span></div>
      <div><strong>Error:</strong> <span id="error">-</span></div>
    </div>
    <div class="panel">
      <img id="frame" alt="Live Pi wrist image">
    </div>
  </div>
  <script>
    async function tick() {
      try {
        const statusResp = await fetch('/status', { cache: 'no-store' });
        const status = await statusResp.json();
        const ok = status.ok;
        document.getElementById('status').textContent = ok ? 'live' : 'not ready';
        document.getElementById('status').className = ok ? 'ok' : 'warn';
        document.getElementById('age').textContent =
          status.last_frame_age_seconds === null ? '-' : status.last_frame_age_seconds + 's';
        document.getElementById('frames').textContent = status.frames;
        document.getElementById('error').textContent = status.error || '-';
        if (ok) {
          document.getElementById('frame').src = '/frame?t=' + Date.now();
        }
      } catch (err) {
        document.getElementById('status').textContent = 'offline';
        document.getElementById('status').className = 'warn';
        document.getElementById('error').textContent = String(err);
      }
    }
    tick();
    setInterval(tick, 500);
  </script>
</body>
</html>
"""


class FrameStore:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.jpeg_bytes: bytes | None = None
        self.updated_at = 0.0
        self.frames = 0
        self.error: str | None = None

    def put(self, data: bytes) -> None:
        with self.lock:
            self.jpeg_bytes = data
            self.updated_at = time.time()
            self.frames += 1
            self.error = None

    def set_error(self, error: str) -> None:
        with self.lock:
            self.error = error

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            age = None if self.updated_at == 0 else round(time.time() - self.updated_at, 3)
            return {
                "ok": self.jpeg_bytes is not None and age is not None and age < 2.0,
                "has_frame": self.jpeg_bytes is not None,
                "last_frame_age_seconds": age,
                "frames": self.frames,
                "error": self.error,
                "source": f"tcp://{PI_IP}:{PI_STREAM_PORT}",
            }

    def frame(self) -> tuple[bytes | None, float]:
        with self.lock:
            return self.jpeg_bytes, self.updated_at


STORE = FrameStore()
PI_HOST = DEFAULT_PI_HOST
PI_IP = DEFAULT_PI_IP
PI_STREAM_PORT = DEFAULT_PI_STREAM_PORT


def run_remote(command: str, timeout: float = 8.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", PI_HOST, command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def start_remote_stream() -> None:
    command = (
        "pkill -x rpicam-vid 2>/dev/null || true; "
        "sleep 0.5; "
        "nohup rpicam-vid "
        f"--width {WIDTH} --height {HEIGHT} --framerate {FPS} "
        "--codec mjpeg --quality 85 --listen -t 0 --nopreview "
        f"-o tcp://0.0.0.0:{PI_STREAM_PORT} "
        ">/tmp/lerobot_wrist_stream.log 2>&1 & "
        "echo $! > /tmp/lerobot_wrist_stream.pid"
    )
    result = run_remote(command)
    if result.returncode != 0:
        raise RuntimeError(result.stdout.strip() or "failed to start remote rpicam-vid")


def read_mjpeg_socket(source_host: str, source_port: int) -> None:
    """Read concatenated JPEG frames from rpicam-vid's raw MJPEG TCP output."""
    buffer = bytearray()
    with socket.create_connection((source_host, source_port), timeout=8.0) as sock:
        sock.settimeout(5.0)
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                raise RuntimeError("MJPEG TCP stream closed")
            buffer.extend(chunk)

            while True:
                start = buffer.find(b"\xff\xd8")
                if start < 0:
                    # Keep a small tail in case the marker spans chunks.
                    del buffer[:-1]
                    break
                end = buffer.find(b"\xff\xd9", start + 2)
                if end < 0:
                    if start > 0:
                        del buffer[:start]
                    break
                jpeg = bytes(buffer[start : end + 2])
                del buffer[: end + 2]
                STORE.put(jpeg)


def reader_loop(start_stream: bool) -> None:
    while True:
        try:
            if start_stream:
                start_remote_stream()
                time.sleep(1.0)

            read_mjpeg_socket(PI_IP, PI_STREAM_PORT)
        except Exception as exc:  # keep the proxy alive and reconnect
            STORE.set_error(str(exc))
            time.sleep(1.0)


class Handler(BaseHTTPRequestHandler):
    def _write(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/index"):
            self._write(200, "text/html; charset=utf-8", HTML.encode())
            return

        if self.path.startswith("/status"):
            self._write(200, "application/json", json.dumps(STORE.snapshot()).encode())
            return

        if self.path.startswith("/frame"):
            jpeg_bytes, updated_at = STORE.frame()
            if jpeg_bytes is None:
                self._write(503, "text/plain; charset=utf-8", b"no live wrist frame yet")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Age-Seconds", f"{time.time() - updated_at:.3f}")
            self.send_header("Content-Length", str(len(jpeg_bytes)))
            self.end_headers()
            self.wfile.write(jpeg_bytes)
            return

        self._write(404, "text/plain; charset=utf-8", b"not found")

    def log_message(self, *_args) -> None:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pi-host", default=DEFAULT_PI_HOST, help="SSH target, for example raspi@192.168.1.5"
    )
    parser.add_argument(
        "--pi-ip", default=DEFAULT_PI_IP, help="IP address used by OpenCV to read the camera TCP stream"
    )
    parser.add_argument("--pi-stream-port", type=int, default=DEFAULT_PI_STREAM_PORT)
    parser.add_argument(
        "--no-start-stream",
        action="store_true",
        help="Do not start rpicam-vid over SSH; only connect to an already running stream.",
    )
    args = parser.parse_args()

    global PI_HOST, PI_IP, PI_STREAM_PORT
    PI_HOST = args.pi_host
    PI_IP = args.pi_ip
    PI_STREAM_PORT = args.pi_stream_port

    thread = threading.Thread(target=reader_loop, args=(not args.no_start_stream,), daemon=True)
    thread.start()

    print(f"Pi wrist live proxy listening on http://{HOST}:{PORT}")
    print(f"Serving latest live frame at http://{HOST}:{PORT}/frame")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
