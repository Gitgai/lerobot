# Backup Manifest - what to take off this workstation

Last updated: 2026-08-06. Audited against the live machine on that date.

This is the counterpart to `NEW_MACHINE_SETUP.md`. That file tells you how to
bring a new machine up; this one tells you what to carry over so there is
anything to bring up. Read both before a migration.

`~` here is `/home/kiran` on the workstation (RTX 5090, Ubuntu, 1.8 TB nvme,
375 GB used). Every size below was measured, not estimated.

> **SCOPE - read this first.** This manifest covers the **NVIDIA / LeRobot /
> Isaac Sim project only**. The workstation hosts a second project of yours -
> the DYNUS/ASIS drone-autonomy work - which this file does NOT cover.
> Backing up only what is listed here loses it.
>
> ```text
> machine-wide index (all 3 projects)
>     ~/projects/git/mavlink-router/MACHINE_BACKUP_INDEX.md
> DYNUS/ASIS manifest
>     ~/projects/git/mavlink-router/drone-autonomy/experiments/branch1/
>         DYNUS_ASIS_BACKUP_MANIFEST.md
> ```

```text
Whole home directory ..................... 183 GB on disk
  ...but 253 GB if you tar/rsync it, because the uv venvs are HARDLINKS
     into ~/.cache/uv (67 GB) and get expanded into real copies on write.
This manifest (NVIDIA project only) ......  63 GB
  of which two HDF5 files are .............  35 GB
  of which everything irreplaceable-and-small is .. under 400 MB
```

---

## 0. Before anything else: PUSH

The highest-value thing on this disk is not a file, it is unpushed git history.
A backup that runs before this step preserves the risk instead of removing it.

```bash
cd /home/kiran/projects/git/nvidia/lerobot
git status -sb          # expect: ## main...origin/main [ahead N]
git push origin main
```

As of 2026-08-06 this was **31 commits ahead of `origin/main`** with a clean
working tree - everything from "Make the real arm the plan again" through
"Build the varied-data generator and the overnight batch driver". That is the
robustness campaign, the sim-to-real preflight, and the data-generation track.
None of it existed anywhere but this disk.

Two more repos hold uncommitted work that no remote has. They are not ours to
push, so their diffs must be captured as files (Section 1).

```text
~/sim/Isaac-GR00T-n16        M gr00t/configs/data/data_config.py
                             M gr00t/eval/real_robot/SO100/eval_so100.py
                             M gr00t/experiment/launch_finetune.py
   These three are the patches that made the N1.6 fine-tune run at all.
   Each has a .orig beside it, so the diff is recoverable either way.

~/lerobot_assets/lerobot_trainingera
                             M src/lerobot/async_inference/policy_server.py
                             ?? src/lerobot/async_inference/image_codec.py
   The JPEG-codec / threading work on the training-era server. `image_codec.py`
   is UNTRACKED - a `git stash` or a clean checkout deletes it silently.
```

---

## 1. Tier A - no copy exists anywhere else (about 400 MB)

Small enough that there is no excuse to skip it, and losing any line of it
costs days.

```text
~/projects/git/nvidia/lerobot            EXCLUDING projects/testproject/.venv
                                         ~300 MB (.git alone is 189 MB)
    The fork, the 31 commits, scripts/, tools/, docs/ - the whole project.

~/projects/git/nvidia/lerobot/projects/testproject/logs/          59 MB
    *** GIT-IGNORED. It will not travel with a `git push`. ***
    Every experiment CSV and log: the robustness campaign, the preflight
    batteries, logs/sm_variations/ and its 36 reference snapshots. Each
    variation battery is ~75 minutes of wall clock to regenerate, and the
    snapshots are the policy's-eye view that the decoy finding rests on.

~/.cache/huggingface/lerobot/calibration/                          8 KB
    robots/so_follower/my_so101_follower.json
    teleoperators/so_leader/my_so101_leader.json
    Both present and verified 2026-08-06. Cannot be recreated without
    physically recalibrating both arms. Travels with the arms, not the
    machine - if the same physical arms move, do NOT recalibrate.

the two repo diffs from Section 0                                  ~KB
    Capture as patch files, see the recipe below.

~/sim/*.log                                                        ~3 MB
    n16_finetune.log, pi05_gt_eval.log, n17_rerun.log, teleop_gui.log,
    sm_variations.log and the rest - the training and eval history that the
    docs cite.

~/.claude/projects/-home-kiran-projects-git-nvidia/memory/         ~KB
    Agent memory for this project (sudo needs a password; no scripts in /tmp).

~/.ssh/runpod_ed25519  (+ the Raspberry Pi key, if key auth)
    Never commit these. See NEW_MACHINE_SETUP.md Section 2.
```

Capture the diffs like this - do it before the archive, so they land in it:

```bash
mkdir -p ~/backup_staging
git -C ~/sim/Isaac-GR00T-n16 diff > ~/backup_staging/isaac-groot-n16.patch
git -C ~/lerobot_assets/lerobot_trainingera diff > ~/backup_staging/trainingera.patch
cp ~/lerobot_assets/lerobot_trainingera/src/lerobot/async_inference/image_codec.py \
   ~/backup_staging/                     # untracked, the diff does NOT contain it
```

---

## 2. Tier B - irreplaceable data, large (about 63 GB)

### Recorded demonstrations (35 GB) - the part you can never get back

```text
~/sim/leisaac-src/datasets/sim_pick_place.hdf5      23 GB, 8 episodes, 3 SUCCESS
~/sim/leisaac-src/datasets/sim_pick_place_ep4.hdf5  12 GB, 1 episode,  1 SUCCESS
```

Hand-teleoped in LeIsaac. Re-recording them means sitting at the GUI again.

**The trap:** these live *inside* a git clone. `leisaac-src` is clean at
`24d3bcd` and otherwise looks entirely re-clonable, so a "just re-clone the
dependencies" migration deletes 35 GB of irreplaceable teleop data. The
datasets are not in the repo and never were.

```text
~/lerobot_assets/datasets/                                        1.9 GB
    so101_orange_49/                                   770 MB
    so101_orange_49_plus_grasp_pick_move_focus/        770 MB
    leisaac_pick_orange/                               398 MB
    The 89 real episodes and the LeRobot-format conversion. Some may exist on
    the Hub - check before trusting that, the local ones are cleaned/trimmed.
```

### Fine-tuned checkpoints (26 GB) - recreatable only by re-running training

```text
~/lerobot_assets/checkpoints/
    gr00t_n16_leisaac_orange/      9.2 GB   ckpt/checkpoint-10000
                                            *** THE working policy. 94% in sim.
                                            This is what the whole project
                                            currently rests on. ***
    pi05_012000/                   8.8 GB   the Pi05 comparison checkpoint
    leisaac_pick_orange_n15/       7.1 GB   step 10000, 5 epochs
    smolvla_so101_digits/          880 MB
    act_leisaac_orange/            198 MB
    gr00t_n16_ft_leisaac/          532 KB   (stub - check before keeping)
```

---

## 3. Tier C - do NOT back up (about 90 GB skipped)

Every item here has a canonical source. Record the pin, drop the bytes.

```text
VENVS - rebuild, never copy (a venv is not relocatable anyway)
    ~/sim/leisaac-venv                              16 GB   <- see Section 4
    ~/projects/git/nvidia/lerobot/projects/testproject/.venv  8.9 GB
    ~/lerobot_assets/lerobot_trainingera/.venv       7.5 GB
    ~/tools/rendervenv

BASE / COMMUNITY MODELS - re-download from HF
    ~/lerobot_assets/checkpoints/gr00t_n16_base      6.2 GB
        NVIDIA release (model card: nvidia/PhysicalAI-Robotics-GR00T-X-Embodiment-Sim)
    ~/lerobot_assets/checkpoints/gr00t_n17_so101     6.1 GB
        `robocurve/gr00t-n1.7-so101-molmoact2`, a community fine-tune.
        Confirmed re-downloadable - see gr00t_n17_sim_evaluation_20260805.md.

HF CACHE
    ~/.cache/huggingface                             4.6 GB   (keep calibration/, Tier A)

CLEAN CLONES - re-clone at these exact commits, they are all 0 commits ahead
    ~/sim/leisaac-src            LightwheelAI/leisaac              24d3bcd
        submodule dependencies/IsaacLab                            3c6e67bb5
        (but see Section 2 - the datasets/ inside it are NOT re-clonable)
    ~/sim/Isaac-GR00T            NVIDIA/Isaac-GR00T                b995540
    ~/sim/Isaac-GR00T-n16        NVIDIA/Isaac-GR00T                ead5283  + patch
    ~/sim/openpi                 Physical-Intelligence/openpi      5bff19b
    ~/lerobot_assets/lerobot_trainingera  huggingface/lerobot      e40b58a8  + patch
        This SHA is load-bearing: NEW_MACHINE_SETUP.md Section 6 records that
        newer code cannot serve the pi05_012000 checkpoint.

CACHES - regenerate, and never put them in an archive
    ~/.cache/uv                                     67 GB
        The venvs above are hardlinked into this. Archiving both writes the
        bytes twice; archiving neither costs nothing but a rebuild.
    ~/.cache/pip                                    2.8 GB
    ~/Downloads                                     654 MB  (.deb installers)

NOT THIS PROJECT - but STILL YOURS, and covered by a separate manifest
    ~/dynus-scip-src, ~/asis_results, ~/asis_smoke*, ~/asis_artifacts,
    ~/flightmare_g485, ~/e10_ply, ~/trajs_m4b, ~/dynus.tgz,
    ~/projects/git/mavlink-router, ~/projects/git/dynus-upstream,
    ~/datasets/euroc_mav_ros2, and ~55 loose scripts in ~ itself.
    *** CORRECTED 2026-08-06: an earlier draft of this file called these
    "another user's drone stack" and told you to skip them. That was WRONG.
    The ASIS scripts SOURCE another user's build (/home/kkondo/code/dynus_ws),
    which is what made them look foreign - but the harness, the results and
    the SCIP port are yours. Do not skip them. ***
```

---

## 4. The rebuild gotcha - capture the environment, not the venv

`~/sim/leisaac-venv` is 16 GB and 550 packages, built with `uv 0.12.1` on
CPython 3.11. **`leisaac-src` has no `pyproject.toml`, `requirements.txt` or
lockfile at its root** - checked 2026-08-06. Nothing in any repo pins that
environment. Rebuilding it from scratch means re-deriving the Isaac Sim 5.1
dependency set by hand.

So capture the recipe even though you are dropping the bytes:

```bash
~/sim/leisaac-venv/bin/python -m pip freeze > ~/backup_staging/leisaac-venv.freeze
~/projects/git/nvidia/lerobot/projects/testproject/.venv/bin/python -m pip freeze \
    > ~/backup_staging/testproject-venv.freeze
apt-mark showmanual > ~/backup_staging/apt-manual.txt
nvidia-smi > ~/backup_staging/gpu.txt          # driver 580.173.02, CUDA 13.0
```

Related, and worth writing down so it is not rediscovered: **this venv is
already subtly broken.** Every Isaac Sim run logs

```text
OSError: libxml2.so.2: cannot open shared object file: No such file or directory
[ext: isaacsim.asset.importer.urdf-2.4.30] Failed to startup python extension.
```

The URDF importer and part of OGN node registration are dead. Sim runs work
anyway because nothing in the current path imports a URDF. Do not reproduce
this on the new machine - install the libxml2 runtime and confirm the extension
starts clean.

---

## 5. Recipes

Sizes assume Tier A + Tier B, about 63 GB. Plain `tar`, no compression - HDF5
and safetensors are already dense and `-z` only costs hours.

### To an external SSD

```bash
mkdir -p ~/backup_staging          # run Section 1 + Section 4 captures first
SSD=/media/$USER/<LABEL>           # needs >= 70 GB free

tar -cvf "$SSD/nvidia_project_$(date +%Y%m%d).tar" -P \
  --exclude='*/.venv' \
  /home/kiran/projects/git/nvidia/lerobot \
  /home/kiran/sim/leisaac-src/datasets \
  /home/kiran/sim/*.log \
  /home/kiran/lerobot_assets/datasets \
  /home/kiran/lerobot_assets/checkpoints/gr00t_n16_leisaac_orange \
  /home/kiran/lerobot_assets/checkpoints/pi05_012000 \
  /home/kiran/lerobot_assets/checkpoints/leisaac_pick_orange_n15 \
  /home/kiran/lerobot_assets/checkpoints/smolvla_so101_digits \
  /home/kiran/lerobot_assets/checkpoints/act_leisaac_orange \
  /home/kiran/.cache/huggingface/lerobot/calibration \
  /home/kiran/.claude/projects/-home-kiran-projects-git-nvidia/memory \
  /home/kiran/backup_staging \
  /home/kiran/.ssh/runpod_ed25519
```

`--exclude='*/.venv'` is what keeps this at 63 GB instead of 90. Verify it
worked before trusting the archive (Section 6).

Restore on the new machine:

```bash
sudo tar -xvf /media/$USER/<LABEL>/nvidia_project_<DATE>.tar -C /
sudo chown -R $USER:$USER ~/projects ~/sim ~/lerobot_assets ~/.cache/huggingface ~/.ssh
chmod 600 ~/.ssh/runpod_ed25519
```

### Directly to a new machine over the network

`rsync` is resumable, which matters for a 35 GB file on a link that may drop.
Push from here rather than pulling - it needs no SSH server on this end.

```bash
NEW=<user>@<new-machine-ip>
IP=${NEW#*@}; ping -c2 -W3 "$IP" && timeout 5 bash -c "echo > /dev/tcp/$IP/22" && echo SSH_OK

rsync -avz --progress --exclude='.venv' \
      ~/projects/git/nvidia/lerobot/                  "$NEW:~/projects/git/nvidia/lerobot/"
rsync -avz --progress ~/sim/leisaac-src/datasets/     "$NEW:~/sim/leisaac-src/datasets/"
rsync -avz --progress ~/lerobot_assets/datasets/      "$NEW:~/lerobot_assets/datasets/"
for c in gr00t_n16_leisaac_orange pi05_012000 leisaac_pick_orange_n15 \
         smolvla_so101_digits act_leisaac_orange; do
  rsync -avz --progress ~/lerobot_assets/checkpoints/$c/ "$NEW:~/lerobot_assets/checkpoints/$c/"
done
rsync -avz --progress ~/.cache/huggingface/lerobot/calibration/ \
                      "$NEW:~/.cache/huggingface/lerobot/calibration/"
rsync -avz --progress ~/backup_staging/ ~/sim/*.log    "$NEW:~/backup_staging/"
```

Note the **trailing slashes on both sides** - without them rsync nests the
directory one level deeper and the restore silently lands in the wrong place.

---

## 6. Verify the backup before you wipe anything

A backup you have not read back is a hypothesis.

```bash
# the two big ones are intact - byte counts, not just presence
tar -tvf "$SSD/nvidia_project_<DATE>.tar" | grep sim_pick_place
#   expect  24305408326  sim_pick_place.hdf5
#   expect  12260177895  sim_pick_place_ep4.hdf5

# no venv sneaked in (each is GBs and makes the archive useless-fat)
tar -tf "$SSD/nvidia_project_<DATE>.tar" | grep -c '/\.venv/'
#   expect  0

# the git-ignored evidence made it
tar -tf "$SSD/nvidia_project_<DATE>.tar" | grep -c 'testproject/logs/'
#   expect  a few thousand, NOT 0

# calibration - the 8 KB whose loss costs a recalibration of both arms
tar -tf "$SSD/nvidia_project_<DATE>.tar" | grep calibration
#   expect  both my_so101_follower.json and my_so101_leader.json

# the working policy is really in there
tar -tf "$SSD/nvidia_project_<DATE>.tar" | grep -c 'gr00t_n16_leisaac_orange/ckpt'
#   expect  > 0
```

---

## 7. Restore order on the new machine

1. Extract, or rsync in. Fix ownership and the key mode.
2. `NEW_MACHINE_SETUP.md` Sections 3-4 - apt packages, `dialout` group,
   rebuild the venvs from the `.freeze` files, re-detect camera and serial
   device paths. **Do not skip Section 4**; the committed device paths are
   this machine's and will point at hardware that does not exist.
3. Install the libxml2 runtime and confirm no `libxml2.so.2` error in the
   first Isaac Sim log (Section 4 above).
4. Re-clone the Tier C repos at the pinned SHAs, then apply
   `isaac-groot-n16.patch` and `trainingera.patch` and drop `image_codec.py`
   back into `src/lerobot/async_inference/`.
5. Re-download the base and community checkpoints from HF.
6. Read `docs/STATE_20260806.md` - that is the project, and it assumes the
   sim stack and `gr00t_n16_leisaac_orange` are both present.

---

## 8. Traps

```text
The 35 GB of teleop HDF5s sit INSIDE a clean git clone (~/sim/leisaac-src).
  "Re-clone the deps, skip the clone dirs" destroys them. They are the single
  largest irreplaceable thing on the machine.

projects/testproject/logs/ is git-ignored. Pushing the repo does NOT save it.
  All the campaign and battery evidence lives there.

image_codec.py in lerobot_trainingera is UNTRACKED, so `git diff` misses it.
  Copy the file, do not rely on the patch.

No lockfile pins leisaac-venv (16 GB, 550 packages). Capture pip freeze BEFORE
  the machine goes away, or rebuild it by hand from Isaac Sim 5.1 upward.

Calibration is 8 KB and cannot be regenerated without both physical arms.
  It is the cheapest thing here and the most expensive to lose.

This manifest is NOT a whole-machine backup. It covers one of your projects.
  The DYNUS/ASIS drone work is a second one and needs its own pass.

Another user (kkondo) runs a ROS/Gazebo/Flightmare stack on this box, which is
  why it sometimes sits at load 60+ on 24 cores. An Isaac Sim run was SIGKILLed
  at 2026-08-06 21:14 under that contention. Their files live in /home/kkondo
  and are not yours to back up - but your ASIS scripts DRIVE their build, so
  your harness is worthless on a new machine without dynus_ws also being there.
```


## Added 2026-08-07 — the N1.6 stack (see docs/N16_REBUILD_RUNBOOK.md)

```text
MUST BACK UP (cannot be rebuilt from git):
  ~/lerobot_assets/checkpoints/gr00t_n16_leisaac_orange   9.2 GB
      THE working policy. Third-party HF upload (12e21/..., revision
      6d73eafb...) - author could delete it; local copy is primary.
      RECOMMENDED: mirror to the user's own private HF repo.
  ~/.cache/huggingface/lerobot/local/varied_corpus        966 MB
      the varied training corpus (35 eps; raw was deleted - this is the
      only copy; regenerable but costs ~4 h of generation + conversion)
  ~/lerobot_assets/datasets/leisaac_pick_orange           667 MB
      LightwheelAI dataset, GR00T-prepped (re-downloadable + ~30 min prep)

EVERYTHING ELSE N1.6-RELATED rebuilds from the runbook + patches/ + pins.
```
