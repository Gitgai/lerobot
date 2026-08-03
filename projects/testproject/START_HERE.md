# START HERE — SO-101 Orange Pick Project (Handoff)

> ## ⚠️ OUTDATED — do not follow this file (2026-08-03)
>
> **If you are an AI agent opening this folder, read these instead:**
> 1. `NEW_MACHINE_SETUP.md` — only if the machine is not set up yet
> 2. `docs/agent_handoff_pi05_20260803.md` — **the current project handoff**
>
> This file is from the **ACT era (2026-07-10)** and is wrong in its most
> important claim: the project moved from **ACT to Pi05** (a
> vision-language-action model), and the robot now grasps, lifts and carries —
> including objects it never trained on. The "one open problem" described
> below was solved weeks ago. Kept for history only.

---

## 0. TL;DR (30 seconds)

- **Goal:** teach a real **SO-101** robot arm to **pick up an orange and move it**, using imitation-learning (policy: **ACT**). Cameras + arm are local; heavy compute (training / fast inference) runs on a rented **RunPod** GPU.
- **Where we are:** ACT models are trained and *work partially* — the arm **reaches the orange and closes the gripper, but doesn't complete the pick.**
- **Root cause (found, evidence-based):** the policy is being run **open-loop** (`n_action_steps=100`) — it plans a whole grasp from one glance and executes it blind, so the gripper closes on a fixed schedule and misses. **This is a *deployment* setting, not a bad model or bad data.**
- **The fix:** run the policy **closed-loop** (temporal ensembling), which needs a **GPU** (this laptop is CPU-only: ~395 ms/step, too slow). Infrastructure for GPU-served closed-loop (RunPod **policy server** + local **robot client**) is **built and staged**; it was blocked only by the physical rig going stale (arm power + Pi camera).
- **The detailed plan is in** [`docs/GRASP_FIX_PLAN.md`](docs/GRASP_FIX_PLAN.md). **Read it after this.**

---

## 1. What this project is

- **Robot:** SO-101 leader + follower arms (Feetech STS3215 servos, 6 DoF incl. gripper). The **leader** is moved by hand to teleoperate the **follower** for recording demos; at eval time the **policy** drives the follower.
- **Cameras (3):** `front`, `top`, `wrist` — the ACT model consumes all three (`observation.images.{front,top,wrist}`).
- **Task string (must match exactly):** `"pick up the orange and move it to another place"`.
- **Policy:** ACT (Action Chunking Transformer), ~52 M params, from the `lerobot` library.
- **Workflow:** record demos (local) → train (RunPod GPU, ~20k steps) → eval on the real arm (local).

---

## 2. Current status (2026-07-10)

| Model | Trained on | Loss | Behavior on the real arm |
|---|---|---|---|
| **30-ep** (`act_orange_checkpoints`) | `move_cleaned` (30 eps) | 0.092 | reaches orange, **never closes** gripper |
| **49-ep** (`act_orange49_checkpoints`) | `orange_49` (30+19 grasp eps) | 0.109 | reaches, **closes gripper**, but **close is mistimed → grabs air** (0/3 picks) |

**Key finding:** the 49-ep model's failure is NOT bad data (demos verified as clean human picks) and NOT the model — it's the **open-loop deployment** (see §3). We also confirmed the gripper closes deep enough and the eval ran at the correct 30 Hz.

---

## 3. The core technical insight (read this before changing anything)

ACT can run two ways at deploy time (see `select_action` in `lerobot/policies/act/modeling_act.py`):

- **Open-loop** (`n_action_steps=100`, `temporal_ensemble_coeff=None`) ← **what we ran (lerobot default) = the bug.** Look once → predict ~100 actions → execute all of them *blind* → look again. The gripper close is pre-scheduled, so if the reach is slightly off, it closes on empty air.
- **Closed-loop** (`temporal_ensemble_coeff=0.01`, `n_action_steps=1`) ← **the fix.** Re-predict *every step* and blend overlapping predictions, so it closes the gripper **when it actually sees it's on the orange.**

**Why we need a GPU:** closed-loop = full model forward *every* step. On this **CPU-only** laptop that's **~395 ms/step (~2.5 Hz)** — unusably slow/jerky. On a GPU it's ~5–15 ms → smooth 30 Hz. So the fix = **serve the (already-trained) model from a GPU, run the robot from the laptop.** No retraining needed to test this.

> ⚠️ Note tested & rejected: naive `--n-action-steps 20` on CPU made it worse (arm hovered, never lifted — chunk truncation). Temporal ensembling on a GPU is the correct closed-loop mode.

---

## 4. Folder / data inventory (what's in the bundle)

Restore these to the same absolute paths on the new machine.

**Project code** — `~/PrakashProjects/testproject/`
- `scripts/act_eval_3cam.py` — **eval**: drives the arm with a checkpoint + 3 cams, `--record`, safety `--max-relative-target`, and closed-loop flags `--n-action-steps` / `--temporal-ensemble`.
- `scripts/record_3cam_demos.py` — **record** teleop demos (leader→follower, 3 cams).
- `scripts/async_client_3cam.py` — **closed-loop client**: robot on laptop, policy on remote GPU server (registers the HTTP wrist camera).
- `scripts/http_camera.py` — registers the `http` LeRobot camera type (needed by the above).
- `scripts/merge_orange_49.py`, `scripts/merge_grasp_19.py` — dataset merge scripts.
- `scripts/so101_runner.py`, `bin/so101` — status / calibrate helpers (`./bin/so101 status|calibrate-follower|calibrate-leader`).
- `tools/pi_wrist_proxy.py` — serves the Pi wrist camera at `http://127.0.0.1:8092/frame` (SSHes to the Pi, runs `rpicam-vid`).
- `docs/` — `GRASP_FIX_PLAN.md` (the plan), `so101_commands.md` (calibration/record/eval commands), and this file.
- config file with ports/ids/camera paths (loaded by `load_config()` — **machine-specific, must be updated**, see §6).

**lerobot source** — `/data/projects/lerobot` (v0.5.2, editable-installed into the env)

**Datasets** — `/data/lerobot_datasets/`
- `so101_orange_49` — **main training set** (30 + 19 grasp eps, decode-verified, all h264)
- `so101_orange_grasp19` — grasp-only set (the 19 good grasp demos)
- `so101_pick_orange_grasp_b1`, `..._grasp_b2_9ep`, `..._move_cleaned` — source episodes (to re-merge)
- (older test/batch sets may remain; the corrupted `move_action_start_cleaned` was deleted)

**Trained models**
- `/data/act_orange49_checkpoints/020000/pretrained_model` — **the current model (49-ep)**
- `/data/act_orange_checkpoints/{005000,010000,020000}` — older 30-ep baseline (optional)

**Results/videos** — `/data/downloads/3cam tests/` (`act_testing*.mp4`), `/data/act_orange_evals/`

**Calibration (critical, tiny)** — `/data/so101_calibration_backup/` (follower+leader json) **and** `~/.cache/huggingface/lerobot/calibration/`. *Calibration is tied to the physical arms, not the laptop — if the same arms move with these files, NO recalibration needed.*

**Keys** — `~/.ssh/runpod_ed25519` (RunPod) + the Pi SSH key + `known_hosts`.

---

## 5. Hardware / rig

- **Follower arm:** serial `5B14114209`, id `my_so101_follower`, port `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00`.
- **Leader arm:** serial `5B14029688`, id `my_so101_leader` (only needed for *recording*, not eval).
- **Cameras:**
  - `front` = the **laptop's built-in webcam** (`Integrated_Webcam_FHD`). ⚠️ **This changes on a new laptop** — different camera/position → the model's front view drifts. Reproduce the framing closely, or expect degradation.
  - `top` = **Logitech C270** USB (`usb-046d_C270_HD_WEBCAM_FC7A6780`), needs `fourcc=MJPG` + ~3 s warmup (returns black on a cold single grab).
  - `wrist` = **Raspberry Pi camera** at `raspi@192.168.1.5`, streamed to `http://127.0.0.1:8092/frame` via `tools/pi_wrist_proxy.py`. New laptop must be on the **same network** + have the Pi SSH key.
- **Safety guard:** always run the arm with `--max-relative-target 5`. **`15` overloaded a motor** (bus timeout → power-cycle the follower to recover).

---

## 6. New-machine setup checklist (Ubuntu)

1. **System packages:** `sudo apt install ffmpeg git git-lfs v4l-utils tmux build-essential curl`
2. **Serial permissions:** `sudo usermod -aG dialout $USER` then log out/in (so it can talk to the arms).
3. **Python env** (recreate — do NOT copy the conda env): install `uv` → `uv venv --python 3.12` → install **CPU** torch + `pip install -e "/data/projects/lerobot[async]"` (the `[async]` extra adds `grpcio` for the closed-loop client). Verify: `python -c "import lerobot, torch, grpc; from lerobot.async_inference import policy_server"`.
4. **Restore data** to the same paths (§4). `chmod 600 ~/.ssh/runpod_ed25519` and the Pi key after restore.
5. **Reconfigure cameras/ports:** re-detect USB `by-id` paths (`ls /dev/v4l/by-id/`, `ls /dev/serial/by-id/`) and **update the `so101` config**. The **front webcam path will be different** — find the new laptop's webcam device and set it.
6. **Verify the rig:** `./bin/so101 status`; a read-only motor check; confirm all 3 cameras give live frames.

**Known env gotcha:** on a *fresh* env, loading a checkpoint may error `module 'packaging' has no attribute 'version'`. Fix: in `lerobot/policies/pretrained.py`, change `import packaging` → `import packaging.version`.

---

## 7. How to run

**Eval (open-loop, local CPU, current default):**
```bash
cd ~/PrakashProjects/testproject/scripts
python act_eval_3cam.py \
  --policy-path /data/act_orange49_checkpoints/020000/pretrained_model \
  --task "pick up the orange and move it to another place" \
  --duration 25 --max-relative-target 5 --record --run-name eval_x \
  --i-understand-this-moves-robot
```

**Record demos:** `python record_3cam_demos.py --episodes N --task "..." --episode-time 20 --reset-time 10 --dataset-repo-id local/NAME --dataset-root /data/lerobot_datasets/NAME`

**Closed-loop (THE FIX — needs a GPU pod):**
1. On the pod: upload the checkpoint, start `python -m lerobot.async_inference.policy_server --host=0.0.0.0 --port=8080` (in `tmux`).
2. On the laptop: SSH-tunnel `ssh -N -L 8080:localhost:8080 -i ~/.ssh/runpod_ed25519 -p <PORT> root@<POD_IP>`.
3. On the laptop: `python async_client_3cam.py --server localhost:8080 --actions-per-chunk 50 --chunk-size-threshold 0.6` (drives the arm; bound the run with `timeout -s INT 35`).

**Training (RunPod GPU):** see `/workspace/train_act_49.sh` pattern — `lerobot-train --dataset.repo_id=... --policy.type=act --policy.device=cuda --steps=20000 --save_freq=2500 --output_dir=...`.

---

## 8. The plan forward (from `GRASP_FIX_PLAN.md`)

- **Step 1 (do this):** GPU policy server + **temporal ensembling** closed-loop → re-test the **existing** 49-ep model. Likely fixes the grasp with no retraining. Target ≥6/10 picks.
- **Step 2 (if needed):** record ~30 more consistent grasp demos → ~50 total, retrain.
- **Step 3 (fallback):** Pi05 (π0.5) fine-tune, served on GPU. More capable but 10× the infra; earlier Pi05 attempts hit the same wall, so only after 1 & 2. **Note:** this laptop's Intel Arc GPU is *not* CUDA — no local CUDA training/inference; RunPod stays the GPU. (Future: Intel Arc + OpenVINO could enable local inference — a separate mini-project.)

---

## 9. Gotchas (accumulated — save yourself the pain)

- **Safety:** always `--max-relative-target 5`. `15` overloads a motor (→ power-cycle follower).
- **Front camera held by Chrome:** if a browser tab is using the webcam, the eval can't open `front`. Close it.
- **Wrist camera / Pi:** the Pi runs a `timelapse.service` that grabs the camera. Stop it: `sudo systemctl stop timelapse.service` on the Pi. Restart the proxy with `python tools/pi_wrist_proxy.py`. If `rpicam-vid` streaming crashes (SIGPIPE), reboot the Pi.
- **Never `rm -rf ~/.cache/huggingface`** — it wipes the arm calibration (happened; had to recalibrate). Calibration is backed up in `/data/so101_calibration_backup/`.
- **Dataset merge:** `merge_datasets` *concatenates* video files, so all source datasets must share the **same actual codec** (re-encode to uniform h264 first: `ffmpeg -c:v libx264 -pix_fmt yuv420p -g 2 -crf 20 -vsync cfr -r 30`). Verify frame counts; never overwrite a source without a backup.
- **Keep Claude scratch off root:** set `CLAUDE_CODE_TMPDIR=/data/claude_tmp` (root filled to 100% once and blocked everything).
- **RunPod pods migrate/stop** when the GPU gets reclaimed; `/workspace` persists but the local venv is wiped — rebuild it.

---

## 10. Quick reference

| Thing | Path |
|---|---|
| Project | `~/PrakashProjects/testproject/` |
| Plan | `~/PrakashProjects/testproject/docs/GRASP_FIX_PLAN.md` |
| lerobot | `/data/projects/lerobot` |
| Current model | `/data/act_orange49_checkpoints/020000/pretrained_model` |
| Main dataset | `/data/lerobot_datasets/so101_orange_49` |
| Calibration backup | `/data/so101_calibration_backup/` |
| RunPod key | `~/.ssh/runpod_ed25519` |
| Wrist proxy | `~/PrakashProjects/testproject/tools/pi_wrist_proxy.py` (serves `:8092`) |
| Pi | `raspi@192.168.1.5` |

**One-line status for a new agent:** *"ACT model reaches + closes on the orange but misses because it's run open-loop; the fix is closed-loop inference on a RunPod GPU (server+client already built in `scripts/async_client_3cam.py`); the laptop is CPU-only so a GPU is required. Read `docs/GRASP_FIX_PLAN.md`."*
