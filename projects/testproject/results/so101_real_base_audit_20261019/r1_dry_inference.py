"""R1: load dongyoonkim/so101-pi05-base in the VLASH/LeRobot-0.4.1 env, feed ONE real frame pair from our
own SO-101 recording (front -> base_0_rgb, wrist -> left_wrist_0_rgb, right_wrist slot = masked dummy via
empty_cameras=1), and report the action chunk, its plausibility against the recorded next actions, and the
per-call latency. No arm, no robot driver. Usage (inside /home/kiran/sim/vlash-venv):
  python r1_dry_inference.py --ckpt <snapshot dir> --frames /home/kiran/tmp/r1_dry --task "pick up the orange and move it to another place"
"""
import argparse, json, time, pathlib, sys
import numpy as np, torch
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--ckpt", required=True); ap.add_argument("--frames", required=True); ap.add_argument("--task", required=True)
ap.add_argument("--n-calls", type=int, default=10); ap.add_argument("--compile", action="store_true")
ap.add_argument("--n-action-steps", type=int, default=20); ap.add_argument("--num-inference-steps", type=int, default=15)
ap.add_argument("--out", default="")
a = ap.parse_args()

from vlash.policies.factory import get_policy_class  # VLASH's PI05 (config fields state_cond/fuse_qkv/… are VLASH's, not LeRobot 0.4.1's)
import vlash.policies.pi05.configuration_pi05  # noqa: registers 'pi05' for PreTrainedConfig
from lerobot.configs.policies import PreTrainedConfig
cfg = PreTrainedConfig.from_pretrained(a.ckpt)
cfg.empty_cameras = 1; cfg.n_action_steps = a.n_action_steps; cfg.num_inference_steps = a.num_inference_steps
cfg.device = "cuda"; cfg.compile_model = bool(a.compile)
print("policy type", cfg.type, "| image features", list(cfg.image_features.keys()), "| chunk", cfg.chunk_size, "| dtype", getattr(cfg, "dtype", None), flush=True)
t0 = time.time(); policy = get_policy_class(cfg.type).from_pretrained(a.ckpt, config=cfg); policy.eval()
print(f"loaded in {time.time()-t0:.1f}s; params {sum(p.numel() for p in policy.parameters())/1e9:.2f}B", flush=True)

F = pathlib.Path(a.frames); meta = json.load(open(F / "frame_t2s.json"))
def img(name):
    x = np.asarray(Image.open(F / f"{name}_t2s.png").convert("RGB"), dtype=np.float32) / 255.0  # HWC
    return torch.from_numpy(x).permute(2, 0, 1).unsqueeze(0).cuda()                                  # 1,3,H,W
obs = {"observation.images.base_0_rgb": img("front"), "observation.images.left_wrist_0_rgb": img("wrist"),
       "observation.state": torch.tensor([meta["state"]], dtype=torch.float32).cuda(), "task": a.task}
print("obs shapes:", {k: tuple(v.shape) for k, v in obs.items() if hasattr(v, "shape")}, "task:", a.task, flush=True)
lat = []
with torch.inference_mode():
    for i in range(a.n_calls):
        torch.cuda.synchronize(); t = time.perf_counter()
        chunk = policy.predict_action_chunk(obs)
        torch.cuda.synchronize(); lat.append(time.perf_counter() - t)
ch = chunk[0].float().cpu().numpy()
print(f"chunk shape {ch.shape}; latency first {1000*lat[0]:.0f} ms, median of rest {1000*np.median(lat[1:]):.0f} ms", flush=True)
st = np.asarray(meta["state"]); rec_next = np.asarray(meta["action"])
print("state now        ", st.round(1).tolist())
print("recorded action  ", rec_next.round(1).tolist())
print("predicted a[0]   ", ch[0].round(1).tolist())
print("predicted a[9]   ", ch[9].round(1).tolist())
print("max |a[0]-state| ", float(np.abs(ch[0] - st).max()).__round__(1), " (a sane first action stays near the current state)")
print("finite:", bool(np.isfinite(ch).all()), " within joint range [-180,180]:", bool((np.abs(ch) <= 180).all()))
if a.out:
    json.dump({"ckpt": a.ckpt, "task": a.task, "state": st.tolist(), "recorded_action": rec_next.tolist(), "chunk": ch.tolist(),
               "latency_ms": [1000 * x for x in lat], "n_action_steps": a.n_action_steps, "num_inference_steps": a.num_inference_steps,
               "compile": a.compile}, open(a.out, "w"), indent=1); print("wrote", a.out)
