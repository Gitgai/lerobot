#!/usr/bin/env python3
"""Evaluate a trained ACT policy on the real SO-101 with all THREE cameras.

The twin of ``record_3cam_demos.py``: it reuses that script's EXACT camera
config (front=laptop OpenCV, top=C270 OpenCV MJPG+warmup, wrist=http :8092) so
what the policy sees at eval matches what it saw in training (train == deploy).
Instead of a leader arm driving the follower, the ACT policy drives it via
``lerobot-rollout`` (the policy-deployment CLI in this lerobot version;
``lerobot-record`` is data-collection only).

SAFETY
  - --max-relative-target caps how far any single command can move a joint, so a
    bad action cannot slam the arm. It does NOT steer toward the orange.
  - The arm does not move unless you pass --i-understand-this-moves-robot.
  - Keep a hand on the power/e-stop. Start with a SHORT --duration.

Prereqs (bring the wrist camera up first):
  - Pi:     rpicam-vid MJPEG on :8892   (check: ssh raspi@<pi> ... )
  - Laptop: tools/pi_wrist_proxy.py  ->  http://127.0.0.1:8092/frame  fresh
  (top C270 + front laptop cam are local OpenCV — no proxy needed.)

Usage:
  python act_eval_3cam.py --policy-path /path/to/checkpoints/020000/pretrained_model \\
      --task "pick up the orange and move it to another place" \\
      --duration 30 --print-only
  # then add --i-understand-this-moves-robot to actually run it
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Registers the `http` camera type with the LeRobot camera registry. MUST be
# imported before the rollout config is parsed. Same module the recorder uses.
import http_camera  # noqa: F401

# Reuse the recorder's config loader + IDENTICAL camera string (train == deploy).
from record_3cam_demos import cameras_arg, load_config, resolve_port


def build_argv(args: argparse.Namespace, cfg: dict) -> list[str]:
    argv = [
        "act_eval_3cam",
        f"--policy.path={args.policy_path}",
        f"--policy.device={args.device}",
        "--robot.type=so101_follower",
        f"--robot.port={resolve_port(cfg, 'follower')}",
        f"--robot.id={cfg['follower_id']}",
        "--robot.disable_torque_on_disconnect=false",
        f"--robot.cameras={cameras_arg(cfg, args.fps)}",
        # SAFETY GUARD: cap per-command joint movement.
        f"--robot.max_relative_target={args.max_relative_target}",
        f"--task={args.task}",
        f"--fps={args.fps}",
        f"--duration={args.duration}",
        "--inference.type=sync",
    ]
    # CLOSED-LOOP override: ACT default is open-loop (n_action_steps=100 = plan once,
    # execute 100 blind). Lower n_action_steps re-plans more often (feedback); temporal
    # ensembling (needs n_action_steps=1) is the smooth fully-closed-loop mode.
    if args.temporal_ensemble is not None:
        argv += [
            f"--policy.temporal_ensemble_coeff={args.temporal_ensemble}",
            "--policy.n_action_steps=1",
        ]
    elif args.n_action_steps is not None:
        argv.append(f"--policy.n_action_steps={args.n_action_steps}")
    if args.record:
        # Record the rollout to a LeRobotDataset on /data (root is disk-tight).
        # Base strategy can't record; sentry records continuously and its finally
        # block saves the final (single) episode when --duration is reached.
        argv += [
            "--strategy.type=sentry",
            f"--dataset.repo_id=local/{args.run_name}",
            f"--dataset.root={args.dataset_root}/{args.run_name}",
            f"--dataset.single_task={args.task}",
            f"--dataset.fps={args.fps}",
            "--dataset.push_to_hub=false",
            "--dataset.video=true",
            "--dataset.streaming_encoding=true",
        ]
    if args.display_data:
        argv.append("--display_data=true")
    return argv


def main() -> None:
    cfg = load_config()
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--policy-path",
        required=True,
        help="Local ACT checkpoint dir, e.g. .../checkpoints/020000/pretrained_model",
    )
    p.add_argument(
        "--task",
        default="pick up the orange and move it to another place",
        help="Must match the dataset's single_task string used in training.",
    )
    p.add_argument("--device", default="cpu", help="cpu (laptop) or cuda.")
    p.add_argument("--fps", type=int, default=int(cfg.get("camera_fps", 30)))
    p.add_argument(
        "--duration", type=float, default=30.0, help="Seconds to run the policy (one attempt)."
    )
    p.add_argument(
        "--max-relative-target",
        type=float,
        default=float(cfg.get("default_max_relative_target", 5)),
        help="SAFETY: max per-command joint move. Lower = safer/slower.",
    )
    p.add_argument("--n-action-steps", type=int, default=None,
                   help="Override ACT open-loop chunk length (default 100). Lower = more feedback "
                        "(e.g. 20). CPU re-plans cost ~0.4s each.")
    p.add_argument("--temporal-ensemble", type=float, default=None,
                   help="Enable temporal ensembling (e.g. 0.01) = smooth fully-closed-loop; forces "
                        "n_action_steps=1. Needs GPU (CPU too slow at ~2.5Hz).")
    p.add_argument("--display-data", action="store_true", help="Open the Rerun viewer.")
    p.add_argument("--record", action="store_true",
                   help="Record the rollout to a LeRobotDataset (video+state+action) for review.")
    p.add_argument("--run-name", default="eval_act_orange",
                   help="Name of the recorded eval dataset (under --dataset-root).")
    p.add_argument("--dataset-root", default="/data/act_orange_evals",
                   help="Parent dir for recorded eval datasets (on /data; root disk is tight).")
    p.add_argument("--print-only", action="store_true", help="Print the rollout command and exit.")
    p.add_argument(
        "--i-understand-this-moves-robot",
        dest="confirm",
        action="store_true",
        help="Required to actually move the real arm.",
    )
    args = p.parse_args()

    # lerobot-rollout requires recorded dataset names to start with 'rollout_'.
    if args.record and not args.run_name.startswith("rollout_"):
        args.run_name = f"rollout_{args.run_name}"

    if not Path(args.policy_path).exists():
        p.error(f"policy path does not exist: {args.policy_path}")

    argv = build_argv(args, cfg)

    print("ACT eval — cameras: front (opencv) + top (opencv C270 MJPG) + wrist (http :8092)")
    print(f"Policy : {args.policy_path}")
    print(f"Safety : max_relative_target={args.max_relative_target}, duration={args.duration}s")
    print("\nEquivalent lerobot-rollout command:\n")
    print(" \\\n  ".join(argv[1:]))
    print()

    if args.print_only:
        return
    if not args.confirm:
        p.error("refusing to move the arm without --i-understand-this-moves-robot")

    if args.record:
        import shutil
        out = Path(args.dataset_root) / args.run_name
        if out.exists():
            print(f"Removing previous recording: {out}")
            shutil.rmtree(out)
        print(f"Recording eval to: {out}")

    # Run lerobot-rollout in-process (http camera type is registered above).
    from lerobot.scripts.lerobot_rollout import rollout

    sys.argv = argv
    rollout()


if __name__ == "__main__":
    main()
