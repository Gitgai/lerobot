#!/usr/bin/env python3
"""Evaluate a LeRobot policy in LeIsaac and SCORE IT FROM SIMULATOR GROUND TRUTH.

Why this exists
---------------
On the real arm we can only infer what happened, which is why
`analyze_grasp_from_trace.py` uses the finger-stall test (fingers cannot pass
through an object) to tell a real grasp from closing on air. In simulation we do
not have to infer anything - the simulator knows exactly where every object and
joint is. This logs that ground truth per step so a run is scored, not watched.

Project rule this implements: "Never diagnose from video alone, and never from
the command stream alone." Here the equivalent of the trace tool is direct GT.

What it records per step
------------------------
    ee_x/y/z            end-effector position, ee_frame index 0 (tool origin)
    d_orange1..3        distance from THAT frame to each orange
    d_min               distance to the NEAREST orange
    d_grasp_min         distance from ee_frame index 1, THE GRASP POINT - this
                        is the frame mdp.orange_grasped actually tests, and it
                        reads ~0.06-0.07 m shorter than d_min
    gripper_cmd         commanded gripper value from the policy action
    o1/o2/o3 x,y,z      world position of EVERY orange   <- the honesty column
    pick_orangeNNN      GT predicate                     (mdp.orange_grasped)
    put_orangeNNN_to_plate  GT: is it on the plate?      <- the PLACE term

*** DO NOT TRUST pick_* ON ITS OWN ***
mdp.orange_grasped (tasks/pick_orange/mdp/observations.py) is:

    (distance(object, ee_frame[1]) < 0.05)  AND  (gripper_joint < 0.60)

PROXIMITY AND CLOSURE. It tests no contact, no force and no lift. A policy that
parks beside the orange and closes on air scores True indefinitely - GR00T N1.7
scored True for 80 consecutive steps while displacing the orange by 0.0001 m.
That is why o1/o2/o3 are logged: OBJECT DISPLACEMENT is what turns the predicate
into evidence. This is the sim twin of the real-arm finger-stall test.

Reading the result
------------------
    d_min never decreases            -> the policy is not reaching at all
    d_min decreases then plateaus    -> it approaches but cannot grasp
    pick_* True AND the object moves -> a real grasp
    pick_* True and it does NOT move -> closed on air; report it as such
    put_*_to_plate ever True         -> a PLACE happened
    ee position frozen for many steps -> for a RELATIVE-action policy this means
                        it is emitting ~zero deltas, i.e. it believes it is done

IMPORTANT - read failure asymmetrically. This checkpoint was fine-tuned on REAL
camera frames of a specific table. Sim renders, sim lighting and sim camera poses
are all out of distribution, and the `top` camera does not exist in this scene
(pi05 pads and masks it). So:
    success in sim  -> STRONG evidence of generalisation
    failure in sim  -> WEAK evidence; most likely the domain gap, not the model
See community_data_strategy_20260804.md Section 4a.

Usage
-----
Start the policy server first (needs the LeIsaac pickle shim):
    cd ~/lerobot_assets/lerobot_trainingera
    HF_HUB_OFFLINE=1 ./.venv/bin/python <...>/policy_server_leisaac_shim.py \
        --host=0.0.0.0 --port=8080

Then:
    cd ~/sim/leisaac-src
    LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y \
    PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
    ~/sim/leisaac-venv/bin/python -u <...>/sim_policy_eval_instrumented.py \
        --policy_checkpoint_path=$HOME/lerobot_assets/checkpoints/pi05_012000 \
        --max_steps=1200 --out=<...>/logs/pi05_sim_gt.csv
"""

import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", default="LeIsaac-SO101-PickOrange-v0")
parser.add_argument("--device", default="cuda")
parser.add_argument("--policy_type", default="lerobot-pi05")
parser.add_argument("--policy_host", default="localhost")
parser.add_argument("--policy_port", type=int, default=8080)
parser.add_argument("--policy_timeout_ms", type=int, default=30000)
parser.add_argument("--policy_action_horizon", type=int, default=50)
parser.add_argument("--policy_checkpoint_path", default=None,
                    help="LeRobot path only; the GR00T server already holds its own checkpoint.")
parser.add_argument(
    "--policy_language_instruction",
    default=None,
    help="Defaults to the ENV'S OWN cfg.task_description, which is the string a "
    "sim-trained checkpoint was recorded with. Override only to run a deliberate "
    "instruction experiment - never to invent a sentence.",
)
parser.add_argument("--max_steps", type=int, default=1200)
parser.add_argument(
    "--seed",
    type=int,
    default=None,
    help="Seeds the ENV only. NOTE: it does NOT control the policy server's "
    "sampling - GR00T's flow matching draws its own noise in the server process, "
    "so repeated runs differ even at a fixed seed. That is exactly why a success "
    "RATE is needed rather than one run.",
)
parser.add_argument("--out", default="logs/sim_policy_gt.csv")
parser.add_argument("--move-oranges", default=None,
                    help="S1: shift ALL oranges by \"dx,dy,dz\" metres to test whether the reach is object-directed or a positional prior.")
parser.add_argument("--scatter-oranges", default=None,
                    help="Harder than --move-oranges: PER-ORANGE offsets \"dx1,dy1,dx2,dy2,dx3,dy3\" (z unchanged). A uniform shift preserves the objects' relative layout; scattering destroys it.")
parser.add_argument("--move-plate", default=None,
                    help="Shift the PLATE (the goal) by \"dx,dy,dz\" metres. Tests goal perception separately from object perception - the env's own training randomization was only +/-3 cm.")
parser.add_argument("--jitter-camera", default=None,
                    help="Perturb the FRONT camera mount by \"dx,dy,dz\" metres. Measures viewpoint sensitivity, which is exactly the error a real camera mount will have. S2 warns: a wrong view can be worse than none.")
parser.add_argument("--tint", default=None,
                    help="Recolor scene entities: \"Name:r,g,b;Name2:r,g,b\" (0-1 floats). Binds a PreviewSurface material stronger-than-descendants, so it overrides the asset's own textures. Names match prim paths, e.g. Plate, Robot, Orange001.")
parser.add_argument("--light-scale", type=float, default=None,
                    help="Multiply every light's intensity (0.35 = dim evening, 2.5 = blown out).")
parser.add_argument("--light-color", default=None,
                    help="Set every light's color to \"r,g,b\" - warm/cool lighting recolors the WHOLE scene cheaply.")
parser.add_argument("--add-plate", default=None,
                    help="Spawn a SECOND identical plate at \"dx,dy\" from the real one. The GT place term still tracks only the original -> measures whether the policy is goal-ambiguous.")
parser.add_argument("--add-decoys", type=int, default=0,
                    help="Spawn N orange-COLORED spheres near the oranges. We have no other fruit assets; a same-color decoy is the sharper test anyway - does it grab AN ORANGE or anything orange-ish?")
parser.add_argument("--scale-oranges", type=float, default=None,
                    help="Scale the oranges (0.75 = small, 1.3 = large). Changes both the visual and the grasp width needed.")
args = parser.parse_args()

from isaaclab.app import AppLauncher  # noqa: E402

app_launcher = AppLauncher(headless=False, enable_cameras=True)
simulation_app = app_launcher.app

import csv  # noqa: E402
from pathlib import Path  # noqa: E402

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

import leisaac  # noqa: F401,E402  (registers the tasks)
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from leisaac.policy import LeRobotServicePolicyClient  # noqa: E402
from leisaac.utils.env_utils import dynamic_reset_gripper_effort_limit_sim  # noqa: E402

ORANGES = ["Orange001", "Orange002", "Orange003"]

# Task strings taken from the TRAINING DATASET's meta/tasks.jsonl - not from the
# env's cfg.task_description, which differs and is not what a model was trained
# on. Source: LightwheelAI/leisaac-pick-orange (v2.1, 60 eps, front+wrist).
DATASET_TASK_STRINGS = {
    "LeIsaac-SO101-PickOrange-v0": "Grab orange and place into plate",
    "LeIsaac-SO101-PickOrange-Direct-v0": "Grab orange and place into plate",
}


def main() -> None:
    env_cfg = parse_env_cfg(args.task, device=args.device, num_envs=1)
    if args.seed is not None:
        env_cfg.seed = args.seed
        torch.manual_seed(args.seed)
        print(f"[eval] env seed={args.seed} (does NOT bind the policy server's sampling)")
    # MUST match the policy's action space. get_task_type() returns "so101leader"
    # for single-arm SO-101 tasks, which configures 6-DoF JOINT actions - what
    # pi05 emits. Using "so101_state_machine" instead configures 8-dim EE-pose
    # actions and fails with:
    #   ValueError: Invalid action shape, expected: 8, received: 6
    from leisaac.utils.env_utils import get_task_type

    task_type = get_task_type(args.task)
    print(f"[eval] task_type={task_type}")
    env_cfg.use_teleop_device(task_type)

    # THE INSTRUCTION IS NOT A FREE PARAMETER. Every LeIsaac task declares its own
    # cfg.task_description, and that is the string recorded into any dataset
    # collected in this scene - so it is what a sim-trained checkpoint saw. For
    # PickOrange it is:
    #   "Pick three oranges and put them into the plate, then reset the arm to
    #    rest state."
    # Runs up to 2026-08-05 sent an INVENTED sentence ("pick up the orange and
    # move it to another place") that appears nowhere in the env or any dataset,
    # and instruction wording measurably changes behaviour. Read it from the env.
    if args.policy_language_instruction is None:
        # PREFER THE DATASET STRING. The env's task_description and the string in
        # the training dataset's meta/tasks.jsonl are DIFFERENT, and the dataset
        # one is what a trained model actually saw:
        #   env     "Pick three oranges and put them into the plate, then reset
        #            the arm to rest state."
        #   dataset "Grab orange and place into plate"   (LightwheelAI/leisaac-
        #            pick-orange, the reference corpus for this scene)
        # Measured on GR00T N1.7, 900 steps each: the dataset string gave the
        # closest approach (d_min 0.100) and the ONLY run that moved the orange
        # (0.023 m); the invented string moved it 0.000 m.
        args.policy_language_instruction = DATASET_TASK_STRINGS.get(args.task) or getattr(
            env_cfg, "task_description", None
        )
        if not args.policy_language_instruction:
            raise RuntimeError(f"{args.task} has no known task string; pass --policy_language_instruction")
        print(f"[eval] instruction: {args.policy_language_instruction!r}")
    else:
        print(f"[eval] instruction OVERRIDDEN: {args.policy_language_instruction!r}")

    # S1: shift the oranges to test whether the policy's reach is
    # OBJECT-DIRECTED or merely a learned positional prior. Each scene object is
    # a RigidObjectCfg on env_cfg.scene carrying init_state.pos taken from the
    # USD (see leisaac/utils/general_assets.py parse_usd_and_create_subassets),
    # so overriding it here moves the object and nothing else.
    # ALL THREE are moved by the same offset, so "nearest orange" stays
    # meaningful - moving only one would just make another the nearest.
    if args.move_oranges:
        dx, dy, dz = (float(v) for v in args.move_oranges.split(","))
        for name in ORANGES:
            cfg = getattr(env_cfg.scene, name, None)
            if cfg is None:
                print(f"[eval] WARNING: {name} not found on scene cfg - not moved")
                continue
            old = cfg.init_state.pos
            cfg.init_state.pos = (old[0] + dx, old[1] + dy, old[2] + dz)
            print(f"[eval] moved {name}: {tuple(round(v, 3) for v in old)} -> "
                  f"{tuple(round(v, 3) for v in cfg.init_state.pos)}")

    if args.scatter_oranges:
        vals = [float(v) for v in args.scatter_oranges.split(",")]
        assert len(vals) == 6, "--scatter-oranges wants dx1,dy1,dx2,dy2,dx3,dy3"
        for (name, dx, dy) in zip(ORANGES, vals[0::2], vals[1::2], strict=True):
            cfg = getattr(env_cfg.scene, name, None)
            if cfg is None:
                continue
            old = cfg.init_state.pos
            cfg.init_state.pos = (old[0] + dx, old[1] + dy, old[2])
            print(f"[eval] scattered {name}: {tuple(round(v, 3) for v in old)} -> "
                  f"{tuple(round(v, 3) for v in cfg.init_state.pos)}")

    if args.move_plate:
        dx, dy, dz = (float(v) for v in args.move_plate.split(","))
        cfg = getattr(env_cfg.scene, "Plate", None)
        if cfg is None:
            print("[eval] WARNING: Plate not found on scene cfg - not moved")
        else:
            old = cfg.init_state.pos
            cfg.init_state.pos = (old[0] + dx, old[1] + dy, old[2] + dz)
            print(f"[eval] moved Plate: {tuple(round(v, 3) for v in old)} -> "
                  f"{tuple(round(v, 3) for v in cfg.init_state.pos)}")

    if args.jitter_camera:
        dx, dy, dz = (float(v) for v in args.jitter_camera.split(","))
        cam = getattr(env_cfg.scene, "front", None)
        if cam is None:
            print("[eval] WARNING: front camera not on scene cfg - not jittered")
        else:
            old = cam.offset.pos
            cam.offset.pos = (old[0] + dx, old[1] + dy, old[2] + dz)
            print(f"[eval] jittered front camera: {tuple(round(v, 3) for v in old)} -> "
                  f"{tuple(round(v, 3) for v in cam.offset.pos)}")

    # ---- CFG-LEVEL scene additions (must happen BEFORE gym.make) ----
    if args.scale_oranges:
        for name in ORANGES:
            cfg = getattr(env_cfg.scene, name, None)
            if cfg is not None:
                cfg.spawn.scale = (args.scale_oranges,) * 3
        print(f"[eval] oranges scaled x{args.scale_oranges}")

    if args.add_plate:
        import copy as _copy

        dx, dy = (float(v) for v in args.add_plate.split(","))
        plate = getattr(env_cfg.scene, "Plate", None)
        if plate is None:
            raise RuntimeError("--add-plate: no Plate on scene cfg")
        plate2 = _copy.deepcopy(plate)
        plate2.prim_path = "{ENV_REGEX_NS}/Plate2"
        old = plate.init_state.pos
        plate2.init_state.pos = (old[0] + dx, old[1] + dy, old[2])
        env_cfg.scene.Plate2 = plate2
        print(f"[eval] second plate at {tuple(round(v, 3) for v in plate2.init_state.pos)} "
              "(GT place term still tracks the ORIGINAL only)")

    if args.add_decoys:
        import isaaclab.sim as sim_utils
        from isaaclab.assets import RigidObjectCfg

        # Offsets fan the decoys out between/around the real oranges.
        offsets = [(0.07, -0.07), (-0.09, 0.06), (0.05, 0.11), (-0.06, -0.10)]
        base = getattr(env_cfg.scene, "Orange001").init_state.pos
        for i in range(min(args.add_decoys, len(offsets))):
            ox, oy = offsets[i]
            decoy = RigidObjectCfg(
                prim_path=f"{{ENV_REGEX_NS}}/Decoy{i + 1}",
                spawn=sim_utils.SphereCfg(
                    radius=0.035,  # ~ the oranges
                    rigid_props=sim_utils.RigidBodyPropertiesCfg(),
                    mass_props=sim_utils.MassPropertiesCfg(mass=0.15),
                    collision_props=sim_utils.CollisionPropertiesCfg(),
                    # orange-fruit colour: the whole point is SAME colour,
                    # different object
                    visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.95, 0.55, 0.12)),
                ),
                init_state=RigidObjectCfg.InitialStateCfg(pos=(base[0] + ox, base[1] + oy, base[2] + 0.02)),
            )
            setattr(env_cfg.scene, f"Decoy{i + 1}", decoy)
        print(f"[eval] {args.add_decoys} orange-coloured decoy spheres added")
    # The recorder defaults to EXPORT_ALL, which opens an HDF5 for writing. We
    # only want the scored CSV, and if ANOTHER sim is still shutting down the two
    # collide with a bewildering
    #   BlockingIOError: unable to lock file, errno = 11
    # that says nothing about recording. Turning the export off removes both the
    # collision and a pointless multi-GB write.
    from isaaclab.managers import DatasetExportMode

    if getattr(env_cfg, "recorders", None) is not None:
        env_cfg.recorders.dataset_export_mode = DatasetExportMode.EXPORT_NONE

    env = gym.make(args.task, cfg=env_cfg).unwrapped

    # ---- STAGE-LEVEL mods (need the live USD stage, i.e. AFTER gym.make) ----
    if args.tint or args.light_scale or args.light_color:
        import omni.usd
        from pxr import Gf, Sdf, UsdShade

        stage = omni.usd.get_context().get_stage()

        if args.tint:
            for spec in args.tint.split(";"):
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
                    raise RuntimeError(f"--tint: no prim ending in /{name} found")
                print(f"[eval] tinted {bound} prim(s) named {name} -> ({r},{g},{b})")

        if args.light_scale or args.light_color:
            changed = 0
            for prim in stage.Traverse():
                if not prim.GetTypeName().endswith("Light"):
                    continue
                if args.light_scale:
                    attr = prim.GetAttribute("inputs:intensity")
                    if attr and attr.Get() is not None:
                        attr.Set(attr.Get() * args.light_scale)
                        changed += 1
                if args.light_color:
                    r, g, b = (float(v) for v in args.light_color.split(","))
                    cattr = prim.GetAttribute("inputs:color")
                    if cattr:
                        cattr.Set(Gf.Vec3f(r, g, b))
            if changed == 0 and args.light_scale:
                raise RuntimeError("--light-scale: no lights found on stage")
            print(f"[eval] lighting adjusted on {changed} light prim(s)")

    from isaaclab.sensors import Camera

    camera_infos = {
        key: sensor.image_shape for key, sensor in env.scene.sensors.items() if isinstance(sensor, Camera)
    }
    print(f"[eval] cameras exposed by the sim: {list(camera_infos)}")
    print("[eval] NOTE: the policy declares front/top/wrist; any missing view is padded and MASKED.")

    # Two serving paths, ONE scoring path - so Pi05 and GR00T numbers are
    # directly comparable (same scene, same ground-truth metrics).
    if args.policy_type == "gr00t-n16":
        # LeIsaac's NATIVE n1.6 client - no adapter of ours in the path. It does
        # the unit conversion (convert_leisaac_action_to_lerobot / ..._to_leisaac)
        # itself and does NOT compose relative actions, which is the correct
        # shape for a server that already applies to_absolute_chunking. That
        # matches what we PROVED for N1.7 by probing the wire (see
        # gr00t_n17_client_adapter.py) and is the strongest reason to prefer this
        # path: it removes our code from the measurement entirely.
        from leisaac.policy import Gr00t16ServicePolicyClient

        gr00t_cameras = [k for k in ("front", "wrist") if k in camera_infos]
        policy = Gr00t16ServicePolicyClient(
            host=args.policy_host,
            port=args.policy_port,
            timeout_ms=args.policy_timeout_ms,
            camera_keys=gr00t_cameras,
        )
        print(f"[eval] GR00T N1.6 via LeIsaac's NATIVE client, cameras={gr00t_cameras}")
    elif args.policy_type.startswith("gr00t"):
        # LeIsaac ships n1.5/n1.6 clients only; N1.7 changed the wire format in
        # seven ways. See scripts/gr00t_n17_client_adapter.py.
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).parent))
        from gr00t_n17_client_adapter import Gr00tN17Client

        # Send ONLY the views the checkpoint declares (conf.yaml video.modality_keys
        # = [front, wrist]). Handing it every camera the scene happens to expose is
        # how run1 ended up feeding an S2 `top` view the model never trained on -
        # the same invented pose that cut Pi05's near-object time 86% -> 23%.
        gr00t_cameras = tuple(k for k in ("front", "wrist") if k in camera_infos)
        missing = tuple(k for k in ("front", "wrist") if k not in camera_infos)
        if missing:
            raise RuntimeError(f"GR00T needs cameras {missing} but the scene exposes {list(camera_infos)}")
        policy = Gr00tN17Client(
            host=args.policy_host,
            port=args.policy_port,
            timeout_ms=args.policy_timeout_ms,
            camera_keys=gr00t_cameras,
        )
        print(f"[eval] GR00T N1.7 client, cameras={gr00t_cameras} (scene has {list(camera_infos)})")
    else:
        policy = LeRobotServicePolicyClient(
            host=args.policy_host,
            port=args.policy_port,
            timeout_ms=args.policy_timeout_ms,
            camera_infos=camera_infos,
            task_type=task_type,
            policy_type=args.policy_type.split("-")[1],
            pretrained_name_or_path=args.policy_checkpoint_path,
            actions_per_chunk=args.policy_action_horizon,
            device=args.device,
        )

    obs_dict, _ = env.reset()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fields = ["step", "ee_x", "ee_y", "ee_z", "d_orange1", "d_orange2", "d_orange3", "d_min", "d_grasp_min", "gripper_cmd"]
    fields += [f"o{i}_{a}" for i in (1, 2, 3) for a in ("x", "y", "z")]
    fields += [f"pick_{o.lower()}" for o in ORANGES] + [f"put_{o.lower()}_to_plate" for o in ORANGES]

    step = 0
    with open(out_path, "w", newline="") as handle, torch.inference_mode():
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        while simulation_app.is_running() and step < args.max_steps:
            policy_obs = obs_dict["policy"]
            policy_obs = dict(policy_obs)
            policy_obs["task_description"] = args.policy_language_instruction
            actions = policy.get_action(policy_obs).to(env.device)
            if args.policy_type.startswith("gr00t") and actions.ndim == 2:
                # The adapter returns [T, DOF]; the env loop below wants LeRobot's
                # [T, 1, DOF]. (A flat [1, T*DOF] is also tolerated.)
                dof = env.action_space.shape[-1]
                actions = actions.reshape(-1, dof).unsqueeze(1)

            for i in range(min(args.policy_action_horizon, actions.shape[0])):
                if step >= args.max_steps:
                    break
                action = actions[i, :, :]
                if env.cfg.dynamic_reset_gripper_effort_limit:
                    dynamic_reset_gripper_effort_limit_sim(env, task_type)
                obs_dict, _, terminated, timed_out, _ = env.step(action)

                # ---- GROUND TRUTH ----
                # TWO frames matter and they are NOT the same point:
                #   index 0 = tool origin  -> what d_min reports
                #   index 1 = GRASP point  -> what mdp.orange_grasped actually
                #             tests (pos_diff < 0.05 AND gripper joint < 0.60,
                #             tasks/pick_orange/mdp/observations.py)
                # Using index 0 alone makes a legitimate grasp look impossible:
                # run3 fired the GT term at d_min=0.092 m because the GRASP frame
                # was inside 0.05 m. Log both so a grasp can be judged honestly.
                grasp_frame = None
                if "ee_frame" in env.scene.keys():
                    tgt = env.scene["ee_frame"].data.target_pos_w
                    ee = tgt[0, 0]
                    grasp_frame = tgt[0, 1] if tgt.shape[1] > 1 else None
                else:
                    ee = obs_dict["policy"]["ee_frame_state"][0, :3]
                row = {
                    "step": step,
                    "ee_x": round(float(ee[0]), 4),
                    "ee_y": round(float(ee[1]), 4),
                    "ee_z": round(float(ee[2]), 4),
                    "gripper_cmd": round(float(action[0, -1]), 4),
                }
                distances = []
                for idx, name in enumerate(ORANGES, start=1):
                    pos = env.scene[name].data.root_pos_w[0]
                    dist = float(torch.linalg.norm(pos - ee))
                    distances.append(dist)
                    row[f"d_orange{idx}"] = round(dist, 4)
                row["d_min"] = round(min(distances), 4)
                # Log EVERY orange's position: "did the object actually move with
                # the gripper" is the check that separates a real grasp from the
                # gripper closing near it - and run3 grasped Orange002 while only
                # Orange001 was being logged, so that check was impossible.
                for idx, name in enumerate(ORANGES, start=1):
                    pos = env.scene[name].data.root_pos_w[0]
                    row[f"o{idx}_x"] = round(float(pos[0]), 4)
                    row[f"o{idx}_y"] = round(float(pos[1]), 4)
                    row[f"o{idx}_z"] = round(float(pos[2]), 4)
                if grasp_frame is not None:
                    row["d_grasp_min"] = round(
                        min(
                            float(torch.linalg.norm(env.scene[n].data.root_pos_w[0] - grasp_frame))
                            for n in ORANGES
                        ),
                        4,
                    )

                subtasks = obs_dict.get("subtask_terms", {})
                for name in ORANGES:
                    key = f"pick_{name.lower()}"
                    place_key = f"put_{name.lower()}_to_plate"
                    row[key] = int(bool(subtasks.get(key, torch.zeros(1))[0])) if key in subtasks else ""
                    row[place_key] = (
                        int(bool(subtasks.get(place_key, torch.zeros(1))[0])) if place_key in subtasks else ""
                    )
                writer.writerow(row)

                if step % 100 == 0:
                    handle.flush()
                    print(f"[eval] step {step:4d}  d_min={row['d_min']:.3f} m  gripper={row['gripper_cmd']:+.2f}")
                step += 1

                if bool(terminated[0]) or bool(timed_out[0]):
                    print(f"[eval] episode ended at step {step} (terminated={bool(terminated[0])})")
                    obs_dict, _ = env.reset()
                    break

    print(f"[eval] wrote {out_path} ({step} steps)")
    env.close()
    simulation_app.close()


if __name__ == "__main__":
    main()
