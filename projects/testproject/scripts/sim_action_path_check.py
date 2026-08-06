#!/usr/bin/env python3
"""Does a 6-DoF JOINT action actually move the simulated arm?

WHY THIS EXISTS - harness validation, per the Era 1 rule
--------------------------------------------------------
Running Pi05 012000 in LeIsaac produced an arm that barely moved (1.4 cm over
900 steps) with gripper_cmd EXACTLY 0.0000 and zero variance. That is either:

    (a) the model is lost in an out-of-distribution scene, or
    (b) our 6-DoF action path does not actually drive the arm.

Those must be separated BEFORE the run means anything. Replaying a recorded
demo does NOT settle it: the state machine records 8-dim end-effector actions
(`so101_state_machine`), while Pi05 emits 6-dim joint actions (`so101leader`).
Replay exercises the WRONG PATH and fails with
    RuntimeError: expanded size of the tensor (6) must match the existing size (8)

So this bypasses any policy and commands the joints directly.

WHAT IT DOES
------------
Configures the env for `so101leader` (6-DoF joints, the space Pi05 uses), then
sends a known, deliberately LARGE joint target and watches the measured joint
positions and the end-effector.

READING THE RESULT
------------------
    joints move toward the target  -> the 6-DoF action path WORKS.
                                      Pi05's near-zero motion is then about the
                                      MODEL (or its inputs), not the plumbing.
    joints do not move             -> the action path is BROKEN. The Pi05 sim
                                      result is meaningless and must be
                                      discarded, exactly as Era 1's local
                                      probes were.

Usage:
    cd ~/sim/leisaac-src
    LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y \
    PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
    ~/sim/leisaac-venv/bin/python -u <...>/sim_action_path_check.py
"""

import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", default="LeIsaac-SO101-PickOrange-v0")
parser.add_argument("--device", default="cuda")
parser.add_argument("--steps", type=int, default=300)
parser.add_argument("--headless", action="store_true")
args = parser.parse_args()

from isaaclab.app import AppLauncher  # noqa: E402

app_launcher = AppLauncher(headless=args.headless, enable_cameras=True)
simulation_app = app_launcher.app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

import leisaac  # noqa: F401,E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from leisaac.utils.env_utils import get_task_type  # noqa: E402


def main() -> None:
    env_cfg = parse_env_cfg(args.task, device=args.device, num_envs=1)
    task_type = get_task_type(args.task)
    env_cfg.use_teleop_device(task_type)
    print(f"[check] task_type={task_type}")

    env = gym.make(args.task, cfg=env_cfg).unwrapped
    obs, _ = env.reset()

    action_dim = env.action_space.shape[-1]
    print(f"[check] env action space = {action_dim} dims")

    start = env.scene["robot"].data.joint_pos[0].clone()
    print(f"[check] start joints = {[round(float(v), 3) for v in start]}")

    # A deliberately large, obviously-visible target: swing joint 0 and 1, and
    # drive the gripper to a clearly non-zero value. If ANY of this shows up in
    # the measured joint positions, actions are reaching the robot.
    target = start.clone()
    target[0] += 0.6
    target[1] += 0.4
    target[-1] = 1.0
    print(f"[check] commanding  = {[round(float(v), 3) for v in target]}")

    action = target.unsqueeze(0)[:, :action_dim]
    with torch.inference_mode():
        for step in range(args.steps):
            obs, _, terminated, timed_out, _ = env.step(action)
            if step % 50 == 0:
                now = env.scene["robot"].data.joint_pos[0]
                delta = float(torch.linalg.norm(now - start))
                print(f"[check] step {step:3d}  |joints - start| = {delta:.4f} rad")
            if bool(terminated[0]) or bool(timed_out[0]):
                obs, _ = env.reset()

    end = env.scene["robot"].data.joint_pos[0]
    moved = float(torch.linalg.norm(end - start))
    print(f"[check] end joints   = {[round(float(v), 3) for v in end]}")
    print(f"[check] TOTAL JOINT MOVEMENT = {moved:.4f} rad")
    print(
        "[check] VERDICT: ACTION PATH WORKS - the arm follows 6-DoF joint commands"
        if moved > 0.05
        else "[check] VERDICT: ACTION PATH BROKEN - joint commands do NOT move the arm"
    )

    env.close()
    simulation_app.close()


if __name__ == "__main__":
    main()
