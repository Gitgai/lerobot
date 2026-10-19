#!/usr/bin/env python3
"""Bench client for the SO-101: drives the REAL arm from the public pi0.5 checkpoint served by our wrapper on AI90
(scripts/so101_base_policy_server.py, LeRobot gRPC async protocol) — NON-PIPELINED (stop-and-wait): send one
observation, wait for the 20-step chunk, execute it at --fps, repeat. Nothing moves while a request is in flight.

Runs on the bench machine (the Acer) in a LeRobot 0.4.x environment (lerobot[feetech] + grpcio + opencv):
  python bench_client.py --server 192.168.194.220:8080 --port /dev/ttyACM0 --robot-id follower \
      --front 0 --wrist 2 --task "Grab oranges and place into plate." --episodes 1 --max-chunks 90
  --wrist can also be an MJPEG/HTTP URL (the Pi camera): --wrist http://<pi>:8080/stream.mjpg
Safety: per-step joint change clamped to --max-delta-deg (default 8°) and the gripper to --max-delta-grip; ESC/Ctrl-C
stops immediately; the arm is NOT moved to any pose at start — it starts wherever it is. Keep a hand on the power.
Logs one JSON line per chunk (state, first action, latency) and one per episode to --out.
"""
import argparse, json, pickle, sys, time, types, threading, pathlib
import numpy as np

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def grpc_client(server, actions_per_chunk):
    import grpc
    from lerobot.async_inference import helpers as H
    from lerobot.transport import services_pb2, services_pb2_grpc
    from lerobot.transport.utils import grpc_channel_options, send_bytes_in_chunks
    ch = grpc.insecure_channel(server, grpc_channel_options()); stub = services_pb2_grpc.AsyncInferenceStub(ch)
    feats = {"observation.state": {"dtype": "float32", "shape": (6,), "names": [f"{j}.pos" for j in JOINTS]},
             "observation.images.front": {"dtype": "image", "shape": (480, 640, 3), "names": ["height", "width", "channels"]},
             "observation.images.wrist": {"dtype": "image", "shape": (480, 640, 3), "names": ["height", "width", "channels"]}}
    cfg = H.RemotePolicyConfig("pi05", "/public/so101-pi05-base", feats, actions_per_chunk, "cuda")
    stub.Ready(services_pb2.Empty()); stub.SendPolicyInstructions(services_pb2.PolicySetup(data=pickle.dumps(cfg)))
    state = {"t": 0}

    import cv2
    def jpg(img):   # JPEG over the wire: ~100 KB instead of 920 KB per image; the server decodes bytes back to RGB
        ok, buf = cv2.imencode(".jpg", np.ascontiguousarray(img[:, :, ::-1]), [int(cv2.IMWRITE_JPEG_QUALITY), 85]); return buf.tobytes()

    def act(front, wrist, joints, task):
        raw = {"front": jpg(front), "wrist": jpg(wrist), "task": task}
        for j, v in zip(JOINTS, joints): raw[f"{j}.pos"] = float(v)
        state["t"] += 1
        obs = H.TimedObservation(timestamp=time.time(), observation=raw, timestep=state["t"])
        stub.SendObservations(send_bytes_in_chunks(pickle.dumps(obs), services_pb2.Observation, log_prefix="[CLIENT] Observation", silent=True))
        for _ in range(1200):
            r = stub.GetActions(services_pb2.Empty())
            if len(r.data): break
            time.sleep(0.05)
        else:
            raise RuntimeError("no actions from server within 60 s")
        chunk = pickle.loads(r.data)
        return np.stack([np.asarray(a.get_action()) for a in chunk]).astype(np.float32)
    return act


class Cam:
    """OpenCV device index/path or an MJPEG/HTTP URL; returns HxWx3 RGB uint8 at 640x480."""
    def __init__(self, src, w=640, h=480):
        import cv2
        self.cv2 = cv2
        self.cap = cv2.VideoCapture(int(src) if str(src).isdigit() else src)
        if str(src).isdigit():
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG")); self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w); self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h); self.cap.set(cv2.CAP_PROP_FPS, 30)
        if not self.cap.isOpened(): raise RuntimeError(f"camera {src} did not open")
        self.w, self.h = w, h

    def read(self):
        for _ in range(3): self.cap.grab()                      # drop stale frames
        ok, bgr = self.cap.read()
        if not ok: raise RuntimeError("camera read failed")
        if bgr.shape[1] != self.w or bgr.shape[0] != self.h: bgr = self.cv2.resize(bgr, (self.w, self.h))
        return np.ascontiguousarray(bgr[:, :, ::-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="192.168.194.220:8080"); ap.add_argument("--port", default="/dev/ttyACM0"); ap.add_argument("--robot-id", default="follower")
    ap.add_argument("--front", required=True); ap.add_argument("--wrist", required=True)
    ap.add_argument("--task", default="Grab oranges and place into plate."); ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--actions-per-chunk", type=int, default=20); ap.add_argument("--max-chunks", type=int, default=90, help="per episode (90 x 20 steps at 30 fps = 60 s of motion)")
    ap.add_argument("--episodes", type=int, default=1); ap.add_argument("--max-delta-deg", type=float, default=8.0); ap.add_argument("--max-delta-grip", type=float, default=15.0)
    ap.add_argument("--out", default="bench_log.jsonl"); ap.add_argument("--dry-run", action="store_true", help="read cameras + arm, query the policy, do NOT send actions")
    ap.add_argument("--no-robot", action="store_true", help="dry run without the arm: cameras + network + policy only (state = zeros)")
    a = ap.parse_args()
    if a.no_robot: a.dry_run = True

    robot = None
    if not a.no_robot:
        try:
            from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig        # lerobot 0.5.x (the Acer's rig venv)
        except ImportError:
            from lerobot.robots.so101_follower import SO101Follower, SO101FollowerConfig     # lerobot 0.4.x / 0.6.x
        robot = SO101Follower(SO101FollowerConfig(port=a.port, id=a.robot_id, cameras={}))   # cameras handled here, not by lerobot
        robot.connect(calibrate=False)
    front, wrist = Cam(a.front), Cam(a.wrist)
    act = grpc_client(a.server, a.actions_per_chunk)
    out = open(a.out, "a"); stop = {"flag": False}

    def key_watch():
        try:
            import termios, tty
            fd = sys.stdin.fileno(); old = termios.tcgetattr(fd); tty.setcbreak(fd)
            while not stop["flag"]:
                c = sys.stdin.read(1)
                if c in ("\x1b", "q"): stop["flag"] = True; print("\n[STOP requested]", flush=True)
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception: pass
    threading.Thread(target=key_watch, daemon=True).start()

    def joints_now():
        if robot is None: return np.zeros(6, dtype=np.float32)
        o = robot.get_observation(); return np.array([float(o[f"{j}.pos"]) for j in JOINTS], dtype=np.float32)

    try:
        for ep in range(a.episodes):
            if not a.dry_run:
                print(f"\n=== episode {ep+1}: place the orange, then press Enter (q/ESC stops) ===", flush=True); input()
            t_ep = time.time(); n_chunks = 0; lat = []
            for ci in range(a.max_chunks):
                if stop["flag"]: break
                q = joints_now(); f, w = front.read(), wrist.read()
                t0 = time.time(); chunk = act(f, w, q, a.task); dt = time.time() - t0; lat.append(dt)
                rec = {"ep": ep + 1, "chunk": ci + 1, "latency_s": round(dt, 3), "state": q.round(1).tolist(), "a0": chunk[0].round(1).tolist(), "max_a0_minus_state": float(np.abs(chunk[0] - q).max())}
                out.write(json.dumps(rec) + "\n"); out.flush()
                print(f"chunk {ci+1:3d}  {1000*dt:5.0f} ms  state {q.round(0).tolist()}  a0 {chunk[0].round(0).tolist()}", flush=True)
                if a.dry_run: continue
                prev = q.copy()
                for act_vec in chunk:
                    if stop["flag"]: break
                    tgt = act_vec.copy()
                    d = tgt - prev; lim = np.array([a.max_delta_deg] * 5 + [a.max_delta_grip], dtype=np.float32)
                    tgt = prev + np.clip(d, -lim, lim)                        # per-step clamp
                    robot.send_action({f"{j}.pos": float(v) for j, v in zip(JOINTS, tgt)})
                    prev = tgt; time.sleep(1.0 / a.fps)
                n_chunks += 1
            res = input("result? [s]uccess / [f]ail / [a]bort: ").strip().lower()[:1] if not a.dry_run else "d"
            out.write(json.dumps({"ep": ep + 1, "result": res, "chunks": n_chunks, "wall_s": round(time.time() - t_ep, 1), "latency_median_s": round(float(np.median(lat)), 3) if lat else None, "task": a.task, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n"); out.flush()
            if res == "a": break
    finally:
        stop["flag"] = True
        try:
            if robot is not None: robot.disconnect()
        except Exception: pass


if __name__ == "__main__":
    main()
