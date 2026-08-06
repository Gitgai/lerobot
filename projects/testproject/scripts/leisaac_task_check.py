#!/usr/bin/env python3
"""Gate 4: can LeIsaac register and instantiate its SO-101 tasks?

Read-only and headless. No robot, no hardware, no teleop device. Answers, in
order of increasing commitment:

    1. does `import leisaac` work at all?
    2. does it REGISTER its tasks into the gymnasium registry?
    3. can the pick-orange env actually be CONSTRUCTED (loads USD, builds
       physics scene, wires cameras)?

Step 3 is the real one - registration only proves the Python imported.

Context: this is the first test of the SO-101 in simulation. The task
`LeIsaac-SO101-PickOrange-v0` is "pick three oranges and put them into the
plate", i.e. it includes the PLACE phase the real robot has never completed
(0 successes across the whole project - see agent_handoff_pi05_20260803.md
Section 3).

Requires driver 580.x + Isaac Sim 5.1 + Isaac Lab 2.3.0 + LeIsaac 0.4.0.
On driver 595.x Isaac Sim 5.1 segfaults before any of this runs - see
docs/isaac_sim_blackwell_investigation_20260804.md.

Usage:
    cd projects/testproject
    ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES \
        ~/sim/leisaac-venv/bin/python -u scripts/leisaac_task_check.py

Always pass `python -u` - Kit closes stdout during shutdown and buffered prints
are lost, making a successful run look silent.
"""

import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", default="LeIsaac-SO101-PickOrange-v0")
parser.add_argument("--construct", action="store_true", help="also try building the env (slow)")
parser.add_argument("--device", default="cuda")
parser.add_argument("--teleop-device", default="keyboard", help="keyboard | gamepad | so101leader | so101_state_machine")
args = parser.parse_args()

# Use Isaac Lab's AppLauncher, NOT a raw SimulationApp. LeIsaac scenes spawn
# cameras, and isaaclab gates those on the carb setting
# "/isaaclab/cameras_enabled", which ONLY AppLauncher sets. Passing
# {"enable_cameras": True} to SimulationApp does NOT work - it is a different
# flag - and you get:
#   RuntimeError: A camera was spawned without the --enable_cameras flag.
from isaaclab.app import AppLauncher  # noqa: E402

app_launcher = AppLauncher(headless=True, enable_cameras=True)
app = app_launcher.app

import gymnasium as gym  # noqa: E402

# 1. import
try:
    import leisaac  # noqa: F401

    print("IMPORT leisaac    OK")
except Exception as exc:  # noqa: BLE001
    print(f"IMPORT leisaac    FAIL -> {type(exc).__name__}: {str(exc)[:160]}")
    app.close()
    raise SystemExit(1)

# 2. registration
tasks = sorted(k for k in gym.registry if "LeIsaac" in k or "SO101" in k)
print(f"REGISTERED TASKS  {len(tasks)}")
for name in tasks:
    print(f"   {name}")

if args.task in tasks:
    print(f"TARGET TASK       {args.task} present")
else:
    print(f"TARGET TASK       {args.task} NOT FOUND")

# 3. construction - the real test
#
# NOTE: gym.make(task, num_envs=1) does NOT work for Isaac Lab envs. They take a
# dataclass config: build it with parse_env_cfg first, then pass cfg=. Calling
# gym.make without it fails with
#   TypeError: ManagerBasedRLEnv.__init__() missing 1 required positional argument: 'cfg'
if args.construct and args.task in tasks:
    try:
        from isaaclab_tasks.utils import parse_env_cfg

        env_cfg = parse_env_cfg(args.task, device=args.device, num_envs=1)
        print("ENV CFG PARSED    OK")

        # REQUIRED: the task config leaves actions.arm_action and
        # actions.gripper_action as MISSING because they depend on the control
        # mode. use_teleop_device() fills them in. Without this you get:
        #   TypeError: Missing values detected in object PickOrangeEnvCfg
        # Accepts: keyboard | gamepad | so101leader | so101_state_machine
        # (keyboard needs no hardware; so101_state_machine is the automated
        #  data-generation path.)
        env_cfg.use_teleop_device(args.teleop_device)
        print(f"TELEOP DEVICE     {args.teleop_device}")

        env = gym.make(args.task, cfg=env_cfg)
        print("ENV CONSTRUCTED   OK")
        print(f"   action_space      {env.action_space}")
        print(f"   observation_space {type(env.observation_space).__name__}")

        obs, info = env.reset()
        print("ENV RESET         OK")
        if isinstance(obs, dict):
            for key, value in list(obs.items())[:6]:
                shape = getattr(value, "shape", type(value).__name__)
                print(f"   obs[{key}] {shape}")
        env.close()
    except Exception as exc:  # noqa: BLE001
        import traceback

        print(f"ENV CONSTRUCT     FAIL -> {type(exc).__name__}: {str(exc)[:220]}")
        # Omniverse raises ErrorException with an EMPTY message; the useful
        # detail is only in the traceback, so always print it.
        print("--- traceback ---")
        traceback.print_exc()

app.close()
