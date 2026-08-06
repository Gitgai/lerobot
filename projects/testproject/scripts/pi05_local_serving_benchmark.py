#!/usr/bin/env python3
"""Load Pi05 locally and measure real chunk-inference latency.

Read-only: never opens a serial port, never moves the arm. Mirrors the load path
in policy_server.py (get_policy_class -> from_pretrained -> to(device) ->
make_pre_post_processors), so a pass here means the pod's serving path works
locally.

MEASUREMENT TRAP THIS SCRIPT AVOIDS
    Pi05 predicts a 50-action chunk and select_action() pops from a queue. Timing
    consecutive select_action() calls therefore measures QUEUE POPS (~2 ms), not
    inference. policy.reset() between calls forces a real forward pass each time.
    A "2 ms" reading means you measured the queue, not the model.

BASELINE (synthetic random input, RTX 5090, 3 cameras, 10 denoising steps)
    driver 595.84 + torch 2.11.0+cu128 ... median 153 ms  (2026-08-04)
    driver 580.173.02 + same torch ....... median 143 ms  (2026-08-04, post-downgrade)
    load ~60 s | 4.14B params | bfloat16 | 9.5 GB VRAM

    For context: a 50-action chunk at 30 Hz is 1.67 s of motion, so ~143 ms is
    ~4.3 control steps of latency vs the pod's ~30 (docs put pod latency at ~60%
    of each chunk). See docs/new_machine_local_serving_20260804.md.

NOTE: finite, plausibly-scaled actions on RANDOM INPUT prove the stack RUNS.
They say NOTHING about numerical correctness. The trust exam against the pod's
known-good numbers (gripper corr 0.826, MAE 4.41) is the real gate before any
robot motion - see scripts/runpod/pi05_episode29_offline_compare.py.

Usage:
    cd ~/lerobot_assets/lerobot_trainingera
    HF_HUB_OFFLINE=1 ./.venv/bin/python \
        ~/projects/git/nvidia/lerobot/projects/testproject/scripts/pi05_local_serving_benchmark.py
"""

from __future__ import annotations

import argparse
import pathlib
import time

import torch

from lerobot.policies import get_policy_class, make_pre_post_processors

DEFAULT_CKPT = pathlib.Path.home() / "lerobot_assets/checkpoints/pi05_012000"
DEFAULT_TASK = "pick up the orange and move it to another place"
CAMERAS = ("front", "top", "wrist")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-path", default=str(DEFAULT_CKPT))
    parser.add_argument("--policy-type", default="pi05")
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--runs", type=int, default=10)
    args = parser.parse_args()

    t0 = time.perf_counter()
    policy = get_policy_class(args.policy_type).from_pretrained(args.policy_path)
    policy.to(args.device)
    policy.eval()
    params = sum(p.numel() for p in policy.parameters()) / 1e9
    print(
        f"LOAD OK          {time.perf_counter() - t0:.1f}s | {params:.2f}B params "
        f"| {next(policy.parameters()).dtype}"
    )

    device_override = {"device": args.device}
    preprocessor, postprocessor = make_pre_post_processors(
        policy.config,
        pretrained_path=args.policy_path,
        preprocessor_overrides={"device_processor": device_override},
        postprocessor_overrides={"device_processor": device_override},
    )

    torch.manual_seed(0)
    obs = {"observation.state": torch.rand(6), "task": args.task}
    for cam in CAMERAS:
        obs[f"observation.images.{cam}"] = torch.rand(3, 480, 640)

    for _ in range(2):  # warmup
        policy.reset()
        with torch.no_grad():
            postprocessor(policy.select_action(preprocessor(obs)))
    torch.cuda.synchronize()

    times = []
    action = None
    for _ in range(args.runs):
        policy.reset()  # forces a REAL chunk inference, not a queue pop
        t0 = time.perf_counter()
        with torch.no_grad():
            action = postprocessor(policy.select_action(preprocessor(obs)))
        torch.cuda.synchronize()
        times.append(time.perf_counter() - t0)

    times.sort()
    median = times[len(times) // 2]
    print(
        f"CHUNK INFERENCE  median {median * 1000:.0f} ms | "
        f"min {times[0] * 1000:.0f} | max {times[-1] * 1000:.0f}"
    )
    print(
        f"  per-action amortised {median * 1000 / policy.config.chunk_size:.1f} ms "
        f"over chunk_size={policy.config.chunk_size}, "
        f"num_inference_steps={policy.config.num_inference_steps}"
    )
    print(f"action           shape={tuple(action.shape)} finite={bool(torch.isfinite(action).all())}")
    print(f"peak VRAM        {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")


if __name__ == "__main__":
    main()
