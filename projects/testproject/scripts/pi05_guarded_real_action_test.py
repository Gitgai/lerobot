#!/usr/bin/env python3
"""Guarded Pi05 action test for the local SO-101 follower.

Default behavior is observation-only:
- read local follower state
- read local camera
- ask the remote Pi05 PolicyServer for actions
- print the first returned action
- print the clamped action that would be sent
- do not move the robot

Motor movement requires both:
- --move-one-step or --steps greater than 0
- --i-understand-this-moves-robot
"""

from __future__ import annotations

import argparse
import json
import pickle  # nosec B403: local LeRobot async protocol uses pickle internally
import time
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

import cv2
import grpc
import numpy as np
import torch

from lerobot.async_inference.helpers import RemotePolicyConfig, TimedObservation
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from lerobot.configs import PolicyFeature
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.transport import services_pb2, services_pb2_grpc
from lerobot.transport.utils import grpc_channel_options, send_bytes_in_chunks
from lerobot.utils.constants import OBS_STR
from lerobot.utils.feature_utils import hw_to_dataset_features

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "so101.json"

SO101_MOTORS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

PI05_CAMERA_NAMES = ["top", "front", "wrist"]


def load_config(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def follower_port(cfg: dict[str, Any]) -> str:
    serial = Path(cfg["follower_serial"])
    return str(serial) if serial.exists() else cfg["follower_port"]


def build_camera_config(
    cfg: dict[str, Any],
    *,
    index_key: str,
    fourcc_key: str | None = None,
    warmup_key: str | None = None,
) -> OpenCVCameraConfig:
    warmup_s = (
        cfg.get(warmup_key, cfg.get("camera_warmup_s", 1)) if warmup_key else cfg.get("camera_warmup_s", 1)
    )
    return OpenCVCameraConfig(
        index_or_path=cfg[index_key],
        width=cfg["camera_width"],
        height=cfg["camera_height"],
        fps=cfg["camera_fps"],
        fourcc=cfg.get(fourcc_key) if fourcc_key else None,
        warmup_s=warmup_s,
    )


def camera_configs(cfg: dict[str, Any], *, only_front: bool = False) -> dict[str, OpenCVCameraConfig]:
    if only_front and "front_camera_name" in cfg and "front_camera_index" in cfg:
        return {
            cfg["front_camera_name"]: build_camera_config(
                cfg,
                index_key="front_camera_index",
                fourcc_key="front_camera_fourcc",
            )
        }

    if (
        "top_camera_name" in cfg
        and "top_camera_index" in cfg
        and "front_camera_name" in cfg
        and "front_camera_index" in cfg
    ):
        return {
            cfg["top_camera_name"]: build_camera_config(
                cfg,
                index_key="top_camera_index",
                fourcc_key="top_camera_fourcc",
                warmup_key="top_camera_warmup_s",
            ),
            cfg["front_camera_name"]: build_camera_config(
                cfg,
                index_key="front_camera_index",
                fourcc_key="front_camera_fourcc",
                warmup_key="front_camera_warmup_s",
            ),
        }

    return {
        cfg["camera_name"]: build_camera_config(
            cfg,
            index_key="camera_index",
            fourcc_key="camera_fourcc",
            warmup_key="camera_warmup_s",
        )
    }


def make_robot(
    cfg: dict[str, Any],
    *,
    with_camera: bool,
    robot_max_relative_target: float | None,
    only_front_camera: bool = False,
) -> SOFollower:
    return SOFollower(
        SOFollowerRobotConfig(
            port=follower_port(cfg),
            id=cfg["follower_id"],
            disable_torque_on_disconnect=False,
            max_relative_target=robot_max_relative_target,
            cameras=camera_configs(cfg, only_front=only_front_camera) if with_camera else {},
        )
    )


def make_lerobot_features(image_shape: tuple[int, int, int]) -> dict[str, PolicyFeature]:
    hardware_features: dict[str, type | tuple[int, int, int]] = {
        **{f"{motor}.pos": float for motor in SO101_MOTORS},
        **dict.fromkeys(PI05_CAMERA_NAMES, image_shape),
    }
    return hw_to_dataset_features(hardware_features, OBS_STR, use_video=False)


def frame_to_bgr(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def resize_rgb(image: np.ndarray, width: int, height: int) -> np.ndarray:
    if image.shape[1] == width and image.shape[0] == height:
        return image
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def fetch_remote_jpeg(url: str, timeout_s: float = 5.0) -> np.ndarray:
    with urllib.request.urlopen(url, timeout=timeout_s) as response:  # nosec B310 - lab camera proxy, http only
        data = response.read()
    image_bytes = np.frombuffer(data, dtype=np.uint8)
    bgr = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if bgr is None:
        raise RuntimeError(f"Could not decode JPEG from {url}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def maybe_make_video_writer(args: argparse.Namespace, cfg: dict[str, Any]) -> cv2.VideoWriter | None:
    if not args.record_video:
        return None

    video_path = Path(args.record_video).expanduser()
    video_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        str(video_path),
        fourcc,
        args.record_fps,
        (cfg["camera_width"], cfg["camera_height"]),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {video_path}")
    print(f"record_video: {video_path}")
    return writer


def write_camera_frame(
    frame: np.ndarray,
    writer: cv2.VideoWriter | None,
    *,
    show_camera: bool,
) -> None:
    bgr = frame_to_bgr(frame)
    if writer is not None:
        writer.write(bgr)
    if show_camera:
        cv2.imshow("SO-101 Pi05 camera", bgr)
        cv2.waitKey(1)


def record_camera_during_settle(
    robot: SOFollower,
    camera_name: str,
    writer: cv2.VideoWriter | None,
    *,
    show_camera: bool,
    duration_s: float,
    fps: float,
) -> None:
    if writer is None and not show_camera:
        time.sleep(duration_s)
        return

    if duration_s <= 0:
        return

    interval_s = 1.0 / fps
    end_time = time.perf_counter() + duration_s
    while time.perf_counter() < end_time:
        frame = robot.cameras[camera_name].read_latest()
        write_camera_frame(frame, writer, show_camera=show_camera)
        remaining_s = end_time - time.perf_counter()
        if remaining_s > 0:
            time.sleep(min(interval_s, remaining_s))


def observation_for_policy(
    cfg: dict[str, Any],
    task: str,
    robot: SOFollower | None = None,
    *,
    robot_max_relative_target: float,
    camera_fill_mode: str,
    top_camera_url: str | None = None,
    wrist_camera_url: str | None = None,
) -> dict[str, Any]:
    owns_robot = robot is None
    only_front_camera = camera_fill_mode == "top-url-front-wrist"
    if robot is None:
        robot = make_robot(
            cfg,
            with_camera=True,
            robot_max_relative_target=robot_max_relative_target,
            only_front_camera=only_front_camera,
        )
    camera_name = cfg["camera_name"]
    target_width = int(cfg["camera_width"])
    target_height = int(cfg["camera_height"])
    top_camera_name = cfg.get("top_camera_name", "top")
    front_camera_name = cfg.get("front_camera_name", cfg["camera_name"])

    try:
        if owns_robot:
            connect_start = time.perf_counter()
            robot.connect()
            print(f"follower_connect_s: {time.perf_counter() - connect_start:.3f}")

        obs_start = time.perf_counter()
        observation = robot.get_observation()
        print(f"live_observation_s: {time.perf_counter() - obs_start:.3f}")
    finally:
        if owns_robot:
            try:
                robot.disconnect()
            except Exception as exc:
                print(f"warning_disconnect_failed: {type(exc).__name__}: {exc}")

    image = resize_rgb(observation[camera_name], target_width, target_height)
    raw_observation = {f"{motor}.pos": float(observation[f"{motor}.pos"]) for motor in SO101_MOTORS}

    if camera_fill_mode == "duplicate":
        # The checkpoint expects three camera views. Until we add more cameras,
        # duplicate the single laptop camera into the expected names.
        for pi05_camera_name in PI05_CAMERA_NAMES:
            raw_observation[pi05_camera_name] = image
    elif camera_fill_mode == "front-black":
        black_image = np.zeros_like(image)
        raw_observation["top"] = black_image
        raw_observation["front"] = image
        raw_observation["wrist"] = black_image
    elif camera_fill_mode == "front-wrist":
        if not wrist_camera_url:
            raise ValueError("--wrist-camera-url is required for camera-fill-mode=front-wrist")
        wrist_image = fetch_remote_jpeg(wrist_camera_url)
        wrist_image = resize_rgb(wrist_image, image.shape[1], image.shape[0])
        black_image = np.zeros_like(image)
        raw_observation["top"] = black_image
        raw_observation["front"] = image
        raw_observation["wrist"] = wrist_image
    elif camera_fill_mode == "top-front-wrist":
        if not wrist_camera_url:
            raise ValueError("--wrist-camera-url is required for camera-fill-mode=top-front-wrist")
        top_image = resize_rgb(observation[top_camera_name], target_width, target_height)
        front_image = resize_rgb(observation[front_camera_name], target_width, target_height)
        wrist_image = fetch_remote_jpeg(wrist_camera_url)
        wrist_image = resize_rgb(wrist_image, target_width, target_height)
        raw_observation["top"] = top_image
        raw_observation["front"] = front_image
        raw_observation["wrist"] = wrist_image
    elif camera_fill_mode == "top-url-front-wrist":
        if not top_camera_url:
            raise ValueError("--top-camera-url is required for camera-fill-mode=top-url-front-wrist")
        if not wrist_camera_url:
            raise ValueError("--wrist-camera-url is required for camera-fill-mode=top-url-front-wrist")
        top_image = fetch_remote_jpeg(top_camera_url)
        top_image = resize_rgb(top_image, target_width, target_height)
        front_image = resize_rgb(observation[front_camera_name], target_width, target_height)
        wrist_image = fetch_remote_jpeg(wrist_camera_url)
        wrist_image = resize_rgb(wrist_image, target_width, target_height)
        raw_observation["top"] = top_image
        raw_observation["front"] = front_image
        raw_observation["wrist"] = wrist_image
    else:
        raise ValueError(f"Unsupported camera fill mode: {camera_fill_mode}")

    raw_observation["task"] = task
    print("observed_state:")
    for motor in SO101_MOTORS:
        print(f"  {motor}.pos: {raw_observation[f'{motor}.pos']:.3f}")
    print(f"camera_shape: {tuple(image.shape)}")
    print(f"camera_fill_mode: {camera_fill_mode}")
    if camera_fill_mode in {"front-wrist", "top-front-wrist", "top-url-front-wrist"}:
        print(f"wrist_camera_url: {wrist_camera_url}")
    if camera_fill_mode == "top-front-wrist":
        print(f"top_camera_name: {top_camera_name}")
        print(f"front_camera_name: {front_camera_name}")
    if camera_fill_mode == "top-url-front-wrist":
        print(f"top_camera_url: {top_camera_url}")
        print(f"front_camera_name: {front_camera_name}")
    return raw_observation


def make_policy_config(args: argparse.Namespace, cfg: dict[str, Any]) -> RemotePolicyConfig:
    image_shape = (
        cfg["camera_height"],
        cfg["camera_width"],
        3,
    )
    return RemotePolicyConfig(
        policy_type=args.policy_type,
        pretrained_name_or_path=args.policy,
        lerobot_features=make_lerobot_features(image_shape),
        actions_per_chunk=args.actions_per_chunk,
        device=args.policy_device,
    )


def make_stub(args: argparse.Namespace) -> services_pb2_grpc.AsyncInferenceStub:
    channel = grpc.insecure_channel(
        args.server_address,
        grpc_channel_options(max_receive_message_length=64 * 1024 * 1024),
    )
    return services_pb2_grpc.AsyncInferenceStub(channel)


def setup_remote_policy(
    args: argparse.Namespace,
    cfg: dict[str, Any],
    stub: services_pb2_grpc.AsyncInferenceStub,
) -> None:
    policy_config = make_policy_config(args, cfg)
    ready_start = time.perf_counter()
    stub.Ready(services_pb2.Empty(), timeout=10)
    print(f"server_ready_ms: {(time.perf_counter() - ready_start) * 1000:.2f}")
    print("policy_config:")
    print(asdict(policy_config))

    if args.skip_policy_setup:
        print("policy_setup_s: skipped")
    else:
        setup_start = time.perf_counter()
        stub.SendPolicyInstructions(
            services_pb2.PolicySetup(data=pickle.dumps(policy_config)),
            timeout=args.timeout_s,  # nosec B301
        )
        print(f"policy_setup_s: {time.perf_counter() - setup_start:.3f}")


def request_actions(
    args: argparse.Namespace,
    raw_observation: dict[str, Any],
    stub: services_pb2_grpc.AsyncInferenceStub,
    timestep: int,
) -> torch.Tensor:
    timed_observation = TimedObservation(
        timestamp=time.time(),
        timestep=timestep,
        observation=raw_observation,
        must_go=True,
    )
    obs_iter = send_bytes_in_chunks(
        pickle.dumps(timed_observation),  # nosec B301
        services_pb2.Observation,
        log_prefix="[guarded observation]",
    )
    send_start = time.perf_counter()
    stub.SendObservations(obs_iter, timeout=30)
    print(f"send_observation_ms: {(time.perf_counter() - send_start) * 1000:.2f}")

    action_start = time.perf_counter()
    response = stub.GetActions(services_pb2.Empty(), timeout=args.timeout_s)
    print(f"get_actions_s: {time.perf_counter() - action_start:.3f}")
    if not response.data:
        raise RuntimeError("PolicyServer returned an empty action response.")

    timed_actions = pickle.loads(response.data)  # nosec B301
    actions = torch.stack([item.get_action() for item in timed_actions])
    print(f"received_actions: {len(timed_actions)}")
    print(f"action_tensor_shape: {tuple(actions.shape)}")
    print(f"first_policy_action: {actions[0].tolist()}")
    return actions


def read_current_state(cfg: dict[str, Any], robot_max_relative_target: float) -> dict[str, float]:
    robot = make_robot(cfg, with_camera=False, robot_max_relative_target=robot_max_relative_target)
    try:
        robot.connect()
        observation = robot.get_observation()
    finally:
        try:
            robot.disconnect()
        except Exception as exc:
            print(f"warning_disconnect_failed: {type(exc).__name__}: {exc}")
    return {f"{motor}.pos": float(observation[f"{motor}.pos"]) for motor in SO101_MOTORS}


def clamp_first_action(
    current_state: dict[str, float],
    first_action: torch.Tensor,
    *,
    max_step_deg: float | None,
    gripper_max_step: float | None,
    disabled_motors: set[str],
) -> dict[str, float]:
    safe_action: dict[str, float] = {}
    for index, motor in enumerate(SO101_MOTORS):
        key = f"{motor}.pos"
        present = current_state[key]
        proposed = float(first_action[index].item())

        if motor in disabled_motors:
            target = present
        elif max_step_deg is None or gripper_max_step is None:
            target = proposed
        else:
            limit = gripper_max_step if motor == "gripper" else max_step_deg
            delta = max(min(proposed - present, limit), -limit)
            target = present + delta

        safe_action[key] = target
    return safe_action


def print_action_table(
    current_state: dict[str, float], policy_action: torch.Tensor, safe_action: dict[str, float]
) -> None:
    print()
    print("motor              current      policy_first      safe_target      safe_delta")
    print("-" * 78)
    for index, motor in enumerate(SO101_MOTORS):
        key = f"{motor}.pos"
        current = current_state[key]
        proposed = float(policy_action[index].item())
        target = safe_action[key]
        print(f"{motor:<18} {current:>9.3f} {proposed:>17.3f} {target:>16.3f} {target - current:>15.3f}")


def format_limit(value: float | None) -> str:
    return "DISABLED" if value is None else str(value)


def send_one_safe_step(
    cfg: dict[str, Any],
    safe_action: dict[str, float],
    settle_s: float,
    robot_max_relative_target: float,
) -> dict[str, float]:
    robot = make_robot(
        cfg,
        with_camera=False,
        robot_max_relative_target=robot_max_relative_target,
    )
    try:
        robot.connect()
        sent_action = robot.send_action(safe_action)
        print("sent_action:")
        for motor in SO101_MOTORS:
            print(f"  {motor}.pos: {float(sent_action[f'{motor}.pos']):.3f}")
        time.sleep(settle_s)
        after = robot.get_observation()
    finally:
        try:
            robot.disconnect()
        except Exception as exc:
            print(f"warning_disconnect_failed: {type(exc).__name__}: {exc}")
    return {f"{motor}.pos": float(after[f"{motor}.pos"]) for motor in SO101_MOTORS}


def run_multi_step(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    if not args.i_understand_this_moves_robot:
        raise RuntimeError("--steps requires --i-understand-this-moves-robot")

    stub = make_stub(args)
    setup_remote_policy(args, cfg, stub)

    writer = maybe_make_video_writer(args, cfg)
    record_camera_name = cfg.get("record_camera_name", cfg["camera_name"])
    robot = make_robot(
        cfg,
        with_camera=True,
        robot_max_relative_target=args.robot_max_relative_target,
        only_front_camera=args.camera_fill_mode == "top-url-front-wrist",
    )
    try:
        connect_start = time.perf_counter()
        robot.connect()
        print(f"follower_connect_s: {time.perf_counter() - connect_start:.3f}")

        for step in range(args.steps):
            print()
            print(f"STEP {step + 1}/{args.steps}")
            raw_observation = observation_for_policy(
                cfg,
                args.task,
                robot=robot,
                robot_max_relative_target=args.robot_max_relative_target,
                camera_fill_mode=args.camera_fill_mode,
                top_camera_url=args.top_camera_url,
                wrist_camera_url=args.wrist_camera_url,
            )
            write_camera_frame(raw_observation[record_camera_name], writer, show_camera=args.show_camera)
            actions = request_actions(args, raw_observation, stub, timestep=step)
            current_state = {f"{motor}.pos": float(raw_observation[f"{motor}.pos"]) for motor in SO101_MOTORS}
            safe_action = clamp_first_action(
                current_state,
                actions[0],
                max_step_deg=args.max_step_deg,
                gripper_max_step=args.gripper_max_step,
                disabled_motors=set(args.disable_motor),
            )
            print_action_table(current_state, actions[0], safe_action)
            sent_action = robot.send_action(safe_action)
            print("sent_action:")
            for motor in SO101_MOTORS:
                print(f"  {motor}.pos: {float(sent_action[f'{motor}.pos']):.3f}")
            record_camera_during_settle(
                robot,
                record_camera_name,
                writer,
                show_camera=args.show_camera,
                duration_s=args.settle_s,
                fps=args.record_fps,
            )
        print("GUARDED_MULTI_STEP_OK")
    finally:
        if writer is not None:
            writer.release()
        if args.show_camera:
            cv2.destroyAllWindows()
        try:
            robot.disconnect()
        except Exception as exc:
            print(f"warning_disconnect_failed: {type(exc).__name__}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--server-address", default="127.0.0.1:8080")
    parser.add_argument("--policy", default="zz4321/so101_pi05")
    parser.add_argument("--policy-type", default="pi05")
    parser.add_argument("--policy-device", default="cuda")
    parser.add_argument("--actions-per-chunk", type=int, default=50)
    parser.add_argument("--task", default="pick up the object")
    parser.add_argument("--timeout-s", type=float, default=300.0)
    parser.add_argument("--skip-policy-setup", action="store_true")
    parser.add_argument("--max-step-deg", type=float, default=1.0)
    parser.add_argument("--gripper-max-step", type=float, default=1.0)
    parser.add_argument(
        "--no-step-clamp",
        action="store_true",
        help="Disable the outer per-step clamp and send the first Pi05 action directly.",
    )
    parser.add_argument(
        "--robot-max-relative-target",
        type=float,
        default=1.0,
        help="LeRobot internal movement limiter. Capped at 5.0 for this guarded script.",
    )
    parser.add_argument(
        "--no-robot-limit",
        action="store_true",
        help="Disable LeRobot internal relative target limiting inside SOFollower.send_action.",
    )
    parser.add_argument("--settle-s", type=float, default=0.5)
    parser.add_argument("--record-video", help="Optional path to save a camera recording of the test.")
    parser.add_argument("--record-fps", type=float, default=10.0)
    parser.add_argument("--show-camera", action="store_true", help="Show a live OpenCV camera window.")
    parser.add_argument(
        "--camera-fill-mode",
        choices=["duplicate", "front-black", "front-wrist", "top-front-wrist", "top-url-front-wrist"],
        default="duplicate",
        help="How to fill Pi05 top/front/wrist camera inputs.",
    )
    parser.add_argument(
        "--top-camera-url",
        default=None,
        help="JPEG endpoint for the top camera when using --camera-fill-mode=top-url-front-wrist.",
    )
    parser.add_argument(
        "--wrist-camera-url",
        default=None,
        help="JPEG endpoint for the wrist camera when using --camera-fill-mode=front-wrist.",
    )
    parser.add_argument("--disable-motor", action="append", default=[], choices=SO101_MOTORS)
    parser.add_argument("--move-one-step", action="store_true")
    parser.add_argument("--steps", type=int, default=0)
    parser.add_argument("--i-understand-this-moves-robot", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.top_camera_url is None:
        args.top_camera_url = cfg.get("top_camera_url")
    if args.wrist_camera_url is None:
        args.wrist_camera_url = cfg.get("wrist_camera_url", "http://127.0.0.1:8092/frame")

    if args.no_step_clamp or args.no_robot_limit:
        print("RAWER PI05 REAL-ACTION TEST.")
    else:
        print("GUARDED PI05 REAL-ACTION TEST.")
    print(f"server_address: {args.server_address}")
    print(f"policy: {args.policy}")
    print(f"follower_port: {follower_port(cfg)}")
    print(
        f"front camera: {cfg.get('front_camera_name', cfg['camera_name'])} index={cfg.get('front_camera_index', cfg['camera_index'])}"
    )
    if "top_camera_name" in cfg and "top_camera_index" in cfg:
        print(f"top camera: {cfg['top_camera_name']} index={cfg['top_camera_index']}")
    if args.no_step_clamp:
        args.max_step_deg = None
        args.gripper_max_step = None
    if args.no_robot_limit:
        args.robot_max_relative_target = None

    print(f"max_step_deg: {format_limit(args.max_step_deg)}")
    print(f"gripper_max_step: {format_limit(args.gripper_max_step)}")
    print(f"robot_max_relative_target: {format_limit(args.robot_max_relative_target)}")
    print(f"camera_fill_mode: {args.camera_fill_mode}")
    print(f"disabled_motors: {args.disable_motor}")
    print()

    if args.max_step_deg is not None and args.max_step_deg <= 0:
        raise ValueError("Step limits must be positive.")
    if args.gripper_max_step is not None and args.gripper_max_step <= 0:
        raise ValueError("Step limits must be positive.")
    if args.robot_max_relative_target is not None and args.robot_max_relative_target <= 0:
        raise ValueError("--robot-max-relative-target must be positive.")
    if args.robot_max_relative_target is not None and args.robot_max_relative_target > 5:
        raise ValueError("--robot-max-relative-target is capped at 5 for this guarded script.")
    if args.steps < 0:
        raise ValueError("--steps must be zero or positive.")
    if args.steps > 0 and args.move_one_step:
        raise ValueError("Use either --steps or --move-one-step, not both.")
    if args.steps > 0:
        run_multi_step(args, cfg)
        return

    raw_observation = observation_for_policy(
        cfg,
        args.task,
        robot_max_relative_target=args.robot_max_relative_target,
        camera_fill_mode=args.camera_fill_mode,
        top_camera_url=args.top_camera_url,
        wrist_camera_url=args.wrist_camera_url,
    )
    stub = make_stub(args)
    setup_remote_policy(args, cfg, stub)
    actions = request_actions(args, raw_observation, stub, timestep=0)

    current_state = read_current_state(cfg, args.robot_max_relative_target)
    safe_action = clamp_first_action(
        current_state,
        actions[0],
        max_step_deg=args.max_step_deg,
        gripper_max_step=args.gripper_max_step,
        disabled_motors=set(args.disable_motor),
    )
    print_action_table(current_state, actions[0], safe_action)

    if not args.move_one_step:
        print()
        print("NO_MOVE_MODE: computed safe one-step action, but did not send it.")
        print("To move one tiny step, rerun with:")
        print("  --move-one-step --i-understand-this-moves-robot")
        return

    if not args.i_understand_this_moves_robot:
        raise RuntimeError("--move-one-step requires --i-understand-this-moves-robot")

    print()
    print("MOVING_ONE_SAFE_STEP_NOW")
    after_state = send_one_safe_step(
        cfg,
        safe_action,
        args.settle_s,
        args.robot_max_relative_target,
    )
    print()
    print("after_state:")
    for motor in SO101_MOTORS:
        key = f"{motor}.pos"
        print(
            f"  {key}: {after_state[key]:.3f}  delta_from_before={after_state[key] - current_state[key]:.3f}"
        )
    print("GUARDED_ONE_STEP_OK")


if __name__ == "__main__":
    main()
