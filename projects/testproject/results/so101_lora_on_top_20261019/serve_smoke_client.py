#!/usr/bin/env python3
"""One-observation gRPC smoke test against a policy wrapper: sends a real front+wrist frame pair from our dataset and the
matching state, prints the first predicted action and the per-joint delta. Run in /home/kiran/sim/vlash-venv:
  python serve_smoke_client.py --port 8082 --episode 0 --frame 60
Purpose (2026-10-21): prove the patched wrapper serves a LoRA checkpoint whose image slots are named
observation.images.front/.wrist (not base_0_rgb/left_wrist_0_rgb) — the camera mapping log line must show both slots.
"""
import argparse, json, pickle, sys, time, types, pathlib
import numpy as np, grpc, pandas as pd, av

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
DS = pathlib.Path("/home/kiran/lerobot_assets/datasets/orange89_plus_plate20")


def frame(cam, ep, idx):
    with av.open(str(DS / f"videos/chunk-000/observation.images.{cam}/episode_{ep:06d}.mp4")) as c:
        for i, f in enumerate(c.decode(video=0)):
            if i == idx: return f.to_ndarray(format="rgb24")
    raise SystemExit("frame not found")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8082); ap.add_argument("--episode", type=int, default=0); ap.add_argument("--frame", type=int, default=60)
    a = ap.parse_args()
    from lerobot.async_inference import helpers as H
    path = "lerobot.scripts.server.helpers"
    for i in range(1, 5):
        sub = ".".join(path.split(".")[:i]); sys.modules.setdefault(sub, types.ModuleType(sub))
    for n in ("TimedAction", "TimedData", "TimedObservation", "RemotePolicyConfig"): setattr(sys.modules[path], n, getattr(H, n))
    from lerobot.transport import services_pb2, services_pb2_grpc
    from lerobot.transport.utils import grpc_channel_options, send_bytes_in_chunks
    df = pd.read_parquet(DS / f"data/chunk-000/episode_{a.episode:06d}.parquet")
    state = np.asarray(df["observation.state"].iloc[a.frame], dtype=np.float32); next_act = np.asarray(df["action"].iloc[a.frame + 1], dtype=np.float32)
    task = json.loads((DS / "meta/tasks.jsonl").read_text().splitlines()[int(df["task_index"].iloc[a.frame])])["task"]
    front, wrist = frame("front", a.episode, a.frame), frame("wrist", a.episode, a.frame)
    ch = grpc.insecure_channel(f"127.0.0.1:{a.port}", grpc_channel_options()); stub = services_pb2_grpc.AsyncInferenceStub(ch)
    feats = {"observation.state": {"dtype": "float32", "shape": (6,), "names": [f"{j}.pos" for j in JOINTS]},
             "observation.images.front": {"dtype": "image", "shape": (480, 640, 3), "names": ["height", "width", "channels"]},
             "observation.images.wrist": {"dtype": "image", "shape": (480, 640, 3), "names": ["height", "width", "channels"]}}
    stub.Ready(services_pb2.Empty()); stub.SendPolicyInstructions(services_pb2.PolicySetup(data=pickle.dumps(H.RemotePolicyConfig("pi05", "/lora", feats, 20, "cuda"))))
    raw = {"front": front, "wrist": wrist, "task": task}; raw.update({f"{j}.pos": float(v) for j, v in zip(JOINTS, state)})
    t0 = time.time(); stub.SendObservations(send_bytes_in_chunks(pickle.dumps(H.TimedObservation(timestamp=time.time(), observation=raw, timestep=1)), services_pb2.Observation, log_prefix="[CLIENT]", silent=True))
    for _ in range(600):
        r = stub.GetActions(services_pb2.Empty())
        if len(r.data): break
        time.sleep(0.05)
    chunk = np.stack([np.asarray(x.get_action()) for x in pickle.loads(r.data)])
    print(f"task={task!r} ep={a.episode} frame={a.frame}  round trip {1000*(time.time()-t0):.0f} ms  chunk {chunk.shape}")
    print("state     ", state.round(1).tolist()); print("a0        ", chunk[0].round(1).tolist()); print("recorded a", next_act.round(1).tolist())
    print("|a0-state| max", float(np.abs(chunk[0] - state).max()).__round__(2), " |a0-recorded| max", float(np.abs(chunk[0] - next_act).max()).__round__(2))


if __name__ == "__main__":
    main()
