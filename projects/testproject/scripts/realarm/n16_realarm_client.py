#!/usr/bin/env python3
"""Real-arm client for the GR00T N1.6 policy server - SINGLE FILE, no gr00t install.

WHY THIS EXISTS
---------------
The arm lives on the OLD machine (gaikwad-prakash@192.168.194.228) whose venv
is the rig's own era (lerobot 0.5.2, so_follower drivers - the environment
that drove this arm before). Installing the Isaac-GR00T stack there for two
small classes is absurd; this file VENDORS them faithfully instead:

    MsgSerializer, PolicyClient   <- gr00t/policy/server_client.py (n1.6-release)
    So100Adapter, eval loop       <- gr00t/eval/real_robot/SO100/eval_so100.py

Vendoring notes (deviations, all deliberate):
  - PolicyClient.get_action == _get_action (BasePolicy validation skipped;
    default strict=False made it non-blocking anyway - wire bytes identical,
    and Stage A's live handshake verified exactly this payload).
  - ModalityConfig decode returns the raw dict (we never call that endpoint).
  - --dry_run: no robot; sends a synthetic observation and prints the action
    chunk - proves network + serialization + server end to end from the arm
    machine before any hardware moves.

USAGE (on the arm machine)
--------------------------
dry run (no robot):
  ~/PrakashProjects/lerobot/lerobot/.venv/bin/python n16_realarm_client.py \
      --policy_host=192.168.194.158 --policy_port=5556 --dry_run=true

real (cameras must be named front/wrist, 640x480; WB LOCKED first):
  ... n16_realarm_client.py \
      --robot.type=so101_follower --robot.port=/dev/ttyACM0 \
      --robot.id=my_so101_follower \
      --robot.cameras="{front: {type: opencv, index_or_path: /dev/videoX, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: /dev/videoY, width: 640, height: 480, fps: 30}}" \
      --policy_host=192.168.194.158 --policy_port=5556 \
      --lang_instruction="Grab orange and place into plate"

Rig spec (measured, priority order): (0) layout match - plate LEFT, oranges
clustered 10-15 cm right; (1) clean table, nothing orange-ish; (2) LOCK white
balance+exposure (v4l2-ctl); (3) ~2 cm mounting slack. Ctrl+C stops.
"""

from dataclasses import dataclass, field
import io
import logging
import time
from typing import Any

import draccus
import msgpack
import numpy as np
import zmq

# ---------------------------------------------------------------- wire format
class MsgSerializer:
    @staticmethod
    def to_bytes(data: Any) -> bytes:
        return msgpack.packb(data, default=MsgSerializer.encode_custom_classes)

    @staticmethod
    def from_bytes(data: bytes) -> Any:
        return msgpack.unpackb(data, object_hook=MsgSerializer.decode_custom_classes)

    @staticmethod
    def decode_custom_classes(obj):
        if not isinstance(obj, dict):
            return obj
        if "__ModalityConfig_class__" in obj:
            return obj["as_json"]  # vendored: raw dict; endpoint unused here
        if "__ndarray_class__" in obj:
            return np.load(io.BytesIO(obj["as_npy"]), allow_pickle=False)
        return obj

    @staticmethod
    def encode_custom_classes(obj):
        if isinstance(obj, np.ndarray):
            output = io.BytesIO()
            np.save(output, obj, allow_pickle=False)
            return {"__ndarray_class__": True, "as_npy": output.getvalue()}
        return obj


def jpeg_frame(rgb: np.ndarray, quality: int = 92) -> dict:
    """Tag an observation image for JPEG transport.

    WHY: 1.76 MiB of raw uint8 per call, and the live run measured 314 ms of the
    615 ms round trip spent purely pushing those bytes NJ<->Pune - against 56 ms
    of actual GPU inference. The pi0.5 pipeline solved this and measured 14.6x
    with 0.4/255 round-trip pixel error at quality 92; the training frames were
    themselves JPEG-compressed, so this matches training conditions rather than
    departing from them.

    Encodes BGR so JPEG's chroma handling sees the channel order it expects; the
    server converts back to RGB. Getting that wrong is silent - the policy would
    see blue oranges - which is why the sim harness carries --img-bgr-swap.

    `lead_dims` preserves the leading (batch, time) axes the wire format adds.
    """
    import cv2 as _cv
    lead = 0
    a = rgb
    while a.ndim > 3:
        a = a[0]
        lead += 1
    ok, enc = _cv.imencode(".jpg", _cv.cvtColor(a, _cv.COLOR_RGB2BGR),
                           [int(_cv.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("JPEG encode failed for an observation image")
    return {"__jpeg_ndarray__": True, "as_jpg": enc.tobytes(), "lead_dims": lead}


class PolicyClient:
    def __init__(self, host="localhost", port=5555, timeout_ms=15000, api_token=None):
        self.context = zmq.Context()
        self.host = host
        self.port = port
        self.timeout_ms = timeout_ms
        self.api_token = api_token
        self._init_socket()

    def _init_socket(self):
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
        self.socket.connect(f"tcp://{self.host}:{self.port}")

    def ping(self) -> bool:
        try:
            self.call_endpoint("ping", requires_input=False)
            return True
        except zmq.error.ZMQError:
            self._init_socket()
            return False

    def call_endpoint(self, endpoint: str, data: dict | None = None, requires_input: bool = True) -> Any:
        request: dict = {"endpoint": endpoint}
        if requires_input:
            request["data"] = data
        if self.api_token:
            request["api_token"] = self.api_token
        self.socket.send(MsgSerializer.to_bytes(request))
        message = self.socket.recv()
        if message == b"ERROR":
            raise RuntimeError("Server error. Make sure we are running the correct policy server.")
        response = MsgSerializer.from_bytes(message)
        if isinstance(response, dict) and "error" in response:
            raise RuntimeError(f"Server error: {response['error']}")
        return response

    def get_action(self, observation: dict, options: dict | None = None):
        response = self.call_endpoint("get_action", {"observation": observation, "options": options})
        return tuple(response)  # (action, info)


# ------------------------------------------------------------------- adapter
def recursive_add_extra_dim(obs: dict) -> dict:
    out = {}
    for k, v in obs.items():
        if isinstance(v, dict):
            out[k] = recursive_add_extra_dim(v)
        elif isinstance(v, np.ndarray):
            out[k] = v[None, ...]
        elif isinstance(v, (int, float, np.floating, np.integer)):
            out[k] = np.array([v])
        elif isinstance(v, str):
            out[k] = [v]
        else:
            out[k] = [v]
    return out


class So100Adapter:
    def __init__(self, policy_client: PolicyClient, jpeg_quality: int = 0):
        self.policy = policy_client
        # 0 = send raw uint8 (previous behaviour). 92 = the pi0.5-measured value.
        self.jpeg_quality = jpeg_quality
        self.robot_state_keys = [
            "shoulder_pan.pos",
            "shoulder_lift.pos",
            "elbow_flex.pos",
            "wrist_flex.pos",
            "wrist_roll.pos",
            "gripper.pos",
        ]
        self.camera_keys = ["front", "wrist"]

    def obs_to_policy_inputs(self, obs: dict) -> dict:
        model_obs = {}
        model_obs["video"] = {k: obs[k] for k in self.camera_keys}
        # NOTE: compression is applied AFTER recursive_add_extra_dim below, so
        # the leading axes exist and jpeg_frame can record how many to restore.
        state = np.array([obs[k] for k in self.robot_state_keys], dtype=np.float32)
        model_obs["state"] = {"single_arm": state[:5], "gripper": state[5:6]}
        model_obs["language"] = {"annotation.human.task_description": obs["lang"]}
        model_obs = recursive_add_extra_dim(model_obs)
        model_obs = recursive_add_extra_dim(model_obs)
        if self.jpeg_quality:
            model_obs["video"] = {k: jpeg_frame(v, self.jpeg_quality)
                                  for k, v in model_obs["video"].items()}
        return model_obs

    def decode_action_chunk(self, chunk: dict, t: int) -> dict:
        single_arm = chunk["single_arm"][0][t]
        gripper = chunk["gripper"][0][t]
        full = np.concatenate([single_arm, gripper], axis=0)
        return {name: float(full[i]) for i, name in enumerate(self.robot_state_keys)}

    def get_action(self, obs: dict) -> list:
        model_input = self.obs_to_policy_inputs(obs)
        action_chunk, info = self.policy.get_action(model_input)
        any_key = next(iter(action_chunk.keys()))
        horizon = action_chunk[any_key].shape[1]
        return [self.decode_action_chunk(action_chunk, t) for t in range(horizon)]


# ---------------------------------------------------------------------- main
@dataclass
class EvalConfig:
    policy_host: str = "192.168.194.158"
    policy_port: int = 5556
    action_horizon: int = 8
    lang_instruction: str = "Grab orange and place into plate"
    # JPEG quality for observation images. 0 = raw uint8 (old behaviour).
    # 92 is the pi0.5-measured value: 15x smaller, 0.83/255 pixel error, and a
    # behavioural change within the policy's own sampling noise (verified
    # 2026-08-14: worst-joint delta 3.36 deg vs a 2.94 deg noise floor).
    jpeg_quality: int = 0
    dry_run: bool = False
    # RTC (plan: n16_rtc_plan_20260820.md): pipeline requests so the arm never
    # waits on the network. false = the sequential loop, byte-identical.
    rtc: bool = False
    robot: dict = field(default_factory=dict)  # replaced below when not dry_run


def run_dry(cfg) -> None:
    client = PolicyClient(host=cfg.policy_host, port=cfg.policy_port)
    print(f"[dry] ping {cfg.policy_host}:{cfg.policy_port} ->", client.ping())
    adapter = So100Adapter(client, jpeg_quality=cfg.jpeg_quality)
    obs = {
        "front": np.zeros((480, 640, 3), np.uint8),
        "wrist": np.zeros((480, 640, 3), np.uint8),
        "lang": cfg.lang_instruction,
        **{k: 0.0 for k in adapter.robot_state_keys},
    }
    t0 = time.time()
    actions = adapter.get_action(obs)
    dt = time.time() - t0
    print(f"[dry] got {len(actions)} action steps in {dt:.2f}s")
    print("[dry] step0:", {k: round(v, 2) for k, v in actions[0].items()})
    print("[dry] last :", {k: round(v, 2) for k, v in actions[-1].items()})
    print("[dry] NETWORK + WIRE + SERVER: OK")


def run_dry_rtc(cfg, n_chunks: int = 25) -> None:
    """Gate G0 of n16_rtc_plan_20260820.md: exercise the full RTC pipeline
    against the live server with a fake robot. Executing an action = sleeping
    one 30 Hz tick. Measures duty cycle and starvation - the two numbers that
    decide whether the pipeline is worth taking to the arm."""
    import queue
    import threading

    client = PolicyClient(host=cfg.policy_host, port=cfg.policy_port)
    print(f"[G0] ping {cfg.policy_host}:{cfg.policy_port} ->", client.ping())
    adapter = So100Adapter(client, jpeg_quality=cfg.jpeg_quality)

    def snap():
        return {
            "front": np.zeros((480, 640, 3), np.uint8),
            "wrist": np.zeros((480, 640, 3), np.uint8),
            "lang": cfg.lang_instruction,
            **{k: 0.0 for k in adapter.robot_state_keys},
        }, {"t_obs": time.time()}

    req: "queue.Queue" = queue.Queue(maxsize=1)
    rep: "queue.Queue" = queue.Queue(maxsize=1)

    def worker():
        while True:
            obs, meta = req.get()
            if obs is None:
                return
            t0 = time.time()
            try:
                acts = adapter.get_action(obs)
            except Exception as exc:
                meta["error"] = repr(exc)
                acts = None
            meta["rtt_ms"] = (time.time() - t0) * 1000
            rep.put((acts, meta))

    threading.Thread(target=worker, daemon=True).start()
    req.put(snap())
    t_wall0 = time.time()
    exec_ticks = starve_ticks = chunks = 0
    starve_run, starve_runs, rtts, ages = 0, [], [], []
    actions, ai = None, 0
    while chunks < n_chunks:
        tic = time.time()
        try:
            acts, meta = rep.get_nowait()
            if acts is None:
                raise RuntimeError(f"policy request failed: {meta.get('error')}")
            rtts.append(meta["rtt_ms"])
            ages.append((time.time() - meta["t_obs"]) * 1000)
            actions, ai = acts, 0
            chunks += 1
            if starve_run:
                starve_runs.append(starve_run)
                starve_run = 0
            req.put(snap())
        except queue.Empty:
            pass
        if actions is not None and ai < len(actions):
            ai += 1
            exec_ticks += 1
        elif actions is not None:
            starve_ticks += 1
            starve_run += 1
            if starve_run > 60:
                raise RuntimeError("G0 FAIL: starved > 2 s")
        dt = time.time() - tic
        if dt < 1 / 30:
            time.sleep(1 / 30 - dt)
    req.put((None, None))
    wall = time.time() - t_wall0
    duty = exec_ticks / 30 / wall * 100
    rtts_s = sorted(rtts)
    print(f"[G0] {chunks} chunks in {wall:.1f}s")
    print(f"[G0] rtt median {rtts_s[len(rtts_s)//2]:.0f} ms  max {rtts_s[-1]:.0f} ms")
    print(f"[G0] chunk age at first execution: median "
          f"{sorted(ages)[len(ages)//2]:.0f} ms")
    print(f"[G0] DUTY CYCLE {duty:.1f}%  (sequential baseline: 31%)")
    print(f"[G0] starvation: {starve_ticks} ticks total, per-chunk runs "
          f"{starve_runs[:8]}{'...' if len(starve_runs) > 8 else ''}")
    ok = duty >= 90 and (not starve_runs or
                         sorted(starve_runs)[len(starve_runs)//2] <= 2)
    print(f"[G0] {'PASS' if ok else 'FAIL'} "
          f"(need duty >=90% and median starvation <=2 ticks)")


def main() -> None:
    import sys

    if any(a.startswith("--dry_run") for a in sys.argv[1:]):
        # light-weight path: no lerobot imports at all
        @draccus.wrap()
        def _dry(cfg: EvalConfig):
            if cfg.rtc:
                run_dry_rtc(cfg)
            else:
                run_dry(cfg)

        _dry()
        return

    # real path - lerobot imports only here so dry_run works anywhere
    from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401
    from lerobot.robots import RobotConfig, make_robot_from_config, so_follower  # noqa: F401

    # register the `http` camera type (the wrist camera is the Raspberry Pi
    # stream proxied at http://127.0.0.1:8092/frame). http_camera.py lives in
    # the OLD repo on the arm machine and self-registers with draccus on import.
    import sys as _sys

    _sys.path.insert(0, str(__import__("pathlib").Path.home()
                          / "PrakashProjects/lerobot/lerobot/projects/testproject/scripts"))
    try:
        import http_camera  # noqa: F401
        print("[real] http camera type registered")
    except Exception as e:
        print(f"[real] http camera type unavailable: {e}")

    @dataclass
    class RealConfig:
        robot: RobotConfig = None
        policy_host: str = "192.168.194.158"
        policy_port: int = 5556
        action_horizon: int = 8
        lang_instruction: str = "Grab orange and place into plate"
        jpeg_quality: int = 0
        # The wrist camera is a Raspberry Pi served by pi_wrist_proxy.py over
        # HTTP. It CANNOT go through --robot.cameras: /frame returns ONE JPEG per
        # request, not a stream, so LeRobot's camera read loop dies with
        # "exceeded maximum consecutive read failures" (verified 2026-08-14).
        # Set this to fetch it directly instead; leave empty to use whatever
        # --robot.cameras provides.
        wrist_url: str = ""
        # RTC (plan: n16_rtc_plan_20260820.md). false = sequential loop.
        rtc: bool = False

    @draccus.wrap()
    def _real(cfg: RealConfig):
        logging.basicConfig(level=logging.INFO)
        robot = make_robot_from_config(cfg.robot)
        robot.connect()
        print("[real] robot connected")
        client = PolicyClient(host=cfg.policy_host, port=cfg.policy_port)
        assert client.ping(), "policy server unreachable"
        policy = So100Adapter(client, jpeg_quality=cfg.jpeg_quality)
        print(f'[real] running with instruction: "{cfg.lang_instruction}"  (Ctrl+C stops)')
        import cv2 as _cv2
        from pathlib import Path as _Path

        _fdir = _Path.home() / "run_frames"
        _fdir.mkdir(exist_ok=True)

        # ---- INSTRUMENTATION (added 2026-08-13) --------------------------
        # The Aug 8 post-mortem recovered everything it could from 286 JPEGs and
        # their FILE MTIMES, because nothing else was written down. The action
        # trace went to a terminal nobody captured; the round trip had to be
        # inferred from timestamps; measured joint state was never saved at all.
        # Four days of analysis for facts a 30-line trace would have handed over
        # in an hour. Everything below exists so that never repeats.
        import json as _json
        import numpy as _np
        _trace = open(_Path.home() / "run_trace.jsonl", "w", buffering=1)

        def _fetch_wrist(url):
            """Pull one JPEG from the wrist proxy and decode it to RGB.

            Returns (frame, age_seconds). The proxy reports X-Frame-Age-Seconds,
            which is how stale ITS cached frame is - distinct from the network
            round trip and worth recording separately, since a frozen proxy
            serving HTTP 200 is a failure mode this rig has hit twice.
            """
            import urllib.request
            try:
                with urllib.request.urlopen(url, timeout=2.0) as r:
                    raw = r.read()
                    age = float(r.headers.get("X-Frame-Age-Seconds", "nan"))
                buf = _np.frombuffer(raw, dtype=_np.uint8)
                bgr = _cv2.imdecode(buf, _cv2.IMREAD_COLOR)
                if bgr is None:
                    return None, age
                return _cv2.cvtColor(bgr, _cv2.COLOR_BGR2RGB), age
            except Exception as exc:
                print(f"[real] wrist fetch failed: {exc}", flush=True)
                return None, float("nan")

        def _wrist_health(_img):
            """Is the wrist camera still looking at the workspace?

            Aug 8 failed because the wrist view drifted onto the floor for the
            final 46% of the run and NOTHING NOTICED. Sim says that condition
            alone takes the task from 83% to 0%, so it is worth a warning.
            sharpness = variance of Laplacian. Calibrated 2026-08-18 against the
            89 training recordings: wrist median 27.6, p10 14.7. Warn only
            below the training p10 - the model never saw sharper anyway.
            """
            g = _cv2.cvtColor(_img, _cv2.COLOR_RGB2GRAY)
            return {
                "sharpness": round(float(_cv2.Laplacian(g, _cv2.CV_64F).var()), 1),
                "brightness": round(float(g.mean()), 1),
                "contrast": round(float(g.std()), 1),
            }

        def _rtc_loop():
            """RTC (n16_rtc_plan_20260820.md): one request always in flight
            while the arm executes the previous answer.

            Thread contract (risk R4): THIS thread owns the serial bus
            (send_action + get_observation). The worker owns the network
            socket and the wrist HTTP proxy. They exchange data only through
            two 1-slot queues. Exits only by exception (Ctrl+C, starvation,
            request failure) so the caller's finally-block always runs.
            """
            import queue as _queue
            import threading as _threading

            _req: "_queue.Queue" = _queue.Queue(maxsize=1)
            _rep: "_queue.Queue" = _queue.Queue(maxsize=1)

            def _worker():
                while True:
                    obs, meta = _req.get()
                    if obs is None:
                        return
                    if cfg.wrist_url:
                        w, age = _fetch_wrist(cfg.wrist_url)
                        if w is not None:
                            obs["wrist"] = w
                        meta["wrist_age_s"] = None if age != age else round(age, 3)
                    t0 = time.time()
                    try:
                        acts = policy.get_action(obs)
                    except Exception as exc:
                        meta["error"] = repr(exc)
                        acts = None
                    meta["rtt_ms"] = round((time.time() - t0) * 1000, 1)
                    _rep.put((acts, obs, meta))

            _threading.Thread(target=_worker, daemon=True).start()

            def _snap():
                obs = robot.get_observation()
                obs["lang"] = cfg.lang_instruction
                return obs, {"t_obs": time.time()}

            _req.put(_snap())
            actions, ai, last_action = None, 0, None
            starved = 0
            ck = 0
            print("[real] RTC pipeline live", flush=True)
            while True:
                tic = time.time()
                fresh = None
                try:
                    fresh = _rep.get_nowait()
                except _queue.Empty:
                    pass
                if fresh is not None:
                    acts, obs_used, meta = fresh
                    if acts is None:
                        raise RuntimeError(
                            f"policy request failed: {meta.get('error')}")
                    for _cam in ("front", "wrist"):
                        if hasattr(obs_used.get(_cam), "shape"):
                            _cv2.imwrite(str(_fdir / f"c{ck:04d}_{_cam}.jpg"),
                                         _cv2.cvtColor(obs_used[_cam],
                                                       _cv2.COLOR_RGB2BGR))
                    _health = (_wrist_health(obs_used["wrist"])
                               if hasattr(obs_used.get("wrist"), "shape") else {})
                    if _health and _health["sharpness"] < 15:
                        print(f"[real] *** WRIST DEGRADED chunk {ck}: "
                              f"sharpness={_health['sharpness']} ***", flush=True)
                    _trace.write(_json.dumps({
                        "chunk": ck,
                        "t": round(meta["t_obs"], 3),
                        "rtt_ms": meta["rtt_ms"],
                        "chunk_age_ms": round((time.time() - meta["t_obs"]) * 1000, 1),
                        "starved_ticks": starved,
                        "rtc": True,
                        "state": {k: round(float(obs_used[k]), 2)
                                  for k in policy.robot_state_keys if k in obs_used},
                        "action0": {k: round(float(v), 2) for k, v in acts[0].items()},
                        "chunk_len": len(acts),
                        "executed": len(acts),
                        "wrist": _health,
                        "wrist_age_s": meta.get("wrist_age_s"),
                    }) + "\n")
                    print(f"[real] chunk {ck}: pan={acts[0]['shoulder_pan.pos']:+.1f} "
                          f"grip={acts[0]['gripper.pos']:+.1f} "
                          f"rtt={meta['rtt_ms']:.0f}ms "
                          f"age={(time.time() - meta['t_obs']) * 1000:.0f}ms "
                          f"starved={starved}", flush=True)
                    actions, ai = acts, 0
                    starved = 0
                    ck += 1
                    _req.put(_snap())  # next request rides the fresh chunk
                if actions is not None and ai < len(actions):
                    last_action = actions[ai]
                    robot.send_action(last_action)
                    ai += 1
                else:
                    starved += 1
                    if last_action is not None:
                        robot.send_action(last_action)  # hold position
                    if starved > 60:
                        raise RuntimeError(
                            "RTC starved >2 s - link or server stalled")
                dt = time.time() - tic
                if dt < 1.0 / 30:
                    time.sleep(1.0 / 30 - dt)

        _chunk = 0
        try:
            if cfg.rtc:
                _rtc_loop()  # exits only by exception; finally below still runs
            while True:
                _t_obs = time.time()
                obs = robot.get_observation()
                if cfg.wrist_url:
                    _w, _age = _fetch_wrist(cfg.wrist_url)
                    if _w is not None:
                        obs["wrist"] = _w
                    _wrist_age_s = _age
                else:
                    _wrist_age_s = None
                obs["lang"] = cfg.lang_instruction
                _t_call = time.time()
                actions = policy.get_action(obs)
                _rtt_ms = round((time.time() - _t_call) * 1000, 1)
                # EVIDENCE: what the policy saw + what it commanded, per chunk.
                # (sim rule, applied to hardware: never diagnose blind)
                for _cam in ("front", "wrist"):
                    if _cam in obs:
                        _cv2.imwrite(str(_fdir / f"c{_chunk:04d}_{_cam}.jpg"),
                                     _cv2.cvtColor(obs[_cam], _cv2.COLOR_RGB2BGR))
                _a0 = actions[0]
                _health = _wrist_health(obs["wrist"]) if "wrist" in obs else {}
                # LOUD, not buried in a file: a wrist camera that has lost the
                # workspace is the single failure mode we know breaks the task.
                if _health and _health["sharpness"] < 15:
                    print(f"[real] *** WRIST DEGRADED chunk {_chunk}: "
                          f"sharpness={_health['sharpness']} "
                          f"brightness={_health['brightness']} *** ", flush=True)
                _trace.write(_json.dumps({
                    "chunk": _chunk,
                    "t": round(_t_obs, 3),
                    "rtt_ms": _rtt_ms,                     # the round trip, MEASURED
                    "state": {k: round(float(obs[k]), 2)   # what the arm actually IS
                              for k in policy.robot_state_keys if k in obs},
                    "action0": {k: round(float(v), 2) for k, v in _a0.items()},
                    "chunk_len": len(actions),             # returned vs executed
                    "executed": min(cfg.action_horizon, len(actions)),
                    "wrist": _health,
                    "wrist_age_s": None if _wrist_age_s is None else round(_wrist_age_s, 3),
                }) + "\n")
                print(f"[real] chunk {_chunk}: pan={_a0['shoulder_pan.pos']:+.1f} "
                      f"lift={_a0['shoulder_lift.pos']:+.1f} grip={_a0['gripper.pos']:+.1f} "
                      f"rtt={_rtt_ms:.0f}ms wrist_sharp={_health.get('sharpness', '?')}",
                      flush=True)
                _chunk += 1
                for action_dict in actions[: cfg.action_horizon]:
                    tic = time.time()
                    robot.send_action(action_dict)
                    toc = time.time()
                    if toc - tic < 1.0 / 30:
                        time.sleep(1.0 / 30 - (toc - tic))
        except KeyboardInterrupt:
            print("\n[real] stopping")
        finally:
            _trace.close()
            robot.disconnect()
            # Print the summary the Aug 8 run could not give, so the operator
            # knows whether the run is worth analysing BEFORE walking away.
            try:
                import json as _j
                rows = [_j.loads(l) for l in open(_Path.home() / "run_trace.jsonl")]
                if rows:
                    rtt = sorted(r["rtt_ms"] for r in rows)
                    sh = [r["wrist"].get("sharpness", 0) for r in rows if r.get("wrist")]
                    bad = sum(1 for v in sh if v < 60)
                    print(f"[real] {len(rows)} chunks | round trip median "
                          f"{rtt[len(rtt)//2]:.0f} ms, max {rtt[-1]:.0f} ms")
                    if sh:
                        print(f"[real] wrist sharpness median {sorted(sh)[len(sh)//2]:.0f}, "
                              f"{bad}/{len(sh)} chunks degraded "
                              f"({100*bad/len(sh):.0f}%)")
                        if bad > len(sh) * 0.2:
                            print("[real] *** WRIST CAMERA WAS DEGRADED FOR MUCH OF THIS "
                                  "RUN - the Aug 8 failure mode. Check the mount. ***")
                    print(f"[real] trace: {_Path.home() / 'run_trace.jsonl'}")
            except Exception as _e:
                print(f"[real] (summary unavailable: {_e})")
            print("[real] robot disconnected")

    _real()


if __name__ == "__main__":
    main()
