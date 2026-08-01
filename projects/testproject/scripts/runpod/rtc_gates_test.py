"""RTC verification gates (run ON THE POD with the training-era code, no robot).

Gate A: RTC OFF -> outputs must match the trusted old-code behavior (exam vs
        recorded live answers from the successful run).
Gate B: RTC ON  -> consecutive chunks must connect smoothly at the switch
        point (seam <= ~5 units vs the 70-114 unit live jumps).
Gate C: RTC ON  -> chunks must still track the task (gripper corr vs live).

Run:  HF_HOME=/workspace/hf_cache /workspace/venv312/bin/python \
        /workspace/exam/rtc_gates_test.py
(no PYTHONPATH override: uses the pod's trusted old lerobot install)
"""

import glob
import json
import math
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image

CKPT = Path("/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model")
TRACE = Path("/workspace/exam/official_async_3cam_012000_fixed_20260728_021800")
STATE_KEYS = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]
FPS = 30

import lerobot
print("lerobot from:", lerobot.__file__, flush=True)
assert "lerobot_new" not in lerobot.__file__, "must run on the OLD trusted code"

from lerobot.configs import PreTrainedConfig
from lerobot.policies.factory import get_policy_class, make_pre_post_processors
from lerobot.policies.rtc.configuration_rtc import RTCConfig

cfg = PreTrainedConfig.from_pretrained(str(CKPT))
cfg.device = "cuda"
policy_cls = get_policy_class(cfg.type)
policy = policy_cls.from_pretrained(str(CKPT), config=cfg)
policy.eval()
pre, post = make_pre_post_processors(cfg, pretrained_path=str(CKPT))
print("policy + saved processors loaded (old code)", flush=True)

obs = [json.loads(l) for l in open(TRACE / "observations.jsonl")]
live = [json.loads(l) for l in open(TRACE / "action_chunks.jsonl")]
cams = {c: sorted(glob.glob(str(TRACE / "images" / c / "*.jpg")), key=lambda f: int(f.split("_")[-2])) for c in ["top", "front", "wrist"]}

def make_item(i):
    o = obs[i]
    item = {"observation.state": torch.tensor([o["state"][k] for k in STATE_KEYS], dtype=torch.float32), "task": o["task"]}
    for c in cams:
        arr = np.asarray(Image.open(cams[c][i]).convert("RGB"), dtype=np.float32) / 255.0
        item[f"observation.images.{c}"] = torch.from_numpy(arr).permute(2, 0, 1)
    return item

def predict(i, rtc_kwargs=None):
    torch.manual_seed(0)
    with torch.no_grad():
        processed = pre(make_item(i))
        norm = policy.predict_action_chunk(processed, **(rtc_kwargs or {}))
        real = post(norm).squeeze(0).cpu().numpy()
    return norm, real

def set_rtc(enabled, horizon=10):
    policy.config.rtc_config = RTCConfig(enabled=enabled, execution_horizon=horizon) if enabled else None
    policy.init_rtc_processor()
    policy.model.rtc_processor = policy.rtc_processor

# ---------------- Gate A: RTC OFF, exam vs live answers ----------------
set_rtc(False)
sel = np.linspace(0, min(len(obs), len(live)) - 1, 20).astype(int)
gp, gl = [], []
for i in sel:
    _, real = predict(i)
    gp.append(float(real[0, 5])); gl.append(float(np.array(live[i]["actions"])[0, 5]))
gp, gl = np.array(gp), np.array(gl)
a_mae, a_corr = float(np.abs(gp - gl).mean()), float(np.corrcoef(gp, gl)[0, 1])
gate_a = a_mae < 6 and a_corr > 0.8
print(f"\nGATE A (RTC off): gripper MAE {a_mae:.2f} corr {a_corr:.3f} -> {'PASS' if gate_a else 'FAIL'}", flush=True)

# ---------------- Gate B: RTC ON, seam continuity ----------------
DELAY = int(os.environ.get("RTC_TEST_DELAY", math.ceil(1.0 * FPS)))  # ~1 s latency
set_rtc(True, horizon=int(os.environ.get("RTC_TEST_HORIZON", "10")))
seams_off, seams_on, corr_pred = [], [], []
pairs = [(int(i), int(i) + 1) for i in np.linspace(0, min(len(obs), len(live)) - 2, 15).astype(int)]
for a, b in pairs:
    gap = max(1, min(obs[b]["timestep"] - obs[a]["timestep"], 45))
    # without RTC
    set_rtc(False)
    n1, r1 = predict(a)
    _, r2 = predict(b)
    seams_off.append(np.abs(r2[0] - r1[min(gap, len(r1) - 1)]).max())
    # with RTC: chunk b conditioned on the leftover of chunk a
    set_rtc(True)
    n1r, r1r = predict(a)
    prev = n1r[:, gap:, :]
    _, r2r = predict(b, {"inference_delay": DELAY, "prev_chunk_left_over": prev})
    seams_on.append(np.abs(r2r[0] - r1r[min(gap, len(r1r) - 1)]).max())
    corr_pred.append(float(r2r[0, 5]))
seams_off, seams_on = np.array(seams_off), np.array(seams_on)
gate_b = np.median(seams_on) <= 5.0
print(f"GATE B (seams, max-joint units): RTC off median {np.median(seams_off):.1f} p90 {np.percentile(seams_off,90):.1f} | "
      f"RTC ON median {np.median(seams_on):.1f} p90 {np.percentile(seams_on,90):.1f} -> {'PASS' if gate_b else 'FAIL'}", flush=True)

# ---------------- Gate C: RTC ON still tracks the task ----------------
gl_b = np.array([float(np.array(live[b]["actions"])[0, 5]) for _, b in pairs])
c_corr = float(np.corrcoef(np.array(corr_pred), gl_b)[0, 1])
gate_c = c_corr > 0.8
print(f"GATE C (RTC on, gripper corr vs live): {c_corr:.3f} -> {'PASS' if gate_c else 'FAIL'}", flush=True)

print(f"\nOVERALL: {'ALL GATES PASS' if (gate_a and gate_b and gate_c) else 'FAILED - do not go live'}")
