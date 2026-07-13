#!/usr/bin/env python3
"""HTTPCamera: a LeRobot camera that pulls JPEG frames from an HTTP endpoint.

This lets `lerobot-record` (and any LeRobot tool) treat a remote camera that is
served over HTTP — like the Raspberry Pi wrist camera proxy (:8092) and the
Logitech C270 top-camera proxy (:8094) — as a normal robot camera. Each frame is
a single JPEG fetched with an HTTP GET, exactly how the Pi05 eval scripts already
fetch them (`fetch_remote_jpeg`), so the recorded dataset matches deployment.

Registered as camera type ``http``. Import this module before parsing a config
that references ``type: http`` so the choice is registered with draccus:

    {wrist: {type: http, url: "http://127.0.0.1:8092/frame", width: 640, height: 480, fps: 30}}

Mirrors the structure of lerobot.cameras.zmq.ZMQCamera (background read thread).
"""

from __future__ import annotations

import logging
import time
import urllib.request
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from lerobot.cameras.camera import Camera
from lerobot.cameras.configs import CameraConfig, ColorMode
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected
from lerobot.utils.errors import DeviceNotConnectedError

logger = logging.getLogger(__name__)


@CameraConfig.register_subclass("http")
@dataclass
class HTTPCameraConfig(CameraConfig):
    """Config for a camera served as single JPEG frames over HTTP GET.

    url: endpoint returning one JPEG per GET (e.g. http://127.0.0.1:8092/frame).
    """

    url: str = ""
    color_mode: ColorMode = ColorMode.RGB
    timeout_ms: int = 5000
    warmup_s: int = 1

    def __post_init__(self) -> None:
        self.color_mode = ColorMode(self.color_mode)
        if not self.url:
            raise ValueError("`url` cannot be empty for an http camera.")
        if self.timeout_ms <= 0:
            raise ValueError(f"`timeout_ms` must be positive, but {self.timeout_ms} is provided.")


class HTTPCamera(Camera):
    """Camera that fetches JPEG frames from an HTTP endpoint via a background thread."""

    def __init__(self, config: HTTPCameraConfig):
        super().__init__(config)
        self.config = config
        self.url = config.url
        self.color_mode = config.color_mode
        self.timeout_s = config.timeout_ms / 1000.0
        self._connected = False

        self.thread: Thread | None = None
        self.stop_event: Event | None = None
        self.frame_lock: Lock = Lock()
        self.latest_frame: NDArray[Any] | None = None
        self.latest_timestamp: float | None = None
        self.new_frame_event: Event = Event()

    def __str__(self) -> str:
        return f"HTTPCamera({self.url})"

    @property
    def is_connected(self) -> bool:
        return self._connected and self.thread is not None and self.thread.is_alive()

    @staticmethod
    def find_cameras() -> list[dict[str, Any]]:
        raise NotImplementedError("Camera detection is not implemented for HTTP cameras.")

    def _read_from_hardware(self) -> NDArray[Any]:
        """GET one JPEG, decode it, and return an RGB (or BGR) frame at the configured size."""
        with urllib.request.urlopen(self.url, timeout=self.timeout_s) as response:  # nosec B310
            data = response.read()
        bgr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            raise RuntimeError(f"{self} failed to decode JPEG from {self.url}")
        frame = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB) if self.color_mode == ColorMode.RGB else bgr
        if self.width and self.height and (frame.shape[1] != self.width or frame.shape[0] != self.height):
            frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_AREA)
        return frame

    @check_if_already_connected
    def connect(self, warmup: bool = True) -> None:
        logger.info(f"Connecting to {self}...")
        try:
            # Auto-detect resolution if not provided.
            temp = self._read_from_hardware()
            if self.height is None or self.width is None:
                self.height, self.width = temp.shape[:2]
                logger.info(f"{self} resolution detected: {self.width}x{self.height}")
            self._connected = True
            self._start_read_thread()

            if warmup:
                start = time.time()
                while time.time() - start < self.config.warmup_s:
                    try:
                        self.async_read(timeout_ms=self.config.warmup_s * 1000)
                    except TimeoutError:
                        pass
                    time.sleep(0.05)
                with self.frame_lock:
                    if self.latest_frame is None:
                        raise ConnectionError(f"{self} failed to capture frames during warmup.")
            logger.info(f"{self} connected.")
        except Exception as e:
            self._connected = False
            raise RuntimeError(f"Failed to connect to {self}: {e}") from e

    def _read_loop(self) -> None:
        assert self.stop_event is not None
        interval = 1.0 / self.fps if self.fps else 0.03
        failure_count = 0
        while not self.stop_event.is_set():
            loop_start = time.perf_counter()
            try:
                frame = self._read_from_hardware()
                with self.frame_lock:
                    self.latest_frame = frame
                    self.latest_timestamp = time.perf_counter()
                self.new_frame_event.set()
                failure_count = 0
            except Exception as e:  # noqa: BLE001
                if failure_count <= 10:
                    failure_count += 1
                    logger.warning(f"{self} read error: {e}")
                else:
                    raise RuntimeError(f"{self} exceeded maximum consecutive read failures.") from e
            sleep_s = interval - (time.perf_counter() - loop_start)
            if sleep_s > 0:
                time.sleep(sleep_s)

    def _start_read_thread(self) -> None:
        if self.stop_event is not None:
            self.stop_event.set()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        with self.frame_lock:
            self.latest_frame = None
            self.latest_timestamp = None
            self.new_frame_event.clear()
        self.stop_event = Event()
        self.thread = Thread(target=self._read_loop, daemon=True, name=f"{self}_read_loop")
        self.thread.start()
        time.sleep(0.1)

    def _stop_read_thread(self) -> None:
        if self.stop_event is not None:
            self.stop_event.set()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.thread = None
        self.stop_event = None

    @check_if_not_connected
    def read(self, color_mode: ColorMode | None = None) -> NDArray[Any]:
        if self.thread is None or not self.thread.is_alive():
            raise RuntimeError(f"{self} read thread is not running.")
        self.new_frame_event.clear()
        return self.async_read(timeout_ms=10000)

    @check_if_not_connected
    def async_read(self, timeout_ms: float = 200) -> NDArray[Any]:
        if self.thread is None or not self.thread.is_alive():
            raise RuntimeError(f"{self} read thread is not running.")
        if not self.new_frame_event.wait(timeout=timeout_ms / 1000.0):
            raise TimeoutError(f"{self} async_read timeout after {timeout_ms}ms")
        with self.frame_lock:
            frame = self.latest_frame
            self.new_frame_event.clear()
        if frame is None:
            raise RuntimeError(f"{self} no frame available")
        return frame

    @check_if_not_connected
    def read_latest(self, max_age_ms: int = 1000) -> NDArray[Any]:
        if self.thread is None or not self.thread.is_alive():
            raise RuntimeError(f"{self} read thread is not running.")
        with self.frame_lock:
            frame = self.latest_frame
            timestamp = self.latest_timestamp
        if frame is None or timestamp is None:
            raise RuntimeError(f"{self} has not captured any frames yet.")
        age_ms = (time.perf_counter() - timestamp) * 1e3
        if age_ms > max_age_ms:
            raise TimeoutError(f"{self} latest frame is too old: {age_ms:.1f} ms (max {max_age_ms} ms).")
        return frame

    def disconnect(self) -> None:
        if self.thread is None and not self._connected:
            raise DeviceNotConnectedError(f"{self} not connected.")
        self._stop_read_thread()
        self._connected = False
        with self.frame_lock:
            self.latest_frame = None
            self.latest_timestamp = None
            self.new_frame_event.clear()
        logger.info(f"{self} disconnected.")
