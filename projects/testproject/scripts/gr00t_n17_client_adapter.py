#!/usr/bin/env python3
"""Bridge LeIsaac's GR00T client to a GR00T **N1.7** inference server.

WHY
---
LeIsaac ships clients for gr00tn1.5 and gr00tn1.6 only. A GR00T N1.7 server
changed the wire format in six ways, so neither client works:

    n1.6 client (what LeIsaac sends)   N1.7 server (what it wants)
    ---------------------------------  ---------------------------------------
    data = obs                         data = {"observation": obs}
    flat keys "video.front"            nested {"video": {"front": ...}}
    groups video./state./annotation.   groups "video" / "state" / "language"
    video ndim 4  [B,H,W,C]            video ndim 5  [B,T,H,W,C]
    state dtype float64                state dtype float32
    response: dict                     response: tuple (action, info)
    language key: n/a                  "language": {"annotation.human.task_description": [[str]]}

Symptoms if you get it wrong (each was hit in order, 2026-08-05):
    gr00tn1.5 -> KeyError: 'action.single_arm'         (wrong annotation key)
    gr00tn1.6 -> ValueError: zero-dimensional arrays cannot be concatenated
    flat data -> "BasePolicy.get_action() got an unexpected keyword argument
                  'video.front'"
    flat obs  -> "Observation must contain a 'video' key"
    float64   -> "State key 'single_arm' must be a numpy array of type np.float32"
    short key -> "Language key 'annotation.human.task_description' must be in
                  observation"

USAGE
-----
Start the N1.7 server first:
    cd ~/sim/Isaac-GR00T
    ./.venv/bin/python -m gr00t.eval.run_gr00t_server \
        --model_path=~/lerobot_assets/checkpoints/gr00t_n17_so101 \
        --embodiment_tag=new_embodiment --port=5555

Then use this class in place of LeIsaac's Gr00t16ServicePolicyClient. It exposes
the same get_action(observation_dict) -> torch.Tensor interface, so it is a drop
-in for scripts/sim_policy_eval_instrumented.py.

Requires pyzmq in the sim venv (`uv pip install pyzmq msgpack`) - verified not to
disturb torch 2.7.0+cu128/sm_120.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import torch
import zmq

# LeIsaac's serializer, loaded by path: importing the `leisaac` package outside
# Isaac Sim pulls in `omni` and fails.
_SER_PATH = Path.home() / "sim/leisaac-src/source/leisaac/leisaac/policy/gr00t/serialization.py"
_spec = importlib.util.spec_from_file_location("_leisaac_gr00t_ser", _SER_PATH)
_ser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ser)
MsgSerializer = _ser.MsgSerializer

SINGLE_ARM_DOF = 5  # SO-101: 5 arm joints + 1 gripper


def _load_so101_limits():
    """USD joint limits (sim, degrees) and motor limits (LeRobot units).

    Imported from LeIsaac when we are inside Isaac Sim; otherwise the same two
    literals are parsed straight out of its source, so there is exactly ONE
    source of truth either way and the standalone smoke test still runs.
    """
    try:
        from leisaac.assets.robots.lerobot import (  # noqa: PLC0415
            SO101_FOLLOWER_MOTOR_LIMITS,
            SO101_FOLLOWER_USD_JOINT_LIMLITS,
        )

        return SO101_FOLLOWER_USD_JOINT_LIMLITS, SO101_FOLLOWER_MOTOR_LIMITS
    except Exception:
        import ast

        src = (Path.home() / "sim/leisaac-src/source/leisaac/leisaac/assets/robots/lerobot.py").read_text()
        found = {}
        for node in ast.parse(src).body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) in (
                "SO101_FOLLOWER_USD_JOINT_LIMLITS",
                "SO101_FOLLOWER_MOTOR_LIMITS",
            ):
                found[node.targets[0].id] = ast.literal_eval(node.value)
        return found["SO101_FOLLOWER_USD_JOINT_LIMLITS"], found["SO101_FOLLOWER_MOTOR_LIMITS"]


_JOINT_LIMITS, _MOTOR_LIMITS = _load_so101_limits()
_JOINT_LO = np.array([_JOINT_LIMITS[j][0] for j in _JOINT_LIMITS], dtype=np.float32)
_JOINT_RANGE = np.array([_JOINT_LIMITS[j][1] - _JOINT_LIMITS[j][0] for j in _JOINT_LIMITS], dtype=np.float32)
_MOTOR_LO = np.array([_MOTOR_LIMITS[j][0] for j in _MOTOR_LIMITS], dtype=np.float32)
_MOTOR_RANGE = np.array([_MOTOR_LIMITS[j][1] - _MOTOR_LIMITS[j][0] for j in _MOTOR_LIMITS], dtype=np.float32)


def sim_to_motor(rad: np.ndarray) -> np.ndarray:
    """[N,6] sim radians -> LeRobot motor units. Mirrors LeIsaac's
    convert_leisaac_action_to_lerobot (utils/robot_utils.py:96)."""
    deg = rad / np.pi * 180.0
    return (deg - _JOINT_LO) / _JOINT_RANGE * _MOTOR_RANGE + _MOTOR_LO


def motor_to_sim(motor: np.ndarray) -> np.ndarray:
    """[N,6] LeRobot motor units -> sim radians. Mirrors LeIsaac's
    convert_lerobot_action_to_leisaac (utils/robot_utils.py:119)."""
    deg = (motor - _MOTOR_LO) / _MOTOR_RANGE * _JOINT_RANGE + _JOINT_LO
    return deg / 180.0 * np.pi


def _as_array(value) -> np.ndarray:
    """Decode a msgpack_numpy envelope if the serializer left one undecoded.

    LeIsaac's MsgSerializer does not always apply its numpy object_hook to the
    SERVER's reply, so arrays can arrive as the raw envelope with BYTE keys:
        {b'nd': True, b'type': '<f4', b'kind': b'', b'shape': [...], b'data': b'...'}
    Decoding it here keeps the adapter independent of that detail.
    """
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, dict):
        keyed = {(k.decode() if isinstance(k, bytes) else k): v for k, v in value.items()}
        if keyed.get("nd"):
            dtype = keyed["type"]
            dtype = dtype.decode() if isinstance(dtype, bytes) else dtype
            return np.frombuffer(keyed["data"], dtype=np.dtype(dtype)).reshape(keyed["shape"])
    return np.asarray(value)


class Gr00tN17Client:
    """Minimal ZMQ client speaking GR00T N1.7's wire format."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5555,
        timeout_ms: int = 60000,
        camera_keys: tuple[str, ...] = ("front", "wrist"),
        language_key: str = "annotation.human.task_description",
        relative_arm: bool = False,
    ) -> None:
        self.camera_keys = tuple(camera_keys)
        self.language_key = language_key
        # checkpoint conf.yaml: use_relative_action: true, reps [RELATIVE, ABSOLUTE]
        self.relative_arm = relative_arm
        self._ctx = zmq.Context()
        self._sock = self._ctx.socket(zmq.REQ)
        self._sock.setsockopt(zmq.RCVTIMEO, timeout_ms)
        self._sock.connect(f"tcp://{host}:{port}")

    def _call(self, endpoint: str, data: dict | None = None):
        request = {"endpoint": endpoint} | ({"data": data} if data is not None else {})
        self._sock.send(MsgSerializer.to_bytes(request))
        return MsgSerializer.from_bytes(self._sock.recv())

    def get_action(self, observation_dict: dict) -> torch.Tensor:
        """observation_dict uses LeIsaac's flat convention; we translate to N1.7."""
        video = {}
        for key in self.camera_keys:
            frame = observation_dict[key]
            arr = frame.cpu().numpy() if hasattr(frame, "cpu") else np.asarray(frame)
            arr = arr.astype(np.uint8, copy=False)
            if arr.ndim == 3:  # [H,W,C] -> [B,T,H,W,C]
                arr = arr[None, None]
            elif arr.ndim == 4:  # [B,H,W,C] -> [B,T,H,W,C]
                arr = arr[:, None]
            video[key] = arr

        joints = observation_dict["joint_pos"]
        joints = joints.cpu().numpy() if hasattr(joints, "cpu") else np.asarray(joints)
        joints = np.asarray(joints, dtype=np.float32).reshape(1, -1)

        # *** UNITS ***
        # The sim speaks RADIANS; this checkpoint was trained on LeRobot MOTOR
        # units. Its own dataset_statistics.json proves it: arm ~ +/-100..111 and
        # gripper -3.9..95.4, matching SO101_FOLLOWER_MOTOR_LIMITS (arm +/-100,
        # gripper 0..100) - not radians. LeIsaac's LeRobot client does this
        # conversion for you; writing a raw ZMQ client bypassed it, so the model
        # was being shown a state pinned near the bottom of its input range and
        # its outputs were applied 57x too large.
        state_motor = sim_to_motor(joints).astype(np.float32)

        observation = {
            "video": video,
            "state": {
                # N1.7 wants float32 and a temporal axis: [B, T, D]
                "single_arm": state_motor[:, :SINGLE_ARM_DOF][:, None, :],
                "gripper": state_motor[:, SINGLE_ARM_DOF : SINGLE_ARM_DOF + 1][:, None, :],
            },
            "language": {self.language_key: [[observation_dict["task_description"]]]},
        }

        result = self._call("get_action", {"observation": observation})
        if isinstance(result, dict) and "error" in result:
            raise RuntimeError(f"GR00T server error: {result['error']}")

        # N1.7 returns (action, info); n1.6 returned a bare dict.
        action = result[0] if isinstance(result, (list, tuple)) else result
        arm = _as_array(action["single_arm"]).astype(np.float32)
        grip = _as_array(action["gripper"]).astype(np.float32)

        # Shape to [T, DOF]: the model returns a chunk of T future steps.
        arm = arm.reshape(-1, arm.shape[-1])
        grip = grip.reshape(-1, grip.shape[-1])

        # *** THE CRITICAL BIT ***
        # This checkpoint declares  use_relative_action: true  with
        #   modality_keys: [single_arm, gripper]
        #   reps:          [RELATIVE,   ABSOLUTE]
        # so single_arm is a DELTA FROM THE CURRENT JOINT STATE, and only the
        # gripper is an absolute target. Passing the arm through as absolute
        # commands wild angles - observed 2026-08-05 as gripper values spanning
        # -24..+46 (vs Pi05's +/-1.4), a flailing arm, and spurious 1-2 step
        # "grasps" at 11 cm from the object. That run measured THIS BUG, not
        # the policy.
        # *** DEFAULT OFF - THE SERVER ALREADY COMPOSES. ***
        # conf.yaml says use_relative_action: true with reps [RELATIVE, ABSOLUTE],
        # which reads as "the arm output is a delta". It is NOT what reaches the
        # client: the N1.7 server applies to_absolute_chunking() itself, so the
        # wire already carries ABSOLUTE motor-space targets. Composing again here
        # doubles every joint target.
        #
        # Do not argue this from the config - PROBE IT. Send a known state and
        # print the raw reply in motor units:
        #     state [ 5.21, -28.65, 23.36, 12.06, -3.58, 29.93]
        #     raw   [ 5.39, -27.17, 22.92, 11.69, -2.79, 20.64]   <- ABSOLUTE
        # near the state => absolute (leave this off). near zero => deltas.
        # Corroboration: LeIsaac's own Gr00t16ServicePolicyClient does NO
        # composition either - it converts units and returns.
        if self.relative_arm:
            arm = arm + state_motor[0, :SINGLE_ARM_DOF][None, :]

        motor_actions = np.concatenate([arm, grip], axis=-1)
        return torch.from_numpy(motor_to_sim(motor_actions).astype(np.float32))

    def close(self) -> None:
        self._sock.close()
        self._ctx.term()


if __name__ == "__main__":
    # Smoke test against a running server, with synthetic observations.
    client = Gr00tN17Client()
    obs = {
        "front": np.zeros((480, 640, 3), dtype=np.uint8),
        "wrist": np.zeros((480, 640, 3), dtype=np.uint8),
        "joint_pos": np.zeros(6, dtype=np.float32),
        "task_description": "pick up the orange and move it to another place",
    }
    action = client.get_action(obs)
    print(f"action shape {tuple(action.shape)} dtype {action.dtype}")
    print(f"first row: {[round(float(v), 4) for v in action.reshape(-1)[:6]]}")
    client.close()
