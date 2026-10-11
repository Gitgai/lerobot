# π0.5 lane — Current Priority and Status

Last updated: 2026-10-10

**This file is the ROUTER and the TRACKER: what is open, in what order, and
where each step stands. It is NOT a log.** Detail, gates and pre-registered
readings live in the plan docs; results get written into the plan docs'
results blocks and only the one-word status is mirrored here.
**Hard limit ~100 lines.** Status words: `todo` `next` `running` `blocked`
`done` `dropped`. Every step has an ID; the plan docs use the same IDs.

> Why this file exists: priority once lived only in chat and the top item got
> buried. When summarising open work read the item BODY in the plan doc, not
> this row — a stale row can outlive the ruling that killed it.

---

## THE QUESTION (one line)

openpi says LoRA fits a consumer card and full fine-tuning needs 80 GB. Does
the route our 32 GB card can run produce a working policy, and how does it
stand next to the route it cannot run — on LIBERO first, then on the arm's
real task.

---

## ▶ L — LIBERO: LoRA vs full fine-tune (plan: `pi05_libero_openpi_vs_ours_plan_20261010.md`)

```text
ID   step                                                      status   owner/when
L1   openpi JAX stack runs on the 5090 (venv, GPU seen,        done     2026-10-10 18:15Z
     one forward pass). jax 0.5.3 sees the GPU; pi05_libero            results/pi05_libero_20261010/
     forward pass finite (10,7), 59 ms warm. Caveat: /tmp               l1_gate.log
     quota exhausted → TMPDIR must be on /home for every run.
L2   score THEIR pi05_libero full-FT checkpoint, our sim,      done     2026-10-10 18:30Z
     Spatial n=200, RTC off. → 200/200 = 100% (CI95 98.1-100),           results/pi05_libero_20261010/
     their 98.8 is inside the interval: HARNESS AGREES. 9.2 min          L2_openpi_pi05_libero_spatial_n200/
     wall. Loop: l2_eval_openpi.py (their convention, logged).
L3   train openpi LoRA on LIBERO here, 30k steps from          running  launched 2026-10-10 20:14Z
     pi05_base. Gate PASS: trainable 467M of 3.40B (LoRA 50M +          batch 32, 3.5 s/step, ~29 h
     SigLIP 415M + proj 2M = openpi's own "low_mem" = "LoRA +            6.5k/30k at 10-11 02:36Z
     vision encoder"). bs32 fits, peak 31.9 of 32.6 GB.                 exp lora_libero_20261010
     ⚠ 10k save cadence → at 10k: stop + --resume with 5k saves          l3_resume_5k.sh armed on go
     (operator 2026-10-11). Loss lines are stdout-buffered.
L4   reproduce THEIR full FT on the 72 GB GPU, recipe as       blocked  operator to point
     published, batch size the only change; no fit → rent               to the machine
     a bigger box (prefer multi-GPU node, batch 256)
L5   score L3 and L4 at 10k/20k/30k, same sim, same seeds;     todo     after L2-L4
     one table, three rows, RTC off
```

Answers: does LoRA work here · does full FT work when WE run it · LoRA vs
full at matched data. A gap to their checkpoint is partly their 7.7M
examples: reported, not attributed.

## ▶ O — Orange task in LeIsaac (plan: `pi05_leisaac_lora_vs_fullft_plan_20261010.md`)

```text
ID   step                                                      status   owner/when
O0   verify EverNorif/so101_place_orange_isaaclab is our       todo     anytime, ~30 min
     kitchen scene (decides 120 vs 200 starting episodes)
O1a  record to 450 pick-orange episodes (log attempts,         todo     can start before L
     successes, s/episode from hour one; project; stop)                 finishes — sim only
O1b  train full FT (72 GB machine) + LoRA (5090), same data,   todo     after O1a, L4 box
     LeRobot; 100 seeded 3000-step eps per row, RTC off
O2   10-20 instruction variants over the 3 single-arm          todo     only if O1b is clear
     scenes; Mimic for data; 50 eps/task; one model
O3   real arm: start from dongyoonkim/so101-pi05-base,         todo     after O1b
     + LightwheelAI real orange + ours; async + RTC ON
```

Public data surveyed 2026-10-10 (plan Appendix B): ~120-200 orange episodes
in our scene; 3,300-ep 11-task Isaac Lab corpus (other scene, train-only);
~14k real SO-101 episodes incl. a 16.7k-episode full fine-tune checkpoint.

## Order of work

```text
1  L1 now — it decides the stack for everything else and costs an hour
2  O0 and O1a in parallel with L — the recorder needs no decision and no GPU
   contention with L2/L3 if scheduled around them; days, not weeks
3  L2, L3 on the 5090; L4 as soon as the 72 GB machine is named
4  L5 → write-up → O1b → O3 (O2 only on a clear O1b)
```

## Standing decisions (do not reopen without a new fact)

```text
openpi stack first, LeRobot fallback          their recipe NEVER bent to fit a card
their checkpoint evaluated, not retrained     one simulator per table
n=200 LIBERO · 100/row LeIsaac · 50/task O2   RTC off in sim, ON on the real arm
August full-FT results not compared           LeRobot (not openpi) for the SO-101 task
DYNUS capped at 16 GB; shut it down for long runs (the old "47 GB" is stale)
```

## Standing rules for this lane

```text
E1 preflight before ANY run >1 h (preflight_features.py) · a rung is a POC
until it checkpoints AND resumes · loss is NOT a proxy for capability · state
every lever explicitly, defaults included (dtype and gradient_checkpointing
both default OFF in lerobot) · setsid for long runs · check
nvidia-smi --query-compute-apps before launching · confirm rtc_config=None
at every sim policy load · checkpoint at most every 5k steps on any run
longer than ~10 h (operator, 2026-10-11) · TMPDIR=/home/kiran/tmp in every
launched script while /tmp's quota is exhausted · never cap JAX memory below
what the smoke needs — a 0.6 fraction masqueraded as an OOM on 2026-10-10
```

---

## Legacy items (compressed; bodies in `pi05_training_capability_plan_20260811.md`)

```text
P0   rung 4 (fp32 Adam in host RAM) trains, checkpoints, resumes   done 2026-08-15
P1   move the display to the iGPU, frees ~1-1.9 GiB VRAM           blocked on operator (cable + reboot)
P2   8-bit vs fp32 Adam, single-variable, 24 h                     dormant — L5/O1b will
                                                                     partly answer it
P3   3g rerun (starting-checkpoint hypothesis)                     dormant, premise retracted
P4   our 89 real episodes (STEP 4)                                 superseded by O3
not doing: rung 5 parameter offload (operator) · DeepSpeed (CPUOffloadAdamW is ~70 lines, verified)
```
