# RESTORE ON NEW MACHINE — SO-101 Orange Pick

> **OUTDATED (2026-08-03). Use [`NEW_MACHINE_SETUP.md`](NEW_MACHINE_SETUP.md) instead.**
> This file describes the pre-fork layout (`/data/projects/lerobot`,
> `~/PrakashProjects/testproject`) from before the project moved inside the
> lerobot fork, and it points at `START_HERE.md` → `GRASP_FIX_PLAN.md`, both
> long superseded. The current entry points are
> `NEW_MACHINE_SETUP.md` (machine bring-up) and
> `docs/agent_handoff_pi05_20260803.md` (the project).
>
> **The transfer recipes below are also superseded.** They move ~9 GB from the
> old laptop era. The workstation now holds 35 GB of teleop HDF5s and 26 GB of
> fine-tuned checkpoints, none of which appear here, and the paths in every
> command below no longer exist. For what to copy and how, use
> [`BACKUP_MANIFEST.md`](BACKUP_MANIFEST.md) (audited 2026-08-06).

This bundle is the **SO-101 orange-pick robotics project**. After you copy it onto the new
machine and restore the folders, **open the project and read [`testproject/START_HERE.md`](START_HERE.md)** —
that explains the project, current state, the open problem, and how to continue.

Two ways to transfer, then how to put the files back.

---

## Transfer method A — Direct over Wi-Fi (recommended)

The **old laptop** (source) already runs an SSH server:
- **Old laptop IP:** `192.168.1.163`  ·  **user:** `prakash-gaikwad`  ·  (Wi-Fi `192.168.1.x`)
- ⚠️ That IP is DHCP — re-check it on the old laptop with `hostname -I` right before transferring.

On the **new laptop** (after Ubuntu is installed and on the *same Wi-Fi*), **pull** each folder:

```bash
# make target dirs
mkdir -p ~/PrakashProjects /data/projects /data/lerobot_datasets \
         /data/act_orange_checkpoints /data/act_orange49_checkpoints \
         "/data/downloads/3cam tests" /data/act_orange_evals /data/so101_calibration_backup \
         ~/.cache/huggingface/lerobot

OLD=prakash-gaikwad@192.168.1.163       # <-- confirm IP first

# code + source
rsync -avz --progress "$OLD:~/PrakashProjects/testproject/"        ~/PrakashProjects/testproject/
rsync -avz --progress "$OLD:/data/projects/lerobot/"               /data/projects/lerobot/
# datasets + models
rsync -avz --progress "$OLD:/data/lerobot_datasets/"               /data/lerobot_datasets/
rsync -avz --progress "$OLD:/data/act_orange49_checkpoints/"       /data/act_orange49_checkpoints/
rsync -avz --progress "$OLD:/data/act_orange_checkpoints/"         /data/act_orange_checkpoints/   # optional (old 30-ep)
# results
rsync -avz --progress "$OLD:'/data/downloads/3cam tests/'"         "/data/downloads/3cam tests/"
rsync -avz --progress "$OLD:/data/act_orange_evals/"               /data/act_orange_evals/
# calibration (BOTH) + keys
rsync -avz --progress "$OLD:/data/so101_calibration_backup/"       /data/so101_calibration_backup/
rsync -avz --progress "$OLD:~/.cache/huggingface/lerobot/calibration/" ~/.cache/huggingface/lerobot/calibration/
mkdir -p ~/.ssh && rsync -avz "$OLD:~/.ssh/runpod_ed25519" ~/.ssh/ && chmod 600 ~/.ssh/runpod_ed25519
# (also copy the Pi SSH key + ~/.ssh/known_hosts the same way)
```

`rsync -avz` preserves permissions + symlinks natively (no filesystem worries). It's also **resumable** — re-run if the network drops. ~9 GB ≈ a few minutes on decent Wi-Fi.

---

## Transfer method B — External SSD (offline / backup)

On the **old laptop**, pack everything into ONE archive on the SSD (preserves Linux
permissions/symlinks even if the SSD is exFAT/NTFS):

```bash
SSD=/media/prakash-gaikwad/<LABEL>        # where the SSD mounted
tar -cvf "$SSD/so101_project.tar" -P \
  /home/prakash-gaikwad/PrakashProjects/testproject \
  /data/projects/lerobot \
  /data/lerobot_datasets \
  /data/act_orange49_checkpoints /data/act_orange_checkpoints \
  "/data/downloads/3cam tests" /data/act_orange_evals \
  /data/so101_calibration_backup \
  /home/prakash-gaikwad/.cache/huggingface/lerobot/calibration \
  /home/prakash-gaikwad/.ssh/runpod_ed25519
```

On the **new laptop**, plug the SSD in and extract to root (recreates the same paths):

```bash
sudo tar -xvf /media/$USER/<LABEL>/so101_project.tar -C /
sudo chown -R $USER:$USER ~/PrakashProjects /data/* ~/.cache/huggingface ~/.ssh 2>/dev/null
chmod 600 ~/.ssh/runpod_ed25519
```

*(No compression is used — the data is already-compressed video, so plain `tar` is fastest.)*

---

## What you need for the transfer (checklist)

- **Network method:** both laptops on the **same Wi-Fi**; the **old laptop's current IP** (`hostname -I`, was `192.168.1.163`); the old laptop's **login password** (for `prakash-gaikwad`). SSH server is already running on the old laptop.
- **SSD method:** an external SSD with ≥ 15 GB free.
- Either way you're moving **~9 GB**.

---

## After the files are restored

1. Follow the **new-machine setup** in [`START_HERE.md`](START_HERE.md) §6 (install `ffmpeg`/`v4l-utils`/etc., `dialout` group, rebuild the Python env, fix the `packaging` import).
2. **Reconfigure cameras/ports** — the USB `by-id` paths differ on the new machine, and the **front camera (laptop webcam) will be a different device**. Update the `so101` config. Re-detect with `ls /dev/v4l/by-id/` and `ls /dev/serial/by-id/`.
3. **Calibration travels with the arms** — if you moved the same physical arms + these calibration files, you do **not** need to recalibrate.
4. Move the hardware (arms + C270 camera). The **wrist Pi camera** stays on the network — new laptop needs the same Wi-Fi + the Pi key; restart `tools/pi_wrist_proxy.py`.

**Then read `START_HERE.md` → `docs/GRASP_FIX_PLAN.md` and continue with Step 1 (GPU closed-loop).**
