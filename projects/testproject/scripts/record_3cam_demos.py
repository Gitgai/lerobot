#!/usr/bin/env python3
"""Record teleoperated SO-101 demos with ALL THREE cameras (top, front, wrist).

The stock `lerobot-record` can only ingest local camera devices, but our top and
wrist cameras are served over HTTP (proxies on :8094 and :8092). This wrapper
registers the custom `http` camera type (see http_camera.py) and then runs the
exact same LeRobot recording machinery in-process, so we get a 100% standard
LeRobotDataset with observation.images.{top,front,wrist} — matching precisely
what the Pi05/SmolVLA policy will see at deployment (train == deploy).

Cameras captured (same as the eval's top-url-front-wrist mode):
  front : local OpenCV device (config camera_index)
  top   : http proxy  (config top_camera_url,   default :8094)
  wrist : http proxy  (config wrist_camera_url,  default :8092)

Usage (after bringing all 3 cameras up):
  python record_3cam_demos.py --episodes 5 --task "Pick up the orange" --delete
  python record_3cam_demos.py --print-only          # show the command, record nothing
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import threading
import time
from pathlib import Path

# Registers the `http` camera type with the LeRobot camera registry. MUST be
# imported before the record config is parsed.
import http_camera  # noqa: F401

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "so101.json"


def load_config() -> dict:
    with CONFIG_PATH.open() as f:
        return json.load(f)


def resolve_port(cfg: dict, kind: str) -> str:
    serial = Path(cfg[f"{kind}_serial"])
    if serial.exists():
        try:
            return str(serial.resolve())
        except OSError:
            return str(serial)
    return str(cfg[f"{kind}_port"])


def cameras_arg(cfg: dict, fps: int) -> str:
    w, h = int(cfg["camera_width"]), int(cfg["camera_height"])
    front_index = cfg["camera_index"]
    # top: the Logitech C270 captured DIRECTLY via OpenCV (MJPG + warmup avoids the
    # black-frame-on-early-grab issue) — no browser proxy needed.
    top_index = cfg["top_camera_index"]
    top_fourcc = cfg.get("top_camera_fourcc", "MJPG")
    top_warmup = int(cfg.get("top_camera_warmup_s", 3))
    # wrist: genuinely remote (Raspberry Pi), so it stays an http proxy.
    wrist_url = cfg.get("wrist_camera_url", "http://127.0.0.1:8092/frame")
    # draccus parses this inline (YAML-flow) dict. Quote string values that
    # contain ':' or '/' so they are read as plain scalars.
    return (
        "{ "
        f'front: {{type: opencv, index_or_path: "{front_index}", width: {w}, height: {h}, fps: {fps}}}, '
        f'top: {{type: opencv, index_or_path: "{top_index}", fourcc: {top_fourcc}, warmup_s: {top_warmup}, width: {w}, height: {h}, fps: {fps}}}, '
        f'wrist: {{type: http, url: "{wrist_url}", width: {w}, height: {h}, fps: {fps}}} '
        "}"
    )


def build_argv(args: argparse.Namespace, cfg: dict) -> list[str]:
    max_rel = args.max_relative_target
    argv = [
        "record_3cam_demos",
        "--robot.type=so101_follower",
        f"--robot.port={resolve_port(cfg, 'follower')}",
        f"--robot.id={cfg['follower_id']}",
        "--robot.disable_torque_on_disconnect=false",
        f"--robot.cameras={cameras_arg(cfg, args.fps)}",
        "--teleop.type=so101_leader",
        f"--teleop.port={resolve_port(cfg, 'leader')}",
        f"--teleop.id={cfg['leader_id']}",
        f"--dataset.repo_id={cfg['dataset_repo_id']}",
        f"--dataset.root={cfg['dataset_root']}",
        f"--dataset.fps={args.fps}",
        f"--dataset.num_episodes={args.episodes}",
        f"--dataset.single_task={args.task}",
        f"--dataset.episode_time_s={args.episode_time}",
        f"--dataset.reset_time_s={args.reset_time}",
        "--dataset.push_to_hub=false",
    ]
    if max_rel is not None:
        argv.append(f"--robot.max_relative_target={max_rel}")
    if args.display_data:
        argv.append("--display_data=true")
    return argv


class ClampWarningFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "Relative goal position magnitude had to be clamped" not in record.getMessage()


def install_timer_patch() -> None:
    import lerobot.scripts.lerobot_record as lerobot_record

    original_record_loop = lerobot_record.record_loop

    def timed_record_loop(*args, **kwargs):
        control_time_s = kwargs.get("control_time_s")
        dataset = kwargs.get("dataset")
        phase = "RECORDING" if dataset is not None else "RESET"

        if control_time_s is None:
            return original_record_loop(*args, **kwargs)

        stop_timer = threading.Event()

        def print_timer() -> None:
            start_t = time.perf_counter()
            while not stop_timer.is_set():
                elapsed = time.perf_counter() - start_t
                remaining = max(float(control_time_s) - elapsed, 0)
                print(
                    f"\r{phase}: {elapsed:5.1f}s / {float(control_time_s):.1f}s "
                    f"(remaining {remaining:5.1f}s) | Right Arrow = finish phase",
                    end="",
                    flush=True,
                )
                time.sleep(0.5)
            elapsed = min(time.perf_counter() - start_t, float(control_time_s))
            print(f"\r{phase}: finished at {elapsed:5.1f}s / {float(control_time_s):.1f}s".ljust(96))

        timer_thread = threading.Thread(target=print_timer, daemon=True)
        timer_thread.start()
        try:
            return original_record_loop(*args, **kwargs)
        finally:
            stop_timer.set()
            timer_thread.join(timeout=1)

    lerobot_record.record_loop = timed_record_loop


def main() -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--task", default="Pick up the orange",
                        help="Single-task instruction stored in the dataset; should match the deploy prompt.")
    parser.add_argument("--fps", type=int, default=int(cfg.get("camera_fps", 30)))
    parser.add_argument("--episode-time", type=float, default=30.0,
                        help="Max seconds per episode (press → to end earlier).")
    parser.add_argument("--reset-time", type=float, default=15.0,
                        help="Max seconds to reset the scene between episodes (press → to skip).")
    parser.add_argument("--show-timer", action="store_true",
                        help="Print a simple terminal timer during record/reset phases.")
    parser.add_argument("--quiet-clamp-warnings", action="store_true",
                        help="Hide repetitive max_relative_target clamp warnings while recording.")
    parser.add_argument("--dataset-root", default=None,
                        help="Override the dataset output folder from config/so101.json.")
    parser.add_argument("--dataset-repo-id", default=None,
                        help="Override the dataset repo_id from config/so101.json.")
    parser.add_argument("--max-relative-target", type=float, default=None,
                        help="Optional LeRobot movement clamp. Default is no clamp.")
    parser.add_argument(
        "--display-data",
        action="store_true",
        help="Open the Rerun viewer during recording. Off by default because the viewer binary may not be installed.",
    )
    parser.add_argument("--delete", action="store_true", help="Delete the existing dataset first.")
    parser.add_argument("--print-only", action="store_true", help="Print the record command and exit.")
    args = parser.parse_args()

    if args.dataset_root:
        cfg["dataset_root"] = args.dataset_root
    if args.dataset_repo_id:
        cfg["dataset_repo_id"] = args.dataset_repo_id

    argv = build_argv(args, cfg)

    print("Cameras: front (opencv) + top (opencv C270, direct) + wrist (http :8092)")
    if args.show_timer:
        print("Timer: enabled")
    if args.quiet_clamp_warnings:
        print("Clamp warning spam: hidden")
    print("Equivalent lerobot-record command:\n")
    print(" \\\n  ".join(argv[1:]))
    print()

    if args.print_only:
        return

    dataset_root = Path(cfg["dataset_root"])
    if args.delete and dataset_root.exists():
        print(f"Deleting previous dataset: {dataset_root}")
        shutil.rmtree(dataset_root)

    # Run the standard LeRobot record entry point in-process (http type is registered).
    if args.show_timer:
        install_timer_patch()
    if args.quiet_clamp_warnings:
        logging.getLogger().addFilter(ClampWarningFilter())

    from lerobot.scripts.lerobot_record import record

    sys.argv = argv
    record()


if __name__ == "__main__":
    main()
