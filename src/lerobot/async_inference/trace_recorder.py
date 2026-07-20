# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import subprocess
import threading
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np
import PIL.Image
import torch

from lerobot.robots.robot import Robot

from .configs import RobotClientConfig
from .helpers import TimedAction, TimedObservation

logger = logging.getLogger(__name__)


class AsyncClientTraceRecorder:
    """Read-only trace recorder for async robot_client diagnostics."""

    def __init__(self, trace_dir: str | Path):
        self.trace_dir = Path(trace_dir).expanduser()
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.trace_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._files: dict[str, Any] = {}
        self._disabled = False

        self.record_event("trace_started", {"timestamp": time.time(), "trace_dir": str(self.trace_dir)})

    def record_manifest(
        self,
        config: RobotClientConfig,
        robot: Robot,
        lerobot_features: dict[str, dict],
    ) -> None:
        try:
            robot_config = asdict(config.robot) if is_dataclass(config.robot) else str(config.robot)
            manifest = {
                "kind": "manifest",
                "created_at_unix": time.time(),
                "trace_dir": str(self.trace_dir),
                "git": self._git_metadata(),
                "client": self._to_jsonable(config.to_dict()),
                "robot": {
                    "type": getattr(config.robot, "type", type(config.robot).__name__),
                    "id": getattr(config.robot, "id", None),
                    "port": getattr(config.robot, "port", None),
                    "max_relative_target": getattr(config.robot, "max_relative_target", None),
                    "config": self._to_jsonable(robot_config),
                    "observation_features": self._to_jsonable(robot.observation_features),
                    "action_features": list(robot.action_features),
                    "lerobot_features": self._to_jsonable(lerobot_features),
                },
            }
            self._write_json_file("manifest.json", manifest)
        except Exception as exc:
            self._disable_after_error(exc)

    def record_event(self, event: str, payload: dict[str, Any] | None = None) -> None:
        record = {"kind": "event", "event": event, "timestamp": time.time()}
        if payload:
            record.update(self._to_jsonable(payload))
        self._write_jsonl("events.jsonl", record)

    def record_observation(
        self,
        observation: TimedObservation,
        *,
        latest_action: int,
        queue_size: int,
    ) -> None:
        if self._disabled:
            return
        try:
            raw_observation = observation.get_observation()
            timestamp_ns = time.time_ns()
            images: dict[str, Any] = {}
            state: dict[str, Any] = {}

            for key, value in raw_observation.items():
                if self._is_image_value(value):
                    image_info = self._save_image(
                        key=key,
                        image=value,
                        prefix=f"obs_{observation.get_timestep():06d}_{timestamp_ns}",
                    )
                    images[key] = image_info
                elif key != "task":
                    state[key] = self._to_jsonable(value)

            record = {
                "kind": "observation",
                "timestep": observation.get_timestep(),
                "client_timestamp": observation.get_timestamp(),
                "recorded_at_unix": time.time(),
                "must_go": observation.must_go,
                "latest_action": latest_action,
                "queue_size": queue_size,
                "task": raw_observation.get("task"),
                "state": state,
                "images": images,
            }
            self._write_jsonl("observations.jsonl", record)
        except Exception as exc:
            self._disable_after_error(exc)

    def record_action_chunk(
        self,
        timed_actions: list[TimedAction],
        *,
        action_names: list[str],
        receive_time: float,
        deserialize_time_s: float,
        queue_update_time_s: float,
        latest_action: int,
        old_queue_size: int,
        old_queue_timesteps: list[int],
        new_queue_size: int,
        new_queue_timesteps: list[int],
        aggregate_fn_name: str,
    ) -> None:
        if self._disabled or not timed_actions:
            return
        try:
            actions = [self._tensor_to_list(action.get_action()) for action in timed_actions]
            record = {
                "kind": "action_chunk",
                "received_at_unix": receive_time,
                "action_count": len(timed_actions),
                "chunk_start_timestep": timed_actions[0].get_timestep(),
                "chunk_end_timestep": timed_actions[-1].get_timestep(),
                "first_action_server_timestamp": timed_actions[0].get_timestamp(),
                "server_to_client_latency_ms": (receive_time - timed_actions[0].get_timestamp()) * 1000,
                "action_names": action_names,
                "actions": actions,
                "summary": self._action_summary(actions, action_names),
                "client_queue": {
                    "latest_action_before_update": latest_action,
                    "old_size": old_queue_size,
                    "old_timesteps": old_queue_timesteps,
                    "new_size": new_queue_size,
                    "new_timesteps": new_queue_timesteps,
                    "aggregate_fn_name": aggregate_fn_name,
                },
                "timing_ms": {
                    "deserialize": deserialize_time_s * 1000,
                    "queue_update": queue_update_time_s * 1000,
                },
            }
            self._write_jsonl("action_chunks.jsonl", record)
        except Exception as exc:
            self._disable_after_error(exc)

    def record_executed_action(
        self,
        timed_action: TimedAction,
        *,
        requested_action: dict[str, float],
        performed_action: dict[str, float],
        queue_size_after_pop: int,
        pop_time_s: float,
    ) -> None:
        if self._disabled:
            return
        try:
            record = {
                "kind": "executed_action",
                "recorded_at_unix": time.time(),
                "action_timestamp": timed_action.get_timestamp(),
                "action_timestep": timed_action.get_timestep(),
                "requested_action": self._to_jsonable(requested_action),
                "performed_action": self._to_jsonable(performed_action),
                "queue_size_after_pop": queue_size_after_pop,
                "pop_time_ms": pop_time_s * 1000,
            }
            self._write_jsonl("executed_actions.jsonl", record)
        except Exception as exc:
            self._disable_after_error(exc)

    def close(self) -> None:
        try:
            self.record_event("trace_closed", {"timestamp": time.time()})
        finally:
            with self._lock:
                for handle in self._files.values():
                    handle.close()
                self._files.clear()

    def _write_json_file(self, relative_path: str, payload: dict[str, Any]) -> None:
        if self._disabled:
            return
        try:
            path = self.trace_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                json.dump(self._to_jsonable(payload), handle, indent=2, sort_keys=True)
                handle.write("\n")
        except Exception as exc:
            self._disable_after_error(exc)

    def _write_jsonl(self, relative_path: str, payload: dict[str, Any]) -> None:
        if self._disabled:
            return
        try:
            with self._lock:
                handle = self._files.get(relative_path)
                if handle is None:
                    path = self.trace_dir / relative_path
                    path.parent.mkdir(parents=True, exist_ok=True)
                    handle = path.open("a", encoding="utf-8", buffering=1)
                    self._files[relative_path] = handle
                handle.write(json.dumps(self._to_jsonable(payload), sort_keys=True) + "\n")
        except Exception as exc:
            self._disable_after_error(exc)

    def _disable_after_error(self, exc: Exception) -> None:
        if not self._disabled:
            logger.exception("Disabling async trace recorder after write error: %s", exc)
        self._disabled = True

    def _save_image(self, *, key: str, image: Any, prefix: str) -> dict[str, Any]:
        np_image = self._to_numpy(image)
        shape = list(np_image.shape)
        dtype = str(np_image.dtype)
        if np_image.ndim == 3 and np_image.shape[0] == 3 and np_image.shape[-1] != 3:
            np_image = np_image.transpose(1, 2, 0)

        safe_key = self._safe_name(key)
        camera_dir = self.images_dir / safe_key
        camera_dir.mkdir(parents=True, exist_ok=True)
        relative_path = Path("images") / safe_key / f"{prefix}_{safe_key}.jpg"
        path = self.trace_dir / relative_path

        # Camera frames are RGB by default in OpenCVCameraConfig.
        PIL.Image.fromarray(np_image.astype(np.uint8)).save(path, quality=85)
        return {
            "path": str(relative_path),
            "shape": shape,
            "dtype": dtype,
        }

    @staticmethod
    def _safe_name(value: str) -> str:
        return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value))

    @staticmethod
    def _is_image_value(value: Any) -> bool:
        try:
            shape = tuple(value.shape)
        except AttributeError:
            return False
        if len(shape) != 3:
            return False
        return shape[-1] in {1, 3, 4} or shape[0] in {1, 3, 4}

    @staticmethod
    def _to_numpy(value: Any) -> np.ndarray:
        if isinstance(value, torch.Tensor):
            value = value.detach().cpu().numpy()
        return np.asarray(value).copy()

    def _tensor_to_list(self, value: torch.Tensor) -> list[float]:
        return [float(x) for x in value.detach().cpu().flatten().tolist()]

    def _action_summary(self, actions: list[list[float]], action_names: list[str]) -> dict[str, Any]:
        if not actions:
            return {}
        action_array = np.asarray(actions, dtype=float)
        summary: dict[str, Any] = {}
        for idx, name in enumerate(action_names[: action_array.shape[1]]):
            values = action_array[:, idx]
            summary[name] = {
                "first": float(values[0]),
                "last": float(values[-1]),
                "min": float(values.min()),
                "max": float(values.max()),
            }
        return summary

    def _to_jsonable(self, value: Any) -> Any:
        if value is None or isinstance(value, str | int | float | bool):
            return value
        if isinstance(value, Path):
            return str(value)
        if is_dataclass(value):
            return self._to_jsonable(asdict(value))
        if isinstance(value, dict):
            return {str(k): self._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._to_jsonable(v) for v in value]
        if isinstance(value, torch.Tensor):
            value = value.detach().cpu()
            if value.numel() <= 256:
                return value.tolist()
            return {"shape": list(value.shape), "dtype": str(value.dtype)}
        if isinstance(value, np.ndarray):
            if value.size <= 256:
                return value.tolist()
            return {"shape": list(value.shape), "dtype": str(value.dtype)}
        return str(value)

    @staticmethod
    def _git_metadata() -> dict[str, Any]:
        def run_git_command(args: list[str]) -> str | None:
            try:
                result = subprocess.run(
                    ["git", *args],
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=2,
                )
            except Exception:
                return None
            if result.returncode != 0:
                return None
            return result.stdout.strip()

        return {
            "commit": run_git_command(["rev-parse", "HEAD"]),
            "status_short": run_git_command(["status", "--short"]),
        }
