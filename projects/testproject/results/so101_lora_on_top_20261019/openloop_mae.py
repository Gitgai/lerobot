#!/usr/bin/env python3
"""Open-loop sanity floor (R5 plan): for each checkpoint, feed real recorded frames + state from our dataset and compare
the model's next-10 actions with the recorded next-10 actions. Per-joint MAE (LeRobot units: degrees, gripper 0-100)
and gripper open/close agreement. Tells us whether the fine-tune moved the model TOWARD our demonstrations (the thing
it was trained to do) — independent of the Isaac gate, which measures what it may have forgotten.
Runs in /home/kiran/sim/vlash-venv on the GPU given by CUDA_VISIBLE_DEVICES (short job, ~9 GB):
  python openloop_mae.py --ckpts base=/mnt/.../snapshots/<hash> lora25k=/mnt/.../checkpoints/025000/pretrained_model
     --episodes 2,8,13,14,16,54,56,60,75,80 --stride 15 --out openloop_mae.json
The hold-out ids are the August baseline's hold-out of so101_orange_89_v21; they ARE in the R5 training set (all 89 were
used), so for the LoRA rows this is a seen-data floor, for the base it is unseen data. Both facts are recorded.
"""
import argparse, json, sys, time, types, pathlib
import numpy as np, pandas as pd, av, torch

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
DS = pathlib.Path("/home/kiran/lerobot_assets/datasets/orange89_plus_plate20")   # overridden by --dataset


def frames(cam, ep):
    with av.open(str(DS / f"videos/chunk-000/observation.images.{cam}/episode_{ep:06d}.mp4")) as c:
        return [f.to_ndarray(format="rgb24") for f in c.decode(video=0)]


def load_policy(path):
    sys.path.insert(0, "/home/kiran/sim/vlash")
    from vlash.policies.factory import get_policy_class
    import vlash.policies.pi05.configuration_pi05  # noqa: F401
    from lerobot.configs.policies import PreTrainedConfig
    cfg = PreTrainedConfig.from_pretrained(path); cfg.device = "cuda"; cfg.empty_cameras = 2; cfg.n_action_steps = 10; cfg.num_inference_steps = 15
    pol = get_policy_class(cfg.type).from_pretrained(path, config=cfg); pol.eval()
    img_keys = list(cfg.image_features.keys())
    return pol, img_keys[0], img_keys[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpts", nargs="+", required=True, help="name=path ...")
    ap.add_argument("--episodes", default="2,8,13,14,16,54,56,60,75,80"); ap.add_argument("--stride", type=int, default=15)
    ap.add_argument("--out", default="openloop_mae.json"); ap.add_argument("--dataset", default=None, help="v2.1 dataset dir (default: the 109-episode merge)")
    a = ap.parse_args()
    global DS
    if a.dataset: DS = pathlib.Path(a.dataset)
    eps = [int(x) for x in a.episodes.split(",")]
    tasks = {int(json.loads(l)["task_index"]): json.loads(l)["task"] for l in (DS / "meta/tasks.jsonl").read_text().splitlines() if l.strip()}
    data = []
    for ep in eps:
        df = pd.read_parquet(DS / f"data/chunk-000/episode_{ep:06d}.parquet")
        fr, wr = frames("front", ep), frames("wrist", ep)
        st = np.stack(df["observation.state"].to_numpy()).astype(np.float32); ac = np.stack(df["action"].to_numpy()).astype(np.float32)
        task = tasks[int(df["task_index"].iloc[0])]
        for i in range(0, len(df) - 11, a.stride):
            data.append((ep, i, fr[i], wr[i], st[i], ac[i + 1:i + 11], task))
    print(f"{len(data)} probe frames from {len(eps)} episodes", flush=True)
    results = {}
    for spec in a.ckpts:
        name, path = spec.split("=", 1)
        pol, k_ext, k_wr = load_policy(path); errs = []; grip_ok = 0; t0 = time.time()
        for ep, i, f, w, s, target, task in data:
            obs = {k_ext: torch.from_numpy(f).permute(2, 0, 1).float().div(255).unsqueeze(0).cuda(),
                   k_wr: torch.from_numpy(w).permute(2, 0, 1).float().div(255).unsqueeze(0).cuda(),
                   "observation.state": torch.from_numpy(s).unsqueeze(0).cuda(), "task": task}
            with torch.inference_mode():
                pred = pol.predict_action_chunk(obs)[0, :10].float().cpu().numpy()
            errs.append(np.abs(pred - target).mean(axis=0))
            grip_ok += int((pred[-1, 5] > 25) == (target[-1, 5] > 25))
        errs = np.stack(errs)
        results[name] = {"path": path, "n_probes": len(data), "mae_per_joint": dict(zip(JOINTS, errs.mean(axis=0).round(2).tolist())),
                         "mae_arm_joints_mean": float(errs[:, :5].mean().round(2)), "mae_gripper": float(errs[:, 5].mean().round(2)),
                         "gripper_open_close_agreement_at_step10": round(grip_ok / len(data), 3), "secs": round(time.time() - t0, 1)}
        print(name, json.dumps(results[name]), flush=True)
        del pol; torch.cuda.empty_cache()
    json.dump({"episodes": eps, "stride": a.stride, "results": results, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
