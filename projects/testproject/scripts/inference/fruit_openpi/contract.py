"""Real-arm contract: dataset units, never simulator coordinates."""

import numpy as np

JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
CHECKPOINT = "/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX/checkpoints/pi05_fruit55_lora_vision/fruit55_lora_vision_5k/4000"
TASK = "pick up the orange and place it on the plate"


def observation(raw):
    state = np.asarray([raw[f"{j}.pos"] for j in JOINTS], dtype=np.float32)
    if not np.isfinite(state).all():
        raise ValueError("Nonfinite measured state")
    images = [np.asarray(raw[k]) for k in ("front", "wrist")]
    if any(a.shape != (480, 640, 3) or a.dtype != np.uint8 for a in images):
        raise ValueError("Expected 640x480 RGB uint8 camera images")
    return {
        "observation/state": state,
        "observation/image": images[0],
        "observation/wrist_image": images[1],
        "prompt": TASK,
    }


def actions(reply):
    a = np.asarray(reply["actions"])
    if a.shape != (30, 6) or not np.isfinite(a).all():
        raise ValueError("Expected finite 30x6 actions")
    return a


def target(row):
    a = np.asarray(row)
    if a.shape != (6,) or not np.isfinite(a).all():
        raise ValueError("Expected finite six-joint target")
    return {f"{j}.pos": float(v) for j, v in zip(JOINTS, a, strict=True)}


def metadata(value):
    if (
        value.get("checkpoint") != CHECKPOINT
        or value.get("rtc") is not False
        or value.get("jpeg") is not False
    ):
        raise ValueError("Wrong checkpoint/RTC/JPEG metadata")
    return value
