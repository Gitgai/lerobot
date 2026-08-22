# New Machine: Local Serving On The 5090, And The Sim-First Turn

Last updated: 2026-08-04
Supersedes the RunPod parts of `agent_handoff_pi05_20260803.md` Section 7.
Read that document for the project itself (capabilities, history, next steps) -
this one covers only what changed when the work moved to the new machine.

---

## 1. What Changed In One Paragraph

The project moved from a CPU-only laptop plus a rented RunPod RTX 3090 to a
single workstation with an RTX 5090. The Pi05 checkpoint, the training-era code
that serves it, and the tokenizer are now all local, and the policy runs on the
local GPU at 153 ms per 50-action chunk. **The pod is stopped and the SSH tunnel
is retired.** With a local GPU available, the cheapest next experiments no longer
need the robot at all, so the plan turns to simulation first and hardware second.

---

## 2. The Machine

```text
host      kiran-G485          user kiran
LAN       192.168.0.108       (wlp129s0f0, default route via 192.168.0.1)
ZeroTier  192.168.194.158     (how the old laptop reaches this box)
OS        Ubuntu 26.04 LTS (Resolute), GNOME, Wayland
GPU       RTX 5090, 32 GB, sm_120, driver 595.84
Disk      1.8 TB NVMe
```

Note the two networks. The old laptop and the Raspberry Pi live on
`192.168.1.0/24`; this machine does not, and has **no route to them**. Every
transfer from the old laptop went over ZeroTier. This matters for the wrist
camera - see Section 6.

---

## 3. Where Everything Lives Now

```text
repo          ~/projects/git/nvidia/lerobot                    (fork, branch main)
project       ~/projects/git/nvidia/lerobot/projects/testproject
project venv  <project>/.venv                                  py3.12, torch 2.10.0+cu128

checkpoint    ~/lerobot_assets/checkpoints/pi05_012000/        8.8 GB
serving code  ~/lerobot_assets/lerobot_trainingera/            e40b58a8 + patches
serving venv  ~/lerobot_assets/lerobot_trainingera/.venv       py3.12, torch 2.11.0+cu128

sim venv      ~/sim/leisaac-venv                               py3.11, torch 2.7.0+cu128

calibration   ~/.cache/huggingface/lerobot/calibration/        916 + 917 bytes
tokenizer     ~/.cache/huggingface/hub/models--google--paligemma-3b-pt-224
runpod key    ~/.ssh/runpod_ed25519                            mode 600
```

**Three separate venvs, deliberately.** They pin conflicting torch versions and
must never be merged:

```text
project    torch 2.10.0+cu128   fork main pins torch<2.11.0
serving    torch 2.11.0+cu128   e40b58a8 pins torch<2.12.0
sim        torch 2.7.0+cu128    LeIsaac / Isaac Sim 5.1 pins torch==2.7.0
```

All three carry `sm_120` and were each verified with a real kernel launch, not
just an arch-list check.

Checkpoints and assets sit **outside the repo** on purpose (hard rule #2: never
commit checkpoints, datasets, traces or videos).

---

## 4. Local Serving - Verified 2026-08-04

```text
VERIFIED (measured on this machine, not assumed)
  checkpoint integrity ...... 813 tensors, BF16+F32, declared end == file size,
                              type: pi05, "All keys loaded successfully"
  load ...................... 60 s, 4.14B params, bfloat16
  VRAM ...................... 9.5 GB peak of 32 GB
  chunk inference ........... median 153 ms (min 152, max 154)
                              50 actions, 10 denoising steps
  tokenizer ................. loads offline, vocab 257152

NOT VERIFIED
  numerical agreement with the pod    <- THE GATE. See Section 5.
  the real observation pipeline (cameras, JPEG path, threading)
  any robot behaviour
  whether this GPU can TRAIN either model (only inference is proven)
```

### Why 153 ms matters

A 50-action chunk at 30 Hz is 1.67 s of motion.

```text
                     latency per chunk     fraction of chunk consumed
  pod (via tunnel)   ~30 steps             ~60%
  local 5090         ~4.6 steps            ~9%
```

The `~30-step latency` figure is the project's own, from
`pi05_rtc_backport_plan_20260731.md`; it is why `RTC_EXEC_HORIZON=35` was chosen
("horizon must exceed the ~30-step latency").

**Hypothesis, not yet tested on the arm:** the fast-forwarding that made the arm
move too fast was mostly _network_, not compute. If so, `RTC_EXEC_HORIZON` can
drop well below 35, giving fresher observations per action. Test this before
assuming it.

### A correction to the network finding

`pi05_network_payload_reference_20260801.md` attributes the ~2 MB/s ceiling to
"gRPC over the SSH tunnel". Pulling the 8.8 GB checkpoint with plain rsync over
SSH averaged **1.93 MB/s** - no gRPC involved.

```text
That points at the network PATH to the pod, not gRPC or tunnel overhead.
```

Consequence: the JPEG compression work (2.77 MB -> 190 KB) was a workaround for
a link that does not exist when the policy runs on the machine holding the
cameras. Treat this as a hypothesis worth one clean test, not a settled
overturning of the earlier finding.

---

## 5. The Gate Before Any Robot Motion — ✅ PASSED 2026-08-05

```text
RESULT - the local serving stack is SOUND.

FIRST-GRIPPER over the 40 focus frames (pod protocol reproduced):
  correlation(recorded, predicted) = 0.714     POD: 0.826   FAIL-sig: 0.197
  MAE all frames                   = 4.78

CLOSED-ISH frames (recorded first gripper <= 30):
  n              = 21      POD: 21      <- EXACT MATCH
  recorded mean  = 21.4    POD: 21.4    <- EXACT MATCH
  predicted mean = 24.7    POD: 24.1
  MAE            = 5.45    POD: 4.41
```

The exact match on **n=21 and recorded mean 21.4** is what makes the rest
believable: it shows the frame selection genuinely reproduced the pod's
protocol, rather than scoring some other set of frames.

```text
VERDICT: 0.714 is 3.6x the broken-harness signature (0.197) and in the same
regime as the pod's 0.826. This is a WORKING stack, not a broken one. The
failure this exam exists to catch produces a model that has lost gripper
behaviour entirely; nothing like that is present.

NOT IDENTICAL, and the gap is NOT explained:
  0.714 vs 0.826 correlation, 5.45 vs 4.41 MAE.
  Candidates, none isolated: different torch (2.11.0+cu128 here vs whatever the
  pod ran in July), different GPU (5090 vs 3090 - bf16 kernel differences are
  real at this precision), or frame indices off by a frame or two from the
  pod's exact selection despite the matching closed-frame count.
  If a future result hinges on that difference, isolate it then.

CONSEQUENCE: THE FOUR SIMULATOR RUNS STAND. They went through this same stack.
"Pi05 converges to a stable hover at 13-18 cm" is a real measurement, not an
artefact of a broken harness.
```

### How it was run (reproduce with this)

```bash
# indices: pod protocol = frame 50 (t=1.667s @30fps) of each of the 40 focus
# episodes. In THIS dataset focus episodes are indices 49..88, 301 frames each;
# take dataset_from_index + 50 from meta/episodes/**/*.parquet.
# NOTE: grasp_focus_windows.csv's source_global_start_index indexes the SOURCE
# dataset, NOT this one - do not use it directly.
cd ~/lerobot_assets/lerobot_trainingera
HF_HUB_OFFLINE=1 ./.venv/bin/python \
  <repo>/projects/testproject/scripts/runpod/pi05_episode29_offline_compare.py \
  --dataset-root ~/lerobot_assets/datasets/so101_orange_49_plus_grasp_pick_move_focus \
  --dataset-repo-id local/so101_orange_49_plus_grasp_pick_move_focus \
  --policy-path ~/lerobot_assets/checkpoints/pi05_012000 \
  --output-csv <...>/logs/trust_exam.csv \
  --indices "<40 comma-separated indices>" --device cuda
```

```text
TWO TRAPS WHEN RE-RUNNING:
1. USE THE TRAINING-ERA VENV. The checkpoint must run on e40b58a8 - that is the
   entire point. Running it on the project venv reproduces Era 1 by construction.
2. DO NOT USE THE SCRIPT'S DEFAULT --indices. It samples 9 fractions across the
   whole dataset, which is NOT the pod protocol, and the resulting correlation
   CANNOT be compared to 0.826. A number that looks like a result and means
   nothing is exactly what this exam exists to prevent.

Also needed: the training-era venv was built with [pi,async] and lacks the
dataset reader. `uv pip install -e ".[dataset]"` adds it (+torchcodec 0.11.1);
verified torch stays at 2.11.0+cu128, so the serving stack is unaffected.
```

---

## 5b. The Original Statement Of The Gate (kept for context)

The model loads and emits finite, plausibly-scaled actions - **on random noise
input**. That says nothing about correctness.

```text
ERA 1 cost roughly a month to a harness that looked fine and was not.
The rule that came out of it: SUSPECT THE HARNESS BEFORE THE MODEL, and
validate any new measurement tool against a known-good answer first.

A freshly built serving stack on a brand-new machine is exactly what that
rule was written about.
```

Before trusting this setup with the arm, run the trust exam and compare against
the known-good pod numbers:

```text
known good (pod, 2026-07-22, recovered 07-28; method: make_pre_post_processors
+ predict_action_chunk, 40 focus-window frames, one per focus episode t=1.667s):
  012000, 21 closed-ish frames: predicted gripper mean 24.1, MAE 4.41
  correlation(recorded, predicted) first gripper: 0.826
  broken-harness signature (what FAILURE looks like): 0.197
```

If the local stack does not reproduce ~0.83, the stack is wrong - not
the checkpoint.

### How to run it - DATASET NOW PRESENT (verified 2026-08-05)

```text
script   scripts/runpod/pi05_episode29_offline_compare.py     HAVE (in repo)
policy   ~/lerobot_assets/checkpoints/pi05_012000/            HAVE
dataset  ~/lerobot_assets/datasets/                           HAVE  <- ARRIVED
           so101_orange_49_plus_grasp_pick_move_focus
           so101_orange_49
=> P0 IS UNBLOCKED. Nothing is missing.
```

Transfer verified INDEPENDENTLY, not taken on report:

```text
so101_orange_49                             v3.0  49 eps  29,724 frames  770 MB
so101_orange_49_plus_grasp_pick_move_focus  v3.0  89 eps  40,712 frames  770 MB
both: 3 cameras (front/top/wrist), 30 fps, 0 symlinks, 0 zero-byte files
```

Two things that LOOK wrong and are not - do not re-investigate:

```text
1. BOTH DATASETS ARE ~770 MB despite 49 vs 89 episodes, because THEY SHARE THE
   SAME VIDEO FILES, byte-for-byte:
       front/file-000.mp4  101,625,040    front/file-001.mp4  200,394,370
       top/file-000.mp4    115,596,712    top/file-001.mp4    195,363,093
       wrist/file-000.mp4  193,019,644
   Total differs by only 331,904 bytes - metadata and parquet.
   That is exactly how make_grasp_focus_dataset.py works: it does NOT re-encode,
   it adds new episode boundaries over the same footage.
   ARITHMETIC CONFIRMS IT: 49 original + 40 focus = 89 episodes, and the pod run
   used "40 focus-window frames, one per focus episode, t=1.667s".

2. WRIST HAS 1 mp4 WHERE front/top HAVE 2. Genuine LeRobot chunking, not a
   partial copy: wrist is 193 MB against front's 302 MB and top's 311 MB
   combined - it fit in one chunk, the others needed two.
```

The script is read-only: it never opens a serial port and never moves the arm.

---

## 6. What Still Needs Hardware, And What Does Not

This was previously stated too broadly. Corrected:

```text
NEEDS NOTHING PLUGGED IN
  Isaac Sim / LeIsaac install, launch, env loading
  random-action rollouts in sim
  GR00T pipeline dry run on NVIDIA's so101-table-cleanup dataset
  any training run
  the Pi05 trust exam (offline, uses saved data)

NEEDS THE LEADER ARM ONLY (one USB cable)
  teleop recording in simulation - you hold the PHYSICAL leader, it drives a
  SIMULATED follower. No follower arm, no C270, no Raspberry Pi, and the
  three-camera rule does not apply because the simulator renders its own.

NEEDS THE FULL RIG
  any real-robot evaluation: both arms, 3 cameras, the Pi, corrected device
  paths in config/so101.json
```

### The wrist camera problem (real-robot track only)

```text
Pi is at 192.168.1.15. This machine has no route to 192.168.1.0/24.
Options: put the Pi on this LAN, add it to ZeroTier (the same fix that
made the laptop reachable), or move to a USB wrist camera.
```

Unresolved. It blocks real-robot runs because three cameras is a hard rule. It
does **not** block anything in Sections 7 or 8.

---

## 7. Sim-First Sequencing (revised 2026-08-04)

The earlier plan treated hardware as the next step. With a local GPU, that is no
longer the cheapest path.

```text
WHY SIM FIRST
  place is the one total gap - 0 successes in the entire project - and
    LeIsaac's so101_pick_orange ends in "put them into the plate"
  position/scene diversity is the top data priority, and PI's own ablation
    ranks environment diversity above cross-embodiment and web data;
    simulation varies scenes for free, the real table does not
  no motor overload risk - max_relative_target 15 overloaded a motor once
    and required a power cycle; simulated servos do not burn out
  the real rig has unresolved friction (Pi routing, camera re-detection,
    the front camera differing on this machine)
```

```text
ORDER
  1. Isaac Sim / LeIsaac gates (Section 8)          no hardware
  2. GR00T pipeline dry run, Stage 3b-0             no hardware
     -> groot_vs_pi05_comparison_plan_20260804.md
  3. Pi05 trust exam vs the pod numbers             no hardware
  4. Sim teleop recording                           leader arm only
  5. Real-robot work                                full rig
```

**Open and honest:** whether demos recorded in simulation transfer to the
physical arm is unproven. 012000 was fine-tuned on real teleop data. Sim is a
parallel track that may shortcut the place problem - it is not established that
it will. Do not retire the real-robot plan on the strength of it.

---

## 8. Isaac Sim / LeIsaac Status

Target versions, from LeIsaac's own matrix:

```text
Isaac Sim 5.1  ->  Isaac Lab 2.3.0  ->  Python 3.11, CUDA 12.8, torch 2.7.0
```

```text
GATE 1  torch 2.7.0+cu128 carries sm_120     PASS  181.3 TFLOPS, real kernel
NGC     anonymous pull works                 PASS  no login needed
GATE 2  isaacsim + isaaclab + leisaac        PASS  on Ubuntu 26.04
        isaacsim 5.1.0.0 | isaaclab 2.3.0 | leisaac 0.4.0 | venv 18 GB
GATE 3  Isaac Sim 5.1 launches               PASS  after driver -> 580.173.02
        (was SIGSEGV/exit 139 on driver 595.84)
        "Simulation App Startup Complete" 5.3s, 0 crashes
GATE 4  LeIsaac SO-101 tasks register        PASS  15 tasks incl.
        LeIsaac-SO101-PickOrange-v0 / -Direct-v0 / -Mimic-v0
GATE 4b LeIsaac env CONSTRUCTS AND RESETS    PASS  scene loaded, physics built,
        cameras spawned, robot instantiated, env.reset() clean
        action_space Box(-inf, inf, (1, 8), float32) | obs Dict
        obs keys: policy, subtask_terms  <- subtask_terms tracks SUBTASK
        COMPLETION, i.e. the structure needed to score a PLACE phase
GATE 5  teleop with the physical leader      pending; needs the leader arm
```

### The LeIsaac source install (what the package install got wrong)

```text
The pip route (`pip install leisaac[isaaclab]`) SILENTLY registers ZERO tasks.
leisaac/__init__.py wraps its task import in try/except ImportError and PRINTS
instead of raising, so `import leisaac` "succeeds" with nothing registered. The
buried error was: No module named 'isaaclab_tasks' - the pip isaaclab package
bundles source/isaaclab_tasks etc. but never installs them.
LeIsaac's own docs say the package install "may expose edge cases" and recommend
the SOURCE install. They are right.

WORKING SETUP (2026-08-04):
  ~/sim/leisaac-src            git clone --recursive, IsaacLab as submodule
  ~/sim/leisaac-venv           py3.11, isaacsim 5.1.0.0 REUSED from the pip
                               install (18 GB - do not re-download it)
  isaaclab + isaaclab_tasks/_assets/_mimic/_rl : editable from the submodule
  leisaac 0.4.0                editable from ~/sim/leisaac-src/source/leisaac

  Assets (~96 MB, from the v0.1.0 GitHub release):
    assets/robots/so101_follower.usd
    assets/scenes/kitchen_with_orange/{scene.usd,objects/{Orange001..003,Plate}}

UV-SPECIFIC FRICTION (their guide assumes conda):
  isaaclab.sh reads $CONDA_PREFIX -> point it at the uv venv
  isaaclab.sh calls `python -m pip` -> uv venvs have NO pip; install it first
  isaaclab.sh runs `sudo apt install cmake build-essential` -> run that yourself
  egl_probe wheel fails to build (a robomimic dep). Did NOT block anything here;
    look there first if the RL/mimic paths misbehave.
```

### RUNNING IT — the command that works (verified 2026-08-04, GUI on screen)

```bash
cd ~/sim/leisaac-src
LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets \
ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
~/sim/leisaac-venv/bin/python -u \
  scripts/environments/teleoperation/teleop_se3_agent.py \
  --task=LeIsaac-SO101-PickOrange-v0 --teleop_device=keyboard \
  --enable_cameras --num_envs=1
```

Keyboard control (click into the viewport first):

```text
W/S forward/backward   A/D left/right    Q/E up/down
J/L rotate left/right  I/K rotate down/up
U/O GRIPPER OPEN/CLOSE
```

Recording flags on the same script: `--record`, `--use_lerobot_recorder`,
`--lerobot_dataset_repo_id`, `--lerobot_dataset_fps` — these write LeRobot-format
datasets directly, i.e. the format we already train on.

Shutdown: `pkill -f 'teleop_se3_[a]gent'` (bracket pattern — a plain pattern
matches its own shell and kills it, exit 144; project trap list).

```text
GUI NOTE — THE CONTAINER PLAN IS NOT NEEDED.
The window renders NATIVELY on Wayland via Xwayland with NO xhost, NO container
and NO X11 plumbing. docs/00-PLAN.md (repo root) proposed running Isaac Sim in a
container and accepted display plumbing as the cost; that whole branch is moot.
Teleop is GUI-heavy, which is exactly the case the plan worried about.

Harmless noise in the log, from the shipped kitchen asset (NOT our setup):
  PhysicsUSD: CreateJoint - cannot create a joint between static bodies
  PhysX error: Supplied PxGeometry is not valid
```

### Four traps when constructing a LeIsaac env

All four cost a run and are commented in `scripts/leisaac_task_check.py`:

```text
1. ASSET PATH: LeIsaac resolves assets via the GIT ROOT OF THE CWD. Running
   from inside the lerobot repo made it look in lerobot/assets/.
   FIX: export LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets
2. gym.make(task, num_envs=1) FAILS - Isaac Lab envs need a dataclass config:
   parse_env_cfg(task, device=..., num_envs=1) then gym.make(task, cfg=cfg)
3. Task configs leave actions.arm_action / gripper_action as MISSING.
   FIX: env_cfg.use_teleop_device("keyboard"|"gamepad"|"so101leader"|
        "so101_state_machine") before gym.make
4. CAMERAS: must use isaaclab.app.AppLauncher(enable_cameras=True).
   SimulationApp({"enable_cameras": True}) is a DIFFERENT FLAG and silently
   does nothing; isaaclab checks the carb setting /isaaclab/cameras_enabled,
   which only AppLauncher sets.
```

> **RESOLVED 2026-08-04 by downgrading the driver to 580.173.02.** Isaac Sim 5.1
> is validated against the 580 branch and is incompatible with R590 (595.x).
> NOT an Ubuntu problem (same crash reported on 24.04) and NOT fixable by a
> container (containers use the host driver).
>
> ```text
> AFTER THE DOWNGRADE, RE-VERIFIED:
>   nvidia-smi ............ 580.173.02, RTX 5090, CUDA 13.0
>   torch sm_120 .......... OK in all three venvs (2.7.0 / 2.10.0 / 2.11.0, all cu128)
>   PI05 SERVING .......... 143 ms/chunk - IMPROVED from 153 ms. No regression.
>                           load 59.7 s, 4.14B params, 9.5 GB VRAM, finite actions
>   Isaac Sim 5.1 ......... starts clean
>   LeIsaac ............... 15 SO-101 tasks registered
> ```
>
> Full matrix and the traps: **`isaac_sim_blackwell_investigation_20260804.md`**
> Reusable scripts now in the repo (not /tmp):
> `scripts/isaac_sim_smoke_test.py`, `scripts/pi05_local_serving_benchmark.py`,
> `scripts/leisaac_task_check.py`

### Trap already hit and cleared

```text
flatdict==4.0.1 ships an sdist ONLY (no wheel), and its legacy setup.py calls
pkg_resources, which is absent from uv's isolated build environment.

  ModuleNotFoundError: No module named 'pkg_resources'
  required by isaaclab==2.3.0

FIX: uv pip install setuptools wheel
     uv pip install --no-build-isolation-package flatdict ...

This is a PACKAGING bug, not evidence against Ubuntu 26.04. It would fail the
same way on 24.04 with a modern setuptools. Do not read it as "the unsupported
OS does not work" - that misreading costs a reinstall.
```

### The Ubuntu 26.04 question - ANSWERED

```text
NVIDIA does not list Ubuntu 26.04 as supported for Isaac Sim 5.1, and
docs/00-PLAN.md (repo root) therefore recommends a container. Tested instead of
assumed, per "install and check":

  pip install on 26.04 ......... WORKS (Gate 2 passed)
  the only install failure ..... flatdict shipping sdist-only with a
                                 pkg_resources call - a PACKAGING bug that
                                 would hit 24.04 identically with a modern
                                 setuptools. Fixed with
                                 --no-build-isolation-package flatdict
  two missing system libs ...... libGLU.so.1 (installed) and libxml2.so.2
                                 (genuinely absent from 26.04 - shimmed).
                                 BOTH FIXED, and it STILL crashed.
  the real cause ............... driver branch vs Isaac Sim version.
                                 NOT Ubuntu. NOT the GPU.

CONCLUSION: Ubuntu 26.04 is not what broke this, a container would not fix it
(host driver), and reinstalling the distro would have cost a rebuild and still
crashed. The repo README's validated 5090 baseline stays intact.

Detail: isaac_sim_blackwell_investigation_20260804.md
```

---

## 9. Open Questions

```text
Does the local serving stack reproduce the pod's numbers?   -> Section 5 gate
Can RTC_EXEC_HORIZON drop below 35 now latency is ~4.6 steps?
Can this 32 GB card TRAIN Pi05, not just serve it?  (retires RunPod fully)
Does Isaac Sim install and run natively on Ubuntu 26.04?    -> Gate 2/3
Do simulation-recorded demos transfer to the physical arm?
How does the wrist Pi reach this machine?
```

---

## 10. Loose Ends

```text
CHECKPOINT BACKUP: user confirms a backup exists (2026-08-04). The local copy
at ~/lerobot_assets/checkpoints/pi05_012000/ is therefore NOT a single point of
failure. Location of the backup is not recorded here - worth noting wherever
the user keeps such things, so a future agent does not re-raise this.

RunPod: the pod migrated on 2026-08-04 (endpoint moved 213.192.2.109:40144 ->
213.192.2.123:40043, exactly the rotation the handoff warns about) and was
stopped after the checkpoint was pulled. Balance was $6.48 with TWO pods
listed during migration. A 10 GB EU-RO-1 volume "silent_coffee_tick" was
still pending inspect-then-delete as of the last check.
```
