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

> **SIZES HERE ARE SUPERSEDED.** Every figure lives in one place now:
> `~/projects/git/mavlink-router/BACKUP_INVENTORY.md`. Keeping them in four
> documents failed within a day. What changed since this file was written:
>
> ```text
> 2026-08-07  the 380 GB of generated raw HDF5 was converted to a 966 MB
>             corpus and deleted
> 2026-08-07  the two day-1 HDF5s (35 GB) were deleted - see the correction
>             in Section 2, they were regenerable state-machine output
> => this project's keep-set went from ~63 GB to ~30 GB, and is now dominated
>    by model checkpoints (26 GB), not data.
> ```

```text
Whole home directory ..................... 183 GB on disk
  ...but 253 GB if you tar/rsync it, because the uv venvs are HARDLINKS
     into ~/.cache/uv (67 GB) and get expanded into real copies on write.
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

## 2. Tier B - the data worth keeping (about 30 GB)

### CORRECTION 2026-08-07 - the "irreplaceable recordings" were neither

This section used to open with *"Recorded demonstrations (35 GB) - the part you
can never get back"*, describing `sim_pick_place.hdf5` and
`sim_pick_place_ep4.hdf5` as hand-teleoped and unrecoverable. **Both claims
were wrong.**

```text
what it said          hand-teleoped in LeIsaac, re-recording means sitting at
                      the GUI again; a re-clone migration destroys 35 GB of
                      irreplaceable data
what was true         STATE-MACHINE OUTPUT. Regenerable in ~30 min by the
                      committed generator. Deleted 2026-08-07 after conversion;
                      nothing unique lost.
```

The provenance was never verified - it was inferred from the files living in
LeIsaac's `datasets/` directory, which is the recording output path for **both**
teleop and generation. The artifact disagreed the whole time:

```text
leisaac/datagen/state_machine/pick_orange.py:134
    """Compute the action tensor for the current step (8D IK pose target)."""
    return torch.cat([target_pos_local, target_quat, gripper_cmd], -1)
                         3 (pos)      +   4 (quat)  +  1 (grip)   = 8

the deleted files                  actions (2340, 8)  -> state machine
leisaac_pick_orange (real teleop)  action  [6] joint  -> leader arm
```

`seed = int(time.time())` proves nothing either way - it is the LeIsaac default
in `generate.py`, `teleop_se3_agent.py` and `policy_inference.py` alike.

**The rule this earns:** *"irreplaceable" is a claim about provenance, and
provenance must be read out of the artifact, never inferred from its path.*
Before marking anything unrecoverable, open it and find the signature.

### What actually holds the data now

```text
~/.cache/huggingface/lerobot/local/varied_corpus/                  966 MB
    35 episodes, 81,645 frames, LeRobot v3. The project's SOLE data artifact
    since the raw deletions. Regenerable by sm_generate_varied.py in ~14 h, so
    not irreplaceable - but 966 MB is far cheaper to keep than to rebuild.

    *** Lives under ~/.cache/huggingface/, which Section 3 tells you to SKIP.
        Re-include lerobot/local/ and lerobot/calibration/ explicitly. ***
```

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

## 5-6. Recipes and verification - MOVED

These two sections held their own `tar`/`rsync` recipes and verification
checks. They drifted: they still assumed ~63 GB, targeted an external SSD that
never existed, and named `sim_pick_place*.hdf5` files that were deleted on
2026-08-07. Two copies of a procedure means one of them is wrong, and it was
this one.

**The single tested procedure now lives in the runbook**, against the real
target and dry-run against the live machine:

```text
~/projects/git/mavlink-router/BACKUP_RESTORE_RUNBOOK.md
    Part I    quiesce pre-flight, the three tiers
    Part III  the Orin: layout, retention, push, verify, promote, restore
              Section 18 is the ordered first run
~/projects/git/mavlink-router/BACKUP_INVENTORY.md
    every path and size, with a completeness-check recipe
```

Target: `kiran@192.168.0.146:~/backup/desktop/`. Tier 2 has been pushed and its
restore verified byte-identical; Tier 3 has not run yet.

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
