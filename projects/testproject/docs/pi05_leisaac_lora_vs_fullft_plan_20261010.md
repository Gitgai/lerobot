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
limit is how many tasks the simulator offers and how fast we can score them.

### What a LeIsaac task is (read from the source, 2026-10-10)

A task is ~60-170 lines of config on a shared single-arm template:
a scene USD with the task's objects pulled out by name · subtask signals
(30-line torch predicates on object/gripper positions) · a success
predicate · object/camera pose randomization · the instruction string.
Robot, cameras, recorder and action space come from the template.

```text
scenes shipped      kitchen with oranges · kitchen with hamburger items ·
                    table with cube · toy room          (+ a loft, LeKiwi only)
tasks shipped       pick orange · lift cube · clean toy table (single arm)
                    fold cloth (two-arm only)
```

### Three tiers of "new task"

```text
A  new instruction on an existing scene   predicate + description string
                                          (+ randomization)        HOURS each
   e.g. pick ONE orange · the orange nearest the plate · lift the cube to
   10 cm · put one letter in the box · pick in a stated order
B  new objects in an existing scene       edit the USD, add rigid bodies,
                                          then tier A              DAYS each
C  a new scene                            USD authoring / Lightwheel Marble
                                                                   A WEEK+ each
```

**Target: 10-20 tier-A variants across the three single-arm scenes. One
model trained on all of them.** Tier B only for an object the real-arm task
needs. Tier C is a separate project, not this plan.

### Data per task — the real cost

```text
teleop          leader arm, real time, one person; how the shipped 60-episode
                sets were made
state machine   scripted phases driven by object positions (the pick-orange
                one is ~300 lines); a tier-A variant on the same objects is a
                parameter change; a NEW motion is ~a day plus tuning; success
                rate depends on spawn positions
Mimic           ~10 teleop demos per task → annotate subtask boundaries (the
                task's own signals) → generate hundreds automatically.
                ★ THE MULTIPLIER that makes 10-20 tasks affordable: a short
                  teleop session per task instead of a controller per task.
density         ≥42 demos per task (LIBERO's per-task count); more for the
                tasks we care most about
```

### Evaluation — the binding constraint

```text
per episode     ~12 min at 3000 steps, one Isaac process
100/task/policy 20 h → 20 tasks × 2 policies ≈ a month of sim. Too much.
⇒ do what LIBERO does: 50 seeded episodes per task, the SUITE AGGREGATE is
  the headline (20 tasks × 50 = 1000 episodes per policy, ±3 points), per-task
  numbers read only for gaps ≥25 points. Still ~10 days per policy serially.
⇒ parallel Isaac envs would cut this; the Mimic generator takes a num_envs
  flag, our eval loop is single-env today. UNVERIFIED for eval. Check early.
```

Start Stage 2 only if Stage 1's LoRA-vs-full answer is clear. It buys
instruction following and a model that does not collapse onto one skill,
at the cost of authoring tasks, data per task, and simulator time.

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
Stage 2 authoring          10-20 tier-A tasks: hours each → ~2 weeks part-time
Stage 2 data               ~10 teleop demos per task + Mimic generation
Stage 2 eval               ~10 days per policy serially at 50/task; less if
                           parallel envs work
```

---

## Appendix — where the facts above come from (LeIsaac 0.4.0 source at ~/sim/leisaac-src)

```text
task anatomy      source/leisaac/leisaac/tasks/pick_orange/pick_orange_env_cfg.py
                  tasks/lift_cube/lift_cube_env_cfg.py · tasks/clean_toy_table/...
predicates        tasks/pick_orange/mdp/observations.py (grasp: <5 cm + gripper
                  <0.6) · mdp/terminations.py (oranges within ±10 cm of plate,
                  at plate height, arm at rest)
template          tasks/template/single_arm_env_cfg.py (robot, wrist+front
                  640x480 cameras, recorder, time-out)
randomization     utils/domain_randomization.py (object pose, camera pose,
                  particle objects)
scenes            assets/scenes/{kitchen,simple,toyroom}.py
state machine     datagen/state_machine/{base,pick_orange}.py; launched via
                  scripts/datagen/state_machine/generate.py (--num_demos,
                  --num_envs, --use_lerobot_recorder)
Mimic             tasks/pick_orange/pick_orange_mimic_env_cfg.py (SubTaskConfig
                  per subtask signal); scripts/mimic/annotate_demos.py (--auto)
                  and scripts/mimic/generate_dataset.py (--num_envs)
EnvHub            huggingface.co/docs/lerobot/en/envhub_leisaac — env id
                  LightwheelAI/leisaac_env:envs/so101_pick_orange.py; pins
                  lerobot 0.4.1 / python 3.11
```
