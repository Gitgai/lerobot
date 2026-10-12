"""L2 — score openpi's published pi05_libero checkpoint in OUR LIBERO loop.

Plan: docs/pi05_libero_openpi_vs_ours_plan_20261010.md (step L2).

This is a faithful port of openpi's examples/libero/main.py execution
convention — 256 px render, 180° rotate, pad-resize to 224, state =
eef_pos + axis-angle + gripper_qpos, prompt = task language, 10 settle
steps, replan every 5 steps of the 10-step chunk, 220-step cap on Spatial,
env seed 7, init state = episode index — with two deliberate differences:

  * n = 20 trials per task x 10 tasks = 200 (theirs: 50 per task), and
    the trial->init-state mapping is recorded so later rows reuse it;
  * every episode's outcome, step count and per-task rate is written to
    JSON, plus LIBERO's check_success() at episode end next to the `done`
    flag openpi counts, so the two success definitions can be compared.

Runs in the PROBE venv (has the libero package + torch); talks to openpi's
policy server over websocket. RTC: none (openpi has none). Backend
"lerobot" is a stub for L5 so the SAME loop scores every row.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import time

import numpy as np
import torch
from libero.libero import benchmark, get_libero_path
from libero.libero.envs import OffScreenRenderEnv
from openpi_client import image_tools
from openpi_client import websocket_client_policy

LIBERO_DUMMY_ACTION = [0.0] * 6 + [-1.0]
LIBERO_ENV_RESOLUTION = 256
MAX_STEPS = {"libero_spatial": 220, "libero_object": 280, "libero_goal": 300, "libero_10": 520, "libero_90": 400}


def quat2axisangle(quat):
    quat = np.array(quat, dtype=np.float64)
    quat[3] = min(1.0, max(-1.0, quat[3]))
    den = np.sqrt(1.0 - quat[3] * quat[3])
    if math.isclose(den, 0.0):
        return np.zeros(3)
    return (quat[:3] * 2.0 * math.acos(quat[3])) / den


def load_init_states(task_suite, task_id):
    # libero's own get_task_init_states uses torch.load without weights_only=False,
    # which fails on torch >= 2.6 with numpy pickles. Mirror lerobot's loader.
    task = task_suite.tasks[task_id]
    path = pathlib.Path(get_libero_path("init_states")) / task.problem_folder / pathlib.Path(task.init_states_file).name
    return torch.load(path, weights_only=False)  # nosec


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="libero_spatial")
    ap.add_argument("--trials-per-task", type=int, default=20)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--replan-steps", type=int, default=5)
    ap.add_argument("--num-steps-wait", type=int, default=10)
    ap.add_argument("--resize", type=int, default=224)
    ap.add_argument("--out", required=True)
    ap.add_argument("--row", default="openpi_pi05_libero_fullft")
    ap.add_argument("--task-ids", default="", help="comma list to restrict tasks (debug)")
    ap.add_argument("--trials", default="", help="comma list of trial indices to run (default: 0..trials-per-task-1)")
    ap.add_argument("--video-dir", default="", help="if set, write one mp4 per episode (agentview | wrist, 224px, 10 fps) via ffmpeg")
    ap.add_argument("--rerun", default="off", choices=["off", "save", "serve"],
                    help="save: one .rrd per episode in --rerun-dir; serve: stream live to a browser (grpc 9876 / web 9090)")
    ap.add_argument("--rerun-dir", default="")
    args = ap.parse_args()
    rr = None
    if args.rerun != "off":
        import rerun as rr  # noqa
        rerun_dir = pathlib.Path(args.rerun_dir or (args.out + "/rerun")); rerun_dir.mkdir(parents=True, exist_ok=True)
        if args.rerun == "serve":
            rr.init(f"libero_{args.row}", spawn=False)
            url = rr.serve_grpc(grpc_port=9876)
            rr.serve_web_viewer(web_port=9090, open_browser=False, connect_to=url)
            print(f"[rerun] live viewer: http://127.0.0.1:9090/?url={url}", flush=True)
    STATE_NAMES = ["eef_x", "eef_y", "eef_z", "rot_ax", "rot_ay", "rot_az", "grip_q0", "grip_q1"]
    ACTION_NAMES = ["dx", "dy", "dz", "drx", "dry", "drz", "gripper"]
    video_dir = pathlib.Path(args.video_dir) if args.video_dir else None
    if video_dir: video_dir.mkdir(parents=True, exist_ok=True)
    trial_list = [int(t) for t in args.trials.split(",") if t] or list(range(args.trials_per_task))

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    per_ep = (out / "per_episode.jsonl").open("a")

    np.random.seed(args.seed)
    suite = benchmark.get_benchmark_dict()[args.suite]()
    max_steps = MAX_STEPS[args.suite]
    task_ids = [int(t) for t in args.task_ids.split(",") if t] or list(range(suite.n_tasks))

    client = websocket_client_policy.WebsocketClientPolicy(args.host, args.port)
    meta = client.get_server_metadata()
    print(f"[L2] server metadata: {meta}", flush=True)

    summary = {"row": args.row, "suite": args.suite, "trials_per_task": args.trials_per_task,
               "env_seed": args.seed, "replan_steps": args.replan_steps, "max_steps": max_steps,
               "num_steps_wait": args.num_steps_wait, "resize": args.resize, "rtc": "none (openpi has none)",
               "convention": "openpi examples/libero/main.py", "server_metadata": str(meta),
               "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tasks": {}}
    total_n = total_k = 0
    t_run = time.time()

    for task_id in task_ids:
        task = suite.get_task(task_id)
        init_states = load_init_states(suite, task_id)
        bddl = pathlib.Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file
        env = OffScreenRenderEnv(bddl_file_name=str(bddl), camera_heights=LIBERO_ENV_RESOLUTION, camera_widths=LIBERO_ENV_RESOLUTION)
        env.seed(args.seed)
        desc = task.language
        k = 0
        t_task = time.time()
        for ep in trial_list:
            env.reset()
            obs = env.set_init_state(init_states[ep])
            plan = collections.deque()
            t = 0
            done = False
            n_infer = 0
            infer_s = 0.0
            t_ep = time.time()
            if rr is not None:
                ep_id = f"task{task_id:02d}_trial{ep:02d}"
                if args.rerun == "save":
                    rr.init(f"libero_{args.row}", recording_id=f"{args.row}_{ep_id}", spawn=False)
                    rr.save(str(rerun_dir / f"{ep_id}.rrd"))
                base = "" if args.rerun == "save" else ep_id + "/"
                rr.log(base + "meta", rr.TextDocument(f"row {args.row}\ntask {task_id}: {desc}\ntrial {ep} (init state {ep})\nreplan {args.replan_steps}, cap {max_steps}, RTC none"), static=True)
                for i, nme in enumerate(STATE_NAMES): rr.log(base + f"state/{nme}", rr.SeriesLines(names=nme), static=True)
                for i, nme in enumerate(ACTION_NAMES): rr.log(base + f"action/{nme}", rr.SeriesLines(names=nme), static=True)
            vw = None
            if video_dir:
                import subprocess
                vpath = video_dir / f"task{task_id:02d}_trial{ep:02d}.mp4"
                vw = subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s","448x224","-r","10","-i","-","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",str(vpath)], stdin=subprocess.PIPE)
            while t < max_steps + args.num_steps_wait:
                if t < args.num_steps_wait:
                    obs, _, done, _ = env.step(LIBERO_DUMMY_ACTION)
                    t += 1
                    continue
                img = np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])
                wrist = np.ascontiguousarray(obs["robot0_eye_in_hand_image"][::-1, ::-1])
                img = image_tools.convert_to_uint8(image_tools.resize_with_pad(img, args.resize, args.resize))
                wrist = image_tools.convert_to_uint8(image_tools.resize_with_pad(wrist, args.resize, args.resize))
                if vw is not None:
                    vw.stdin.write(np.ascontiguousarray(np.concatenate([img, wrist], axis=1)).tobytes())
                if rr is not None:
                    rr.set_time("step", sequence=t)
                    rr.log(base + "cam/agent", rr.Image(img).compress(jpeg_quality=85))
                    rr.log(base + "cam/wrist", rr.Image(wrist).compress(jpeg_quality=85))
                    st = np.concatenate((obs["robot0_eef_pos"], quat2axisangle(obs["robot0_eef_quat"]), obs["robot0_gripper_qpos"]))
                    for i, nme in enumerate(STATE_NAMES): rr.log(base + f"state/{nme}", rr.Scalars(float(st[i])))
                if not plan:
                    element = {
                        "observation/image": img,
                        "observation/wrist_image": wrist,
                        "observation/state": np.concatenate((obs["robot0_eef_pos"], quat2axisangle(obs["robot0_eef_quat"]), obs["robot0_gripper_qpos"])),
                        "prompt": str(desc),
                    }
                    t0 = time.time()
                    chunk = client.infer(element)["actions"]
                    infer_s += time.time() - t0
                    n_infer += 1
                    assert len(chunk) >= args.replan_steps, len(chunk)
                    plan.extend(chunk[: args.replan_steps])
                    if rr is not None:
                        rr.log(base + "infer/latency_ms", rr.Scalars(1000.0 * (time.time() - t0)))
                        rr.log(base + "infer/chunk_index", rr.Scalars(float(n_infer)))
                action = plan.popleft()
                if rr is not None:
                    for i, nme in enumerate(ACTION_NAMES): rr.log(base + f"action/{nme}", rr.Scalars(float(action[i])))
                obs, _, done, _ = env.step(action.tolist())
                if done:
                    break
                t += 1
            if vw is not None:
                # hold the final frame for 1 s so the outcome is visible
                for _ in range(10): vw.stdin.write(np.ascontiguousarray(np.concatenate([img, wrist], axis=1)).tobytes())
                vw.stdin.close(); vw.wait()
                final = video_dir / f"task{task_id:02d}_trial{ep:02d}_{'ok' if done else 'FAIL'}.mp4"
                (video_dir / f"task{task_id:02d}_trial{ep:02d}.mp4").rename(final)
            check = bool(env.check_success()) if hasattr(env, "check_success") else None
            if rr is not None:
                rr.log(base + "outcome", rr.TextLog(f"{'SUCCESS' if done else 'FAIL (timeout)'} at step {t}, {n_infer} inferences, mean {1000*infer_s/max(n_infer,1):.0f} ms"), static=True)
                rr.log(base + "success", rr.Scalars(1.0 if done else 0.0))
            k += int(done)
            rec = {"row": args.row, "suite": args.suite, "task_id": task_id, "task": desc, "trial": ep,
                   "init_state_index": ep, "success_done": bool(done), "check_success_at_end": check,
                   "steps": t, "n_infer": n_infer, "infer_s_mean": (infer_s / n_infer) if n_infer else None,
                   "episode_s": round(time.time() - t_ep, 1)}
            per_ep.write(json.dumps(rec) + "\n")
            per_ep.flush()
            print(f"[L2] task {task_id:2d} trial {ep:2d} success={int(done)} steps={t} "
                  f"infer={n_infer}x{(infer_s/max(n_infer,1))*1000:.0f}ms  ({rec['episode_s']}s)", flush=True)
        env.close()
        n = len(trial_list)
        lo, hi = wilson(k, n)
        summary["tasks"][str(task_id)] = {"task": desc, "k": k, "n": n, "rate": k / n, "ci95": [lo, hi],
                                          "task_s": round(time.time() - t_task)}
        total_k += k
        total_n += n
        print(f"[L2] === task {task_id} '{desc}': {k}/{n} = {100*k/n:.0f}%  running total {total_k}/{total_n}", flush=True)
        (out / "summary.json").write_text(json.dumps(summary, indent=2))

    lo, hi = wilson(total_k, total_n)
    summary.update({"k": total_k, "n": total_n, "rate": total_k / total_n if total_n else None, "ci95": [lo, hi],
                    "wall_s": round(time.time() - t_run), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"[L2] RESULT {args.row} {args.suite}: {total_k}/{total_n} = {100*total_k/total_n:.1f}%  "
          f"95% CI [{100*lo:.1f}, {100*hi:.1f}]  wall {summary['wall_s']}s", flush=True)


if __name__ == "__main__":
    main()
