# How to run a supervised SO-101 trial — updated 2026-10-03

## Current instructions: this section supersedes the historical guide below

### Latest user decision: existing client, RTC OFF (2026-10-04)

The user accepts project integration and wants only custom RTC disabled for the next comparison. The strict official/raw-image environment rebuild is deferred. Follow the superseding section of `GROOT_OFFICIAL_BASELINE_PLAN_20261004.md`. Use `run_numbered_groot_trial.py 1 --series tomato-rtc-off` only after fresh readiness checks; this starts physical motion. Add `--show-command` to preview without hardware access. Settings: same model, tomato task, JPEG92, existing sequential execution8 actions/reply, unchanged protections/logging, no trial timer. Label results **GR00T existing client, RTC off**, not unmodified official GR00T. Separate series1–3; retain earlier trial IDs. Stop/investigate if overload recurs. All older strict-official prerequisites and RTC-on commands below are superseded for this experiment.

### Current decision — 2026-10-04: official baseline, no custom RTC

The user has excluded the project's custom RTC scheduler from upcoming baseline tests. **Do not run the current numbered launcher unchanged: it still enables custom RTC.** Follow [GROOT_OFFICIAL_BASELINE_PLAN_20261004.md](GROOT_OFFICIAL_BASELINE_PLAN_20261004.md): audit the version-matched official N1.6 path, document any required integration, then prepare a separate initial three-trial tomato baseline series. Setting `rtc=false` alone is not verification of official execution.

Keep historical trial IDs unchanged and label their execution as GR00T + custom RTC. Tomato trial1 on2026-10-04 stopped with gripper Status32 after19.43s, after grasp/lift/transport but before a confirmed release. Do not mix it with `official-baseline tomato1–3`.

Deeper overload investigation is deferred until recurrence or a current readiness fault. Protections, startup checks and stop/cleanup remain enabled. If overload recurs, stop and investigate before another trial; no automatic clear/retry or increased limits. Existing command examples below remain historical/preparation references, not authorization to resume custom RTC.

### Latest amendment: trial 6 review and tomato numbering (2026-10-03)

Trial 6 is now a **confirmed placement success**: release onto the plate around91.4–91.8s, withdrawal, and stable placement through the final overview at281.85s. Review covered both overview sheets and112 consecutive saved images around89–99s, not all3102 images visually. No motor fault was recorded; operator stopped later. The historical six-run mixed-object set now has **2 confirmed full successes, 1 partial/release-unconfirmed, and3 unsuccessful placements**. Do not call this a six-orange success rate: earlier runs included larger yellow fruit.

The user requested a separate **Tomato trial1–5** series rather than continuing tomato at legacy number7. Preserve all old trial IDs and evidence. No tomato run has started. Older pending-review and hardcoded-launcher statements below are superseded by this amendment.

The numbered launcher now accepts `--series tomato`, selects the verified tomato task, records object/series/task and actual date, and refuses reuse of a series number even on a later date. It preserves RTC-on/JPEG92, no trial timer, motor protections and no automatic homing/restart.

```bash
# Preparation only: prints command/manifest, no hardware access or movement
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python /home/gaikwad-prakash/Documents/ChatGPT/Lerobot/run_numbered_groot_trial.py 1 --series tomato --show-command
```

Remove `--show-command` ONLY when a physical trial is explicitly ready/authorized and today's rig checks have passed. That starts real movement. Each tomato trial remains supervised and separate from orange results.

This is a project runbook, not a statement of official LeRobot defaults. No physical trial or motor-setting change was performed during this documentation update.

### Current progress

- Overall GR00T trials 1–6 have run; 7–10 are pending. Initial run = overall 1; old repeats 1–4 = overall 2–5. Original directory names are preserved.
- First five: one camera-confirmed full placement, one pick/transport with release unconfirmed, three unsuccessful placements. The operator recalls 2/5 successes; preserve that separately from the recorded verdict.
- Trial 6: operator stopped after about 282 seconds; 1,551 images per camera, no recorded motor faults. Visual outcome review is pending. Afterwards all six motors were independently verified torque off and Status 0; the arm was not homed. This is historical state, not a live check today.
- The user replaced the orange with a tomato. Treat subsequent tomato trials as a separate object condition. No tomato trial has been launched by this update.

### Tomato support verified on 2026-10-03

The existing AI90 server process, PID 11632, runs `/home/kiran/sim/Isaac-GR00T-n16/.venv/bin/python /home/kiran/srv_wrap_recov.py` with `RECOV_CKPT=6000`. The wrapper selects `/home/kiran/lerobot_assets/checkpoints/n16_recovery_v1/n16_recovery_v1/checkpoint-6000` on port 5555. Process/configuration evidence is not by itself a fresh inference-health test.

The checkpoint's `experiment_cfg/config.yaml` identifies `/home/kiran/lerobot_assets/datasets/new30_plus_recov30` and initialization from the older `n16_new30_v1/.../checkpoint-6000`. Dataset metadata contains **60 episodes: 50 orange and 10 tomato**. Both its `meta/tasks.jsonl` and the recovery checkpoint family's `TASKS.json` include:

```text
pick up the orange and place it on the plate
pick up the tomato and place it on the plate
```

This supports a tomato trial with the exact tomato instruction; it does not guarantee a successful or gentle grasp of this tomato. Do not increase gripper settings for the object change.

Acer's `/home/gaikwad-prakash/model_tasks.json` accepts both labels but still names the older `new30_merged` dataset. That provenance field is stale; it is not sole proof of the currently served model's training. It was not silently rewritten.

### One supervised trial at a time

1. Check the exact server/checkpoint, task, current pose, motor status, torque state, cameras and clear workspace. The operator supervises with access to physical power cutoff.
2. Home separately when necessary and authorized; verify the result. Do not assume yesterday's pose persists.
3. Launch one trial with fresh evidence storage. No automatic retry or next-trial start.
4. Stop the exact owned launcher/client process when requested or when the attempt ends. Verify cleanup and torque readback.
5. Review grasp, lift, transport, release, final rest and interventions in both camera streams; document the outcome. Reset the fruit before the next trial. Task success does not guarantee automatic homing or program exit.

### Current GR00T commands and environments

If the AI90 server is absent and a launch is requested, use the established interpreter, not generic system Python:

```bash
# AI90 — do not launch a duplicate server
RECOV_CKPT=6000 /home/kiran/sim/Isaac-GR00T-n16/.venv/bin/python -u /home/kiran/srv_wrap_recov.py
```

Current numbered launcher on Acer:

```bash
# ORANGE example only — NOT suitable unchanged for the user's tomato
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python -u /home/gaikwad-prakash/Documents/ChatGPT/Lerobot/run_numbered_groot_trial.py 7
```

It accepts 6–10, refuses existing output folders, uses RTC on/JPEG 92, and has no trial-lifetime timer. It does NOT home. It currently hardcodes the orange instruction: **prepare an explicit tomato task option before running it for tomato**. No launcher change was made in this documentation update. It also hardcodes directory suffix `20261002`; the actual timezone-aware start date is in `launch_manifest.json`. Correct new-day naming before future launches without renaming/deleting existing evidence.

The older `home_and_trial.sh <N>` is a different path: it homes first and defaults to a 300-second client lifetime including startup. Do not silently substitute it for an unlimited numbered trial.

Trial 6 root is `/home/gaikwad-prakash/so101_trials/groot-trial-006-20261002/`. It contains `launch_manifest.json`, `client_console.log`, `client_console.log.exit.json`, and `client/` with events, frames, diagnostics and `post_trial/` reports. Legacy runner evidence paths differ; not every result.json has the same fields.

### Stop/home corrections

Resolve the exact owned launcher PID before SIGTERM; avoid broad process-name kills. The numbered launcher's 15-second cleanup grace is not a trial timer. Inspect the exit record for forced termination, and verify all six torque readbacks. Releasing torque may drop an arm or payload; it is not automatically safe in every physical arrangement.

When homing is requested and the workspace/startup checks are ready:

```bash
# Acer — physical movement
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python -u /home/gaikwad-prakash/home_arm.py
```

The existing script checks faults, interpolates to home, checks final errors and releases torque. If it fails, investigate. Do not blindly clear/retry three times. `clear_overload.py` issues torque-off writes and verifies replies; it is not just a bus warm-up and does not repair the cause.

### Important motor-setting difference

| Register | GR00T environment | Patched pi05 client environment |
|---|---:|---:|
| Max_Torque_Limit | 500 | 1000 |
| Protection_Current | 250 | 500 |
| Overload_Torque | 25 | 80 |

Verified in the local follower configuration code. GR00T uses `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv`; pi05 uses `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/.venv-official-client-061`. The latter's old inline percentage comments no longer match its edited values. These are register settings, not measured force.

**Overload is not conclusively solved:** recent GR00T and human-teleoperation runs reported Status 32. Raising settings does not establish a fix. These different settings confound model comparisons. No setting changes are recommended or made here. Startup configure() rewriting registers is not proof that every setting resets to factory on power cycling.

The follower supply was historically adjusted to about 7.4 V. Verify the applicable hardware ratings and live conditions; do not generalize a voltage rating to every servo variant. The adapter display alone does not establish loaded servo voltage.

### Automatic reports and visual review

The existing journal-based GR00T and logged-teleoperation paths generate offline metrics, decode checks and sampled front/wrist review sheets after hardware cleanup and clean journal closure. They do NOT automatically determine visual task success. New verdicts remain awaiting visual review. Crashes or incomplete journals may prevent reporting. Obtain operator-stop classification from the exit record when the journal lacks it.

There is no universal gripper-position threshold that proves a grasp. Judge placement from the sequence, not a single after-run photo. A later fault does not erase an earlier completed placement, but a fault-release drop onto the plate is not normal policy-controlled placement. Separate tomato/orange conditions and exclude human teleoperation from policy success rates.

Acer's authoritative documents (these filesystem paths are on Acer, not AI90):

- `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/SO101_TRIAL_RESULTS_LEDGER.md`
- `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/SO101_TRIAL_REPORTING_WORKFLOW_20261002.md`
- `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/trial_results/reviewed_outcomes.json`

Do not open a competing camera reader during a trial. Saved frames CAN be inspected while the client owns the cameras. Afterward the existing preview script warms each camera for about eight seconds; 45 reads are not an equivalent guarantee. Network latency varies, and a fixed random seed does not guarantee identical physical outcomes.

### pi05 historical commands are not current defaults

The old `run_fullft10k_raw_trial.py` below is raw-image, RTC-off and explicitly runs a fake-actuator phase before live motion. It is not the later JPEG comparison path. The user has declined mandatory fake-hardware testing; do not run this old path as an assumed default. Select the exact checkpoint, launcher and transport explicitly before another pi05 trial. Verify actual server lifetime instead of assuming every variant lasts 15 minutes. RTC is not a guaranteed smooth-motion fix.

Keep the pickle-bearing pi05 transport loopback/tunneled. The historical reverse tunnel was launched on AI90:

```bash
ssh -N -o ExitOnForwardFailure=yes -R 127.0.0.1:18088:127.0.0.1:8085 gaikwad-prakash@192.168.194.228
```

Check ownership/ports before starting a duplicate. The historical server interpreter is `/home/kiran/sim/pi05-official-20260922/.venv/bin/python`; additional dependency/environment setup is variant-specific, as in the archived commands below.

### Preservation

The prior AI90 guide is backed up beside this file as `HOW_TO_RUN_A_TRIAL.before_20261003_update.md`. Original evidence and environments are unchanged. Review the correction section before using any historical command below.

---

# Historical guide — retained for provenance, NOT current operating instructions

**The following text contains superseded claims, including overload solved, universal grip thresholds, blind retries and deterministic physical results. Use the corrected sections above instead.**

## Original: How to run a trial (SO-101 arm) — plain guide + exact commands

For a human or an agent picking this up. The TOP is the simple workflow; the lower
sections are the exact commands, per model, plus the gotchas that bit us.

---

## The workflow in 5 steps (what a "trial" is)
```text
1. START   run ONE command that tells the arm to do the task (pick the orange, put it on the plate).
2. RUNS    the arm moves. The command runs in the background (shows "running"); you wait.
           NOTE: you can't watch it live today — the program holds both cameras while it runs.
3. DONE    you get a "finished" notice.
4. CHECK   look at a front-camera PHOTO of where the orange + arm ended up, plus the saved
           numbers (did the gripper close? lift? release?). Decide: did it place the orange?
5. RESET   send the arm back to its rest pose (home). A *successful* run should return by
           itself; you home it manually after an unfinished/stopped run.
```

## The rig (two computers)
```text
AI90  kiran@192.168.194.220          the GPU box. Runs the policy "brain" (server). Big GPU.
Acer  gaikwad-prakash@192.168.194.228 the arm + cameras. Trial client runs here.
link  ZeroTier network between them (~345 ms).
power follower MUST be ~7.4V (STS3215 servos). At 5V it throws voltage faults. Physical supply.
```

---

## A) GR00T trial (our model) — the simple one
GR00T has a turnkey script. The brain usually already runs on AI90 (port 5555).
```text
# 1. (AI90) start the brain if it is down:
RECOV_CKPT=6000 python3 ~/srv_wrap_recov.py        # serves checkpoint-6000 on :5555

# 2. (Acer) one command per trial — homes the arm, then runs the policy:
~/home_and_trial.sh <N>        # <N> = any trial number, e.g. 801

# evidence lands in:  ~/so101_trials/trial_<N>/   (trace.jsonl, client.log, result.json, frames)
```

## B) pi05 trial (Codex's model) — three pieces
pi05 has no turnkey script; it is a custom launcher. Needs a server + a tunnel + the client.
```text
# 1. (AI90) start the pi05 brain. It is loopback-only + has a 15-MINUTE lifetime, so start it
#    right before the trial. Make a FRESH-output-dir copy each time (the script refuses to reuse
#    an existing output dir, and we must not delete old evidence):
D=/home/kiran/sim/pi05-fullft-orange50-20260922
sed 's/raw_physical_trial/raw_physical_trial_<FRESH>/g' "$D/fullft10k_trial_server.py" > "$D/server_<FRESH>.py"
env PYTHONPATH=/home/kiran/sim/pi05-official-20260922/orange50_30k_deployment_check_20260922/server_dependencies \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
    /home/kiran/sim/pi05-official-20260922/.venv/bin/python -u "$D/server_<FRESH>.py"   # waits ~60s, prints "ready"

# 2. (AI90) open a reverse tunnel so the Acer reaches the brain on its own loopback:
ssh -N -o ExitOnForwardFailure=yes -R 127.0.0.1:18088:127.0.0.1:8085 gaikwad-prakash@192.168.194.228

# 3. (Acer) run the client (fresh output dir again). It does a NO-ARM check first, then moves the arm:
cd ~/Documents/ChatGPT/Lerobot
sed 's/fullft10k_raw_trial_20260924/fullft10k_raw_trial_<FRESH>/' run_fullft10k_raw_trial.py > run_<FRESH>.py
./.venv-official-client-061/bin/python run_<FRESH>.py

# evidence lands in:  ~/Documents/ChatGPT/Lerobot/fullft10k_raw_trial_<FRESH>/live/
#   (observation_*.npz per step, events.jsonl, result.json)
```

---

## CHECK the result (step 4)
```text
- result.json      -> status, commands_sent, and why it stopped
- grip numbers     -> from the trace/observations: did gripper CLOSE (~<20), LIFT, then RELEASE (>50)?
                      close-early-then-release = a real grasp; closed-on-air (~13) or never-closed = miss
- front snapshot   -> where the orange + arm ended up; is the orange IN the plate?
- VERDICT: trust the WRIST camera / your eyes, not an auto-detector (it false-positives on wood grain).
```
Grab a front snapshot AFTER the run (camera is free then) with a warm-up read:
```text
(Acer) open /dev/v4l/by-id/usb-046d_C270_... with OpenCV, read ~45 frames (warm-up), save the last.
```

## STOP / HOME (step 5)
```text
stop   pkill -TERM the client  -> releases torque (arm goes limp/safe)
home   python3 ~/home_arm.py   (if the bus glitches with "no status packet", run
       ~/clear_overload.py then retry home — up to ~3x)
```

---

## GOTCHAS (things that WILL bite you)
```text
- BUS FLAKY: first access often fails "no status packet" -> run clear_overload.py to warm it, retry.
- pi05 SERVER 15-MIN LIFETIME: it self-expires. Start it right before the trial; relaunch per run.
- pi05 IS DETERMINISTIC (seed 0): same orange position => identical result. To learn anything new,
  MOVE the orange between runs.
- FRESH OUTPUT DIRS: both server and client refuse to overwrite an existing output dir (exist_ok=False).
  Use a new <FRESH> name each run. Do NOT delete previous evidence to reuse a name.
- CAMERA BUSY DURING A RUN: the client holds both cameras, so you cannot snapshot mid-run. Snapshot AFTER.
- SECURITY: the pi05 transport is gRPC+pickle on loopback -> keep it TUNNELED, never bind it to the network.
- GRIPPER OVERLOAD: lerobot's configure() resets the gripper to a cautious limit (Overload_Torque=25)
  on every connect, which trips "overload" (status 32) on a hard clamp. We PATCHED the pi05 client's
  lerobot (.venv-official-client-061/.../so_follower.py, gripper block -> 1000/500/80; backup .bak_20260927)
  so pi05 runs overload-free. Restore the .bak to revert. GR00T's separate venv is NOT patched.
- POWER reverts: the gripper protection + any servo-limit tweak revert to factory on a power cycle;
  the 7.4V supply is physical (check it if voltage faults return).
```

## Current status (2026-10-03)
Both hardware walls solved (power 7.4V, gripper overload). pi05 10k RUNS the full policy on the
arm but does not grasp yet — the motion is sequential/jerky (no RTC). Next step: add smooth motion
(RTC) to the pi05 client. See `pi05_first_arm_and_power_fix_20260927.md` for the full story.
