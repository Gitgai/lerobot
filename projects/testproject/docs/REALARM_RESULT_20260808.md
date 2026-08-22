# FIRST REAL-ARM RESULT — the as-is bet, measured

Date: 2026-08-08. The first policy-driven motion of the physical SO-101 in
this project's history, and the first hardware datapoint on its central bet.

## Setup (two-machine, everything pre-verified)

```text
policy   GR00T N1.6 (12e21/..., 94% in sim) served on the 5090 (:5556)
client   vendored single-file, on the arm laptop's own-era venv (lerobot 0.5.2)
cameras  front = laptop webcam /dev/video0 (bright, WB locked, exposure auto)
         wrist = Raspberry Pi rpicam-vid -> pi_wrist_proxy -> :8092 (revived)
scene    plate LEFT, one orange center-right, clean bright table - layout rule
instr    "Grab orange and place into plate" (the dataset string)
safety   150 s runs, SIGINT self-stop, user at the arm
```

## Run 1 (confounded - exposure lock pinned gain low, front view dim)

User observation: smooth motion from rest, sweep to the LEFT (the plate
side), never toward the orange, gripper never closed.

## Run 2 (confound REMOVED; evidence recorded per chunk)

```text
policy's view   verified BRIGHT and sharp (saved frames, chunk 0 onward):
                plate left, orange dead center - a clean scene
actions         143 chunks, smooth and coherent: lift -104 -> +35,
                pan -1 -> -51, no flailing
gripper         NEVER closed: range 45-59 all run (a close is single digits)
vs the orange   no approach at any point - user's eyes and the trajectory
                agree; final frame shows the gripper extended away, orange
                untouched
```

## Verdict

```text
THE AS-IS TRANSFER FAILS: coherent motion priors, ZERO object-directedness
on real pixels. Two runs, consistent; the second with the policy's own view
verified clean, eliminating every pipeline explanation in advance (that was
the point of the preflight, the client verification, and the frame logging).

This was the PRE-REGISTERED most-likely outcome ("purposeful reach =
success; completion = surprise" - and we got neither). The project's
original bet - sim/community checkpoints work as-is across SO-101 rigs -
is now MEASURED on hardware: no.

Symmetry note: this completes the mirror experiment. Real-trained Pi05
fails in sim; sim-trained N1.6 fails on real. Domain dominates, in both
directions, measured both ways.
```

## What activates next (per the standing plan)

Fine-tuning. The strongest option was armed for exactly this moment:
GR00T N1.6 on OUR 89 real-arm episodes (the working architecture, on data
from this exact table/arm/cameras). Remaining blocker: the 32 GB training
ceiling -> 8-bit Adam attempt. Alternatives on the same table: co-train
real + the 35-episode varied sim corpus.

The hardware pipeline built today is permanent: any future checkpoint tests
on the arm are now one command.

---

## Same-day follow-through: both fine-tune tracks unblocked, Pi0.5 TRAINING

> ⚠ **2026-08-11 — THE `adamw_bnb_8bit` RESULT BELOW IS NOT CURRENTLY
> REPRODUCIBLE.** `bitsandbytes` is not present anywhere on this machine: not in
> the GR00T venv, not in leisaac, not in testproject, not in the uv cache. The
> only filesystem hits are `transformers/` and `diffusers/` integration shims
> merely _named_ bitsandbytes. Either this venv was rebuilt since (see
> `N16_REBUILD_RUNBOOK.md`) or the claim is wrong.
> ⇒ **Do not cite "8-bit Adam works on this card" as established.** It is being
> tested from scratch as STEP −1 of
> [`pi05_full_finetune_on_5090_plan_20260811.md`](pi05_full_finetune_on_5090_plan_20260811.md).
> Correct this note when that settles.

```text
GR00T ceiling BROKEN   adamw_bnb_8bit: 100 probe steps at 4.15 it/s, 23.1 GB,
                       zero OOM - the wall that blocked training for 3 days.
                       (patch in launch_finetune.py; update the patches file)
                       ⚠ SEE THE NOTE ABOVE - bitsandbytes is not installed
                         anywhere now, so this cannot currently be confirmed.

PI05 LAUNCHED          pi05_sim_varied: from pi05_base on the 35-episode
                       varied corpus, 30k steps @ bs4, ~6 h, output
                       ~/lerobot_assets/checkpoints/pi05_sim_varied
   The OOM ladder that got there (each rung measured):
     bs16 fp32                 OOM  (fp32 weights = 16.6 GB alone)
     bs8/bs4 fp32              OOM
     bs8 bf16                  OOM  (trainable was ALL 4.14B -> 33 GB Adam)
     + train_expert_only=true  693M learnable - THE 012000 RECIPE; base
       + freeze_vision_encoder   config does NOT set these, 012000's did
     bs8 bf16 expert-only      OOM  (activations)
     bs4 bf16 expert-only      TRAINS: 1.4 steps/s, 26.3 GB, GPU 97%
   Also needed: --rename_map front->base_0_rgb, wrist->left_wrist_0_rgb
   (pi05_base uses pi0 camera naming), --policy.push_to_hub=false, and
   accelerate installed into the training venv.

WHY THIS EXACT SETUP IS THE RIGHT DIAGNOSTIC: same recipe as 012000
(expert-only, frozen VLM), same architecture, ONLY THE DATA differs
(varied sim vs their real 89). Score in sim at n>=3:
  grasps in sim   -> architecture exonerated; the real dataset is the suspect
  fails where N1.6 succeeded -> architecture convicted, Pi05 retires
TOMORROW: v3->GR00T-v2 bridge for the 89 real episodes -> GR00T-real
fine-tune (the hardware shot; the only untested 2x2 cell).
```
