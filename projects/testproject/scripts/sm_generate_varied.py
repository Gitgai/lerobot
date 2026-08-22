#!/usr/bin/env python3
"""Record state-machine demonstrations under SCENE VARIATIONS.

WHY
---
LeIsaac's scripts/datagen/state_machine/generate.py does the recording (state
machine + recorder + success gating) but has no variation knobs; our variation
code lives in the eval/positive-control scripts but does not record. This is a
FAITHFUL replica of generate.py's flow with the variation flags added:

    cfg side  (before gym.make): --move-oranges --scatter-oranges --move-plate
                                 --scale-oranges --add-decoys
    stage side (after gym.make): --tint  (PreviewSurface, stronger-than-
                                 descendants - overrides asset textures)

Two details the positive-control harness GOT WRONG, replicated correctly here
(they are why the PC's "~56% SM" verdict overstated the demonstrator's
weakness):
    sm.setup(env)      FK calibration - rest pose EE target for the return-home
                       phase and task_done() verification
    gravity disable    on every robot link prim, exactly as generate.py does

EXPORT MODES
    --export all       (default) keep everything, post-filter at conversion
                       time (~2.2 GB/episode of disk). THE ONLY MODE THAT
                       WORKS: "success" (EXPORT_SUCCEEDED_ONLY) hangs the
                       streaming recorder silently on this stack.
    --export success   KNOWN BROKEN HERE - kept for future debugging only

Usage (one batch):
    cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets \
    ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
    ~/sim/leisaac-venv/bin/python -u sm_generate_varied.py \
        --dataset_file ~/sim/leisaac-src/datasets/varied/b2_counterA.hdf5 \
        --num_demos 6 --max_attempts 15 --seed 42 \
        --tint "counter_main_main_group:0.2,0.3,0.8;wall_room:0.2,0.7,0.3"

NEVER commit the HDF5 outputs. Datasets live outside the git tree.
"""

import multiprocessing

if multiprocessing.get_start_method() != "spawn":
    multiprocessing.set_start_method("spawn", force=True)

import argparse
import os
import signal
import time

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="State-machine data generation with scene variations.")
parser.add_argument("--task", default="LeIsaac-SO101-PickOrange-v0")
parser.add_argument("--device", default="cuda")
parser.add_argument("--seed", type=int, default=None)
parser.add_argument("--step_hz", type=int, default=60)
parser.add_argument("--dataset_file", required=True)
parser.add_argument("--num_demos", type=int, default=5, help="successful episodes to record; 0 = unlimited")
parser.add_argument(
    "--max_attempts",
    type=int,
    default=0,
    help="stop after this many EPISODES regardless of success (0 = unlimited). Bounds an overnight batch.",
)
# DEFAULT IS "all": EXPORT_SUCCEEDED_ONLY + StreamingRecorderManager HANGS
# SILENTLY on this stack (100% CPU, no output, diagnosed 2026-08-06 via probe
# markers - "recorder attached" never printed). EXPORT_ALL is the day-1-proven
# path; filter failures at conversion time with the GT criterion instead.
parser.add_argument("--export", choices=("success", "all"), default="all")
# variations
parser.add_argument("--move-oranges", default=None)
parser.add_argument("--scatter-oranges", default=None)
parser.add_argument("--move-plate", default=None)
parser.add_argument("--scale-oranges", type=float, default=None)
parser.add_argument("--add-decoys", type=int, default=0)
parser.add_argument("--tint", default=None)
args_cli = parser.parse_args()

app_launcher = AppLauncher(headless=False, enable_cameras=True)
simulation_app = app_launcher.app

import gymnasium as gym  # noqa: E402
import leisaac  # noqa: F401,E402
import torch  # noqa: E402
from isaaclab.envs import ManagerBasedRLEnv  # noqa: E402
from isaaclab.managers import DatasetExportMode, TerminationTermCfg  # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from leisaac.datagen.state_machine import PickOrangeStateMachine  # noqa: E402
from leisaac.enhance.managers import StreamingRecorderManager  # noqa: E402
from leisaac.utils.env_utils import dynamic_reset_gripper_effort_limit_sim  # noqa: E402

ORANGES = ["Orange001", "Orange002", "Orange003"]


class RateLimiter:
    def __init__(self, hz):
        self.hz = hz
        self.last_time = time.time()
        self.sleep_duration = 1.0 / hz
        self.render_period = min(0.0166, self.sleep_duration)

    def sleep(self, env):
        next_wakeup_time = self.last_time + self.sleep_duration
        while time.time() < next_wakeup_time:
            time.sleep(self.render_period)
            env.sim.render()
        self.last_time = self.last_time + self.sleep_duration
        if self.last_time < time.time():
            while self.last_time < time.time():
                self.last_time += self.sleep_duration


def auto_terminate(env, success: bool):
    env.termination_manager.set_term_cfg(
        "success",
        TerminationTermCfg(
            func=lambda env: (torch.ones if success else torch.zeros)(
                env.num_envs, dtype=torch.bool, device=env.device
            )
        ),
    )
    env.termination_manager.compute()


def apply_cfg_variations(env_cfg) -> None:
    if args_cli.move_oranges:
        dx, dy, dz = (float(v) for v in args_cli.move_oranges.split(","))
        for name in ORANGES:
            cfg = getattr(env_cfg.scene, name)
            old = cfg.init_state.pos
            cfg.init_state.pos = (old[0] + dx, old[1] + dy, old[2] + dz)
    if args_cli.scatter_oranges:
        vals = [float(v) for v in args_cli.scatter_oranges.split(",")]
        for name, dx, dy in zip(ORANGES, vals[0::2], vals[1::2], strict=True):
            cfg = getattr(env_cfg.scene, name)
            old = cfg.init_state.pos
            cfg.init_state.pos = (old[0] + dx, old[1] + dy, old[2])
    if args_cli.move_plate:
        dx, dy, dz = (float(v) for v in args_cli.move_plate.split(","))
        old = env_cfg.scene.Plate.init_state.pos
        env_cfg.scene.Plate.init_state.pos = (old[0] + dx, old[1] + dy, old[2] + dz)
    if args_cli.scale_oranges:
        for name in ORANGES:
            getattr(env_cfg.scene, name).spawn.scale = (args_cli.scale_oranges,) * 3
    if args_cli.add_decoys:
        import isaaclab.sim as sim_utils
        from isaaclab.assets import RigidObjectCfg

        offsets = [(0.07, -0.07), (-0.09, 0.06), (0.05, 0.11), (-0.06, -0.10)]
        base = env_cfg.scene.Orange001.init_state.pos
        for i in range(min(args_cli.add_decoys, len(offsets))):
            ox, oy = offsets[i]
            setattr(
                env_cfg.scene,
                f"Decoy{i + 1}",
                RigidObjectCfg(
                    prim_path=f"{{ENV_REGEX_NS}}/Decoy{i + 1}",
                    spawn=sim_utils.SphereCfg(
                        radius=0.035,
                        rigid_props=sim_utils.RigidBodyPropertiesCfg(),
                        mass_props=sim_utils.MassPropertiesCfg(mass=0.15),
                        collision_props=sim_utils.CollisionPropertiesCfg(),
                        visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.95, 0.55, 0.12)),
                    ),
                    init_state=RigidObjectCfg.InitialStateCfg(
                        pos=(base[0] + ox, base[1] + oy, base[2] + 0.02)
                    ),
                ),
            )


def apply_stage_variations(stage) -> None:
    if not args_cli.tint:
        return
    from pxr import Gf, Sdf, UsdShade

    for spec in args_cli.tint.split(";"):
        name, rgb = spec.split(":")
        r, g, b = (float(v) for v in rgb.split(","))
        mat_path = Sdf.Path(f"/World/Looks/tint_{name}")
        material = UsdShade.Material.Define(stage, mat_path)
        shader = UsdShade.Shader.Define(stage, mat_path.AppendChild("shader"))
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(r, g, b))
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        bound = 0
        for prim in stage.Traverse():
            if prim.GetPath().pathString.endswith(f"/{name}"):
                UsdShade.MaterialBindingAPI.Apply(prim).Bind(
                    material, bindingStrength=UsdShade.Tokens.strongerThanDescendants
                )
                bound += 1
        if bound == 0:
            raise RuntimeError(f"--tint: no prim ending in /{name}")
        print(f"[gen] tinted {bound} prim(s): {name} -> ({r},{g},{b})")


def main() -> None:
    output_dir = os.path.dirname(args_cli.dataset_file)
    output_file_name = os.path.splitext(os.path.basename(args_cli.dataset_file))[0]
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    assert not os.path.exists(args_cli.dataset_file), (
        f"{args_cli.dataset_file} exists - each batch writes a FRESH file"
    )

    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=1)
    env_cfg.use_teleop_device("so101_state_machine")
    env_cfg.seed = args_cli.seed if args_cli.seed is not None else int(time.time())

    if hasattr(env_cfg.terminations, "time_out"):
        env_cfg.terminations.time_out = None
    if hasattr(env_cfg.terminations, "success"):
        env_cfg.terminations.success = None

    apply_cfg_variations(env_cfg)

    # recorder config, exactly as generate.py does it
    env_cfg.recorders.dataset_export_mode = (
        DatasetExportMode.EXPORT_SUCCEEDED_ONLY
        if args_cli.export == "success"
        else DatasetExportMode.EXPORT_ALL
    )
    env_cfg.recorders.dataset_export_dir_path = output_dir
    env_cfg.recorders.dataset_filename = output_file_name
    if not hasattr(env_cfg.terminations, "success"):
        env_cfg.terminations.success = None
    env_cfg.terminations.success = TerminationTermCfg(
        func=lambda env: torch.zeros(env.num_envs, dtype=torch.bool, device=env.device)
    )

    env: ManagerBasedRLEnv = gym.make(args_cli.task, cfg=env_cfg).unwrapped

    # gravity off for robot links (generate.py does this; the PC harness did not)
    import omni.usd
    from pxr import PhysxSchema, UsdPhysics

    stage = omni.usd.get_context().get_stage()
    for prim in stage.Traverse():
        if "Robot" in str(prim.GetPath()) and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateDisableGravityAttr(True)

    apply_stage_variations(stage)

    # streaming HDF5 recorder, as generate.py
    del env.recorder_manager
    env.recorder_manager = StreamingRecorderManager(env_cfg.recorders, env)
    env.recorder_manager.flush_steps = 100
    env.recorder_manager.compression = "lzf"
    print("[gen] recorder attached", flush=True)

    rate_limiter = RateLimiter(args_cli.step_hz)

    sm = PickOrangeStateMachine()
    sm.setup(env)  # FK calibration - the step the PC harness missed
    print("[gen] setup done", flush=True)
    env.reset()
    print("[gen] first reset done", flush=True)
    sm.reset()

    demos = 0
    attempts = 0
    interrupted = False

    def handler(signum, frame):
        nonlocal interrupted
        interrupted = True
        print("\n[gen] SIGINT - cleaning up")

    orig = signal.signal(signal.SIGINT, handler)
    t0 = time.time()

    try:
        while simulation_app.is_running() and not simulation_app.is_exiting() and not interrupted:
            with torch.inference_mode():
                if env.cfg.dynamic_reset_gripper_effort_limit:
                    dynamic_reset_gripper_effort_limit_sim(env, "so101_state_machine")

                if sm.is_episode_done:
                    attempts += 1
                    try:
                        success = sm.check_success(env)
                    except Exception as e:
                        print("[gen] success check failed:", e)
                        success = False
                    auto_terminate(env, success)
                    demos = env.recorder_manager.exported_successful_episode_count
                    rate = demos / attempts if attempts else 0.0
                    hours = (time.time() - t0) / 3600
                    print(
                        f"[gen] episode {attempts}: {'SUCCESS' if success else 'failed'} | "
                        f"kept {demos}/{args_cli.num_demos or '?'} | rate {rate:.0%} | {hours:.2f} h"
                    )
                    if args_cli.num_demos and demos >= args_cli.num_demos:
                        print("[gen] target reached")
                        # BUG FIX (2026-08-07): breaking here WITHOUT a reset
                        # leaves the final successful episode unmarked in the
                        # HDF5 (no success attr -> the converter skips it).
                        # The reset triggers the recorder's export-with-flag.
                        env.reset()
                        break
                    if args_cli.max_attempts and attempts >= args_cli.max_attempts:
                        print("[gen] max attempts reached")
                        break
                    env.reset()
                    sm.reset()
                    auto_terminate(env, False)
                else:
                    sm.pre_step(env)
                    actions = sm.get_action(env)
                    env.step(actions)
                    sm.advance()
                    _steps = getattr(main, "_steps", 0) + 1
                    main._steps = _steps
                    if _steps % 200 == 0:
                        print(f"[gen] step {_steps}", flush=True)
                if rate_limiter:
                    rate_limiter.sleep(env)
    except Exception as e:
        import traceback

        print(f"[gen] ERROR: {e}")
        traceback.print_exc()
    finally:
        signal.signal(signal.SIGINT, orig)
        if hasattr(env.recorder_manager, "finalize"):
            env.recorder_manager.finalize()
        env.close()
        simulation_app.close()
        print(f"[gen] DONE: kept {demos} of {attempts} attempts -> {args_cli.dataset_file}")


if __name__ == "__main__":
    main()
