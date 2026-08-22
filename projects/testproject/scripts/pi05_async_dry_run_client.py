#!/usr/bin/env python3
"""Dry-run LeRobot async client for Pi05.

This script talks to a LeRobot async PolicyServer and prints the returned
action chunk. It does not instantiate a robot, open serial ports, or send
actions to motors.
"""

from __future__ import annotations

import argparse
import pickle  # nosec B403: local LeRobot async protocol uses pickle internally
import time
from dataclasses import asdict

import grpc
import numpy as np
import torch

from lerobot.async_inference.helpers import RemotePolicyConfig, TimedObservation
from lerobot.transport import services_pb2, services_pb2_grpc
from lerobot.transport.utils import grpc_channel_options, send_bytes_in_chunks
from lerobot.utils.constants import OBS_STR
from lerobot.utils.feature_utils import hw_to_dataset_features

SO101_MOTORS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]


def make_lerobot_features(image_shape: tuple[int, int, int]) -> dict[str, dict]:
    hardware_features: dict[str, type | tuple[int, int, int]] = {
        **{f"{motor}.pos": float for motor in SO101_MOTORS},
        # Include all three Pi05 camera names. For dry-run they can all carry
        # the same synthetic image; real robot tests should use real views.
        "top": image_shape,
        "front": image_shape,
        "wrist": image_shape,
    }
    return hw_to_dataset_features(hardware_features, OBS_STR, use_video=False)


def make_raw_observation(width: int, height: int, task: str) -> dict:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    observation = {f"{motor}.pos": 0.0 for motor in SO101_MOTORS}
    observation.update(
        {
            "top": image,
            "front": image,
            "wrist": image,
            "task": task,
        }
    )
    return observation


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-address", default="127.0.0.1:8080")
    parser.add_argument("--policy", default="zz4321/so101_pi05")
    parser.add_argument("--policy-type", default="pi05")
    parser.add_argument("--policy-device", default="cuda")
    parser.add_argument("--actions-per-chunk", type=int, default=50)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--task", default="pick up the object")
    parser.add_argument("--timeout-s", type=float, default=240.0)
    parser.add_argument(
        "--skip-policy-setup",
        action="store_true",
        help="Skip SendPolicyInstructions when the server already has the policy loaded.",
    )
    args = parser.parse_args()

    print("DRY RUN ONLY: no robot object, no serial port, no motor commands.")
    print(f"server_address: {args.server_address}")
    print(f"policy: {args.policy}")

    channel = grpc.insecure_channel(
        args.server_address, grpc_channel_options(max_receive_message_length=64 * 1024 * 1024)
    )
    stub = services_pb2_grpc.AsyncInferenceStub(channel)

    ready_start = time.perf_counter()
    stub.Ready(services_pb2.Empty(), timeout=10)
    print(f"server_ready_ms: {(time.perf_counter() - ready_start) * 1000:.2f}")

    image_shape = (args.height, args.width, 3)
    lerobot_features = make_lerobot_features(image_shape)
    policy_config = RemotePolicyConfig(
        policy_type=args.policy_type,
        pretrained_name_or_path=args.policy,
        lerobot_features=lerobot_features,
        actions_per_chunk=args.actions_per_chunk,
        device=args.policy_device,
    )
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

    raw_observation = make_raw_observation(args.width, args.height, args.task)
    timed_observation = TimedObservation(
        timestamp=time.time(),
        timestep=0,
        observation=raw_observation,
        must_go=True,
    )
    obs_bytes = pickle.dumps(timed_observation)  # nosec B301
    obs_iter = send_bytes_in_chunks(obs_bytes, services_pb2.Observation, log_prefix="[dry-run observation]")
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
    print("ASYNC_DRY_RUN_OK")


if __name__ == "__main__":
    main()
