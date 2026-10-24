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

## Status (mirrored into `PI05_CURRENT_PRIORITY.md`)

```text
O0   verify EverNorif scene                       todo
O1a  record to 450 orange episodes                todo — can start now, sim only
O1b  full FT + LoRA on the same data, score       todo — after O1a and the L4 machine
O2   10-20 instruction variants, one model        todo — only on a clear O1b
O3   real arm from dongyoonkim/so101-pi05-base    todo — after O1b
```

## Stage 1 (O1) — one task: pick orange

### Data (O1a): 450 episodes

```text
target   450 successful pick-orange episodes in LeIsaac's kitchen scene
why 450  matches the LIBERO training set in frames (~270k), so a 30k-step
         run at batch 256 passes over the data about as many times as their
         LIBERO run did (~28), instead of ~210 passes over 60 episodes
have     ~120 verified public (LightwheelAI 60 + their Mimic 60), ~200 if
         EverNorif's 83 turn out to be the same scene — see Appendix B
rest     recorded by the LeIsaac data generator, running continuously
how      log attempts, successes and seconds per episode from the FIRST
         HOUR; project the finish date from those numbers, not from
         estimates; stop at 450; transcode to video as you go so storage
         stays flat
before   dedupe the community re-uploads; check camera pose and naming
mixing   against the LeIsaac rig (a moved camera breaks a pixel policy on
         the same robot); keep one fps
```

What varies and what does not (clarified 2026-10-19, operator's question):

```text
varies       object placements — LeIsaac's scripted generator respawns the three oranges and the plate
             each episode (utils/domain_randomization.py: object pose; camera-pose jitter is available in
             the same module and is a DECISION at O0, ranges recorded there — not yet taken)
fixed        the scene: one kitchen, same oranges, plate, lighting, robot, 640x480 front + wrist cameras
looks like   NOT our real episodes, by design. These episodes serve the Stage 1 comparison (LoRA vs full
our real     fine-tune), which is trained AND scored in simulation so the real-to-sim gap stays out of the
data?        comparison. They are not meant to reach the bench.
variety vs   for the controlled comparison, variety in placements is what matters (the eval is 100 seeded
matching     random placements). For the real arm it is the reverse: a pixel policy breaks when the camera
             moves, so matching our rig matters more than variety, and useful variety there is variety
             INSIDE real data (placements, fruit, lighting on our own setup).
two data     simulated data → the clean method comparison (O1); our 109 unique real episodes (89 + 20 plate demos; the 99-episode set repeats 79 of the 89) → the arm (R5 / O3).
stories      Mixing them in one run is ruled out (standing decision below: real sets for the arm, sim sets
             for the comparison).
```

### Training (O1b): two rows, same data

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
RTC        OFF in sim, every row. The sim waits for each chunk, so there is
           no inference delay to hide; guided RTC would only add a variable.
           Confirm rtc_config=None at every policy load and log it.
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

## Stage 2 (O2) — many tasks, one model

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

## Stage 3 (O3) — the real arm

> 2026-10-19: the public real-SO-101 base (dongyoonkim) is audited and tested FIRST, before our own
> recordings — split out to `pi05_so101_real_base_audit_plan_20261019.md` (R0-R3). This section
> remains the plan for what follows R3. Audit result so far (2026-10-19): the public corpus is usable with
> a cleaned manifest (R4: 13% of episodes have swapped camera slots, 304 sim episodes inside, 450 at 10 fps);
> real orange-fruit demos in it are ~61 + part of 200 — our own 89 + 99 real orange episodes stay essential.

The winning route from Stage 1 (or the multi-task model from Stage 2) goes
to the physical SO-101. Sim-to-real is its own question with its own plan;
this document only says it is where the answer is finally read.

**Start from `dongyoonkim/so101-pi05-base`, not from `pi05_base`.** It is
pi0.5 FULLY fine-tuned (3.62B trainable, no LoRA) on 16,687 real SO-101
episodes from 181 public sources — effective batch 256, 40k steps, 8×A100
for ~40 h — i.e. the real-arm full fine-tune we would otherwise be doing
ourselves. Claimed ~90% on one pick-and-place task over an unrecorded trial
count: treat as a starting point, not a result. Expects three camera slots
(base_0_rgb, left_wrist_0_rgb, right_wrist_0_rgb) with masking; trained
with VLASH on top of the openpi/LeRobot PI05 policy. Fine-tune it on our
real orange episodes plus LightwheelAI's real orange set (Appendix B.D).

**On the real arm, RTC is ON — asynchronous inference plus chunk guidance,
for every policy alike, and recorded as a lever.** The arm cannot wait for
inference the way the sim does: a synchronous loop froze our arm for ~650 ms
per chunk at ~31% duty and wrecked the grasp; the pipelined loop ran at
~95% duty. Two variants exist (see the LIBERO plan's RTC section): guided
RTC is LeRobot's inference switch (`rtc_config`, default OFF — turn it on);
trained RTC needs the delay simulated in training, which the dongyoonkim
checkpoint already had (VLASH, `max_delay_steps` 8) and which neither openpi
nor LeRobot's trainer provides. Whether our GR00T client's `--rtc` applied
prefix guidance or only pipelined is unverified — check before comparing.

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
RTC off in sim, on for the real arm        same setting for every policy in a
                                           table; recorded as a lever
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

## Appendix B — public SO-101 datasets (Hugging Face, surveyed 2026-10-10)

Numbers from each dataset's own `meta/info.json`. Grouped by how directly
we can use them. All Apache-2.0 where a licence was shown.

### B.A — LeIsaac pick-orange, OUR evaluation scene (Stage 1 training data)

```text
LightwheelAI/leisaac-pick-orange            60 ep    36k fr   front+wrist 30fps  local
LightwheelAI/leisaac-pick-orange-mimic-v0   60 ep    42k fr   Mimic-generated
EverNorif/so101_place_orange_isaaclab       83 ep    20k fr   front+wrist 30fps
                                            ⚠ scene NOT confirmed as LeIsaac's kitchen — check first
~25 community re-uploads named leisaac-pick-orange(-v30/-prepared)
                                            likely duplicates — dedupe, do not count
```

### B.B — LeIsaac sim, other tasks (Stage 2 candidates, same robot + rig)

```text
tshiamor/leisaac-pick-block-1000          1000 ep   766k fr  front+wrist 30fps  pick block
aaronsu11/so101_fruit_leisaac               57 ep     8k fr  fruit
azazdeaz/teleop_so101_leisaac_combined      30 ep    25k fr  lift cube + toyroom pick
azazdeaz/teleop_so101_leisaac_lift_cube, _toyroom_pick_e_e        small teleop sets
Aaronng456/leisaac_{red,blue,yellow}cube{,v2}, _bluecylinder{,v2}  small cube/cylinder sets
```

### B.C — Isaac Lab SO-101 multi-task, DIFFERENT scene (training breadth only)

```text
CoRL2026-CSI/Isaaclab-so101_11task_openpi_v21
    3,300 ep · 1.18M fr · 11 skills · 800 instruction strings
    ("Pick up the lime block and place it on the gray dish." …)
    top + left_wrist 480x640 · 10 fps · v2.1 · so101_follower
Cache-SCA/Isaaclab-so101_11task_baseCaP_3300epi(_10fps)   same corpus, other cut
Cache-SCA/IsaacLab-SO101_<task>_baseCaP_{100,300}epi      per task: pick_place,
    sort_by_color, stack_2_cubes, push_button, turn_on/off_lever, open/close_box,
    push_cube, pull_cube, extract_cube, touch_cube
Cache-SCA/isaaclab-pickplacecube-so101-1000epis-no-randomize(-baseline_10fps)
    1,000 ep · 362k fr · one task · carries skill/subtask annotations
Cache-SCA/SO101-teleop_multitask_7tasks_700epi(_10fps)    700 ep teleop, 7 tasks
⚠ their environment is not published as something we can run, so these can
  TRAIN a broader model but cannot be SCORED. Stage 2 evaluation stays on
  our LeIsaac tasks.
```

### B.D — real SO-101 (Stage 3)

```text
dongyoonkim/so101-pi05-base-dataset   13,969 ep · 7.27M fr · 156 merged public
    sources · 3 camera slots w/ masks · 30 fps (450 ep are really 10 fps) · v2.1
    + the checkpoint trained on it: dongyoonkim/so101-pi05-base (see Stage 3)
armnet/armnetbench_v01_lerobot_so101   2,499 ep · 1.13M fr · 8 tasks · 3 cams
    (front/top 576x1024, wrist 720x1280) · AV1 20 fps · includes rollouts from
    7 policies incl. π0.5 and GR00T N1.7 · Apache-2.0
hungho77/so101-ai20k-multitask           455 ep · 222k fr · 9 tasks · top+wrist · v3.0
LightwheelAI/so101-place-orange           61 ep ·  43k fr · front+wrist 30fps  ★ same
LightwheelAI/so101-pick-pen               61 ep ·  41k fr · front+wrist 30fps    naming as our rig
wsagi/leisaac-real-pick-orange            99 ep ·  41k fr · 3 tasks · real orange
lerobot/svla_so101_pickplace              50 ep ·  12k fr · so100_follower · up+side cams
```

### B.E — what the survey changes

```text
Stage 1   starts from ~120-200 orange episodes, not 60
Stage 2   a 3,300-episode multi-task sim corpus exists for breadth; evaluation
          still needs our authored LeIsaac variants
Stage 3   start from dongyoonkim/so101-pi05-base; add LightwheelAI's real
          orange set and our own real episodes
always    verify camera pose/naming against our rig · one fps per training
          run (10 vs 30 differ across sets) · dedupe re-uploads · keep the
          licence list
```

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
