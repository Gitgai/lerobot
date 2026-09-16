# The two machines — what lives where

Written 2026-09-15 after an agent running on the Acer searched for the project's
baseline checkpoint, failed to find it, and concluded no model had been chosen.
The checkpoint was there the whole time — on the other machine.

**If you are looking for something and cannot find it, check which machine you
are on before concluding it does not exist.**

---

## The short version

```text
kiran-AI90   New Jersey   RTX 5090    models, datasets, training, analysis
Acer         Pune         no GPU      the arms, the cameras, recording
```

They are joined by ZeroTier and each can SSH to the other **without a password
already**. No access needs to be requested or granted.

---

## Reaching the GPU box from the Acer

This works today. It was verified on 2026-09-15 by running it:

```bash
ssh kiran@192.168.194.220 'hostname'          # -> kiran-AI90
```

```bash
ssh kiran@192.168.194.220 'cat /home/kiran/lerobot_assets/checkpoints/orange_pick_baseline_v1/LINEAGE.json'
```

```bash
ssh kiran@192.168.194.220 'nvidia-smi --query-gpu=name,memory.free --format=csv,noheader'
```

If any of those fail, the fault is the network link, not permissions — see
"When the link is down" below.

---

## kiran-AI90 — the GPU box (New Jersey)

```text
user          kiran
ZeroTier      192.168.194.220        <- use this; it works from Pune
LAN           192.168.0.119 wired, 192.168.0.118 wifi
GPU           NVIDIA GeForce RTX 5090
OS            Ubuntu 26.04.1
```

### What lives here, and nowhere else

```text
/home/kiran/lerobot_assets/checkpoints/     ALL model weights (~13 GB each)
/home/kiran/lerobot_assets/datasets/        ALL training datasets
/home/kiran/projects/git/nvidia/lerobot/    the repo, including projects/testproject
```

**`lerobot_assets` is OUTSIDE the repo.** It is a separate top-level directory
with no symlink joining them, so searching the project tree will never reach the
weights. This is exactly the trap that misled one agent.

Also running here: the policy server on port 5555, and the DYNUS flight work,
which is a **separate project sharing the same machine**. Flight containers
compete for memory and have killed training runs via systemd-oomd (SIGTERM,
EXIT=143, clean log, no error message). If a training run dies silently, check
whether a flight container started.

---

## The Acer — the robot bench (Pune)

```text
user          gaikwad-prakash
ZeroTier      192.168.194.228
```

### What lives here

```text
the arms          follower serial 5B14114209, leader serial 5B14029688
the cameras       OV4689 wrist ("AK-Camera"), Logitech C270 front
~/esp_orange/     freshly recorded demonstrations (currently empty)
~/esp_apple/      "
~/PrakashProjects/lerobot/lerobot/   LeRobot install with its own .venv
~/*.py, ~/rec_esp.sh                 the bench scripts - see the handoff doc
```

### What does NOT live here

**No model weights. No training datasets. `~/lerobot_assets` does not exist.**

Model work cannot be done on this machine. Do not try to copy checkpoints here
to work around that — they are 13 GB each and the link to Pune is unreliable.
Run model work on the GPU box over SSH instead.

---

## Which machine for which task

| Task | Machine | Why |
|---|---|---|
| Recording demonstrations | **Acer** | the arms and cameras are physically here |
| Anything touching the arm | **Acer** | same |
| Camera diagnosis | **Acer** | same |
| Training / fine-tuning | **kiran-AI90** | the GPU and the weights are here |
| Reading a checkpoint or its lineage | **kiran-AI90** | the weights are here |
| Dataset conversion / merging | **kiran-AI90** | the datasets are here |
| Analysing recorded video | **either** | copy the episode over; they are small |
| Editing the repo and docs | **kiran-AI90** | the git repo is here |

A recorded dataset is produced on the Acer and must be **copied to the GPU box**
before it can be trained on. A few hundred MB, which the link handles.

---

## When the link is down

The Pune site has been reachable roughly a third of the time over the past week,
and **both Pune machines go dark together**, which points at the site network
rather than either computer. This now costs more time than any technical problem
recently solved.

Symptoms and what they mean:

```text
ping to .228 fails                 the site is down; nothing at the bench is reachable
ssh times out but ping works       the laptop is up, sshd or the link is struggling
arm_ports.py finds nothing         the arms are unplugged or unpowered, not a network fault
```

Retry rather than concluding a machine is broken. When recording, wait for a long
stable stretch — thirty episodes needs one.

---

## Rules that have already been learned the hard way

**Never address a device by number.** `/dev/ttyACM0` was the leader in the
morning of 2026-09-14 and the follower by evening; camera indices have swapped
twice. Resolve by serial or by name:

```bash
eval $(~/PrakashProjects/lerobot/lerobot/.venv/bin/python arm_ports.py | grep '^export')   # arms
eval $(python3 ~/camfind.py)                                                                # cameras
```

**Never identify a model by guessing from the repo.** This is a LeRobot checkout,
so it ships ACT, diffusion, SmolVLA and others — none of which this project uses.
The project trains **GR00T N1.6**. Read `MODELS.md` for the registry, and read a
checkpoint's own `config.json` (`model_type`) or `LINEAGE.json` to identify it.

**Do not search for `train_config.json`.** That is a LeRobot convention; GR00T
does not write one. Searching for it finds only `act_leisaac_orange` and
`pi05_012000`, both dead ends, and never the real baseline.

---

## Related documents

```text
PLAN.md                              the project's direction
MODELS.md                            the model registry - authoritative
agent_handoff_codex_20260915.md      the current blocking problem (follower USB)
```
