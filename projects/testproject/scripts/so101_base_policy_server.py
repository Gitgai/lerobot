#!/usr/bin/env python3
"""W0 "policy wrapper": serve the public SO-101 pi0.5 checkpoint (dongyoonkim/so101-pi05-base, VLASH stack)
behind LeRobot's gRPC async policy server, so LeIsaac's `--policy_type=lerobot-pi05` client (and any other
LeRobot async client) can drive it unchanged.

Run inside /home/kiran/sim/vlash-venv (LeRobot 0.4.1 + VLASH @22cbabfe + the author's patches):
    CUDA_VISIBLE_DEVICES=1 python so101_base_policy_server.py --host 0.0.0.0 --port 8080 \
        --ckpt /mnt/data4tb/huggingface-cache/models--dongyoonkim--so101-pi05-base/snapshots/<hash> [--compile]

What it changes relative to the stock server (everything else is the stock 0.4.1 code path):
  * module aliases so LeIsaac's pickles (pinned to lerobot 0.4.2's `lerobot.scripts.server.helpers`) load here,
    and ours load there (same trick as scripts/policy_server_leisaac_shim.py);
  * SendPolicyInstructions loads the VLASH PI05 policy from --ckpt (the client's checkpoint path is ignored and
    logged) with empty_cameras=1 (third slot = masked black dummy), n_action_steps = client's actions_per_chunk;
  * no LeRobot pre/post-processor: VLASH's predict_action_chunk normalises inputs and un-normalises outputs
    itself (verified in R1), so the observation is mapped by hand:
        front  -> observation.images.base_0_rgb        wrist -> observation.images.left_wrist_0_rgb
        <joint>.pos x6 (LeIsaac/LeRobot order)  -> observation.state (1,6)      task -> task (str)
  * per-call timing and the first action vs. the state are logged, so a mapping bug shows up immediately.
"""
import argparse, logging, pickle, sys, time, types
import numpy as np, torch

import os
JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
SLOTS = {"front": "observation.images.base_0_rgb", "wrist": "observation.images.left_wrist_0_rgb"}
RECORD_DIR = os.environ.get("RECORD_DIR", "")          # if set: JPEG frame pairs every RECORD_EVERY calls + calls.csv
RECORD_EVERY = int(os.environ.get("RECORD_EVERY", "5"))


def alias_modules():
    """LeIsaac pins its pickled classes to lerobot.scripts.server.helpers; our helpers are lerobot.async_inference.helpers."""
    from lerobot.async_inference import helpers as H
    path = "lerobot.scripts.server.helpers"
    parts = path.split(".")
    for i in range(1, len(parts) + 1):
        sub = ".".join(parts[:i])
        if sub not in sys.modules:
            m = types.ModuleType(sub); sys.modules[sub] = m
    for name in ("RemotePolicyConfig", "TimedObservation", "TimedAction", "TimedData", "PolicyFeature", "FeatureType"):
        if hasattr(H, name):
            setattr(sys.modules[path], name, getattr(H, name))
    # field LeIsaac's copy of RemotePolicyConfig never sends
    H.RemotePolicyConfig.rename_map = {}
    # pickles WE send must land in the client's module layout
    for name in ("TimedAction", "TimedData"):
        getattr(H, name).__module__ = path
    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0"); ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--ckpt", required=True); ap.add_argument("--compile", action="store_true")
    ap.add_argument("--num-inference-steps", type=int, default=15)
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--inference-latency", type=float, default=1 / 30)
    ap.add_argument("--obs-queue-timeout", type=float, default=2.0)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    H = alias_modules()
    from lerobot.async_inference import policy_server as PS
    from lerobot.async_inference.configs import PolicyServerConfig
    from lerobot.async_inference.helpers import TimedObservation
    from lerobot.transport import services_pb2
    from vlash.policies.factory import get_policy_class
    import vlash.policies.pi05.configuration_pi05  # noqa: F401 (registers 'pi05' with VLASH's config)
    from lerobot.configs.policies import PreTrainedConfig

    log = logging.getLogger("so101_base_server")

    class Server(PS.PolicyServer):
        def SendPolicyInstructions(self, request, context):  # noqa: N802
            specs = pickle.loads(request.data)  # nosec - trusted client on our own network
            log.info("client policy request: type=%s path=%s actions_per_chunk=%s device=%s (path IGNORED, serving %s)",
                     specs.policy_type, specs.pretrained_name_or_path, specs.actions_per_chunk, specs.device, a.ckpt)
            # Reply pickles must use the module layout THIS client has: LeIsaac pins lerobot.scripts.server.helpers
            # (0.4.2 layout); a stock LeRobot 0.4.x bench client expects lerobot.async_inference.helpers.
            client_layout = type(specs).__module__
            for name in ("TimedAction", "TimedData"):
                getattr(H, name).__module__ = client_layout
            log.info("reply pickle layout set to %s", client_layout)
            self.device = "cuda"; self.policy_type = "pi05"
            self.lerobot_features = specs.lerobot_features; self.actions_per_chunk = int(specs.actions_per_chunk)
            if getattr(self, "policy", None) is None:
                cfg = PreTrainedConfig.from_pretrained(a.ckpt)
                cfg.empty_cameras = 2; cfg.device = "cuda"; cfg.compile_model = bool(a.compile)   # fill up to 2 missing slots (1- or 2-camera clients)
                cfg.n_action_steps = min(self.actions_per_chunk, cfg.chunk_size); cfg.num_inference_steps = a.num_inference_steps
                t0 = time.perf_counter()
                self.policy = get_policy_class(cfg.type).from_pretrained(a.ckpt, config=cfg); self.policy.eval()
                log.info("VLASH pi05 loaded in %.1fs: chunk %d, n_action_steps %d, infer steps %d, compile %s",
                         time.perf_counter() - t0, cfg.chunk_size, cfg.n_action_steps, cfg.num_inference_steps, a.compile)
                # warm-up (compile) on a dummy observation so the first real call is not minutes long
                dummy = {v: torch.zeros(1, 3, 480, 640, device="cuda") for v in SLOTS.values()}
                dummy["observation.state"] = torch.zeros(1, 6, device="cuda"); dummy["task"] = "warm up"
                with torch.inference_mode():
                    for _ in range(3): self.policy.predict_action_chunk(dummy)
                log.info("warm-up done")
            self.preprocessor = None; self.postprocessor = None
            # per-connection counter for logging; the RECORDING index never resets (a reset made later runs
            # overwrite earlier runs' frames — found 2026-10-19), and each connection gets its own prefix
            self._n = 0
            self._conn = getattr(self, "_conn", 0) + 1
            self._rec = getattr(self, "_rec", 0)
            return services_pb2.Empty()

        def _predict_action_chunk(self, observation_t: TimedObservation):
            raw = observation_t.get_observation(); t0 = time.perf_counter()
            obs = {}
            # camera keys vary per environment: pick the external and the wrist view by name; missing slots are
            # filled with masked dummies by the policy (empty_cameras). Found 2026-10-19: LeIsaac LiftCube sends no
            # "wrist" key, the old code raised KeyError and the client silently replayed its last action.
            # JPEG bytes (bench client over a slow link) → decode to HxWx3 RGB first
            for k, v in list(raw.items()):
                if isinstance(v, (bytes, bytearray)) and len(v) > 1000 and v[:2] == b"\xff\xd8":
                    import cv2
                    bgr = cv2.imdecode(np.frombuffer(v, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if bgr is not None: raw[k] = np.ascontiguousarray(bgr[:, :, ::-1])
            img_keys = [k for k, v in raw.items() if hasattr(v, "shape") and getattr(v, "ndim", 0) == 3 and v.shape[-1] == 3]
            is_wrist = lambda k: any(t in k.lower() for t in ("wrist", "handeye", "gripper", "endeff", "hand", "ego"))
            wrist_keys = [k for k in img_keys if is_wrist(k)]; ext_keys = [k for k in img_keys if not is_wrist(k)]
            mapping = {}
            if ext_keys: mapping[ext_keys[0]] = "observation.images.base_0_rgb"
            if wrist_keys: mapping[wrist_keys[0]] = "observation.images.left_wrist_0_rgb"
            elif len(ext_keys) > 1: mapping[ext_keys[1]] = "observation.images.left_wrist_0_rgb"   # second external view in the wrist slot (as the corpus did)
            if not hasattr(self, "_mapping_logged") or self._mapping_logged != mapping:
                log.info("camera mapping for this client: %s (image keys seen: %s)", mapping, img_keys); self._mapping_logged = mapping
            for k, slot in mapping.items():
                img = raw[k]
                if not isinstance(img, torch.Tensor): img = torch.from_numpy(np.ascontiguousarray(img))
                if img.ndim == 3 and img.shape[-1] == 3: img = img.permute(2, 0, 1)       # HWC -> CHW
                obs[slot] = (img.float() / 255.0).unsqueeze(0).cuda(non_blocking=True)
            state = torch.tensor([[float(raw[f"{j}.pos"]) for j in JOINTS]], dtype=torch.float32, device="cuda")
            obs["observation.state"] = state
            obs["task"] = str(raw.get("task", ""))
            with torch.inference_mode():
                chunk = self.policy.predict_action_chunk(obs)                                   # (1, n, 6), joint units
            if chunk.ndim == 2: chunk = chunk.unsqueeze(0)
            chunk = chunk[:, : self.actions_per_chunk, :].float().cpu()
            actions = list(chunk.squeeze(0))
            dt = time.perf_counter() - t0; self._n += 1
            a0 = actions[0].numpy(); s0 = state[0].cpu().numpy()
            # optional recording for review: every RECORD_EVERY-th call, the two images as JPEG + a CSV row per call
            if RECORD_DIR:
                import csv, os
                from PIL import Image
                os.makedirs(RECORD_DIR, exist_ok=True)
                self._rec = getattr(self, "_rec", 0) + 1
                if self._n % RECORD_EVERY == 1 or RECORD_EVERY == 1:
                    for k in mapping:                                   # only the cameras this client actually sends
                        img = raw[k]; img = img.cpu().numpy() if isinstance(img, torch.Tensor) else np.asarray(img)
                        Image.fromarray(img.astype(np.uint8)).save(os.path.join(RECORD_DIR, f"c{getattr(self, '_conn', 0):02d}_call{self._n:06d}_{k}.jpg"), quality=85)
                with open(os.path.join(RECORD_DIR, "calls.csv"), "a", newline="") as f:
                    csv.writer(f).writerow([getattr(self, "_conn", 0), self._n, round(time.time(), 3), round(1000 * dt, 1), obs["task"]] + np.round(s0, 2).tolist() + np.round(a0, 2).tolist())
            if self._n <= 5 or self._n % 50 == 0:
                log.info("call %d: %.0f ms | task=%r | state=%s | a0=%s | max|a0-s|=%.1f | n=%d",
                         self._n, 1000 * dt, obs["task"][:60], np.round(s0, 1).tolist(), np.round(a0, 1).tolist(),
                         float(np.abs(a0 - s0).max()), len(actions))
            else:
                log.info("call %d: %.0f ms", self._n, 1000 * dt)
            return self._time_action_chunk(observation_t.get_timestamp(), actions, observation_t.get_timestep())

    cfg = PolicyServerConfig(host=a.host, port=a.port, fps=a.fps, inference_latency=a.inference_latency,
                             obs_queue_timeout=a.obs_queue_timeout)
    server = Server(cfg)
    PS.serve(cfg, server_instance=server) if "server_instance" in PS.serve.__code__.co_varnames else _serve(PS, server, cfg)


def _serve(PS, server, cfg):
    """Mirror of lerobot 0.4.1 policy_server.serve() but with our subclass instance."""
    import grpc
    from concurrent import futures
    from lerobot.transport import services_pb2_grpc
    s = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    services_pb2_grpc.add_AsyncInferenceServicer_to_server(server, s)
    s.add_insecure_port(f"{cfg.host}:{cfg.port}")
    logging.getLogger("so101_base_server").info("PolicyServer started on %s:%s", cfg.host, cfg.port)
    s.start()
    try:
        s.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(); s.stop(0)


if __name__ == "__main__":
    main()
