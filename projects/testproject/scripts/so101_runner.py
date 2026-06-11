#!/usr/bin/env python3
"""Project CLI for the local SO-101 leader/follower setup."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SIGINT_RETURN_CODE = -signal.SIGINT


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "so101.json"


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open() as f:
        cfg = json.load(f)
    cfg["dataset_root"] = Path(cfg["dataset_root"])
    cfg["lerobot_dir"] = Path(cfg["lerobot_dir"])
    cfg["log_dir"] = PROJECT_ROOT / cfg["log_dir"]
    return cfg


def camera_config(cfg: dict[str, Any]) -> str:
    return (
        "{ "
        f"{cfg['camera_name']}: "
        "{"
        f"type: opencv, index_or_path: {cfg['camera_index']}, "
        f"width: {cfg['camera_width']}, height: {cfg['camera_height']}, fps: {cfg['camera_fps']}"
        "}"
        "}"
    )


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def log_path(cfg: dict[str, Any], name: str) -> Path:
    cfg["log_dir"].mkdir(parents=True, exist_ok=True)
    return cfg["log_dir"] / f"{timestamp()}_{name}.log"


def print_command(cmd: list[str]) -> None:
    print("\nRunning:")
    print(" ".join(cmd))
    print()


def run(cmd: list[str], cfg: dict[str, Any], name: str, log: bool = True) -> None:
    print_command(cmd)

    cwd = cfg["lerobot_dir"] if cfg["lerobot_dir"].exists() else PROJECT_ROOT
    if not log:
        subprocess.run(cmd, cwd=cwd, check=True)
        return

    path = log_path(cfg, name)
    print(f"Log file: {path}\n")

    with path.open("w", buffering=1) as log_file:
        log_file.write(f"# SO-101 session log\n")
        log_file.write(f"# started: {datetime.now().isoformat(timespec='seconds')}\n")
        log_file.write(f"# cwd: {cwd}\n")
        log_file.write(f"# command: {' '.join(cmd)}\n\n")

        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdin=sys.stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="")
                log_file.write(line)
        except KeyboardInterrupt:
            print("\nStopping child command...")
            process.send_signal(signal.SIGINT)
        finally:
            return_code = process.wait()
            log_file.write(f"\n# finished: {datetime.now().isoformat(timespec='seconds')}\n")
            log_file.write(f"# return_code: {return_code}\n")

    if return_code == SIGINT_RETURN_CODE:
        print("Command stopped by Ctrl+C.")
        return

    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def base_robot_args(cfg: dict[str, Any], max_relative_target: float | None) -> list[str]:
    args = [
        "--robot.type=so101_follower",
        f"--robot.port={cfg['follower_port']}",
        f"--robot.id={cfg['follower_id']}",
        "--robot.disable_torque_on_disconnect=false",
    ]
    if max_relative_target is not None:
        args.append(f"--robot.max_relative_target={max_relative_target}")
    return args


def base_teleop_args(cfg: dict[str, Any]) -> list[str]:
    return [
        "--teleop.type=so101_leader",
        f"--teleop.port={cfg['leader_port']}",
        f"--teleop.id={cfg['leader_id']}",
    ]


def teleop(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    max_relative_target = None if args.no_max_relative_target else args.max_relative_target
    cmd = ["lerobot-teleoperate"]
    cmd += base_robot_args(cfg, max_relative_target)
    if args.camera:
        cmd.append(f"--robot.cameras={camera_config(cfg)}")
    cmd += base_teleop_args(cfg)
    if args.camera:
        cmd.append("--display_data=true")
    if args.seconds is not None:
        cmd.append(f"--teleop_time_s={args.seconds}")
    run(cmd, cfg, "teleop", log=not args.no_log)


def record(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    max_relative_target = None if args.no_max_relative_target else args.max_relative_target
    if args.delete and cfg["dataset_root"].exists():
        print(f"Deleting previous dataset: {cfg['dataset_root']}")
        shutil.rmtree(cfg["dataset_root"])

    cmd = ["lerobot-record"]
    cmd += base_robot_args(cfg, max_relative_target)
    cmd.append(f"--robot.cameras={camera_config(cfg)}")
    cmd += base_teleop_args(cfg)
    cmd += [
        "--display_data=true",
        f"--dataset.repo_id={cfg['dataset_repo_id']}",
        f"--dataset.root={cfg['dataset_root']}",
        f"--dataset.num_episodes={args.episodes}",
        f"--dataset.single_task={cfg['task']}",
        "--dataset.push_to_hub=false",
    ]
    run(cmd, cfg, "record", log=not args.no_log)


def replay(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    cmd = [
        "lerobot-replay",
        "--robot.type=so101_follower",
        f"--robot.port={cfg['follower_port']}",
        f"--robot.id={cfg['follower_id']}",
        "--robot.disable_torque_on_disconnect=false",
        f"--dataset.repo_id={cfg['dataset_repo_id']}",
        f"--dataset.root={cfg['dataset_root']}",
        f"--dataset.episode={args.episode}",
    ]
    run(cmd, cfg, f"replay_ep{args.episode}", log=not args.no_log)


def calibrate_follower(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    run(
        [
            "lerobot-calibrate",
            "--robot.type=so101_follower",
            f"--robot.port={cfg['follower_port']}",
            f"--robot.id={cfg['follower_id']}",
        ],
        cfg,
        "calibrate_follower",
        log=not args.no_log,
    )


def calibrate_leader(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    run(
        [
            "lerobot-calibrate",
            "--teleop.type=so101_leader",
            f"--teleop.port={cfg['leader_port']}",
            f"--teleop.id={cfg['leader_id']}",
        ],
        cfg,
        "calibrate_leader",
        log=not args.no_log,
    )


def ports(_: argparse.Namespace, cfg: dict[str, Any]) -> None:
    run(["bash", "-lc", "ls -l /dev/ttyACM* /dev/serial/by-id/ 2>/dev/null || true"], cfg, "ports", log=False)


def exists_label(path: str | Path) -> str:
    return "OK" if Path(path).exists() else "MISSING"


def command_label(command: str) -> str:
    return "OK" if shutil.which(command) else "MISSING"


def status(_: argparse.Namespace, cfg: dict[str, Any]) -> None:
    leader_cal = (
        Path.home()
        / ".cache/huggingface/lerobot/calibration/teleoperators/so_leader"
        / f"{cfg['leader_id']}.json"
    )
    follower_cal = (
        Path.home()
        / ".cache/huggingface/lerobot/calibration/robots/so_follower"
        / f"{cfg['follower_id']}.json"
    )

    print("SO-101 status\n")
    print(f"Project:         {PROJECT_ROOT}")
    print(f"Config:          {CONFIG_PATH} ({exists_label(CONFIG_PATH)})")
    print(f"LeRobot dir:     {cfg['lerobot_dir']} ({exists_label(cfg['lerobot_dir'])})")
    print(f"Conda env:       {cfg['conda_env']} ({exists_label(cfg['conda_env'])})")
    print(f"lerobot command: {command_label('lerobot-teleoperate')}")
    print()
    print(f"Leader port:     {cfg['leader_port']} ({exists_label(cfg['leader_port'])})")
    print(f"Follower port:   {cfg['follower_port']} ({exists_label(cfg['follower_port'])})")
    print(f"Leader serial:   {cfg['leader_serial']} ({exists_label(cfg['leader_serial'])})")
    print(f"Follower serial: {cfg['follower_serial']} ({exists_label(cfg['follower_serial'])})")
    print()
    print(f"Leader cal:      {leader_cal} ({exists_label(leader_cal)})")
    print(f"Follower cal:    {follower_cal} ({exists_label(follower_cal)})")
    print()
    print(f"Dataset:         {cfg['dataset_root']} ({exists_label(cfg['dataset_root'])})")
    print(f"Logs:            {cfg['log_dir']} ({exists_label(cfg['log_dir'])})")


def logs(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    if not cfg["log_dir"].exists():
        print(f"No log directory yet: {cfg['log_dir']}")
        return
    paths = sorted(cfg["log_dir"].glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths[: args.limit]:
        print(path)


def tail_log(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    if not cfg["log_dir"].exists():
        print(f"No log directory yet: {cfg['log_dir']}")
        return
    paths = sorted(cfg["log_dir"].glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not paths:
        print("No logs yet.")
        return
    path = paths[0]
    print(f"Showing last {args.lines} lines of {path}\n")
    lines = path.read_text(errors="replace").splitlines()
    for line in lines[-args.lines :]:
        print(line)


def _load_hf_json(repo_id: str, filename: str) -> dict[str, Any] | None:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError("huggingface_hub is required. Install it with: pip install huggingface_hub") from exc

    try:
        path = Path(hf_hub_download(repo_id, filename))
    except Exception:
        return None

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _hf_model_size_label(repo_id: str) -> str:
    try:
        from huggingface_hub import model_info
    except ImportError:
        return "unknown"

    try:
        info = model_info(repo_id, files_metadata=True)
    except Exception:
        return "unknown"

    total_size = 0
    for sibling in info.siblings:
        size = getattr(sibling, "size", None)
        if size and (
            sibling.rfilename.endswith(".safetensors")
            or sibling.rfilename.endswith(".bin")
            or sibling.rfilename.endswith(".pt")
        ):
            total_size += size

    if total_size <= 0:
        return "unknown"

    gib = total_size / 1024**3
    return f"{gib:.2f} GiB"


def _feature_shape(features: dict[str, Any], name: str) -> list[int] | None:
    value = features.get(name)
    if not isinstance(value, dict):
        return None
    shape = value.get("shape")
    return shape if isinstance(shape, list) else None


def _feature_names_by_type(features: dict[str, Any], feature_type: str) -> list[str]:
    names = []
    for name, spec in features.items():
        if isinstance(spec, dict) and spec.get("type") == feature_type:
            names.append(name)
    return sorted(names)


def _status_line(label: str, ok: bool, detail: str) -> None:
    status_text = "OK" if ok else "MISMATCH"
    print(f"{label:<14} {status_text:<10} {detail}")


def inspect_policy(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    repo_id = args.repo_id
    config_paths = [
        "config.json",
        "pretrained_model/config.json",
    ]
    train_config_paths = [
        "train_config.json",
        "pretrained_model/train_config.json",
    ]

    policy_config = None
    policy_config_path = None
    for path in config_paths:
        policy_config = _load_hf_json(repo_id, path)
        if policy_config is not None:
            policy_config_path = path
            break

    train_config = None
    train_config_path = None
    for path in train_config_paths:
        train_config = _load_hf_json(repo_id, path)
        if train_config is not None:
            train_config_path = path
            break

    if policy_config is None and train_config is None:
        raise RuntimeError(f"No supported config JSON found for {repo_id}")

    source = policy_config or train_config.get("policy", {})
    if "policy" in source and isinstance(source["policy"], dict):
        source = source["policy"]

    input_features = source.get("input_features", {})
    output_features = source.get("output_features", {})
    policy_type = source.get("type", "unknown")
    chunk_size = source.get("chunk_size", "unknown")
    n_action_steps = source.get("n_action_steps", "unknown")
    pretrained_path = source.get("pretrained_path", "unknown")

    state_shape = _feature_shape(input_features, "observation.state")
    action_shape = _feature_shape(output_features, "action")
    visual_features = _feature_names_by_type(input_features, "VISUAL")

    our_camera = f"observation.images.{cfg['camera_name']}"
    our_state_shape = [6]
    our_action_shape = [6]
    missing_cameras = [name for name in visual_features if name != our_camera]
    has_our_camera = our_camera in visual_features

    print(f"Policy repo:       {repo_id}")
    print(f"Model size:        {_hf_model_size_label(repo_id)}")
    print(f"Policy config:     {policy_config_path or 'not found'}")
    print(f"Train config:      {train_config_path or 'not found'}")
    print(f"Policy type:       {policy_type}")
    print(f"Pretrained path:   {pretrained_path}")
    print(f"Chunk size:        {chunk_size}")
    print(f"Action steps:      {n_action_steps}")
    print()

    print("Expected inputs")
    print(f"  state:           observation.state shape={state_shape}")
    print("  cameras:")
    if visual_features:
        for name in visual_features:
            print(f"  - {name} shape={_feature_shape(input_features, name)}")
    else:
        print("  - none found")
    print(f"Expected output:   action shape={action_shape}")
    print()

    print("Our current setup")
    print(f"  state:           observation.state shape={our_state_shape}")
    print(f"  camera:          {our_camera}")
    print(f"  action:          shape={our_action_shape}")
    print()

    print("Compatibility")
    _status_line("policy", policy_type == "pi05", f"expected pi05, got {policy_type}")
    _status_line("state", state_shape == our_state_shape, f"expected {state_shape}, ours {our_state_shape}")
    _status_line("action", action_shape == our_action_shape, f"expected {action_shape}, ours {our_action_shape}")

    camera_ok = bool(visual_features) and has_our_camera and not missing_cameras
    if camera_ok:
        camera_detail = f"matches {our_camera}"
    elif has_our_camera:
        camera_detail = f"has {our_camera}, missing additional cameras: {', '.join(missing_cameras)}"
    elif visual_features:
        camera_detail = f"missing {our_camera}; expected: {', '.join(visual_features)}"
    else:
        camera_detail = "no visual features found"
    _status_line("cameras", camera_ok, camera_detail)
    print()

    if policy_type == "pi05" and state_shape == our_state_shape and action_shape == our_action_shape:
        if camera_ok:
            print("Result: strong candidate for our current setup.")
        else:
            print("Result: action/state match, but camera setup does not fully match.")
            print("Next: add required cameras or use this model for offline-only testing first.")
    else:
        print("Result: not safe to run on the real arm without adaptation.")


def positions(_: argparse.Namespace, cfg: dict[str, Any]) -> None:
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
    from lerobot.robots.so_follower.so_follower import SOFollower
    from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig
    from lerobot.teleoperators.so_leader.so_leader import SOLeader

    motors = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
    leader = SOLeader(SOLeaderTeleopConfig(port=cfg["leader_port"], id=cfg["leader_id"]))
    follower = SOFollower(
        SOFollowerRobotConfig(
            port=cfg["follower_port"],
            id=cfg["follower_id"],
            disable_torque_on_disconnect=False,
        )
    )

    leader_action = None
    follower_obs = None

    try:
        leader.connect()
        leader_action = leader.get_action()
        print(f"Leader read: OK ({cfg['leader_port']})")
    except Exception as exc:
        print(f"Leader read: FAILED ({cfg['leader_port']})")
        print(f"{type(exc).__name__}: {exc}")
    finally:
        try:
            leader.disconnect()
        except Exception:
            pass

    try:
        follower.connect()
        follower_obs = follower.get_observation()
        print(f"Follower read: OK ({cfg['follower_port']})")
    except Exception as exc:
        print(f"Follower read: FAILED ({cfg['follower_port']})")
        print(f"{type(exc).__name__}: {exc}")
    finally:
        try:
            follower.disconnect()
        except Exception:
            pass

    if leader_action is None or follower_obs is None:
        print("\nPosition comparison skipped because one side did not respond.")
        print("\nWhat this usually means:")
        if leader_action is None:
            print("- Leader arm did not return positions. Check leader USB, cable, and calibration.")
        if follower_obs is None:
            print("- Follower arm did not return positions. Check follower power, servo bus cables, and motor response.")
        print("\nSafe next checks:")
        print("1. Run: ./bin/so101 status")
        print("2. Power-cycle the failed arm if needed.")
        print("3. Run: ./bin/so101 positions")
        return

    print()
    print("motor              leader     follower     diff(follower-leader)    status")
    print("-" * 78)
    for motor in motors:
        leader_pos = float(leader_action[f"{motor}.pos"])
        follower_pos = float(follower_obs[f"{motor}.pos"])
        diff = follower_pos - leader_pos
        status_text = "GOOD" if abs(diff) <= 3 else "OK-ish" if abs(diff) <= 10 else "MISMATCH"
        print(f"{motor:<18} {leader_pos:>9.2f} {follower_pos:>12.2f} {diff:>18.2f}    {status_text}")


def main() -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Run common SO-101 LeRobot commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    teleop_parser = subparsers.add_parser("teleop", help="Run leader/follower teleop until Ctrl+C.")
    teleop_parser.add_argument("--max-relative-target", type=float, default=cfg["default_max_relative_target"])
    teleop_parser.add_argument(
        "--no-max-relative-target",
        action="store_true",
        help="Omit robot.max_relative_target. This removes the joint jump limiter.",
    )
    teleop_parser.add_argument("--seconds", type=float)
    teleop_parser.add_argument("--camera", action="store_true")
    teleop_parser.add_argument("--no-log", action="store_true")
    teleop_parser.set_defaults(func=teleop)

    record_parser = subparsers.add_parser("record", help="Record a local dataset.")
    record_parser.add_argument("--episodes", type=int, default=5)
    record_parser.add_argument("--max-relative-target", type=float, default=cfg["default_max_relative_target"])
    record_parser.add_argument(
        "--no-max-relative-target",
        action="store_true",
        help="Omit robot.max_relative_target. This removes the joint jump limiter.",
    )
    record_parser.add_argument("--delete", action="store_true", help="Delete old dataset before recording.")
    record_parser.add_argument("--no-log", action="store_true")
    record_parser.set_defaults(func=record)

    replay_parser = subparsers.add_parser("replay", help="Replay one recorded episode.")
    replay_parser.add_argument("episode", nargs="?", type=int, default=0)
    replay_parser.add_argument("--no-log", action="store_true")
    replay_parser.set_defaults(func=replay)

    calibrate_follower_parser = subparsers.add_parser("calibrate-follower", help="Calibrate follower arm.")
    calibrate_follower_parser.add_argument("--no-log", action="store_true")
    calibrate_follower_parser.set_defaults(func=calibrate_follower)

    calibrate_leader_parser = subparsers.add_parser("calibrate-leader", help="Calibrate leader arm.")
    calibrate_leader_parser.add_argument("--no-log", action="store_true")
    calibrate_leader_parser.set_defaults(func=calibrate_leader)

    subparsers.add_parser("ports", help="Show USB serial ports.").set_defaults(func=ports)
    subparsers.add_parser("status", help="Show project, robot, calibration, and dataset status.").set_defaults(
        func=status
    )
    subparsers.add_parser("positions", help="Read leader/follower joint positions and compare them.").set_defaults(
        func=positions
    )

    inspect_parser = subparsers.add_parser("inspect-policy", help="Inspect a Hugging Face policy config.")
    inspect_parser.add_argument("repo_id", help="Hugging Face model repo, for example zz4321/so101_pi05")
    inspect_parser.set_defaults(func=inspect_policy)

    logs_parser = subparsers.add_parser("logs", help="List recent SO-101 session logs.")
    logs_parser.add_argument("--limit", type=int, default=10)
    logs_parser.set_defaults(func=logs)

    tail_parser = subparsers.add_parser("tail-log", help="Show the end of the latest SO-101 log.")
    tail_parser.add_argument("--lines", type=int, default=80)
    tail_parser.set_defaults(func=tail_log)

    args = parser.parse_args()
    args.func(args, cfg)


if __name__ == "__main__":
    main()
