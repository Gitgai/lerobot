# LoRA vs full fine-tune of π0.5 on the SO-101 orange task, in LeIsaac — what we are doing

Date: 2026-10-10, kiran-AI90. Status: **PLANNED, NOT STARTED. Follows the
LIBERO plan** (`pi05_libero_openpi_vs_ours_plan_20261010.md`); starts once
that has answered the method question.

This file says WHAT and WHY. The HOW gets written when each stage starts.
This is a fresh experiment; earlier orange results are not inputs to it.

---

## The question

LIBERO tells us whether LoRA on a 32 GB card holds up against a full
fine-tune on a benchmark. This plan asks the same question on the task the
arm is actually for — pick oranges and place them on the plate with an
SO-101 — and then grows it from one task to many.

Simulation is the test bed: LeIsaac's SO-101 scenes, as published through
LeRobot EnvHub (`LightwheelAI/leisaac_env:envs/so101_pick_orange.py`).
Seeded episodes are cheap there and the success check is automatic. The
real arm comes last, with the winner.

---

## Stage 1 — one task: pick orange

### Data: 450 episodes

```text
target   450 successful pick-orange episodes recorded in LeIsaac
why 450  matches the LIBERO training set in frames (~270k), so a 30k-step
         run at batch 256 passes over the data about as many times as their
         LIBERO run did (~28), instead of ~210 passes over 60 episodes
have     60 (LightwheelAI/leisaac-pick-orange, already local) — they count
rest     recorded by the LeIsaac data generator, running continuously
how      log attempts, successes and seconds per episode from the FIRST
         HOUR; project the finish date from those numbers, not from
         estimates; stop at 450; transcode to video as you go so storage
         stays flat
```

### Training: two rows, same data

```text
full FT   π0.5 from pi05_base, LeRobot's official recipe (bf16, gradient
          checkpointing, nothing frozen) on the 72 GB machine; or the
          host-RAM optimizer recipe here if that machine is busy
LoRA      π0.5 from pi05_base, LeRobot PEFT LoRA, on the 5090
same      dataset, steps, batch where the cards allow, seed
optional  GR00T N1.6 fine-tuned on the same 450 — a reference row from a
          different architecture, if we want one
```

LeRobot, not openpi, for this task: openpi has no SO-101 pipeline and its
lerobot pin is old.

### Evaluation: 100 seeded episodes per row

```text
n          100 per row, 3000 steps each   → ±8 points, separates gaps ≥15
close call 250 per row if two rows land within 10 points AND the choice
           between them matters
same       simulator, seeds, success predicate for every row
```

### Harness decision

```text
π0.5 cannot run inside the EnvHub process: that environment pins lerobot
0.4.1 on Python 3.11, π0.5 needs lerobot 0.6.1 on Python 3.12. So the policy
is SERVED over a socket from the probe venv into the Isaac process. We
already have that loop (policy server + LeIsaac + ground-truth scoring).
Use it. Take EnvHub's check_success as the predicate if it is stricter
than ours. Before trusting the EnvHub pip install, list its registered
environments — a pip install that registers zero tasks is a known failure
shape; the source install is the fallback.
```

### What Stage 1 will and will not tell us

```text
WILL   whether each route produces a working orange picker in sim
WILL   LoRA vs full at matched data, steps and seeds — on the real task
WON'T  real-arm performance. Sim-trained, sim-scored. Stage 3 answers that.
WON'T  be comparable in difficulty to LIBERO's 98%: this is one task with
       ~450 demos; theirs is 40 tasks with ~42 demos each. Lower bar.
```

---

## Stage 2 — many tasks, one model

The model is language-conditioned; one fine-tune can hold many tasks. The
limit is how many tasks the simulator offers.

```text
exist today (single SO-101 arm)   pick orange · lift cube · clean toy table
                                  (fold cloth is two-arm only)
the cheap way to many tasks       LIBERO's own trick: reuse a scene, vary the
                                  INSTRUCTION — which object, where it goes,
                                  what the goal is. Each variant is a config
                                  change plus a success predicate, not a new
                                  environment.
target                            10-20 instruction variants across the three
                                  scenes; ~42+ demos per variant (LIBERO's
                                  per-task density); one model trained on all
eval                              100 seeded episodes PER TASK, same rules
new assets                        only for a task we actually want on the
                                  real arm
```

Start Stage 2 only if Stage 1's LoRA-vs-full answer is clear. It buys
instruction following and a model that does not collapse onto one skill,
at the cost of authoring tasks and data per task.

---

## Stage 3 — the real arm

The winning route from Stage 1 (or the multi-task model from Stage 2) goes
to the physical SO-101. Sim-to-real is its own question with its own plan;
this document only says it is where the answer is finally read.

---

## Decisions already made

```text
sim first, real arm last                   operator, 2026-10-10
train on sim data, score in sim            keeps the domain out of the comparison
450 episodes for Stage 1                   LIBERO-equivalent frame count
100 seeded eval episodes per row           ±8 points; 250 on a close call
LeRobot stack for this task                no SO-101 path in openpi
policy served into Isaac, not in-process   lerobot/python pin conflict
one task first, many tasks second          baseline before breadth
```

---

## Cost, roughly

```text
recording 390 episodes     days, not weeks — projected from the first hour's log
full FT training           ~a day on the 72 GB machine (smoke first)
LoRA training              ~7 h on the 5090
eval, 2-3 rows × 100       ~a day each at ~12 min per 3000-step episode
                           (parallel Isaac envs may cut this; unverified)
Stage 2                    unscoped until Stage 1 reports
```
