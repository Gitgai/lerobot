# Isaac Sim On The 5090: Why It Crashed, And What Actually Fixes It

Last updated: 2026-08-04
Status: INVESTIGATION COMPLETE, fix not yet applied.
Bottom line: **do NOT downgrade the NVIDIA driver, and do NOT reinstall Ubuntu.**
The installed Isaac Sim is simply the wrong version for this machine.

---

## 0. THE COMPATIBILITY MATRIX — READ THIS, DON'T RE-INVESTIGATE

Everything below was established the hard way on 2026-08-04. If you are deciding
what to install, this table is the answer.

> ## ✅ RESOLVED 2026-08-04: driver downgraded to 580.173.02, EVERYTHING WORKS.
> Isaac Sim 5.1 starts clean (0 crashes, was SIGSEGV) and **all 15 LeIsaac
> SO-101 tasks register, including `LeIsaac-SO101-PickOrange-v0`.**
> Pi05 serving did NOT regress - it improved to 143 ms/chunk (was 153 ms).
> The sections below are the investigation that got here; keep them for the
> version matrix and the traps, not as a description of current state.

```text
THIS MACHINE: RTX 5090 (Blackwell, sm_120) | Ubuntu 26.04
              driver 580.173.02  (was 595.84 R590 - downgraded 2026-08-04)
              Docker 29.7.1 + nvidia-container-toolkit 1.19.1
```

| Isaac Sim | Isaac Lab | LeIsaac | Python | torch | Driver needed | Verified on this machine |
|---|---|---|---|---|---|---|
| **5.1.0** | 2.3.0 | 0.4.0 ✅ | 3.11 | 2.7.0+cu128 | **580.x** | ✅ **WORKS on 580.173.02** (❌ segfaults on 595.84) |
| **6.0.1** | 3.0.0b2 (beta) | ❌ **none** | 3.12 | — | **595.58.03** | ✅ engine runs on 595.84, but nothing above it supports SO-101 |

```text
THE ANSWER, IF YOU READ NOTHING ELSE:
  Use driver 580.x with Isaac Sim 5.1 + Isaac Lab 2.3.0 + LeIsaac 0.4.0.
  apt's 580.173.02 works - the exact validated 580.65.06 was NOT required.
  Do NOT go to a 595/R590 driver while LeIsaac is needed.
```

```text
CORRECTION (2026-08-04): an earlier version of this doc claimed "no Isaac Lab
exists for Isaac Sim 6.0". WRONG - isaaclab 3.0.0b2.post1 is installable and
its release notes state support for Isaac Sim 6.0.1. That claim was made from
container tags (no isaac-lab:2.4.0) and LeIsaac's docs, neither of which covers
the 3.0 beta line.
It does not change the conclusion: LEISAAC is the binding constraint, not
Isaac Lab. See the LeIsaac check below.
```

```text
THE CORE TENSION
  LeIsaac (our SO-101 tasks) exists ONLY for Isaac Sim 5.1.
  Isaac Sim 5.1 requires a 580-branch driver.
  We run a 595 (R590) driver, which only Isaac Sim 6.0 supports.
  Isaac Lab 3.0.0b2 DOES target Isaac Sim 6.0 - but LeIsaac pins Isaac Lab
  2.3.0, so the chain breaks at LEISAAC regardless of what runs above it.
  => To get LeIsaac locally, the DRIVER must move to 580. Nothing else works.

CHECKED DIRECTLY 2026-08-04 (git clone, not docs, not assumption):
  LeIsaac latest commit  24d3bcd  2026-04-15   (~4 months stale)
  LeIsaac latest tag     v0.4.0                (what we have installed)
  pin on main NOW        isaaclab[isaacsim,all]==2.3.0   UNCHANGED
  => NO 6.0-compatible LeIsaac release exists.
  Timing explains it: LeIsaac's last commit predates Isaac Sim 6.0 (~June 2026)
  entirely. Re-check this before assuming it is still true - a single upstream
  release would collapse this whole problem.

VERIFIED 2026-08-04 (container, current driver, no changes to this machine):
  nvcr.io/nvidia/isaac-sim:6.0.1  ->  SIM APP STARTED 23.0s, engine loop ran,
  clean shutdown, ZERO errors, ZERO crashes.
  Warp reported: "cuda:0": "NVIDIA GeForce RTX 5090" (31 GiB, sm_120, mempool enabled)

  => THE MACHINE, THE GPU AND BLACKWELL ARE ALL FINE.
     The 5.1 failure was PURELY an Isaac Sim version vs driver branch mismatch.
```

### What is NOT the problem (proven, stop suspecting these)

```text
Ubuntu 26.04 ....... NOT the cause. Same 5.1 crash reported on 24.04 with
                     RTX 4090 and RTX 5080. A reinstall would be wasted.
Blackwell/sm_120 ... NOT broken. Isaac Sim 6.0 runs on it cleanly.
The GPU ............ fine. Detected correctly even by the version that crashed.
CUDA / PyTorch ..... fine. sm_120 verified on torch 2.7.0, 2.10.0, 2.11.0, 2.13.0.
Missing libs ....... fixed and NOT the cause (see Section 3). Both were cleared
                     and 5.1 still segfaulted.
```

### Container vs native

```text
CONTAINER SOLVES: Python version mismatches (6.0 needs 3.12, 5.1 needs 3.11),
  dependency resolution across pypi.nvidia.com + pypi.org, and missing system
  libs (libxml2.so.2, libGLU.so.1 come bundled).
  Three native pip attempts failed on exactly these; the container worked first try.

CONTAINER DOES NOT SOLVE: driver incompatibility. Containers use the HOST
  driver via nvidia-container-toolkit. An isaac-sim:5.1.0 container would
  segfault on 595.84 exactly as the native install does.

Available tags (anonymous pull, NO NGC login needed):
  nvcr.io/nvidia/isaac-sim:6.0.1   32.3 GB   VERIFIED WORKING HERE
  nvcr.io/nvidia/isaac-sim:5.1.0
  nvcr.io/nvidia/isaac-lab:2.3.2 / 2.3.0     (no 2.4.0 exists - ecosystem is
                                              still on the 5.1 generation)
```

### About Brev (asked 2026-08-04)

```text
Brev is NVIDIA's CLOUD GPU platform - rented instances, billed hourly. It is
NOT installable locally. A "launchable" is a pre-configured environment running
on THEIR hardware.

Our earlier Brev work used an NVIDIA L4 (Ada, sm_89) - NOT Blackwell - which is
likely part of why it worked: none of the Blackwell-specific issues applied.

DECISION: use the local 5090. It outclasses an L4, we already own it, and the
only advantage Brev had was being pre-configured - which this section removes.
```

---

## 1. One-Paragraph Answer

Isaac Sim 5.1 segfaults on startup on this machine. It is not Ubuntu 26.04, not
the missing system libraries we fixed along the way, and not a lack of Blackwell
support in CUDA or PyTorch. **Isaac Sim 5.1 is validated against NVIDIA driver
580.65.06 and has a known incompatibility with the R590 driver branch (595.x),
which is what this machine runs.** Isaac Sim 6.0 - the current release - is
validated against driver **595.58.03**, the same branch we already have, and
lists Blackwell GPUs as supported. The fix is to move Isaac Sim forward, not to
move the driver backward.

---

## 2. What Was Verified On This Machine

```text
GATE 1  torch 2.7.0+cu128 exposes sm_120           PASS  181.3 TFLOPS, real kernel
        (mattered most: had it failed, no OS or driver change could help)
NGC     anonymous pull of isaac-lab / isaac-sim    PASS  no login required
GATE 2  pip install isaacsim+isaaclab+leisaac      PASS  on UBUNTU 26.04
          isaacsim 5.1.0.0 | isaaclab 2.3.0 | leisaac 0.4.0 | numpy 1.26.0
          venv 18 GB
GATE 3  Isaac Sim starts                           FAIL  SIGSEGV, exit 139
GATE 4  so101_pick_orange loads                    blocked by Gate 3
GATE 5  teleop with physical leader                blocked; needs leader arm
```

Isaac Sim itself saw the GPU correctly before dying:

```text
| Driver Version: 595.84        | Graphics API: Vulkan
| 0 | NVIDIA GeForce RTX 5090   | Yes: 0 | | 32607 MB | 10de |
CUDA Version : 13.2
```

**The GPU was never the problem.**

---

## 3. The Two Red Herrings (fixed, and worth recording)

Both were real problems that had to be cleared before the true cause was
visible. Neither was the cause.

```text
libGLU.so.1 MISSING
  broke libneuray.so (iray) and then "Failed to load MDL-SDK"
  FIX: sudo apt install -y libglu1-mesa          <- APPLIED, works
  after this, omni.mdl-56.0.3 starts cleanly

libxml2.so.2 MISSING - and this one IS an Ubuntu 26.04 difference
  26.04 dropped the `libxml2` package; it ships `libxml2-16` -> libxml2.so.16.
  Isaac Sim 5.1 is built against the old .so.2 soname. No compat package exists.
  Breaks the URDF / MJCF / asset-converter extensions only.
  WORKAROUND (tested, contained, no sudo):
    fetch libxml2_2.9.14+dfsg-1.3ubuntu3_amd64.deb from the 24.04 archive
    dpkg-deb -x it, then run with LD_LIBRARY_PATH=<extracted>/usr/lib/x86_64-linux-gnu
    -> libxml2 errors drop to ZERO
```

**With BOTH fixed, it still segfaults.** That is the finding that redirected the
whole investigation.

---

## 4. Proving It Was Not Our Test Code

The first crash landed right after `app ready`, which is exactly where the test
script began building a scene. So the test was reduced to the minimum:

```text
SimulationApp({"headless": True}) -> app.update() x10 -> app.close()
no World, no ground plane, no asset fetch
```

```text
RESULT: Segmentation fault (core dumped), exit 139. Same crash frame:
        librtx.scenedb.plugin.so
```

The Kit engine cannot start. Nothing to do with our code, our scene, or Isaac Lab.

---

## 5. The Actual Cause

Known, documented, and matching our crash frame exactly.

```text
Isaac Sim 5.1.0 validated Linux driver ....... 580.65.06
This machine ................................. 595.84  (R590 branch)

The R590 branch has known incompatibilities with the Omniverse RTX renderer,
reported across RTX 4070, 4090, 5070 Ti, 5080 and 5090, on BOTH Windows and
Linux, all crashing in librtx.scenedb.plugin.so during renderer init.
```

Two conclusions that save real work:

```text
UBUNTU IS NOT THE CAUSE. The same crash is reported on Ubuntu 24.04 with an
  RTX 4090 and with an RTX 5080. A distro reinstall would NOT have fixed it.
  -> the "install and check" instinct was correct. Accepting the "26.04 is
     unsupported" label at face value would have cost a reinstall AND still
     crashed.

THE CONTAINER WOULD NOT FIX IT EITHER. Containers use the HOST's NVIDIA driver
  via nvidia-container-toolkit. Same driver, same Isaac Sim, same crash.
  docs/00-PLAN.md (repo root) recommends a container for Isaac Sim. That
  reasoning is sound for USERLAND library mismatches - which is what libxml2
  is - but it cannot address a driver/renderer incompatibility.
```

---

## 6. The Fix: Move Isaac Sim Forward, Not The Driver Back

```text
                    validated Linux driver     Blackwell in supported tiers
Isaac Sim 5.1       580.65.06                  no
Isaac Sim 6.0       595.58.03  <- OUR BRANCH   yes: RTX 5080 "good",
                                                RTX PRO 6000 Blackwell "ideal"

This machine        595.84 - same R590 branch, later point release than 6.0's
                    validated 595.58.03
```

There is no Isaac Sim 5.2. The line went 5.0 (Aug 2025) -> 5.1 (Oct 2025) ->
6.0 (6.0.1 around June 2026). **We installed the previous generation, validated
against a driver branch two releases behind ours.**

### The driver downgrade: rejected, then REINSTATED on evidence

This position changed twice. Both changes were driven by premises moving, and
the reasoning is recorded so it is not re-litigated.

```text
REJECTED (earlier 2026-08-04), because:
  1. Ubuntu 26.04 offers 580.173.02, NOT the validated 580.65.06, and later
     580.x builds (580.95.05, 580.126.16) are reported failing on Blackwell.
  2. It would disturb a VERIFIED-WORKING stack: the repo README's 5090 baseline
     and the Pi05 local-serving result (153 ms/chunk) were measured on 595.84.
  3. Brev was available, so sim did not require local.
  4. "Maybe Blackwell just does not work with Isaac Sim" was live and unresolved.

REINSTATED (later 2026-08-04), because those premises fell:
  3'. The user DECLINED Brev and requires a working LOCAL setup. Brev is a
      CLOUD service (hourly billing, not installable locally) and its instances
      were L4-class - weaker than the 5090 we already own.
  4'. RESOLVED BY EVIDENCE: Isaac Sim 6.0 ran cleanly in a container on THIS
      machine, on the CURRENT driver - 0 errors, 0 crashes, sm_120 active.
      Blackwell is fine. A validated Sim<->driver pairing demonstrably works
      on this hardware.
  => Downgrading makes 5.1+580 a validated pairing too - the SAME relationship
     that just succeeded. It is now a founded bet, not a guess.

REMAINING UNCERTAINTY (narrow, and honestly stated):
  apt offers 580.173.02, not the validated 580.65.06. Try apt first - one
  command, one reboot, one command to revert. If it fails, NVIDIA's .run
  installer for the exact 580.65.06 is the next step.
  Reason (1) above still stands as a caveat; only reasons (3) and (4) fell.
```

---

## 7. The Version Deadlock (CONFIRMED 2026-08-04)

Checked against the INSTALLED package metadata, not the website:

```text
leisaac 0.4.0  requires  isaaclab[all,isaacsim]==2.3.0
                                              ^^^^^^^ EXACT PIN, not a floor
Isaac Lab 2.3.0 pairs with Isaac Sim 5.1.
```

So LeIsaac 0.4.0 **cannot** use Isaac Sim 6.0 without someone bumping that pin.
The local sim track is deadlocked:

```text
Isaac Sim 5.1  LeIsaac supports it   -> BUT THE ENGINE WILL NOT START on our
                                        driver branch (Section 5)
Isaac Sim 6.0  runs on our driver    -> BUT LeIsaac PINS IT OUT
```

**BREV IS OFF THE TABLE (user decision, 2026-08-04).** Sim was confirmed working
there, but the user does not want to use it. That removes the easy answer and
makes solving this LOCALLY the only path to simulation.

### Path B was tested and is CLOSED (2026-08-04)

"Isaac Sim 6.0 works on our driver - can we just run LeIsaac on it?" was worth
asking and was tested rather than assumed. Result: no.

```text
WHAT WORKED
  isaac-sim:6.0.1 container       ran clean on the current driver (Section 0)
  import isaaclab (2.3.0)         OK - it is PURE PYTHON (Root-Is-Purelib: true,
                                  zero .so files), so the cp311 wheel tag is
                                  cosmetic; only pip's tag check blocks 3.12.
  import isaaclab.sim             OK after installing flatdict + prettytable

WHAT BROKE - a genuine API restructure
  isaaclab.scene / .envs / .assets / .sensors
    -> ModuleNotFoundError: No module named 'omni.physics.tensors.impl'
  In Isaac Sim 6.0 that module is GONE: omni/physics/tensors/ was flattened to
  api.py + frontend_*.py + bindings, with NO impl/ submodule.
  6.0 also ships isaacsim.physics.newton - NVIDIA's new Newton physics engine.
  6.0 is a physics-architecture rewrite; this is not shimmable.

AND THE SIMPLER, DECISIVE REASON
  Even with Isaac Lab 3.0.0b2 (which DOES target 6.0), LeIsaac pins
  isaaclab==2.3.0. The chain breaks at LEISAAC no matter what runs above it.

Do not re-run this experiment. Re-check only whether LEISAAC has released
6.0/Isaac Lab 3.0 support - that is the single thing that would change it.
```

Ways out, ranked by what is actually actionable:

```text
1. PROBE ISAAC SIM 6.0 LOCALLY.  <- DO THIS FIRST, see below.
2. Fork LeIsaac and override the isaaclab==2.3.0 pin, or port its SO-101 task
   definitions onto a newer Isaac Lab. Only sensible AFTER (1) succeeds.
   Untested; Isaac Lab 2.3.0 on Isaac Sim 6.0 may break differently.
3. Wait for a LeIsaac release bumping to Isaac Lab 2.4+/Isaac Sim 6.0.
   Not in our control; repo is active (705 stars, 123 forks, 13 issues).
4. Downgrade the driver.  <- STILL REJECTED, see Section 6. Ubuntu offers
   580.173.02, NOT the validated 580.65.06, and later 580.x builds are
   themselves reported failing on Blackwell. It would disturb the verified
   5090 baseline and the working Pi05 stack on a poor bet.
```

### Why the 6.0 probe is now the critical path for sim

We currently **cannot distinguish two very different situations**:

```text
  "this MACHINE cannot run Isaac Sim"        vs
  "ISAAC SIM 5.1 cannot run on this driver"
```

Every failure so far has been version-specific. Isaac Sim 6.0 is validated
against driver 595.58.03 - this machine runs 595.84, same R590 branch - and
lists Blackwell in its supported tiers. So:

```text
6.0 RUNS    -> the machine is fine. The problem shrinks to a PACKAGING one
               (getting SO-101 tasks onto 6.0), which is attackable by us.
6.0 CRASHES -> the machine genuinely cannot run Isaac Sim on this driver, and
               the driver becomes the only remaining lever. That would be the
               evidence needed to reconsider option 4.
```

Cost: separate venv, ~18 GB, no sudo, touches nothing that works.

**Honest odds:** even if 6.0 starts, LeIsaac on it is untested and may break
differently. This unblocks the POSSIBILITY of local sim, not local sim itself.

### TiledCamera: a workaround exists, and it fits our case

```text
ISSUE: TiledCamera HANGS (not crashes) on RTX 5090 - 100% CPU, no output for
       10+ minutes. Still OPEN. Isaac Lab 0.53.1 / Isaac Sim 5.1.0 / Warp 1.11.1.
ROOT:  Isaac Sim's omni.replicator tiled-rendering path, NOT Warp and NOT Isaac
       Lab. Warp kernels and sm_120 binaries work correctly in isolation.

WORKAROUND (from the issue thread): use standard `Camera` sensors instead of
  `TiledCamera`. Identical RGB output for SINGLE-ENVIRONMENT scenarios with
  comparable performance; just extract RGB from the RGBA data.

WHY THIS BARELY AFFECTS US: TiledCamera exists to render THOUSANDS of parallel
  environments for RL. We need ONE environment - one arm, three cameras, teleop
  recording. We are not in the use case that needs it.

ALSO NOTE: the reporter ran Isaac Sim 5.1 with driver 590.48.01 - the SAME
  R590-branch mismatch diagnosed in Section 5. This hang may be the same root
  cause wearing a different hat, and may not exist on 6.0 at all. Unproven.
```

Downgrade this from "blocks Gate 4" to "known, with a fitting workaround".

### LeIsaac capabilities worth knowing before planning data work

From LeIsaac's docs (lightwheelai.github.io/leisaac - sections: Introduction,
Getting Started, Tutorials, Extra Features, Troubleshooting, Cloud Simulation):

```text
1. AUTOMATED DATA COLLECTION VIA STATE-MACHINE POLICIES.
   Scripted policies can generate demonstrations WITHOUT teleoperation.
   => PLACE demonstrations could be generated with NO leader arm, NO robot
      time, NO teleop labour. Place is our ONE total gap (0 successes in the
      entire project). This is a data path for it that needs no hardware.
      Potentially the single most valuable thing LeIsaac offers us.

2. DOCUMENTED GR00T N1.5 PATH - "policy training and deployment on physical
   hardware using GR00T N1.5". The comparison in
   groot_vs_pi05_comparison_plan_20260804.md is SUPPORTED, not something we
   would have to build.

3. HDF5 -> LeRobot dataset conversion ships with it, so sim output lands in the
   format we already train on.
```

### Bonus finding: LeIsaac already integrates both policy families

```text
leisaac 0.4.0 optional extras:
  extra == "gr00t"          pyzmq, pydantic, msgpack
  extra == "openpi"         dm-tree, msgpack, numpy<2, pillow, websockets
  extra == "lerobot"        lerobot==0.4.2
  extra == "lerobot-async"  grpcio, protobuf
```

`openpi` is Physical Intelligence's pi0/pi05 stack. **LeIsaac ships integration
points for evaluating BOTH pi05 and GR00T policies in simulation** - which is
exactly the sim-testing plan in `community_data_strategy_20260804.md` Section 4a.
That harness does not need writing; it needs a working simulator.

---

## 8. Next Actions

```text
STEP 1  DONE 2026-08-04: Isaac Sim 6.0 container ran CLEANLY on this machine
        (Section 0). Machine capability CONFIRMED. Blackwell is not the issue.

STEP 2  DOWNGRADE THE DRIVER. This is now the whole remaining task.
          sudo apt install -y nvidia-driver-580-open \
                              linux-modules-nvidia-580-open-7.0.0-28-generic
          # then REBOOT
        INCLUDE THE linux-modules PACKAGE. Without it apt pulls nvidia-dkms-580
        plus gcc-15 and COMPILES the module against kernel 7.0.0 at install
        time - slower and able to fail. A PREBUILT module for this exact kernel
        exists; the current 595 install uses the prebuilt equivalent.
        Verified by `apt-get install -s`: 16 packages removed (the whole 595
        stack incl. its kernel modules), 48 installed.
        ROLLBACK NEEDS NO NETWORK: 17 cached 595 .debs are already in
        /var/cache/apt/archives.
        Do NOT run apt upgrade at the same time (kernel 7.0.0-29 is pending -
        that would be two variables; also "100 not upgraded" is expected).
        Rollback if the display does not return: Ctrl+Alt+F3 to a TTY, then
          sudo apt install -y nvidia-driver-595-open && sudo reboot

STEP 3  VERIFY IN THIS ORDER so a failure points at one thing:
          a. nvidia-smi reads 580.x, 5090 detected
          b. torch sm_120 kernel launch in ALL THREE venvs
             (cu128 is comfortable on 580; torch 2.13.0+cu130 needs >= 580.65,
              which 580.173.02 satisfies but only just)
          c. PI05 STILL LOADS AND SERVES - re-measure the 153 ms/chunk result.
             THIS IS THE ONE THAT MATTERS; it is the working track.
          d. Isaac Sim 5.1 headless (the native ~/sim/leisaac-venv install)
          e. LeIsaac so101_pick_orange loads

STEP 4  IF 5.1 STILL CRASHES ON 580.173.02: get the exact validated 580.65.06
        from NVIDIA's .run installer. apt's point release is the only remaining
        known deviation from a validated configuration.

STEP 5  IF PI05 SERVING REGRESSES: roll back immediately (Step 2). The Pi05
        track owns every verified result in the project; sim does not.

NOTHING ELSE NEEDS INSTALLING. Isaac Sim 5.1 + Isaac Lab 2.3.0 + LeIsaac 0.4.0
+ Python 3.11 + torch 2.7.0+cu128 are ALREADY correctly installed in
~/sim/leisaac-venv. The driver is the single wrong variable.
```

**Sequencing note - this is the important part.** The Pi05 local-serving track
works today and owns every verified result in the project. Sim is speculative,
locally deadlocked, and has known-bad interactions with this GPU generation.

```text
DO NOT let sim debugging block the TRUST EXAM
(new_machine_local_serving_20260804.md Section 5).

That exam is the gate before ANY robot motion. It needs no hardware, no
simulator, no driver change. Right now a freshly built serving stack on a new
machine has NEVER been checked against the pod's known-good numbers
(gripper corr 0.83, MAE 4.4). Era 1 cost a month to exactly this situation.
It is the highest-evidence-value task available - see pi05_work_prioritization.md.
```

---

## 9. Unrelated Finding, Already Applied

Isaac Sim warned `CPU performance profile is set to powersave`.

```text
Somewhat a false alarm: it reads scaling_governor, and with intel_pstate in
ACTIVE mode that string says "powersave" while still boosting to full turbo.
The knob that matters is EPP (energy_performance_preference).

APPLIED anyway, since EPP genuinely biases sustained load:
  powerprofilesctl set performance
  -> EPP = performance on all 24 cores, observed 5405 MHz (5.7 GHz spec max)
  MADE PERMANENT: ~/.config/systemd/user/power-performance.service (enabled)
  revert: systemctl --user disable --now power-performance.service
```

The same log also warned `IOMMU is enabled`. **Left alone deliberately** -
disabling it is a firmware/kernel-cmdline change with security implications, and
one public report shows the same rtx.scenedb crash occurring *after* IOMMU was
disabled, so it would not have helped.

---

## 10. Sources

```text
Isaac Sim requirements (6.0)  docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html
Isaac Sim 5.1 requirements    docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html
rtx.scenedb crash, RTX 4090   github.com/isaac-sim/IsaacSim/discussions/648
rtx.scenedb crash, RTX 5080   github.com/isaac-sim/IsaacSim/issues/651
TiledCamera hang, RTX 5090    github.com/isaac-sim/IsaacLab/issues/4951
Blackwell issues (various)    github.com/isaac-sim/IsaacLab/issues/2483
                              github.com/isaac-sim/IsaacLab/discussions/3612
LeIsaac install matrix        lightwheelai.github.io/leisaac/docs/getting_started/installation
```
