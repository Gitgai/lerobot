# RESULTS — LoRA vs full fine-tune of π0.5 on LIBERO (the 32 GB question)

Written 2026-10-13, kiran-AI90. This is the standalone record: what we asked,
what we did, how, and what came out. Plan and running status:
`pi05_libero_openpi_vs_ours_plan_20261010.md` · tracker: `PI05_CURRENT_PRIORITY.md`
· raw artefacts: `results/pi05_libero_20261010/` (all scripts, every per-episode
log and summary are in git; mp4 and .rrd media are on disk only).

---

## 1. The question

openpi's README lists two ways to fine-tune π0.5:

```text
Fine-Tuning (LoRA)   > 22.5 GB   RTX 4090          ← our RTX 5090 (32 GB) can run this
Fine-Tuning (Full)   > 70 GB     A100 80GB / H100  ← it cannot
```

Does the route our card can run produce a policy that works, and how does it
stand next to the route it cannot run? LIBERO is the test bed because openpi
publishes both the full-fine-tune checkpoint and its score there (98.8% on
LIBERO Spatial), so their side costs nothing and has a reference number.

## 2. The answer

**Yes. On the 5090, openpi's LoRA recipe produces a LIBERO Spatial policy that
is statistically indistinguishable from their published full fine-tune.**

```text
                                          LIBERO Spatial       examples seen in training
openpi full FT, their checkpoint          200/200 = 100.0%     7.68M   (30k steps × batch 256)
ours, LoRA, best checkpoint (20k)         396/400 =  99.0%     640k    (20k steps × batch 32)
ours, LoRA, pooled over 9 checkpoints    1761/1800 =  97.8%
their published number (their harness)              98.8%
```

The LoRA policy saw 8-12× fewer example presentations and still lands within
1-2 points, inside sampling noise at these sample sizes. The one row still
missing is OUR full fine-tune at OUR data volume (L4, needs a ≥72 GB GPU),
which is what would separate "LoRA vs full" from "their data vs ours".

## 3. What we did, in order

```text
L1  2026-10-10  built openpi's JAX stack on the 5090 for the first time; gate:
                jax 0.5.3 sees the GPU, pi05_libero forward pass finite (10,7),
                59 ms warm.                                  l1_gate.log
L2  2026-10-10  scored THEIR pi05_libero full-FT checkpoint in OUR loop:
                200/200. Their 98.8 is inside our interval → harness agrees.
L3  10-10→10-12 trained openpi's LoRA from pi05_base, 30k steps, batch 32,
                on physical-intelligence/libero; 9 checkpoints kept.
L5  2026-10-12  scored every checkpoint, 200 episodes each; then a second
                200 layouts on 15k/20k/22.5k (n=400); filmed the drawer-task
                failures; added Rerun traces to the loop.
```

## 4. How — the setup, stated so it can be reproduced

### 4.1 Model and what "LoRA" trains

```text
base            openpi pi05_base (3.403B params as openpi builds it; LeRobot's
                port reports 4.14B because it carries LM-head/untied weights)
config          pi05_libero_low_mem_finetune — ADDED LOCALLY to
                ~/sim/openpi/src/openpi/training/config.py (marked), built from
                openpi's shipped pi0 low_mem config with pi05=True,
                action_horizon=10, discrete_state_input=False, the pi05_libero
                data settings, their *_lora variants, ema_decay=None
trainable       467.0M of 3.403B (13.7%), measured at init:
                  414.8M  SigLIP vision encoder   ← openpi leaves it trainable
                   50.0M  LoRA adapters: gemma_2b_lora r16 + gemma_300m_lora r32,
                          on attention + FFN of backbone and action expert
                    2.2M  action/time projections
                ⇒ openpi's "LoRA" is "LoRA + vision encoder". Same filter as
                  their published pi0 low_mem config, so it IS their table row.
frozen          the Gemma weights (2.94B), stored in bf16
optimizer       AdamW, cosine 2.5e-5 → 2.5e-6, 1k warmup, clip 1.0, no EMA
                (openpi's LoRA defaults). Adam state for 467M fp32 params ≈ 3.7 GB.
precision       trainable params fp32, frozen bf16 — openpi's own scheme
```

### 4.2 Data and volume

```text
dataset         physical-intelligence/libero — 1,693 demos, 273,465 frames,
                40 tasks across all four suites, 10 fps, 33 GB local
                (the SAME dataset their full FT used; norm stats computed with
                openpi's compute_norm_stats.py)
run             30,000 steps × batch 32 = 960k sample presentations ≈ 3.5 passes
theirs          30,000 × 256 = 7.68M ≈ 28 passes
```

### 4.3 Hardware and cost

```text
GPU             one RTX 5090, 32 GB; batch 32 peaked at 31.9 GB (JAX pool
                high-water with the card otherwise empty); 3.4-3.5 s/step
wall            ~28 GPU-hours of training INCLUDING 8.6 h lost when the host
                rebooted at step 18.8k (only the 10k checkpoint had been saved);
                resumed from 10k with a checkpoint every 2,500 steps
contention      a DYNUS flight's Gazebo renderer took 29-59% of the GPU while
                it ran and slowed training to 5.8 s/step (measured with
                nvidia-smi pmon; CPU was NOT the cause)
scoring         ~10 min per 200 episodes; 2,700 episodes total ≈ 2.5 h
```

### 4.4 Evaluation protocol — one loop for every row

```text
loop            results/pi05_libero_20261010/l2_eval_openpi.py — a port of
                openpi's examples/libero/main.py: 256 px render, 180° rotate,
                pad-resize to 224, state = eef pos + axis-angle + gripper (8),
                prompt = task string, 10 settle steps, policy returns 10
                actions, execute 5, replan; 220-step cap (+10 settle);
                env seed 7; trial i uses LIBERO's fixed initial state i
policy          openpi's own websocket policy server (serve_policy.py) in the
                openpi venv; client in the probe venv (python 3.12, libero pkg)
success         LIBERO's `done` from env.step (openpi's definition); LIBERO's
                check_success() logged alongside — they agreed on every episode
n               20 trials × 10 tasks = 200 per checkpoint (layouts 0-19);
                second set layouts 20-39 for three checkpoints → 400
RTC             none — openpi has no RTC; their 98.8 was measured synchronously
seeds / noise   the policy samples its own noise; a re-run of one episode is a
                fresh draw, not a replay
intervals       Wilson 95%: n=200 ≈ ±2-5 points near the top; n=400 ≈ ±1.5-3
```

## 5. Results in full

### 5.1 Learning curve, layouts 0-19 (n=200 each)

```text
step      success   rate    CI95          failures by task (task:count)
10000     195/200   97.5%   94.3-98.9     1:2 5:1 6:1 8:1
12500     195/200   97.5%   94.3-98.9     1:2 4:1 7:1 8:1
15000     198/200   99.0%   96.4-99.7     4:1 6:1
17500     195/200   97.5%   94.3-98.9     3 5 7 8 9 (one each)
20000     199/200   99.5%   97.2-99.9     7:1
22500     190/200   95.0%   91.0-97.3     4:5 7:2 8:2 1:1
25000     197/200   98.5%   95.7-99.5     4:2 5:1
27500     197/200   98.5%   95.7-99.5     4:2 9:1
29999     195/200   97.5%   94.3-98.9     4:3 8:2
pooled   1761/1800  97.8%
their FT  200/200  100.0%   98.1-100
```

Training loss (flow-matching MSE) went 0.094 → 0.020 by 10k → 0.014 by 22k,
smooth, no spikes. **The policy is essentially trained by 15k steps; after
that the scores move inside the noise band with no trend.** openpi's 30k
default bought nothing measurable here.

### 5.2 Second layout set, 15k / 20k / 22.5k (n=400 pooled)

```text
step     layouts 0-19   layouts 20-39   pooled        CI95         drawer task
15000    198/200        194/200         392/400 98.0  96.1-99.0    19 | 19 of 20
20000    199/200        197/200         396/400 99.0  97.5-99.6    20 | 18
22500    190/200        195/200         385/400 96.2  93.9-97.7    15 | 19
```

⇒ **20k is the checkpoint to keep.** The 22.5k dip was mostly one unlucky
layout set; at n=400 it still trails 20k by ~3 points with intervals barely
touching — a mild late wobble on the hardest task, not a collapse.

### 5.3 The ten tasks

All are "pick up the black bowl <somewhere> and place it on the plate", the
<somewhere> varying: between the plate and the ramekin; next to the ramekin;
table centre; on the cookie box; in the top drawer of the wooden cabinet; on
the ramekin; next to the cookie box; on the stove; next to the plate; on the
wooden cabinet. Six tasks were 20/20 at nearly every checkpoint. Task 4, the
drawer, accounts for 14 of the 39 failures in the first set and worsens late
(0 failures through 12.5k, 12 from 22.5k on).

### 5.4 What the failures are (filmed)

Every failure, all 39 plus those in the second set, is a **timeout**: the arm
never completes the place within 230 steps. None is a wrong object, a drop or
a collision. The filmed drawer failures all look the same: the arm reaches
into the drawer, closes on the bowl, then never lifts it out, making small
adjustments inside the drawer until the clock runs out; in some the drawer is
pushed sideways. Perception and instruction-following are not the problem;
grasp-and-extract in the one confined-space task is.

Re-runs on film reproduced the pattern: drawer task at 22.5k 17/20 (15/20 in
the scored run), at 15k 19/20 (19/20); all ten tasks at 20k, trial 0, 10/10.
Montages: `results/pi05_libero_20261010/videos/*/montage_last_frames.png`.

## 6. Instrumentation built along the way

```text
--video-dir      one mp4 per episode, agent | wrist cameras, 224 px, 10 fps
--rerun save     one .rrd per episode: both cameras, 8 state + 7 action series,
                 inference latency per policy call, the FULL 10×7 predicted
                 chunk per call, plan-vs-execute summaries, 3D end-effector
                 path with the planned chunk overlaid, outcome. ~2.5 MB each.
--rerun serve    the same, streamed live to a browser (grpc 9876, web 9090)
open             rerun <file.rrd> [more.rrd]   (~/.local/bin/rerun → probe venv)
recorded         600 episodes of the second layout set (L5b_*/rerun/, ~1 GB)
                 + a matched drawer pair at 22.5k and 20k (viz_pair_task4_trial37/)
```

This completes phases 1-2 of `LIVE_VIZ_PLAN.md` for the sim path; the
arm-only channels (motor loads, fault register) remain for the arm stage.

## 7. Things learned that are not about the model

```text
/tmp quota        /tmp is a 30 GB tmpfs with a per-user quota; 24 GB of stale
                  DYNUS scratch had exhausted it, which silently killed the Bash
                  tool and the first uv sync. Cleared by the operator. Runs set
                  TMPDIR on /home as insurance.
JAX memory cap    XLA_PYTHON_CLIENT_MEM_FRACTION=0.6 made batch 32 "OOM" at
                  18.9 GB — the cap, not the card. 0.92 with an empty GPU fits.
cuBLAS workspace  the openpi server beside a 10 GB tenant failed to init cuBLAS
                  with JAX's default 75% preallocation; PREALLOCATE=false fixes it.
tyro ordering     serve_policy.py's --port must precede `policy:checkpoint`.
checkpoint cadence  a host reboot at 18.8k cost 8.6 h with 10k saves; the lane
                  rule is now a save every 2,500 steps on any run over ~10 h.
GPU sharing       flights render on the same GPU (type G context, invisible to
                  --query-compute-apps); budget ~1.6× step time during flights.
```

## 8. Caveats, stated plainly

- LoRA vs full fine-tune at EQUAL data is not tested. Their run saw 8× more
  presentations; the L4 row (our full FT, ≥72 GB GPU) is what separates the
  recipe from the volume.
- "LoRA" here trains the vision encoder fully (415M of the 467M trainable);
  that is openpi's definition, not a pure-adapter run.
- n=200/400 cannot separate 99 from 100. Overlapping intervals mean "no
  difference shown", not "equal".
- One benchmark suite, Spatial. Object/Goal/Libero-10 were not scored.
- Sim only. Nothing here speaks to the real arm.

## 9. What is open

```text
L4   our full FT on a ≥72 GB machine (operator to name it); recipe as published,
     batch size the only permitted change; if 72 GB is short, rent a bigger box
O    the same question on the SO-101 orange task in LeIsaac
     (pi05_leisaac_lora_vs_fullft_plan_20261010.md): O0 scene check → O1a
     record to 450 episodes → O1b full FT + LoRA → O3 real arm from
     dongyoonkim/so101-pi05-base with RTC on
```

## 10. Git record

```text
f7b03ee7 / 79214504   plans, tracker, L1 PASS, L2 200/200, L3 running
3059caa3              resume-at-20k armed, 5k cadence, run record
7732e613              LoRA row complete: 9 checkpoints, 97.5-99.5%
05057134              second layout set n=400, filmed failures, rerun traces
17904090              full-chunk tensor, plan series, 3D path overlay
```
