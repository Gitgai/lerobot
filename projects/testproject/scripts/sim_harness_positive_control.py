#!/usr/bin/env python3
"""POSITIVE CONTROL: can our scoring harness register a SUCCESS at all?

Why this exists
---------------
Every policy we have scored in LeIsaac has FAILED. Pi05 hovers 13-18 cm and
never grasps; GR00T N1.7 closes on air. From failures alone we cannot tell
these two apart:

    (a) the policies genuinely fail, or
    (b) our scoring harness cannot detect a success even when one happens

Until (b) is excluded, every negative result in this project is uninterpretable.
That is what this script settles.

It runs LeIsaac's OWN scripted state machine - the same one that produced this
project's 12 completed place operations, so it is KNOWN to succeed - and scores
it with the SAME ground-truth code path used by
`sim_policy_eval_instrumented.py`:

    obs_dict["subtask_terms"]["pick_orangeNNN"]
    obs_dict["subtask_terms"]["put_orangeNNN_to_plate"]
    d_min / d_grasp_min / per-orange positions

EXPECTED: pick_* and put_*_to_plate BOTH go True, and the oranges MOVE.

    they fire            -> the harness works; every prior failure is real
    they never fire      -> THE HARNESS IS BROKEN and every number reported
                            from it - including the Pi05 baseline - is void

Note the action space differs from the policy runs by design: the state machine
drives `so101_state_machine` (8-dim EE-pose actions), while policies drive
`so101leader` (6-DoF joint actions). That is fine and is the point - we are
validating the SCORING path, not the action path. `sim_action_path_check.py`
already validated the 6-DoF action path separately.

Usage
-----
    cd ~/sim/leisaac-src
    LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y \
    PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
    ~/sim/leisaac-venv/bin/python -u <...>/sim_harness_positive_control.py \
        --max_steps=3000 --out=<...>/logs/positive_control.csv
"""

import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", default="LeIsaac-SO101-PickOrange-v0")
parser.add_argument("--device", default="cuda")
parser.add_argument("--max_steps", type=int, default=3000)
parser.add_argument("--out", default="logs/positive_control.csv")
args = parser.parse_args()

from isaaclab.app import AppLauncher  # noqa: E402

app_launcher = AppLauncher(headless=False, enable_cameras=True)
simulation_app = app_launcher.app

import csv  # noqa: E402
from pathlib import Path  # noqa: E402

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

import leisaac  # noqa: F401,E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from leisaac.datagen.state_machine import PickOrangeStateMachine  # noqa: E402
from leisaac.utils.env_utils import dynamic_reset_gripper_effort_limit_sim  # noqa: E402

ORANGES = ["Orange001", "Orange002", "Orange003"]


def main() -> None:
    env_cfg = parse_env_cfg(args.task, device=args.device, num_envs=1)
    # The state machine emits 8-dim EE-pose actions, so it needs this teleop
    # device - NOT the "so101leader" 6-DoF joint mode the policies use.
    env_cfg.use_teleop_device("so101_state_machine")

    # The recorder defaults to EXPORT_ALL, which opens an HDF5 for writing and
    # fails with "unable to lock file" if anything else holds it - and would
    # otherwise dump another multi-GB dataset we do not want. We only need the
    # scored CSV, so turn the export off.
    from isaaclab.managers import DatasetExportMode

    if getattr(env_cfg, "recorders", None) is not None:
        env_cfg.recorders.dataset_export_mode = DatasetExportMode.EXPORT_NONE

    # Let the scripted run go as long as it needs rather than being cut short.
    if hasattr(env_cfg, "terminations") and hasattr(env_cfg.terminations, "time_out"):
        env_cfg.terminations.time_out = None
    env_cfg.never_time_out = True

    env = gym.make(args.task, cfg=env_cfg).unwrapped

    # Takes num_oranges (int), NOT the env - passing env sets _num_oranges=env and
    # dies later with "'<' not supported between 'int' and 'ManagerBasedRLEnv'".
    sm = PickOrangeStateMachine(len(ORANGES))
    obs_dict, _ = env.reset()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["step", "ee_x", "ee_y", "ee_z", "d_min", "d_grasp_min"]
    fields += [f"o{i}_{a}" for i in (1, 2, 3) for a in ("x", "y", "z")]
    fields += [f"pick_{o.lower()}" for o in ORANGES] + [f"put_{o.lower()}_to_plate" for o in ORANGES]

    step = 0
    with open(out_path, "w", newline="") as handle, torch.inference_mode():
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        while simulation_app.is_running() and step < args.max_steps:
            if env.cfg.dynamic_reset_gripper_effort_limit:
                dynamic_reset_gripper_effort_limit_sim(env, args.device)

            if sm.is_episode_done:
                print(f"[pc] episode done at step {step}; resetting")
                obs_dict, _ = env.reset()
                sm.reset()
                continue

            sm.pre_step(env)
            actions = sm.get_action(env)
            obs_dict, _, _, _, _ = env.step(actions)
            sm.advance()

            # ---- IDENTICAL GT PATH to sim_policy_eval_instrumented.py ----
            tgt = env.scene["ee_frame"].data.target_pos_w
            ee = tgt[0, 0]
            grasp_frame = tgt[0, 1] if tgt.shape[1] > 1 else None
            row = {
                "step": step,
                "ee_x": round(float(ee[0]), 4),
                "ee_y": round(float(ee[1]), 4),
                "ee_z": round(float(ee[2]), 4),
            }
            dists = []
            for idx, name in enumerate(ORANGES, start=1):
                pos = env.scene[name].data.root_pos_w[0]
                dists.append(float(torch.linalg.norm(pos - ee)))
                row[f"o{idx}_x"] = round(float(pos[0]), 4)
                row[f"o{idx}_y"] = round(float(pos[1]), 4)
                row[f"o{idx}_z"] = round(float(pos[2]), 4)
            row["d_min"] = round(min(dists), 4)
            if grasp_frame is not None:
                row["d_grasp_min"] = round(
                    min(float(torch.linalg.norm(env.scene[n].data.root_pos_w[0] - grasp_frame)) for n in ORANGES), 4
                )

            subtasks = obs_dict.get("subtask_terms", {})
            for name in ORANGES:
                for key in (f"pick_{name.lower()}", f"put_{name.lower()}_to_plate"):
                    row[key] = int(bool(subtasks.get(key, torch.zeros(1))[0])) if key in subtasks else ""
            writer.writerow(row)

            if step % 200 == 0:
                handle.flush()
                fired = [k for k in row if k.startswith(("pick_", "put_")) and row[k] == 1]
                print(f"[pc] step {step:4d}  d_min={row['d_min']:.3f}  TRUE now: {fired or 'none'}")
            step += 1

    print(f"[pc] wrote {out_path} ({step} steps)")
    env.close()
    simulation_app.close()


if __name__ == "__main__":
    main()
