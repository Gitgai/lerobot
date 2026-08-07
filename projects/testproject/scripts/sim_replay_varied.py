"""Script to replay recorded state-machine demonstrations."""

import multiprocessing

if multiprocessing.get_start_method() != "spawn":
    multiprocessing.set_start_method("spawn", force=True)

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Replay state-machine recorded demonstrations.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
parser.add_argument("--num_envs", type=int, default=1, help="Number of environments to simulate.")
parser.add_argument("--step_hz", type=int, default=60, help="Environment stepping rate in Hz.")
parser.add_argument(
    "--dataset_file", type=str, default="./datasets/dataset.hdf5", help="File path to load recorded demos."
)
parser.add_argument(
    "--replay_mode",
    type=str,
    default="action",
    choices=["action", "state"],
    help="Replay mode: action replays actions, state replays joint states.",
)
parser.add_argument(
    "--select_episodes",
    type=int,
    nargs="+",
    default=[],
    help="List of episode indices to replay. Empty = replay all.",
)
parser.add_argument(
    "--task_type",
    type=str,
    default=None,
    help=(
        "State machine device type used during recording, e.g. 'so101_state_machine' or "
        "'bi_so101_state_machine'. If not set, inferred from the task name."
    ),
)

AppLauncher.add_app_launcher_args(parser)
parser.add_argument("--tint", default=None, help='"Name:r,g,b;..." recolor scene entities to MATCH the recording')
parser.add_argument("--scale-oranges", type=float, default=None)
parser.add_argument("--add-decoys", type=int, default=0)
args_cli = parser.parse_args()

app_launcher = AppLauncher(vars(args_cli))
simulation_app = app_launcher.app

import contextlib
import os
import time

import gymnasium as gym
import torch
from isaaclab.envs import ManagerBasedRLEnv
from isaaclab.utils.datasets import EpisodeData, HDF5DatasetFileHandler
from isaaclab_tasks.utils import parse_env_cfg
from leisaac.utils.env_utils import get_task_type

import leisaac  # noqa: F401


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


def get_next_action(episode_data: EpisodeData, return_state: bool = False, task_type: str = None):
    if return_state:
        next_state = episode_data.get_next_state()
        if next_state is None:
            return None
        if task_type == "bi_so101_state_machine":
            left_joint_pos = next_state["articulation"]["left_arm"]["joint_position"]
            right_joint_pos = next_state["articulation"]["right_arm"]["joint_position"]
            return torch.cat([left_joint_pos, right_joint_pos], dim=0)
        else:
            return next_state["articulation"]["robot"]["joint_position"]
    else:
        return episode_data.get_next_action()


def apply_damping(env, task_type: str):
    """Apply joint damping each step to match state-machine recording behavior."""
    if task_type == "so101_state_machine":
        env.scene["robot"].write_joint_damping_to_sim(damping=10.0)
    elif task_type == "bi_so101_state_machine":
        env.scene["left_arm"].write_joint_damping_to_sim(damping=10.0)
        env.scene["right_arm"].write_joint_damping_to_sim(damping=10.0)


def main():
    if not os.path.exists(args_cli.dataset_file):
        raise FileNotFoundError(f"Dataset file not found: {args_cli.dataset_file}")

    dataset_file_handler = HDF5DatasetFileHandler()
    dataset_file_handler.open(args_cli.dataset_file)
    episode_count = dataset_file_handler.get_num_episodes()

    if episode_count == 0:
        print("No episodes found in the dataset.")
        return

    episode_indices_to_replay = args_cli.select_episodes or list(range(episode_count))
    num_envs = args_cli.num_envs

    task_type = get_task_type(args_cli.task, args_cli.task_type)

    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=num_envs)
    env_cfg.use_teleop_device(task_type)
    env_cfg.recorders = {}
    env_cfg.terminations = {}

    # --- scene variations to MATCH the recording (replays of varied batches
    # need the same spawn-level scene: scaled oranges, decoy objects) ---
    if args_cli.scale_oranges:
        for _n in ("Orange001", "Orange002", "Orange003"):
            getattr(env_cfg.scene, _n).spawn.scale = (args_cli.scale_oranges,) * 3
    if args_cli.add_decoys:
        import isaaclab.sim as sim_utils
        from isaaclab.assets import RigidObjectCfg
        _offsets = [(0.07, -0.07), (-0.09, 0.06)]
        _base = env_cfg.scene.Orange001.init_state.pos
        for _i in range(min(args_cli.add_decoys, len(_offsets))):
            _ox, _oy = _offsets[_i]
            setattr(env_cfg.scene, f"Decoy{_i + 1}", RigidObjectCfg(
                prim_path=f"{{ENV_REGEX_NS}}/Decoy{_i + 1}",
                spawn=sim_utils.SphereCfg(radius=0.035,
                    rigid_props=sim_utils.RigidBodyPropertiesCfg(),
                    mass_props=sim_utils.MassPropertiesCfg(mass=0.15),
                    collision_props=sim_utils.CollisionPropertiesCfg(),
                    visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.95, 0.55, 0.12))),
                init_state=RigidObjectCfg.InitialStateCfg(pos=(_base[0] + _ox, _base[1] + _oy, _base[2] + 0.02))))

    env: ManagerBasedRLEnv = gym.make(args_cli.task, cfg=env_cfg).unwrapped

    # Disable gravity for all robot link prims (matches state-machine recording setup).
    import omni.usd
    from pxr import PhysxSchema, UsdPhysics

    _stage = omni.usd.get_context().get_stage()
    for _prim in _stage.Traverse():
        if "Robot" in str(_prim.GetPath()) and _prim.HasAPI(UsdPhysics.RigidBodyAPI):
            PhysxSchema.PhysxRigidBodyAPI.Apply(_prim).CreateDisableGravityAttr(True)

    if args_cli.tint:
        from pxr import Gf, Sdf, UsdShade
        for _spec in args_cli.tint.split(";"):
            _name, _rgb = _spec.split(":")
            _r, _g, _b = (float(v) for v in _rgb.split(","))
            _mp = Sdf.Path(f"/World/Looks/tint_{_name}")
            _mat = UsdShade.Material.Define(_stage, _mp)
            _sh = UsdShade.Shader.Define(_stage, _mp.AppendChild("shader"))
            _sh.CreateIdAttr("UsdPreviewSurface")
            _sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(_r, _g, _b))
            _mat.CreateSurfaceOutput().ConnectToSource(_sh.ConnectableAPI(), "surface")
            for _p2 in _stage.Traverse():
                if _p2.GetPath().pathString.endswith(f"/{_name}"):
                    UsdShade.MaterialBindingAPI.Apply(_p2).Bind(
                        _mat, bindingStrength=UsdShade.Tokens.strongerThanDescendants)
        print(f"[replay] tints applied: {args_cli.tint}")

    idle_action = torch.zeros(env.action_space.shape)

    if hasattr(env, "initialize"):
        env.initialize()
    env.reset()

    rate_limiter = RateLimiter(args_cli.step_hz)
    episode_names = list(dataset_file_handler.get_episode_names())
    replayed_episode_count = 0

    with contextlib.suppress(KeyboardInterrupt) and torch.inference_mode():
        while simulation_app.is_running() and not simulation_app.is_exiting():
            env_episode_data_map = {i: EpisodeData() for i in range(num_envs)}
            has_next_action = True
            while has_next_action:
                actions = idle_action
                has_next_action = False
                for env_id in range(num_envs):
                    env_next_action = get_next_action(
                        env_episode_data_map[env_id],
                        return_state=args_cli.replay_mode == "state",
                        task_type=task_type,
                    )
                    if env_next_action is None:
                        next_episode_index = None
                        while episode_indices_to_replay:
                            next_episode_index = episode_indices_to_replay.pop(0)
                            if next_episode_index < episode_count:
                                break
                            next_episode_index = None

                        if next_episode_index is not None:
                            replayed_episode_count += 1
                            print(f"{replayed_episode_count:4}: Loading #{next_episode_index} episode to env_{env_id}")
                            episode_data = dataset_file_handler.load_episode(
                                episode_names[next_episode_index], env.device
                            )
                            env_episode_data_map[env_id] = episode_data
                            initial_state = episode_data.get_initial_state()
                            env.reset_to(
                                initial_state,
                                torch.tensor([env_id], device=env.device),
                                seed=int(episode_data.seed) if episode_data.seed is not None else None,
                                is_relative=True,
                            )
                            env_next_action = get_next_action(
                                env_episode_data_map[env_id],
                                return_state=args_cli.replay_mode == "state",
                                task_type=task_type,
                            )
                            has_next_action = True
                        else:
                            continue
                    else:
                        has_next_action = True
                    actions[env_id] = env_next_action

                # Apply damping every step to match state-machine recording behavior.
                apply_damping(env, task_type)

                env.step(actions)
                rate_limiter.sleep(env)
            break

    print(f"Finished replaying {replayed_episode_count} episode{'s' if replayed_episode_count != 1 else ''}.")
    env.close()


if __name__ == "__main__":
    main()
