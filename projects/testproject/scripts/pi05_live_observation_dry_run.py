#!/usr/bin/env python3
"""Send one real SO-101 observation to a remote Pi05 PolicyServer.

Safety boundary:
- Reads follower joint positions.
- Reads the configured laptop/OpenCV camera.
- Sends the observation to the remote policy server.
- Prints the returned action chunk.
- Never calls robot.send_action().
- Never writes returned actions to motors.
"""

from __future__ import annotations

import argparse
import json
import pickle  # nosec B403: local LeRobot async protocol uses pickle internally
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import grpc
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


def make_lerobot_features(image_shape: tuple[int, int, int]) -> dict[str, PolicyFeature]:
    hardware_features: dict[str, type | tuple[int, int, int]] = {
        **{f"{motor}.pos": float for motor in SO101_MOTORS},
        **dict.fromkeys(PI05_CAMERA_NAMES, image_shape),
    }
    return hw_to_dataset_features(hardware_features, OBS_STR, use_video=False)


def print_action_summary(timed_actions: list) -> None:
    if not timed_actions:
        print("No actions returned.")
        return

    actions = torch.stack([item.get_action() for item in timed_actions])
    print(f"received_actions: {len(timed_actions)}")
    print(f"action_tensor_shape: {tuple(actions.shape)}")
    print(f"action_dtype: {actions.dtype}")
    print(f"action_min: {actions.min().item():.6f}")
    print(f"action_max: {actions.max().item():.6f}")
    print(f"first_timestep: {timed_actions[0].get_timestep()}")
    print(f"last_timestep: {timed_actions[-1].get_timestep()}")
    print(f"first_action: {actions[0].tolist()}")


def read_live_observation(cfg: dict[str, Any], task: str) -> dict[str, Any]:
    camera_name = cfg["camera_name"]
    follower_port = cfg["follower_serial"] if Path(cfg["follower_serial"]).exists() else cfg["follower_port"]
    cameras = {
        camera_name: OpenCVCameraConfig(
            index_or_path=cfg["camera_index"],
            width=cfg["camera_width"],
            height=cfg["camera_height"],
            fps=cfg["camera_fps"],
        )
    }
    robot = SOFollower(
        SOFollowerRobotConfig(
            port=follower_port,
            id=cfg["follower_id"],
            disable_torque_on_disconnect=False,
            cameras=cameras,
        )
    )

    try:
        connect_start = time.perf_counter()
        robot.connect()
        print(f"follower_connect_s: {time.perf_counter() - connect_start:.3f}")

        obs_start = time.perf_counter()
        observation = robot.get_observation()
        print(f"live_observation_s: {time.perf_counter() - obs_start:.3f}")
    finally:
        try:
            robot.disconnect()
        except Exception as exc:
            print(f"warning_disconnect_failed: {type(exc).__name__}: {exc}")

    image = observation[camera_name]
    raw_observation = {f"{motor}.pos": float(observation[f"{motor}.pos"]) for motor in SO101_MOTORS}

    # The candidate Pi05 checkpoint expects top/front/wrist cameras. For this
    # dry run, duplicate the single laptop camera frame into all expected views.
    # This is enough to test the network/model path, not enough for real policy quality.
    for pi05_camera_name in PI05_CAMERA_NAMES:
        raw_observation[pi05_camera_name] = image

    raw_observation["task"] = task
    print("state:")
    for motor in SO101_MOTORS:
        print(f"  {motor}.pos: {raw_observation[f'{motor}.pos']:.3f}")
    print(f"camera_shape: {tuple(image.shape)}")
    return raw_observation


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
    parser.add_argument(
        "--skip-policy-setup",
        action="store_true",
        help="Skip SendPolicyInstructions when the server already has the policy loaded.",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    print("LIVE OBSERVATION DRY RUN ONLY.")
    print("This script reads follower state and camera, but does not send actions to motors.")
    print(f"server_address: {args.server_address}")
    print(f"policy: {args.policy}")
    follower_port = cfg["follower_serial"] if Path(cfg["follower_serial"]).exists() else cfg["follower_port"]
    print(f"follower_port: {follower_port}")
    print(f"camera: {cfg['camera_name']} index={cfg['camera_index']}")

    raw_observation = read_live_observation(cfg, args.task)

    image_shape = (
        cfg["camera_height"],
        cfg["camera_width"],
        3,
    )
    lerobot_features = make_lerobot_features(image_shape)
    policy_config = RemotePolicyConfig(
        policy_type=args.policy_type,
        pretrained_name_or_path=args.policy,
        lerobot_features=lerobot_features,
        actions_per_chunk=args.actions_per_chunk,
        device=args.policy_device,
    )

    channel = grpc.insecure_channel(
        args.server_address,
        grpc_channel_options(max_receive_message_length=64 * 1024 * 1024),
    )
    stub = services_pb2_grpc.AsyncInferenceStub(channel)

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

    timed_observation = TimedObservation(
        timestamp=time.time(),
        timestep=0,
        observation=raw_observation,
        must_go=True,
    )
    obs_bytes = pickle.dumps(timed_observation)  # nosec B301
    obs_iter = send_bytes_in_chunks(obs_bytes, services_pb2.Observation, log_prefix="[live observation]")
    send_start = time.perf_counter()
    stub.SendObservations(obs_iter, timeout=30)
    print(f"send_observation_ms: {(time.perf_counter() - send_start) * 1000:.2f}")

    action_start = time.perf_counter()
    response = stub.GetActions(services_pb2.Empty(), timeout=args.timeout_s)
    print(f"get_actions_s: {time.perf_counter() - action_start:.3f}")

    if not response.data:
        raise RuntimeError("PolicyServer returned an empty action response.")

    timed_actions = pickle.loads(response.data)  # nosec B301
    print_action_summary(timed_actions)
    print("LIVE_OBSERVATION_DRY_RUN_OK")


if __name__ == "__main__":
    main()
