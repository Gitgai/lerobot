#!/usr/bin/env python3
"""Test 2: safe CLOSED-LOOP Pi05 evaluation on the real SO-101 follower.

This runs Pi05 the way it is designed to run:

    loop:
      observe (state + top/front/wrist cameras)
      ask Pi05 for a 50-action chunk
      execute the first K actions of that chunk
      re-observe and ask again
    until success / max-steps / human stop

Safety model (read this):
  - --robot-max-relative-target is a SAFETY GUARD only. It caps how far any single
    send can move a joint, so a bad action cannot slam the arm. It does NOT steer
    the arm toward the orange or "help" it grasp. If Pi05 can pick, it picks within
    the guard; if it cannot, the guard just makes the failure safe to watch.
  - There is NO outer behaviour-shaping clamp. The raw Pi05 action is sent; only the
    robot-level relative-target guard limits per-step magnitude.
  - Keep a hand on the power/e-stop the entire run.

Nothing moves unless you pass --i-understand-this-moves-robot.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import cv2
import numpy as np
from pi05_guarded_real_action_test import (
    CONFIG_PATH,
    SO101_MOTORS,
    fetch_remote_jpeg,
    follower_port,
    frame_to_bgr,
    load_config,
    make_robot,
    make_stub,
    observation_for_policy,
    request_actions,
    resize_rgb,
    setup_remote_policy,
    write_camera_frame,
)


def tensor_action_to_robot_action(action) -> dict[str, float]:
    return {f"{motor}.pos": float(action[index].item()) for index, motor in enumerate(SO101_MOTORS)}


def read_state(robot) -> dict[str, float]:
    obs = robot.get_observation()
    return {f"{motor}.pos": float(obs[f"{motor}.pos"]) for motor in SO101_MOTORS}


def print_state(title: str, state: dict[str, float]) -> None:
    print(title)
    for motor in SO101_MOTORS:
        print(f"  {motor}.pos: {state[f'{motor}.pos']:.3f}")


def make_video_writer(path: Path, width: int, height: int, fps: float) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {path}")
    print(f"record_video: {path}")
    return writer


def make_mosaic(raw_observation: dict[str, object]) -> np.ndarray:
    missing = [camera for camera in ("top", "front", "wrist") if camera not in raw_observation]
    if missing:
        raise KeyError(f"Cannot record mosaic; missing camera(s): {', '.join(missing)}")

    frames = []
    for name in ("top", "front", "wrist"):
        frame = np.asarray(raw_observation[name])
        bgr = frame_to_bgr(frame)
        cv2.putText(bgr, name, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(bgr, name, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        frames.append(bgr)
    return np.concatenate(frames, axis=1)


def write_eval_frame(
    raw_observation: dict[str, object],
    writer: cv2.VideoWriter | None,
    *,
    show_camera: bool,
    record_layout: str,
    record_camera_name: str,
) -> None:
    if writer is None and not show_camera:
        return

    if record_layout == "mosaic":
        bgr = make_mosaic(raw_observation)
        if writer is not None:
            writer.write(bgr)
        if show_camera:
            cv2.imshow("SO-101 Pi05 top/front/wrist", bgr)
            cv2.waitKey(1)
        return

    write_camera_frame(np.asarray(raw_observation[record_camera_name]), writer, show_camera=show_camera)


def raw_observation_from_existing_robot_obs(
    cfg: dict,
    task: str,
    robot_obs: dict,
    *,
    camera_fill_mode: str,
    top_camera_url: str | None,
    wrist_camera_url: str | None,
) -> dict[str, object]:
    target_width = int(cfg["camera_width"])
    target_height = int(cfg["camera_height"])
    camera_name = cfg["camera_name"]
    top_camera_name = cfg.get("top_camera_name", "top")
    front_camera_name = cfg.get("front_camera_name", cfg["camera_name"])

    image = resize_rgb(robot_obs[camera_name], target_width, target_height)
    raw_observation: dict[str, object] = {
        f"{motor}.pos": float(robot_obs[f"{motor}.pos"]) for motor in SO101_MOTORS
    }

    if camera_fill_mode == "duplicate":
        raw_observation["top"] = image
        raw_observation["front"] = image
        raw_observation["wrist"] = image
    elif camera_fill_mode == "front-black":
        black_image = np.zeros_like(image)
        raw_observation["top"] = black_image
        raw_observation["front"] = image
        raw_observation["wrist"] = black_image
    elif camera_fill_mode == "front-wrist":
        if not wrist_camera_url:
            raise ValueError("--wrist-camera-url is required for camera-fill-mode=front-wrist")
        wrist_image = fetch_remote_jpeg(wrist_camera_url)
        raw_observation["top"] = np.zeros_like(image)
        raw_observation["front"] = image
        raw_observation["wrist"] = resize_rgb(wrist_image, target_width, target_height)
    elif camera_fill_mode == "top-front-wrist":
        if not wrist_camera_url:
            raise ValueError("--wrist-camera-url is required for camera-fill-mode=top-front-wrist")
        raw_observation["top"] = resize_rgb(robot_obs[top_camera_name], target_width, target_height)
        raw_observation["front"] = resize_rgb(robot_obs[front_camera_name], target_width, target_height)
        raw_observation["wrist"] = resize_rgb(
            fetch_remote_jpeg(wrist_camera_url), target_width, target_height
        )
    elif camera_fill_mode == "top-url-front-wrist":
        if not top_camera_url:
            raise ValueError("--top-camera-url is required for camera-fill-mode=top-url-front-wrist")
        if not wrist_camera_url:
            raise ValueError("--wrist-camera-url is required for camera-fill-mode=top-url-front-wrist")
        raw_observation["top"] = resize_rgb(fetch_remote_jpeg(top_camera_url), target_width, target_height)
        raw_observation["front"] = resize_rgb(robot_obs[front_camera_name], target_width, target_height)
        raw_observation["wrist"] = resize_rgb(
            fetch_remote_jpeg(wrist_camera_url), target_width, target_height
        )
    else:
        raise ValueError(f"Unsupported camera fill mode: {camera_fill_mode}")

    raw_observation["task"] = task
    return raw_observation


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--server-address", default="127.0.0.1:8080")
    parser.add_argument("--policy", default="zz4321/so101_pi05")
    parser.add_argument("--policy-type", default="pi05")
    parser.add_argument("--policy-device", default="cuda")
    parser.add_argument("--actions-per-chunk", type=int, default=50)
    parser.add_argument("--task", default="pick up the orange and move it to another place")
    parser.add_argument("--timeout-s", type=float, default=600.0)
    parser.add_argument(
        "--actions-per-query",
        type=int,
        default=10,
        help="How many chunk actions to execute before re-observing and re-querying Pi05.",
    )
    parser.add_argument("--max-steps", type=int, default=150, help="Total send_action steps before stopping.")
    parser.add_argument(
        "--robot-max-relative-target",
        type=float,
        default=8.0,
        help="SAFETY GUARD: max per-send joint move (deg). Caps slams; does not steer behaviour.",
    )
    parser.add_argument(
        "--settle-s", type=float, default=0.15, help="Pause after each send (lets the arm move)."
    )
    parser.add_argument("--camera-fill-mode", default="top-url-front-wrist")
    parser.add_argument("--top-camera-url", default=None)
    parser.add_argument("--wrist-camera-url", default=None)
    parser.add_argument("--record-video", required=True)
    parser.add_argument("--record-fps", type=float, default=10.0)
    parser.add_argument(
        "--record-layout",
        choices=["mosaic", "single"],
        default="mosaic",
        help="Video layout. 'mosaic' records top/front/wrist; 'single' keeps the old one-camera video.",
    )
    parser.add_argument("--show-camera", action="store_true")
    parser.add_argument("--action-log", default=None)
    parser.add_argument("--skip-policy-setup", action="store_true")
    parser.add_argument("--i-understand-this-moves-robot", action="store_true")
    args = parser.parse_args()

    if not args.i_understand_this_moves_robot:
        raise RuntimeError("This MOVES the real robot. Pass --i-understand-this-moves-robot.")
    if args.actions_per_query <= 0 or args.actions_per_query > args.actions_per_chunk:
        raise ValueError("--actions-per-query must be in 1..actions_per_chunk.")
    if args.robot_max_relative_target is not None and args.robot_max_relative_target <= 0:
        raise ValueError("--robot-max-relative-target must be positive (it is a safety guard).")

    cfg = load_config(args.config)
    if args.top_camera_url is None:
        args.top_camera_url = cfg.get("top_camera_url")
    if args.wrist_camera_url is None:
        args.wrist_camera_url = cfg.get("wrist_camera_url", "http://127.0.0.1:8092/frame")

    video_path = Path(args.record_video).expanduser()
    if args.action_log is None:
        args.action_log = str(video_path.with_suffix(".actions.csv"))
    action_log_path = Path(args.action_log).expanduser()
    action_log_path.parent.mkdir(parents=True, exist_ok=True)

    print("CLOSED-LOOP PI05 EVAL (Test 2)")
    print(f"server_address: {args.server_address}")
    print(f"policy: {args.policy}")
    print(f"follower_port: {follower_port(cfg)}")
    print(f"task: {args.task}")
    print(f"actions_per_query (K): {args.actions_per_query}")
    print(f"max_steps: {args.max_steps}")
    print(f"safety_guard_max_relative_target_deg: {args.robot_max_relative_target}")
    print(f"camera_fill_mode: {args.camera_fill_mode}")
    print(f"record_layout: {args.record_layout}")
    print(f"record_video: {video_path}")
    print(f"action_log: {action_log_path}")
    print()

    stub = make_stub(args)
    setup_remote_policy(args, cfg, stub)

    video_width = int(cfg["camera_width"]) * (3 if args.record_layout == "mosaic" else 1)
    video_height = int(cfg["camera_height"])
    writer = make_video_writer(video_path, video_width, video_height, args.record_fps)
    record_camera_name = cfg.get("record_camera_name", cfg["camera_name"])
    robot = make_robot(
        cfg,
        with_camera=True,
        robot_max_relative_target=args.robot_max_relative_target,
        only_front_camera=args.camera_fill_mode == "top-url-front-wrist",
    )

    step = 0
    query = 0
    try:
        robot.connect()
        before_state = read_state(robot)
        print_state("before_state:", before_state)
        print()

        with action_log_path.open("w", newline="") as f:
            fieldnames = ["phase", "query", "step", "action_in_chunk", *[f"{m}.pos" for m in SO101_MOTORS]]
            writer_csv = csv.DictWriter(f, fieldnames=fieldnames)
            writer_csv.writeheader()
            writer_csv.writerow(
                {"phase": "before", "query": -1, "step": -1, "action_in_chunk": -1, **before_state}
            )

            while step < args.max_steps:
                raw_observation = observation_for_policy(
                    cfg,
                    args.task,
                    robot=robot,
                    robot_max_relative_target=args.robot_max_relative_target,
                    camera_fill_mode=args.camera_fill_mode,
                    top_camera_url=args.top_camera_url,
                    wrist_camera_url=args.wrist_camera_url,
                )
                write_eval_frame(
                    raw_observation,
                    writer,
                    show_camera=args.show_camera,
                    record_layout=args.record_layout,
                    record_camera_name=record_camera_name,
                )
                actions = request_actions(args, raw_observation, stub, timestep=query)

                k_this = min(args.actions_per_query, actions.shape[0])
                print(f"QUERY {query}: executing {k_this} actions (step {step}..{step + k_this - 1})")
                for k in range(k_this):
                    if step >= args.max_steps:
                        break
                    policy_action = actions[k]
                    target = tensor_action_to_robot_action(policy_action)
                    writer_csv.writerow(
                        {
                            "phase": "commanded",
                            "query": query,
                            "step": step,
                            "action_in_chunk": k,
                            **{
                                f"{m}.pos": float(policy_action[i].item()) for i, m in enumerate(SO101_MOTORS)
                            },
                        }
                    )
                    sent_action = robot.send_action(target)
                    writer_csv.writerow(
                        {
                            "phase": "sent",
                            "query": query,
                            "step": step,
                            "action_in_chunk": k,
                            **{f"{m}.pos": float(sent_action[f"{m}.pos"]) for m in SO101_MOTORS},
                        }
                    )

                    settle_until = time.perf_counter() + args.settle_s
                    while time.perf_counter() < settle_until:
                        obs = robot.get_observation()
                        video_observation = raw_observation_from_existing_robot_obs(
                            cfg,
                            args.task,
                            obs,
                            camera_fill_mode=args.camera_fill_mode,
                            top_camera_url=args.top_camera_url,
                            wrist_camera_url=args.wrist_camera_url,
                        )
                        write_eval_frame(
                            video_observation,
                            writer,
                            show_camera=args.show_camera,
                            record_layout=args.record_layout,
                            record_camera_name=record_camera_name,
                        )
                        time.sleep(max(1.0 / args.record_fps, 0.01))
                    step += 1
                query += 1

            after_state = read_state(robot)
            writer_csv.writerow(
                {"phase": "after", "query": query, "step": step, "action_in_chunk": -1, **after_state}
            )

        print()
        print_state("after_state:", after_state)
        print(f"CLOSED_LOOP_EVAL_DONE steps={step} queries={query}")
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
