#!/usr/bin/env python3
"""Async-inference robot client for the SO-101 3-cam rig.

Drives the local SO-101 follower + 3 cameras (front/top OpenCV, wrist HTTP proxy),
sending observations to a remote lerobot policy_server (on a GPU) and executing the
returned action chunks CLOSED-LOOP. Server reached via SSH tunnel at localhost:8080.

Server side (on the GPU pod):
  python -m lerobot.async_inference.policy_server --host=0.0.0.0 --port=8080 --fps=30
SSH tunnel (laptop):
  ssh -N -L 8080:localhost:8080 -i <key> -p <port> root@<pod-ip>
"""
from __future__ import annotations
import argparse, sys
import http_camera  # noqa: F401  registers the `http` camera type
from record_3cam_demos import cameras_arg, load_config, resolve_port
from lerobot.async_inference.robot_client import async_client, register_third_party_plugins


def main() -> None:
    cfg = load_config()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--server", default="localhost:8080", help="policy_server host:port (SSH tunnel).")
    p.add_argument("--ckpt", default="/workspace/ckpt/pretrained_model", help="checkpoint path ON THE POD.")
    p.add_argument("--task", default="pick up the orange and move it to another place")
    p.add_argument("--fps", type=int, default=int(cfg.get("camera_fps", 30)))
    p.add_argument("--max-relative-target", default="5", help="per-step joint cap (safety). 'null' to disable.")
    p.add_argument("--actions-per-chunk", type=int, default=50)
    p.add_argument("--chunk-size-threshold", type=float, default=0.6, help="->1 = more feedback/closed-loop")
    p.add_argument("--aggregate-fn", default="weighted_average")
    p.add_argument("--policy-type", default="act", help="policy type on the server (act, pi05, ...)")
    p.add_argument("--trace-dir", default=None, help="optional read-only trace output directory")
    p.add_argument("--jpeg-quality", type=int, default=None, help="JPEG-compress observation images (e.g. 92)")
    p.add_argument("--obs-min-interval", type=float, default=None, help="min seconds between observation sends")
    p.add_argument("--print-only", action="store_true")
    args = p.parse_args()

    argv = [
        "async_client_3cam",
        f"--server_address={args.server}",
        "--robot.type=so101_follower",
        f"--robot.port={resolve_port(cfg, 'follower')}",
        f"--robot.id={cfg['follower_id']}",
        f"--robot.max_relative_target={args.max_relative_target}",
        f"--robot.cameras={cameras_arg(cfg, args.fps)}",
        f"--task={args.task}",
        f"--policy_type={args.policy_type}",
        f"--pretrained_name_or_path={args.ckpt}",
        "--policy_device=cuda",
        "--client_device=cpu",
        f"--actions_per_chunk={args.actions_per_chunk}",
        f"--chunk_size_threshold={args.chunk_size_threshold}",
        f"--aggregate_fn_name={args.aggregate_fn}",
        f"--fps={args.fps}",
        "--debug_visualize_queue_size=False",
    ]
    if args.trace_dir:
        argv.append(f"--trace_dir={args.trace_dir}")
    if args.jpeg_quality is not None:
        argv.append(f"--jpeg_quality={args.jpeg_quality}")
    if args.obs_min_interval is not None:
        argv.append(f"--obs_min_interval_s={args.obs_min_interval}")
    print("Async client -> server", args.server, f"| closed-loop {args.policy_type}")
    print(" \\\n  ".join(argv[1:]))
    if args.print_only:
        return
    register_third_party_plugins()
    sys.argv = argv
    async_client()


if __name__ == "__main__":
    main()
