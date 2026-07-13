#!/usr/bin/env python3
"""Run a short faithful Pi05 action-chunk test on the real SO-101 follower.

This is different from pi05_guarded_real_action_test.py:
- It requests one action chunk from Pi05.
- It executes several actions from that same chunk in order.
- It does not clamp each action unless you explicitly ask for a robot-level
  max_relative_target.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import cv2

from pi05_guarded_real_action_test import (
    CONFIG_PATH,
    SO101_MOTORS,
    follower_port,
    load_config,
    make_robot,
    make_stub,
    maybe_make_video_writer,
    observation_for_policy,
    request_actions,
    setup_remote_policy,
    write_camera_frame,
)


def action_row(action_index: int, action) -> dict[str, float | int]:
    row: dict[str, float | int] = {"action_index": action_index}
    for motor_index, motor in enumerate(SO101_MOTORS):
        row[f"{motor}.pos"] = float(action[motor_index].item())
    return row


def tensor_action_to_robot_action(action) -> dict[str, float]:
    return {f"{motor}.pos": float(action[index].item()) for index, motor in enumerate(SO101_MOTORS)}


def read_state(robot) -> dict[str, float]:
    obs = robot.get_observation()
    return {f"{motor}.pos": float(obs[f"{motor}.pos"]) for motor in SO101_MOTORS}


def print_state(title: str, state: dict[str, float]) -> None:
    print(title)
    for motor in SO101_MOTORS:
        key = f"{motor}.pos"
        print(f"  {key}: {state[key]:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--server-address", default="127.0.0.1:8080")
    parser.add_argument("--policy", default="zz4321/so101_pi05")
    parser.add_argument("--policy-type", default="pi05")
    parser.add_argument("--policy-device", default="cuda")
    parser.add_argument("--actions-per-chunk", type=int, default=50)
    parser.add_argument("--task", default="pick up the orange and move it to another place")
    parser.add_argument("--timeout-s", type=float, default=300.0)
    parser.add_argument("--chunk-actions", type=int, default=3)
    parser.add_argument("--settle-s", type=float, default=0.5)
    parser.add_argument("--camera-fill-mode", default="top-front-wrist")
    parser.add_argument("--top-camera-url", default=None)
    parser.add_argument("--wrist-camera-url", default=None)
    parser.add_argument("--record-video", default=None)
    parser.add_argument("--record-fps", type=float, default=10.0)
    parser.add_argument("--show-camera", action="store_true")
    parser.add_argument("--action-log", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Request ONE chunk, log ALL returned actions, and do NOT move the robot. "
        "Use this to inspect the full 50-action trajectory before executing anything.",
    )
    parser.add_argument("--skip-policy-setup", action="store_true")
    parser.add_argument(
        "--robot-max-relative-target",
        type=float,
        default=None,
        help="Optional LeRobot internal relative target limit. Default None means no custom robot-level limiter.",
    )
    parser.add_argument("--i-understand-this-moves-robot", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.i_understand_this_moves_robot:
        raise RuntimeError("This moves the real robot. Pass --i-understand-this-moves-robot.")
    if args.chunk_actions <= 0:
        raise ValueError("--chunk-actions must be positive.")
    if args.chunk_actions > args.actions_per_chunk:
        raise ValueError("--chunk-actions cannot exceed --actions-per-chunk.")

    cfg = load_config(args.config)
    if args.top_camera_url is None:
        args.top_camera_url = cfg.get("top_camera_url")
    if args.wrist_camera_url is None:
        args.wrist_camera_url = cfg.get("wrist_camera_url", "http://127.0.0.1:8092/frame")

    video_path = Path(args.record_video).expanduser() if args.record_video else None
    if args.action_log is None:
        if video_path is not None:
            args.action_log = str(video_path.with_suffix(".actions.csv"))
        else:
            args.action_log = str(Path.cwd() / "pi05_dry_chunk.actions.csv")
    action_log_path = Path(args.action_log).expanduser()
    action_log_path.parent.mkdir(parents=True, exist_ok=True)

    print("FAITHFUL PI05 CHUNK TEST")
    print(f"server_address: {args.server_address}")
    print(f"policy: {args.policy}")
    print(f"follower_port: {follower_port(cfg)}")
    print(f"task: {args.task}")
    print(f"dry_run: {args.dry_run}")
    print(f"chunk_actions_to_execute: {args.chunk_actions}")
    print(f"robot_max_relative_target: {args.robot_max_relative_target}")
    print(f"camera_fill_mode: {args.camera_fill_mode}")
    print(f"record_video: {video_path}")
    print(f"action_log: {action_log_path}")
    print()

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
        robot.connect()
        before_state = read_state(robot)
        print_state("before_state:", before_state)

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
        actions = request_actions(args, raw_observation, stub, timestep=0)

        if args.dry_run:
            num_actions = int(actions.shape[0])
            with action_log_path.open("w", newline="") as f:
                fieldnames = ["phase", "action_index", *[f"{motor}.pos" for motor in SO101_MOTORS]]
                writer_csv = csv.DictWriter(f, fieldnames=fieldnames)
                writer_csv.writeheader()
                writer_csv.writerow({"phase": "before", **{"action_index": -1}, **before_state})
                for action_index in range(num_actions):
                    writer_csv.writerow({"phase": "dry_chunk", **action_row(action_index, actions[action_index])})
            print()
            print(f"DRY_RUN_OK actions_logged={num_actions}")
            print(f"action_log: {action_log_path}")
            print("NO ROBOT MOTION. Inspect the full chunk before executing.")
            return

        with action_log_path.open("w", newline="") as f:
            fieldnames = ["phase", "action_index", *[f"{motor}.pos" for motor in SO101_MOTORS]]
            writer_csv = csv.DictWriter(f, fieldnames=fieldnames)
            writer_csv.writeheader()
            writer_csv.writerow({"phase": "before", **{"action_index": -1}, **before_state})

            for action_index in range(args.chunk_actions):
                policy_action = actions[action_index]
                target = tensor_action_to_robot_action(policy_action)
                row = action_row(action_index, policy_action)
                writer_csv.writerow({"phase": "policy_action", **row})

                print()
                print(f"EXECUTING_CHUNK_ACTION {action_index + 1}/{args.chunk_actions}")
                for motor in SO101_MOTORS:
                    key = f"{motor}.pos"
                    print(f"  {key}: {target[key]:.3f}")

                sent_action = robot.send_action(target)
                writer_csv.writerow(
                    {
                        "phase": "sent_action",
                        "action_index": action_index,
                        **{f"{motor}.pos": float(sent_action[f"{motor}.pos"]) for motor in SO101_MOTORS},
                    }
                )

                settle_until = time.perf_counter() + args.settle_s
                while time.perf_counter() < settle_until:
                    observation = robot.get_observation()
                    if record_camera_name in observation:
                        write_camera_frame(observation[record_camera_name], writer, show_camera=args.show_camera)
                    time.sleep(max(1.0 / args.record_fps, 0.01))

            after_state = read_state(robot)
            writer_csv.writerow({"phase": "after", **{"action_index": args.chunk_actions}, **after_state})

        print()
        print_state("after_state:", after_state)
        print("FAITHFUL_CHUNK_TEST_OK")
    finally:
        if writer is not None:
            writer.release()
        if args.show_camera:
            cv2.destroyAllWindows()
        try:
            robot.disconnect()
        except Exception as exc:
            print(f"warning_disconnect_failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
