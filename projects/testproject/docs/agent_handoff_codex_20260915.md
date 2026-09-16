# Handoff to Codex — 2026-09-15

Written at the end of the 2026-09-14 bench session (Pune evening / NJ morning).
Read `PLAN.md` for the project's direction and `MODELS.md` for the model
registry. This document covers the model in use, what changed in that session,
and the one problem that now blocks everything.

---

## You are probably on the wrong machine

If you are running on the **Acer** in Pune, the model weights and datasets are
not on your filesystem and never will be. They live on **kiran-AI90**, the GPU
box in New Jersey, which you can already reach without a password:

```bash
ssh kiran@192.168.194.220 'cat /home/kiran/lerobot_assets/checkpoints/orange_pick_baseline_v1/LINEAGE.json'
```

Verified working from the Acer on 2026-09-15. See `MACHINES.md` for what lives
on each machine and which one to use for which task.

---

## The model — read this before anything else

**This project fine-tunes NVIDIA GR00T N1.6. It is not an ACT project, and never
has been.** No model selection is open; it was settled on 2026-08-19 and the
baseline has been frozen since 2026-08-20.

```text
nvidia/GR00T-N1.6-3B  (3.29B params, off the shelf)
  |
  +-- 79 real orange demos, 10,000 steps
        |
        +-- orange_pick_baseline_v1     THE BASELINE. 9/10 full task on the
        |                               arm, 2026-08-20. FROZEN, write-protected.
        |
        +-- + 20 plate demos, 6,000 steps
              |
              +-- plate_v1              the model currently under test
```

### The baseline, on disk — AND WHICH MACHINE

**The checkpoints do not live inside this repo, and they are not on the Pune
laptop. They are on the New Jersey GPU box, `kiran-AI90`, in a separate
top-level directory.** An agent scoped to the project tree will not find them,
and this has already wasted one agent's search:

```text
repo           /home/kiran/projects/git/nvidia/lerobot/projects/testproject
checkpoints    /home/kiran/lerobot_assets/checkpoints          <- different tree
datasets       /home/kiran/lerobot_assets/datasets             <- same
```

There is no symlink joining them. Use the absolute path:

```text
/home/kiran/lerobot_assets/checkpoints/orange_pick_baseline_v1
  -> /home/kiran/lerobot_assets/checkpoints/n16_real79_side/checkpoint-10000
     13 GB, on kiran-AI90 only
```

Verify it in one command before concluding anything is missing:

```bash
ls -l /home/kiran/lerobot_assets/checkpoints/ && cat /home/kiran/lerobot_assets/checkpoints/orange_pick_baseline_v1/LINEAGE.json
```

If that fails, you are on the wrong machine — the weights exist nowhere else.
`~/lerobot_assets` does **not** exist on the Pune laptop; that machine holds the
arms, the cameras, and the freshly recorded datasets, nothing more.

It carries its own `LINEAGE.json`:

```json
{
  "name": "orange_pick_baseline_v1",
  "trained": "2026-08-19",
  "parent": "nvidia/GR00T-N1.6-3B (off the shelf)",
  "dataset": "so101_orange_89_v21_train79 (79 episodes; holdout 2,8,13,14,16,54,56,60,75,80)",
  "steps": 10000,
  "status": "FROZEN BASELINE - 9/10 full task completions on the arm, 2026-08-20",
  "note": "write-protected; never overwrite"
}
```

and its `config.json` reports the architecture directly:

```text
model_type      Gr00tN1d6
architectures   ['Gr00tN1d6']
action_horizon  50
```

### Do NOT search for `train_config.json`

**This is a live trap and it has already misled one agent.** `train_config.json`
is a **LeRobot** convention. GR00T does not write one — it uses `config.json`
plus an `experiment_cfg/` directory. So a search for that filename finds only
dead ends and never the real baseline:

```text
act_leisaac_orange       train_config.json   policy.type: act    <- DEAD END
pi05_012000              train_config.json                       <- DEAD END
orange_pick_baseline_v1  config.json         Gr00tN1d6           <- THE BASELINE
n16_plate_v1             config.json         Gr00tN1d6
```

`act_leisaac_orange` is an abandoned simulator experiment from 2026-08-05,
trained on a third party's HuggingFace dataset. It is **not listed in
`MODELS.md` at all**, which is itself the signal: if a checkpoint is not in the
registry, it is not part of this project.

**To identify any checkpoint here, read its `config.json` `model_type`, or its
`LINEAGE.json`.** To find out which model is current, read `MODELS.md` — that is
the registry, and it is authoritative.

### The trainer

Training runs through the vendored GR00T trainer at
`scripts/gr00t_patches/launch_finetune.py`, which carries two local patches: an
env-gated 8-bit optimizer, and automatic `LINEAGE.json` writing. The second
exists because on 2026-08-26 nobody could answer which model a fine-tune had
started from, and it had to be settled by comparing action-head weights. **Every
checkpoint must be able to state its own parentage without forensics.**

What actually gets trained: `tune_llm=False` but `tune_top_llm_layers=4`,
`tune_visual=False`, `tune_projector=True`, `tune_diffusion_model=True`,
`tune_vlln=True` — **50% of parameters (1.63B)**, not the 43% that the action
head alone would suggest.

---

## The single blocking fact

**The follower arm cannot hold a USB connection. Recording is impossible until
that is fixed.** Nothing else on the critical path is broken.

Do not start a recording session, do not schedule training, and do not interpret
any arm trial, until the follower survives a 30-second connection test. A
dropout mid-episode corrupts that episode, and the plan calls for thirty of them.

---

## What the failure looks like

```text
19:13:39  usb 3-2: USB disconnect, device number 20
19:13:39  cdc_acm 3-2:1.1: acm_start_wb - usb_submit_urb(write bulk) failed: -19
19:13:41  usb 3-2: new full-speed USB device number 26 using xhci_hcd
19:13:41  usb 3-2: SerialNumber: 5B14114209        <- the follower
```

The board vanishes from the bus and comes back about two seconds later with a
new device number. Python sees `SerialException: write failed: [Errno 19] No
such device`, or `termios.error: (5, 'Input/output error')` if it dies during
shutdown. Both are the same event.

It happened **six times in roughly twenty minutes**, on two different laptop USB
ports, under four different programs.

---

## What has been ruled out, and how

Each line is a measurement taken on 2026-09-14, not an inference.

| Suspect | Test | Result |
|---|---|---|
| Our test script | Ran LeRobot's own `lerobot-teleoperate` | **Died the same way** |
| A bad laptop port | Moved follower from port 3-2 to 3-1 | **Died on both** |
| Torque / motor current | Same 30 s read loop with torque never enabled | **Died at 18 s anyway** |
| Servo supply sagging | Logged `Present_Voltage` every 50 ms until death | **Steady 5.9 V throughout** |
| Cable signal integrity | Counted kernel `-71 / -32 / -110` errors | **Zero.** Every drop is a clean power-cycle |
| The laptop's USB stack | Identical CH340 board (the leader) hammered 30 s | **Survived, 564 read cycles, no drop** |

The leader control (last row) is the decisive one. Same board model, same
laptop, same driver, same read pattern, same moment — the leader is fine and the
follower is not. **The fault is physical and specific to the follower's USB
path: its cable, its connector, or its board.**

### Do not re-derive these

The supply voltage is a red herring and cost an hour. It reads 6.0–6.1 V idle
and 5.6–5.9 V under load, which *is* under the STS3215's 6.0–8.4 V spec and is
worth improving eventually — but it is **not** the cause of the dropouts,
because the voltage trace is flat across the instant the board disappears, and
because the board dies just as readily with torque off and the servos idle.

Likewise, `power/control = on` on both boards means USB autosuspend is
**disabled**. It is not the cause. (`on` = stay awake; `auto` = allow suspend.
Easy to read backwards.)

---

## The timeline matters

```text
2026-09-14 ~18:50 IST   a full 30-second recording SUCCEEDED, torque on throughout
2026-09-14  19:13 IST   first dropout
                        ... and five more within twenty minutes
```

**It worked, then twenty minutes later it did not.** In between, the operator was
at the bench restoring power to the arms (they had been dead — motor supply off;
that was a separate, now-resolved problem). Something was disturbed in that
window. The first symptom was a gripper `Overload error!` at the end of the
successful recording.

This is why the leading hypothesis is mechanical — a cable pulled, a connector
part-seated, a solder joint cracked — rather than anything that would have been
wrong all along.

---

## Where the operator left it

**The operator was moving the follower's cable onto a USB hub** when the session
ended. The last topology read, taken mid-rewire, showed the rig partly
unplugged — leader, hub, and both cameras off the bus, follower on port 3-3.
**That snapshot means nothing; it was taken while hands were on the cables.**

Re-read the topology before concluding anything:

```bash
ssh gaikwad-prakash@192.168.194.228 'for u in /sys/bus/usb/devices/3-*; do [ -e "$u/idVendor" ] || continue; echo "$(basename $u) $(cat $u/idVendor):$(cat $u/idProduct) $(cat $u/serial 2>/dev/null)"; done'
```

```text
5B14114209 = FOLLOWER arm
5B14029688 = LEADER arm
```

### Note on the hub

A USB hub is a reasonable thing to try, but be aware it **adds** a component
rather than removing one, so a failure on the hub does not cleanly implicate the
arm. The hub already present in this rig is `2109:2817` (a USB 2.0 hub).

**The cleaner experiment is still to swap the two arms' cables**, leaving
everything else alone:

- leader starts dropping → **the cable is bad**, replace it
- follower still drops → **the board or its socket**, inspect the follower's USB
  socket for physical wobble

---

## The test to run

`~/notorque.py` on the laptop is the fastest verdict — 30 seconds, torque never
enabled, so it is safe to run with nobody standing by:

```bash
ssh gaikwad-prakash@192.168.194.228 'cd ~/PrakashProjects/lerobot/lerobot && .venv/bin/python ~/notorque.py'
```

```text
"SURVIVED 30 s with torque OFF: N read cycles, no dropout"   -> good, move on
"DIED at N s with torque OFF"                                -> still broken
```

`~/notorque_leader.py` is the same test aimed at the leader, for use as a
control whenever a result is ambiguous.

Only after the follower survives that should you run `~/synctest.py`, which does
enable torque and does move the arm.

---

## Safety: torque survives a crash

When the USB drops, `disconnect()` never completes, so `disable_torque` never
reaches the servos. **Torque lives in the servo's own register and the servos
keep their external supply, so the arm stays stiff and holding position after the
program has died.** This happened twice in the session; both times the arm was
found holding, once with a joint pegged at maximum load (1000/1000).

After any crashed arm program, run:

```bash
ssh gaikwad-prakash@192.168.194.228 'cd ~/PrakashProjects/lerobot/lerobot && .venv/bin/python ~/safe.py'
```

It prints the torque/load/voltage of all six joints and then releases torque.
`~/synctest.py` has since been hardened to attempt this itself on a fresh handle
before giving up, and to print one line instead of a traceback.

---

## Settled this session: the arms ARE in sync

The operator's question was whether leader and follower agree. **They do.**
Measured read-only, normalised through each arm's own calibration:

```text
joint            leader   follower   gap
shoulder_pan       5.2        5.3     0.1 deg
shoulder_lift   -102.8     -102.6     0.2 deg
elbow_flex        96.8       96.9     0.1 deg
wrist_flex        79.4       78.9     0.5 deg
wrist_roll         8.4        8.4     0.0 deg
gripper           53.7       -7.4    61.1 deg
```

Five joints within half a degree — and they reached that agreement by *tracking*
during the seconds each test survived, so the follower genuinely follows.
Calibration is sound. Close this question; do not re-open it.

**The gripper's 61° is not a fault.** The leader's gripper is a trigger you
squeeze, the follower's is a pair of jaws — different mechanisms, different
ranges, mapped through calibration rather than copied. The number was large
simply because the trigger was open while the jaws were closed.

Script: `~/startgap.py` (read-only, never enables torque, safe to run anytime).

---

## Bug fixed: `rec_esp.sh` would have deleted recorded episodes

**This was a live data-loss bug and is worth understanding before touching the
recorder.**

`rec_esp.sh` decided whether to resume by counting files with a glob written for
the **v2.1** dataset layout:

```text
v2.1  videos/chunk-000/<camera>/episode_NNNNNN.mp4
v3.0  videos/<camera>/chunk-000/file-NNN.mp4        <- what the recorder writes
```

The recorder writes v3.0, so the glob always returned 0, so the script always
took its "this is an empty stub from a crashed attempt" branch — `rm -rf "$ROOT"`.
**The next invocation would have destroyed a dataset containing real episodes.**

Counting `*.mp4` is wrong in principle too: v3.0 packs many episodes into one
video file, so the file count is not the episode count.

Fixed by reading the dataset's own metadata. New file `~/epcount.py` prints
`meta/info.json`'s `total_episodes`, or 0 if absent/unreadable; `rec_esp.sh` now
uses it for both the resume decision and the closing count, and only clears a
directory when epcount says 0 *and* the path exists.

---

## The test episode, and why it was deleted

One episode was recorded to verify the pipeline, then **cleared at the operator's
instruction**. It was a valid recording of an invalid demonstration:

```text
0.0 – 8.3s    arm motionless, orange on the table
8.3s          gripper closes — on nothing; the arm is far from the orange
8.3 – 16s     still motionless, gripper held shut
18 – 21s      arm finally moves toward the orange
21 – 30s      arm reaches the orange; recording ends
END           orange still on the table, plate still empty
```

As training data this teaches closing on empty air followed by dawdling.

**Guidance for the real session: start reaching the moment recording begins, and
keep the gripper open until the fingers are at the fruit.** Thirty seconds is
ample for a pick-and-place but not with eight seconds of stillness at the front.

The mechanical side of that recording was perfect, and that is the useful result:
897 video frames against 897 data rows on both cameras, no drift, both views
well framed and exposed. **The pipeline works; the demonstration did not.**

---

## Rig reference

```text
GPU BOX     kiran-AI90, New Jersey. Policy server on :5555. 22 GB GPU free,
            781 GB disk. Training and analysis run here, and ALL model weights
            and datasets live here, under /home/kiran/lerobot_assets/ - which is
            OUTSIDE the project repo. Nothing in lerobot_assets is mirrored to
            the laptop.
LAPTOP      gaikwad-prakash@192.168.194.228 (Acer, Pune), over ZeroTier.
            Holds the arms and cameras. Availability has been poor — roughly a
            third of the time over the past week, with both Pune machines
            dropping together, which points at the site network.

FOLLOWER    serial 5B14114209    <- the one that drops
LEADER      serial 5B14029688
WRIST CAM   OV4689, "AK-Camera"
FRONT CAM   Logitech C270
```

**Never address an arm or a camera by device number.** They renumber constantly
— three times in this session alone, and `/dev/ttyACM0` was the leader in the
morning and the follower by evening. Resolve by name or serial:

```bash
eval $(~/PrakashProjects/lerobot/lerobot/.venv/bin/python arm_ports.py | grep '^export')   # arms
eval $(python3 ~/camfind.py)                                                                # cameras
```

Both refuse rather than guess when a device is missing. `~/synctest.py` was
patched this session to use `arm_ports.py` after it was found hardcoding
`/dev/ttyACM0`, which by then would have addressed the wrong arm.

### Scripts on the laptop

| File | Moves the arm? | Purpose |
|---|---|---|
| `~/arm_ports.py` | no | resolve arm ports by serial |
| `~/camfind.py` | no | resolve cameras by name |
| `~/epcount.py` | no | episodes in a dataset, from its metadata |
| `~/probe_ports.py` | no | which ports have responding motors |
| `~/startgap.py` | no | leader vs follower pose, calibrated |
| `~/notorque.py` | no | 30 s bus hammer, follower, torque off |
| `~/notorque_leader.py` | no | same, leader — the control |
| `~/gripcheck.py` | no | per-joint load, voltage, temperature |
| `~/safe.py` | releases | report torque state, then disable |
| `~/voltrace.py` | **enables torque** | voltage trace to the moment of death |
| `~/synctest.py` | **moves the arm** | 60 s teleop, measures tracking error |
| `~/rec_esp.sh` | **moves the arm** | record demonstrations |

Local copies of the ones written this session are in this session's scratchpad;
they are not yet committed to the repo. **Consider committing them** — they have
already been rewritten twice from memory across sessions.

---

## What is waiting, once the arm is reliable

From `PLAN.md`, unchanged by this session:

1. **Record 20 orange-plate + 10 apple episodes** through the OV4689 wrist camera
   and C270 front camera.
2. **Hold 5 of the 20 out of training** — the lesson from plate_v2.
3. **Train from `orange_pick_baseline_v1`**, old demos mixed in as replay against
   forgetting, 6000 steps (measured as the right budget; more buys ~nothing).
4. **Test**: held-out demos offline first, then the arm, scoring GRASP and PLACE
   separately.

The apple set is recorded with the apple **alone** (operator's choice,
2026-09-10). This teaches the apple as an object but will **not** teach the model
to read the instruction — with one fruit in view the picture already says which
to pick. A language-grounding set needs both fruits present with the words
choosing between them.

---

## How this operator works

Worth internalising; these are standing preferences, repeatedly enforced.

- **Plain language, direct answer first.** Jargon in a summary is treated as a
  defect, not a style choice.
- **Measure, do not theorise.** Claims get challenged with "are you sure?" and
  the correct response is to go and check, not to defend.
- **Never guess when asked for clarification.** "Do not try to guess, i need
  clear clarification" is a direct quote.
- **Ask before destructive or physical actions.** Deleting recordings and moving
  the arm both get confirmed first.
- **Corrections are expected and welcome.** Several confident claims were wrong
  in this session and in prior ones; retracting promptly is the norm. Two from
  this session: the four-frame sample of the test episode was called "exactly
  right" before the full episode showed the pick never happened, and a
  goal-vs-position reading was presented as evidence before it turned out to be
  contaminated by a torque release performed moments earlier.

A concrete instance worth repeating: a `max_relative_target` safety cap was added
to the teleop test, and the operator asked whether that matched LeRobot's
defaults. It did not — the default is `None`, and neither `lerobot-teleoperate`,
`lerobot-record`, nor `rec_esp.sh` sets it. **It would also have corrupted the
measurement**, rate-limiting the follower and adding a `Present_Position` read
per cycle, inflating both the tracking error and the lag. It was removed. The
challenge was correct on both counts.

---

## Open questions, carried forward

- **Why the Pune site drops off the network so often** (~1/3 availability). This
  now costs more time than any technical problem solved recently.
- **Arm supply voltage**, 5.6–6.1 V where the STS3215 wants 6.0–8.4 V. Not the
  cause of the USB dropouts, but under spec and worth correcting.
- **Whether Brain B was genuinely worse** or merely less tempo-tolerant — three
  RTC runs were never done. See the caveat in `MODELS.md`.
- **Whether mixing two camera geometries in training helps or hurts.**
