#!/usr/bin/env python3
"""R2b rungs 4-5: drive a MuJoCo EnvHub SO-101 environment with the public pi0.5 checkpoint served by our wrapper
(scripts/so101_base_policy_server.py, LeRobot gRPC async protocol). Non-pipelined: execute the chunk, then ask again.
Run inside /home/kiran/sim/mujoco-envhub-venv312:
  python mujoco_envhub_eval.py --env namenu --episodes 50 --port 8081 --instruction "Pick the orange cube and place it in the green target zone." --out results_mj_pickplace.jsonl
  python mujoco_envhub_eval.py --env nexus:MuJoCoPickLift-v1 --episodes 50 --port 8081 --out results_nexus_picklift.jsonl
Units: the wrapper expects LeRobot motor units (body joints in degrees, gripper 0-100) in and out.
  namenu: observation agent_pos is degrees (its env converts rad->deg), actions are degrees in the MJCF ctrlrange -> pass through.
  nexus:  agent_pos / actions are radians -> so101_nexus.sim_qpos_to_dataset_row / dataset_row_to_sim_qpos.
Cameras: the external view -> "front" (base_0_rgb), the wrist/second view -> "wrist" (left_wrist_0_rgb).
"""

import argparse
import json
import pickle
import sys
import time
import types

import grpc
import numpy as np

MAX_STEPS = 0
JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
ENVS = {
    "namenu": dict(
        hub="/mnt/data4tb/huggingface-cache/models--namenu--so101-pick-place-env/snapshots/67f6cb7676cba923c7389b2aaf298c4fd0c07b4d/env.py",
        cams={"front": "up", "wrist": "side"},
        units="lerobot",
        default_instr="Pick the orange cube and place it in the green target zone.",
        hz=20,
        max_steps=200,
    ),
}


def alias_for_pickles():
    """Our pickles must carry module paths the server aliases (lerobot.scripts.server.helpers); we use the real 0.4.1 classes."""
    from lerobot.async_inference import helpers as H

    path = "lerobot.scripts.server.helpers"  # the server re-tags TimedAction/TimedData with this path (LeIsaac's layout)
    parts = path.split(".")
    for i in range(1, len(parts) + 1):
        sub = ".".join(parts[:i])
        if sub not in sys.modules:
            sys.modules[sub] = types.ModuleType(sub)
    for name in ("TimedAction", "TimedData", "TimedObservation", "RemotePolicyConfig"):
        setattr(sys.modules[path], name, getattr(H, name))
    return H


class Client:
    def __init__(self, host, port, actions_per_chunk, cams, H):
        from lerobot.transport import services_pb2, services_pb2_grpc
        from lerobot.transport.utils import grpc_channel_options, send_bytes_in_chunks

        self.pb, self.send_chunks, self.H = services_pb2, send_bytes_in_chunks, H
        self.channel = grpc.insecure_channel(f"{host}:{port}", grpc_channel_options())
        self.stub = services_pb2_grpc.AsyncInferenceStub(self.channel)
        feats = {
            "observation.state": {"dtype": "float32", "shape": (6,), "names": [f"{j}.pos" for j in JOINTS]}
        }
        for k in cams:
            feats[f"observation.images.{k}"] = {
                "dtype": "image",
                "shape": (480, 640, 3),
                "names": ["height", "width", "channels"],
            }
        cfg = H.RemotePolicyConfig("pi05", "/public/so101-pi05-base", feats, actions_per_chunk, "cuda")
        self.stub.Ready(self.pb.Empty())
        self.stub.SendPolicyInstructions(self.pb.PolicySetup(data=pickle.dumps(cfg)))
        self.t = 0

    def act(self, front, wrist, state_lerobot, task):
        raw = {"front": front.astype(np.uint8), "wrist": wrist.astype(np.uint8), "task": task}
        for j, v in zip(JOINTS, state_lerobot):
            raw[f"{j}.pos"] = float(v)
        self.t += 1
        obs = self.H.TimedObservation(timestamp=time.time(), observation=raw, timestep=self.t)
        self.stub.SendObservations(
            self.send_chunks(
                pickle.dumps(obs), self.pb.Observation, log_prefix="[CLIENT] Observation", silent=True
            )
        )
        for _ in range(600):
            r = self.stub.GetActions(self.pb.Empty())
            if len(r.data):
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("no actions from server")
        chunk = pickle.loads(r.data)
        return np.stack(
            [
                a.get_action().numpy() if hasattr(a.get_action(), "numpy") else np.asarray(a.get_action())
                for a in chunk
            ]
        )


def load_env(spec, seed):
    import gymnasium as gym

    if spec == "namenu":
        import importlib.util

        mod_spec = importlib.util.spec_from_file_location("namenu_env", ENVS["namenu"]["hub"])
        mod = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(mod)
        kw = {"max_episode_steps": MAX_STEPS} if MAX_STEPS else {}
        return gym.make("SO101PickPlace-v0", **kw), ENVS["namenu"]
    if spec.startswith("nexus:"):
        env_id = spec.split(":", 1)[1]
        from so101_nexus.envhub import make_env

        d = make_env(n_envs=1, use_async_envs=False, env_id=env_id, obs_type="pixels_agent_pos")
        suite = next(iter(d))
        vec = d[suite][0]
        env = vec.envs[0] if hasattr(vec, "envs") else vec
        return env, dict(
            cams={"front": "overhead", "wrist": "wrist"},
            units="rad",
            default_instr=None,
            hz=None,
            max_steps=None,
        )
    raise SystemExit(f"unknown env {spec}")


def to_lerobot(state, units):
    if units == "lerobot":
        return np.asarray(state, dtype=np.float32)
    from so101_nexus import sim_qpos_to_dataset_row

    return np.asarray(sim_qpos_to_dataset_row(np.asarray(state, dtype=np.float64)), dtype=np.float32)


def from_lerobot(action, units):
    if units == "lerobot":
        return np.asarray(action, dtype=np.float32)
    from so101_nexus import dataset_row_to_sim_qpos

    return np.asarray(dataset_row_to_sim_qpos(np.asarray(action, dtype=np.float64)), dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--episodes", type=int, default=2)
    ap.add_argument("--seed", type=int, default=500)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8081)
    ap.add_argument("--actions-per-chunk", type=int, default=20)
    ap.add_argument("--instruction", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames-dir", default="")
    ap.add_argument(
        "--max-steps", type=int, default=0, help="namenu only: override the registered 200-step time limit"
    )
    a = ap.parse_args()
    global MAX_STEPS
    MAX_STEPS = a.max_steps
    H = alias_for_pickles()
    env, meta = load_env(a.env, a.seed)
    instr = a.instruction or meta["default_instr"]
    client = Client(a.host, a.port, a.actions_per_chunk, meta["cams"], H)
    out = open(a.out, "a")
    k = 0
    for ep in range(a.episodes):
        obs, info = env.reset(seed=a.seed + ep)
        task = (
            instr
            or (info.get("task_description") if isinstance(info, dict) else None)
            or getattr(env.unwrapped, "task_description", "")
            or ""
        )
        steps = calls = 0
        success = False
        t0 = time.time()
        done = False
        while not done:
            pix = obs["pixels"]
            st = to_lerobot(np.asarray(obs["agent_pos"]).reshape(-1)[:6], meta["units"])
            front = np.asarray(pix[meta["cams"]["front"]])
            wrist = np.asarray(pix[meta["cams"]["wrist"]])
            if front.ndim == 4:
                front, wrist = front[0], wrist[0]
            chunk = client.act(front, wrist, st, task)
            calls += 1
            if calls == 1 and ep == 0:
                print(
                    f"[dbg] state(lerobot)={np.round(st, 1).tolist()} a0(lerobot)={np.round(chunk[0], 1).tolist()} task={task!r} img {front.shape}",
                    flush=True,
                )
            for act in chunk:
                obs, rew, term, trunc, info = env.step(from_lerobot(act, meta["units"]))
                steps += 1
                if isinstance(info, dict) and info.get("is_success"):
                    success = True
                if term or trunc:
                    fi = info.get("final_info") if isinstance(info, dict) else None
                    if isinstance(fi, dict) and fi.get("is_success"):
                        success = True
                    done = True
                    break
        k += int(success)
        rec = {
            "episode": ep + 1,
            "success": bool(success),
            "steps": steps,
            "policy_calls": calls,
            "wall_s": round(time.time() - t0, 1),
            "seed": a.seed + ep,
            "env": a.env,
            "instruction": task,
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        out.write(json.dumps(rec) + "\n")
        out.flush()
        print("[RESULT] " + json.dumps(rec), flush=True)
    print(f"[FINAL] {a.env}: {k}/{a.episodes}", flush=True)


if __name__ == "__main__":
    main()
