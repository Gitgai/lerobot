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
