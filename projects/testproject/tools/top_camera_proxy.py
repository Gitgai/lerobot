#!/usr/bin/env python3
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = 8094

HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Top Camera Proxy</title>
  <style>
    :root {
      --bg: #10161d;
      --panel: #1a222b;
      --text: #eef4f8;
      --muted: #9eb0c0;
      --ok: #86efac;
      --warn: #facc15;
      --accent: #7dd3fc;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      padding: 24px;
      background: radial-gradient(circle at top, #233140 0%, var(--bg) 55%);
      color: var(--text);
      font-family: system-ui, sans-serif;
    }
    .wrap { max-width: 1100px; margin: 0 auto; display: grid; gap: 16px; }
    .panel {
      background: rgba(26, 34, 43, 0.95);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px;
      padding: 18px;
    }
    h1 { margin: 0 0 8px; font-size: 1.4rem; }
    p { margin: 0; color: var(--muted); line-height: 1.45; }
    .row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }
    button, select {
      border: 1px solid rgba(255,255,255,0.14);
      background: #0f151b;
      color: var(--text);
      border-radius: 10px;
      padding: 10px 12px;
      font: inherit;
    }
    button { cursor: pointer; }
    video {
      width: 100%;
      max-width: 100%;
      border-radius: 12px;
      background: #000;
      display: block;
    }
    .status { color: var(--muted); }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    code {
      color: var(--accent);
      font-family: ui-monospace, monospace;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <h1>Top Camera Proxy</h1>
      <p>This page uses the browser camera stack that already works for the Logitech C270 and forwards JPEG frames to a local HTTP endpoint for Pi05.</p>
    </section>
    <section class="panel row">
      <button id="start">Start Proxy</button>
      <select id="devices"></select>
      <button id="switch">Switch Camera</button>
      <span id="status" class="status">waiting</span>
    </section>
    <section class="panel row">
      <span class="status">Page loads: <strong id="serverLoads">-</strong></span>
      <span class="status">Browser uploads: <strong id="browserUploads">0</strong></span>
      <span class="status">Server frame age: <strong id="serverAge">-</strong></span>
      <span class="status">Upload error: <strong id="uploadError">-</strong></span>
    </section>
    <section class="panel">
      <p>Pi05 top-camera URL: <code>http://127.0.0.1:8094/frame</code></p>
    </section>
    <section class="panel">
      <video id="video" autoplay playsinline muted></video>
    </section>
  </div>
  <script>
    const startBtn = document.getElementById("start");
    const switchBtn = document.getElementById("switch");
    const devicesSel = document.getElementById("devices");
    const statusEl = document.getElementById("status");
    const video = document.getElementById("video");
    const canvas = document.createElement("canvas");
    let currentStream = null;
    let uploadTimer = null;
    let browserUploads = 0;

    function setStatus(text, cls = "status") {
      statusEl.textContent = text;
      statusEl.className = cls;
    }

    async function listDevices() {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cameras = devices.filter(d => d.kind === "videoinput");
      devicesSel.innerHTML = "";
      for (const cam of cameras) {
        const opt = document.createElement("option");
        opt.value = cam.deviceId;
        opt.textContent = cam.label || `Camera ${devicesSel.length + 1}`;
        devicesSel.appendChild(opt);
      }
      const preferred = cameras.find(c => /c270|logitech/i.test(c.label || ""));
      if (preferred) {
        devicesSel.value = preferred.deviceId;
      }
    }

    async function uploadFrame() {
      if (!video.videoWidth || !video.videoHeight) {
        return;
      }
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.9));
      if (!blob) {
        return;
      }
      await fetch("/upload", {
        method: "POST",
        headers: { "Content-Type": "image/jpeg" },
        body: blob,
        cache: "no-store",
      });
      browserUploads += 1;
      document.getElementById("browserUploads").textContent = String(browserUploads);
      document.getElementById("uploadError").textContent = "-";
    }

    async function refreshServerStatus() {
      try {
        const resp = await fetch("/status", { cache: "no-store" });
        const status = await resp.json();
        document.getElementById("serverAge").textContent =
          status.last_capture_age_seconds === null ? "-" : `${status.last_capture_age_seconds}s`;
        document.getElementById("serverLoads").textContent = String(status.page_load_count);
      } catch (err) {
        document.getElementById("serverAge").textContent = "offline";
      }
    }

    function startUploadLoop() {
      if (uploadTimer) {
        clearInterval(uploadTimer);
      }
      uploadTimer = setInterval(() => {
        uploadFrame().catch(err => {
          setStatus(String(err), "warn");
          document.getElementById("uploadError").textContent = String(err);
        });
      }, 250);
      setInterval(() => {
        refreshServerStatus().catch(() => {});
      }, 1000);
    }

    async function startStream(deviceId = null) {
      if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
      }
      setStatus("requesting camera...", "status");
      const constraints = {
        video: deviceId
          ? { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      currentStream = stream;
      video.srcObject = stream;
      await new Promise(resolve => {
        if (video.readyState >= 1 && video.videoWidth && video.videoHeight) {
          resolve();
          return;
        }
        video.onloadedmetadata = () => resolve();
      });
      await video.play();
      await listDevices();
      const track = stream.getVideoTracks()[0];
      const label = track ? track.label : "camera connected";
      const settings = track ? track.getSettings() : {};
      if (settings.deviceId) {
        devicesSel.value = settings.deviceId;
      }
      setStatus(`${label} ${video.videoWidth}x${video.videoHeight} -> proxying to /frame`, "ok");
      startUploadLoop();
    }

    startBtn.addEventListener("click", async () => {
      try {
        await startStream();
      } catch (err) {
        setStatus(String(err), "warn");
      }
    });

    switchBtn.addEventListener("click", async () => {
      try {
        if (!devicesSel.value) {
          await listDevices();
        }
        await startStream(devicesSel.value);
      } catch (err) {
        setStatus(String(err), "warn");
      }
    });

    navigator.mediaDevices?.addEventListener?.("devicechange", async () => {
      try {
        await listDevices();
      } catch (_err) {
      }
    });

    window.addEventListener("load", async () => {
      try {
        await fetch("/load", { method: "POST", cache: "no-store" });
        await listDevices();
        await startStream(devicesSel.value || null);
      } catch (err) {
        setStatus(String(err), "warn");
      }
    });
  </script>
</body>
</html>
"""


class FrameStore:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.jpeg_bytes: bytes | None = None
        self.updated_at = 0.0
        self.upload_count = 0
        self.last_upload_size = 0
        self.page_load_count = 0

    def put(self, data: bytes) -> None:
        with self.lock:
            self.jpeg_bytes = data
            self.updated_at = time.time()
            self.upload_count += 1
            self.last_upload_size = len(data)

    def mark_page_load(self) -> None:
        with self.lock:
            self.page_load_count += 1

    def get(self) -> tuple[bytes | None, float, int, int, int]:
        with self.lock:
            return (
                self.jpeg_bytes,
                self.updated_at,
                self.upload_count,
                self.last_upload_size,
                self.page_load_count,
            )


STORE = FrameStore()


class Handler(BaseHTTPRequestHandler):
    def _write(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed_path = urlparse(self.path).path

        if parsed_path == "/" or parsed_path.startswith("/index"):
            self._write(200, "text/html; charset=utf-8", HTML.encode())
            return

        if parsed_path.startswith("/status"):
            jpeg_bytes, updated_at, upload_count, last_upload_size, page_load_count = STORE.get()
            now = time.time()
            payload = {
                "ok": jpeg_bytes is not None,
                "last_capture_age_seconds": None if updated_at == 0 else round(now - updated_at, 2),
                "has_frame": jpeg_bytes is not None,
                "upload_count": upload_count,
                "last_upload_size": last_upload_size,
                "page_load_count": page_load_count,
            }
            self._write(200, "application/json", json.dumps(payload).encode())
            return

        if parsed_path.startswith("/frame"):
            jpeg_bytes, updated_at, _upload_count, _last_upload_size, _page_load_count = STORE.get()
            if jpeg_bytes is None:
                self._write(503, "text/plain; charset=utf-8", b"no frame uploaded yet")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Age-Seconds", f"{time.time() - updated_at:.2f}")
            self.send_header("Content-Length", str(len(jpeg_bytes)))
            self.end_headers()
            self.wfile.write(jpeg_bytes)
            return

        self._write(404, "text/plain; charset=utf-8", b"not found")

    def do_POST(self) -> None:
        parsed_path = urlparse(self.path).path

        if parsed_path.startswith("/load"):
            STORE.mark_page_load()
            self._write(200, "application/json", b'{"ok": true}')
            return

        if not parsed_path.startswith("/upload"):
            self._write(404, "text/plain; charset=utf-8", b"not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._write(400, "text/plain; charset=utf-8", b"empty body")
            return

        data = self.rfile.read(content_length)
        STORE.put(data)
        self._write(200, "application/json", b'{"ok": true}')

    def log_message(self, *_args) -> None:
        pass


if __name__ == "__main__":
    print(f"Top camera proxy listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
