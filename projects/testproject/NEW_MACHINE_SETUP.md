# New Machine Setup - SO-101 + Pi05

Last updated: 2026-08-03

Read this if you have just cloned the repo onto a new machine and nothing runs
yet. When the setup verifies clean, switch to
`docs/agent_handoff_pi05_20260803.md` - that is the project itself (what we
are doing, what is proven, what is next). This file is only about making the
machine work.

Supersedes `RESTORE_ON_NEW_MACHINE.md`, which describes an older layout
(`/data/projects/lerobot`, `~/PrakashProjects/testproject`) from before the
project moved inside the lerobot fork.

---

## 0. Getting The Code Onto The New Machine

```bash
# fresh machine:
git clone https://github.com/Gitgai/lerobot.git
cd lerobot

# already cloned earlier? just update - the setup and handoff docs are new:
git pull

# confirm you have them (all three must be present):
git log --oneline -3
#   613a6c02 New-machine setup guide; redirect stale entry-point docs
#   8fd62fc9 Agent handoff doc, objective grasp scorer, pi05 architecture findings
#   95925d87 Five-run count, edge-grip diagnosis, generalization roadmap + Stage 1 probes
```

Then read this file from Section 1, and finish with
`docs/agent_handoff_pi05_20260803.md`.

---

## 1. What `git clone` Gives You, And What It Does Not

```text
IN GIT (you already have it):
  the lerobot fork + all our async_inference changes (JPEG codec, threading)
  projects/testproject/scripts/    client wrapper, recording, analysis tools
  projects/testproject/tools/      pi_wrist_proxy.py, top_camera_proxy.py
  projects/testproject/config/so101.json   (values need editing - Section 4)
  projects/testproject/docs/       the entire project history and plans

NOT IN GIT (must come from the old machine, or be re-created):
  1. the Python venv .................. rebuild (Section 3)
  2. ROBOT CALIBRATION ................ COPY IT - cannot be re-created without
                                        re-calibrating both arms
  3. SSH keys (RunPod + Raspberry Pi) . copy, never commit
  4. correct camera device paths ...... MACHINE-SPECIFIC, must re-detect
  5. HF token ......................... re-create, never commit
  6. datasets / checkpoints ........... only needed for training (Section 7)
```

The two that silently ruin a session if missed are **calibration** (the arm
moves to wrong angles and you will blame the model) and **camera paths** (the
old values point at hardware that does not exist here).

---

## 2. Copy These From The Old Machine First

Small, essential, no substitutes - about 8 KB of calibration plus one SSH key.

**Two gotchas checked on 2026-08-03:**

```text
1. The old laptop's IP MOVES. It was 192.168.1.163, then 192.168.1.14.
   Confirm on the old laptop with `hostname -I` immediately before copying.
   (Note .14 was once the Raspberry Pi's address - the Pi is now .15. Do not
   copy from the Pi by mistake.)
2. The old laptop's SSH SERVER IS NOT RUNNING by default, so pulling from the
   new machine fails with "connection refused". Either start it on the old
   laptop first:  sudo systemctl start ssh
   or skip the network entirely and use a USB stick - it is 8 KB, and this is
   the more reliable option:
       # on the OLD laptop
       cp -r ~/.cache/huggingface/lerobot/calibration /media/$USER/<STICK>/
       cp ~/.ssh/runpod_ed25519 /media/$USER/<STICK>/
       # on the NEW machine
       mkdir -p ~/.cache/huggingface/lerobot ~/.ssh
       cp -r /media/$USER/<STICK>/calibration ~/.cache/huggingface/lerobot/
       cp /media/$USER/<STICK>/runpod_ed25519 ~/.ssh/ && chmod 600 ~/.ssh/runpod_ed25519
```

Network method (only after the SSH server is running on the old laptop):

```bash
OLD=gaikwad-prakash@192.168.1.14        # CONFIRM with `hostname -I` first

# 1. ROBOT CALIBRATION - the most important non-git files in the project.
#    Travels with the physical arms; if you moved the same arms, do NOT
#    recalibrate, just copy these two JSONs.
mkdir -p ~/.cache/huggingface/lerobot/calibration
rsync -avz "$OLD:~/.cache/huggingface/lerobot/calibration/" \
           ~/.cache/huggingface/lerobot/calibration/
# expect exactly:
#   robots/so_follower/my_so101_follower.json
#   teleoperators/so_leader/my_so101_leader.json

# 2. SSH KEYS - RunPod (GPU server) and the Raspberry Pi (wrist camera)
mkdir -p ~/.ssh
rsync -avz "$OLD:~/.ssh/runpod_ed25519" ~/.ssh/
chmod 600 ~/.ssh/runpod_ed25519
# copy the Pi key the same way if the Pi uses key auth
```

If the old machine is gone and calibration is lost, both arms must be
re-calibrated with the official lerobot calibration flow before ANY policy run
- an uncalibrated follower makes every result meaningless.

---

## 3. Build The Environment

System packages and permissions (Ubuntu):

```bash
sudo apt update
sudo apt install -y ffmpeg v4l-utils git-lfs curl
sudo usermod -aG dialout $USER      # serial access to the arms
# LOG OUT AND BACK IN for the group change to take effect
```

Python env. The project uses its OWN venv inside `projects/testproject`, with
the repo installed editable, and **CPU-only torch** (all GPU work happens on
the pod - installing CUDA torch here wastes ~3 GB for nothing):

```bash
cd <REPO>/projects/testproject          # <REPO> = wherever you cloned
curl -LsSf https://astral.sh/uv/install.sh | sh     # if uv is missing
uv venv --python 3.12
uv pip install --python .venv/bin/python \
    --index-url https://download.pytorch.org/whl/cpu torch
uv pip install --python .venv/bin/python -e "../..[feetech,async]"
```

Verify it matches the known-good old machine:

```bash
./.venv/bin/python -c "import lerobot, torch, cv2, grpc, scservo_sdk; \
print(lerobot.__file__); print('torch', torch.__version__)"
```

```text
Expect: .../<REPO>/src/lerobot/__init__.py     <- editable, points INTO the repo
        torch 2.10.0+cpu (or newer +cpu)
If lerobot resolves anywhere else, the editable install failed and you will be
running different code than you are editing.
```

---

## 4. Re-detect Hardware And Fix `config/so101.json`

**This is the step people skip and then lose an evening to.** The committed
config holds the OLD laptop's device paths. Three of its values are
machine-specific and one is stable:

```bash
ls -l /dev/v4l/by-id/ /dev/v4l/by-path/    # cameras
ls -l /dev/serial/by-id/                   # the arms
```

```text
top camera (Logitech C270) - STABLE, travels with the camera:
  /dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0
  Same string on any machine. Keep it.

front camera (laptop built-in) - WILL BE DIFFERENT. Rewrite it.
  Use a by-path node, NOT by-id. Hard-won reason: on the old laptop the by-id
  name jumped to the IR sensor after a reboot and silently produced GREY
  640x360@15 frames. by-path is stable per physical USB position.
  Old value (do not reuse): pci-0000:00:14.0-usb-0:5:1.0-video-index0
  Find the new one, then CONFIRM it is the RGB camera, not IR:
    v4l2-ctl -d <PATH> --list-formats-ext | head
  You want MJPG/YUYV at 640x480, not GREY.

arms - STABLE by-id serials, travel with the hardware:
  follower /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00
  leader   /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14029688-if00
  Prefer these over /dev/ttyACM0|1, whose numbering swaps between boots.

wrist camera - network, nothing to detect. Served by the laptop-side proxy at
  http://127.0.0.1:8092/frame (Section 5).
```

Edit `config/so101.json`: set `camera_index` and `front_camera_index` to the
new front-camera by-path. Two legacy fields, `lerobot_dir` and `conda_env`,
still point at the old machine's layout; only `scripts/so101_runner.py` (the
old teleop runner) reads them and it falls back safely, so fix them only if
you use that script.

---

## 5. Wrist Camera (Raspberry Pi)

The wrist camera is a Pi on the same Wi-Fi, not USB. Its IP has moved before
(`.14` -> `.15`), so confirm it.

```bash
ssh raspi@192.168.1.15
# BEFORE a session, free the camera (these services own it otherwise):
sudo systemctl stop timelapse.service pipics.service
# AFTER the session, start them again - the user's other projects need them.
```

Then run the laptop-side proxy (leave it running for the whole session):

```bash
cd <REPO>/projects/testproject
./.venv/bin/python tools/pi_wrist_proxy.py --pi-host raspi@192.168.1.15 --pi-ip 192.168.1.15
curl -sf -o /tmp/wrist.jpg http://127.0.0.1:8092/frame && echo WRIST_OK
```

```text
Distinguish the two failure modes - they have different fixes:
  "no cameras available"           = electrical; reseat the ribbon cable
  "failed to acquire / in use"     = something holds it; stop the services,
                                     or close the Chrome tab showing the feed
```

---

## 6. GPU Server (RunPod) And The Tunnel

Nothing to install locally - the policy runs on the pod. You need the SSH key
from Section 2, plus the pod's current IP/port (they rotate on every
migration; get them from the RunPod console).

```bash
ssh -N -L 8080:localhost:8080 -o ServerAliveInterval=15 -o ServerAliveCountMax=8 \
    -p <PORT> -i ~/.ssh/runpod_ed25519 root@<IP>
```

The pod serves the checkpoint on **training-era code** at `/workspace/lerobot`
(upstream commit `e40b58a8`). This is not optional - newer code cannot serve
this checkpoint (see handoff Section 4, Era 1). After any pod migration, repair
the pod environment and re-apply the two idempotent patches - all documented in
handoff Section 7.

An HF token is needed only for downloading models/datasets. Put it in the
environment (`huggingface-cli login`), never in a file in this repo.

---

## 7. Datasets And Checkpoints (only for Stage 2/3)

Not needed to run the robot. The active checkpoint lives on the pod at
`/workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/`.
Old teleop datasets sat in `/data/lerobot_datasets/` on the old machine; copy
them only if you plan to retrain on the old data. The current plan records a
fresh, more diverse dataset anyway (handoff Section 9, Stage 2), so a clean
machine without them is fine.

---

## 8. Verification Gates - Prove It Works Before Any Robot Motion

Run these in order. Do not skip to a policy run; every one of these caught a
real failure at least once.

```bash
cd <REPO>/projects/testproject

# 1. env sane (see Section 3 expectations)
./.venv/bin/python -c "import lerobot, torch; print(lerobot.__file__, torch.__version__)"

# 2. calibration present
ls ~/.cache/huggingface/lerobot/calibration/robots/so_follower/my_so101_follower.json

# 3. all three cameras up - and LOOK at the images, do not just count them.
#    Confirm: front actually faces the robot; top sees the table AND the plate;
#    wrist is not black. The laptop must physically face the arm (this has
#    bitten three times).
curl -sf -o /tmp/wrist.jpg http://127.0.0.1:8092/frame && echo WRIST_OK

# 4. tunnel open
timeout 5 bash -c 'echo > /dev/tcp/127.0.0.1/8080' && echo TUNNEL_OK

# 5. analysis tool works on a known trace (needs an old trace dir; skip on a
#    clean machine - artifacts are not in git)
./.venv/bin/python scripts/analyze_grasp_from_trace.py artifacts/traces/<RUN>
```

Then the first live run, from handoff Section 7 (the frozen h35 recipe). Judge
it by the numbers, not by eye:

```text
healthy: ~1.5-2 obs/s, ~20 act/s
below 0.8 obs/s = the run is BLIND; fix infrastructure, discard the behavior
```

---

## 9. Traps Specific To A Fresh Machine

```text
Serial permission denied on /dev/ttyACM*  -> you did not log out after
  usermod -aG dialout. Group changes need a new session.
Cameras open but frames are GREY 640x360  -> you grabbed the IR sensor. Use
  by-path and verify formats with v4l2-ctl (Section 4).
lerobot imports from site-packages, not the repo -> editable install failed;
  redo Section 3. You would be running code you are not editing.
torch pulled ~3 GB of CUDA wheels -> you skipped the CPU index-url. Harmless
  but pointless; the GPU is on the pod.
Background shells start in the REPO ROOT, not projects/testproject. Use
  absolute paths or cd first.
pkill matching your own command kills the shell (exit 144). Use bracket
  patterns: pkill -f 'async_client_3cam[.]py'
```

---

## 10. When Setup Is Done

Read `docs/agent_handoff_pi05_20260803.md` from the top. It has the hard rules
(defaults untouched, three cameras or it does not count, never commit
artifacts, stop the pod), the verified capability state, the history including
the wrong turns, and the prioritized next steps.
