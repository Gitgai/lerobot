# LoRA vs full fine-tune of π0.5 on LIBERO — what we are doing

Date: 2026-10-10, kiran-AI90. Status: **L1-L3, L5(LoRA) DONE 2026-10-12; L4 (full FT on 72 GB) open.**
➡ **Standalone write-up of what was done and found: `RESULTS_pi05_libero_lora_vs_fullft_20261013.md`.**
This file says WHAT and WHY. The HOW is sketched in the appendix and gets
written properly when we start each phase.

➡ **What follows this:** the same question on the arm's real task, in
LeIsaac — `pi05_leisaac_lora_vs_fullft_plan_20261010.md` (one task, then
many tasks, then the real arm).

---

## The question

openpi's README lists two ways to fine-tune π0.5:

```text
Fine-Tuning (LoRA)   > 22.5 GB   RTX 4090          ← our 32 GB card can run this
Fine-Tuning (Full)   > 70 GB     A100 80GB / H100  ← it cannot
```

We want to know: **does the route our card can run produce a policy that
works, and how does it stand next to the route it cannot run?**

LIBERO is the test bed because openpi publishes both the full-fine-tune
checkpoint and its scores there (98.8% on LIBERO Spatial). So their side is
free, and there is a reference number.

The August full-fine-tune work on this machine is **out of scope** here. We
are comparing openpi's two routes, not revisiting ours.

---

## Status (mirrored one word at a time into `PI05_CURRENT_PRIORITY.md`)

```text
L1  openpi runs on the 5090          done 2026-10-10 — jax 0.5.3 sees the GPU,
                                     pi05_libero forward pass finite (10,7),
                                     23 s cold / 59 ms warm. Record:
                                     results/pi05_libero_20261010/l1_gate.log
                                     ⚠ /tmp quota exhausted on this box: set
                                     TMPDIR=/home/kiran/tmp for every run
L2  score their checkpoint           done 2026-10-10 — 200/200 on Spatial, CI95
                                     98.1-100, 20 trials x 10 tasks, env seed 7,
                                     init states 0-19 per task, their replan-5
                                     convention, RTC none, 9.2 min wall. Their
                                     98.8 sits inside the interval → harness
                                     agrees; L5 may be read against it.
                                     results/pi05_libero_20261010/
                                       L2_openpi_pi05_libero_spatial_n200/
                                       {summary.json, per_episode.jsonl}
                                     loop: l2_eval_openpi.py (reused for L5)
L3  train LoRA here                  running since 2026-10-10 20:14Z — config
                                     pi05_libero_low_mem_finetune, batch 32,
                                     30k steps, EMA off, lr cosine 2.5e-5→2.5e-6.
                                     Smoke: 3.5 s/step, peak 31.9 of 32.6 GB
                                     (JAX pool high-water, GPU otherwise empty).
                                     ETA ~29 h (finish ≈ 2026-10-12 01:40Z).
                                     ⚠ the plan's "~7 h" was a guess; measured
                                     is 4x that. Trainable 467M (see appendix).
                                     02:36Z 10-11: 6,470 steps, 100% GPU, 80 °C,
                                     575 W, 31.9 GB, rate flat at 3.5 s/step.
                                     CHECKPOINT CADENCE (operator, 2026-10-11):
                                     10k apart risks losing 10 h to a crash.
                                     Decision: do NOT restart now (certain loss
                                     of 6.4 h); at the 10k checkpoint stop and
                                     --resume with save_interval=5000,
                                     keep_period=5000 (schedule continues; step
                                     counter intact; ~20 min reload+compile).
                                     10k passed un-armed (I waited for a go;
                                     lesson: arm timed, vetoable steps and say
                                     so). ARMED 2026-10-11 11:29Z for 20k:
                                     stop → score 10k and 20k with the L2 loop
                                     while the GPU is free → --resume with 5k
                                     saves. Checkpoints then 10k,20k,25k,30k.
                                     Loss at 12.5k: 0.018 (from 0.094), smooth.
                                     ⚠ 2026-10-11 ~16:17Z HOST REBOOT killed the
                                     trainer at 18.8k; the 20k save (and the
                                     armed 5k-resume) never happened; only 10k
                                     survived (8.9 GB). 8.6 h lost. Restarted
                                     18:40Z: score 10k → --resume from 10k with
                                     save_interval=2500 (operator) → score all.
                                     Checkpoints now every 2.5k from 12.5k.
                                     Note: openpi's "Step N: loss=" lines are
                                     stdout-buffered; the live log shows rate
                                     only. Loss is readable per checkpoint.
L4  reproduce full FT on 72 GB       blocked 2026-10-14 05:41Z — DOES NOT FIT.
                                     Smoke on GPU 1 (RTX PRO 5000 72GB, 73,415 MiB
                                     total, JAX cap 95%), recipe as published
                                     (fp32 weights, fp32 AdamW, EMA 0.999):
                                       batch 32  OOM at 66.1 GB used, asked +20.2 GB
                                       batch 16  OOM at 66.1 GB used, asked +18.0 GB
                                       batch  8  OOM at 66.0 GB used, asked +16.9 GB
                                     Train state initialised fine (~60 GB persistent:
                                     3.40B × (4 w + 4 g + 8 Adam + 4 EMA) ≈ 68 GB
                                     before activations, matching the 66 GB peak);
                                     the OOM is inside the FIRST train_step, and the
                                     requested block barely shrinks with batch, so
                                     no single-card batch size rescues it. Their
                                     ">70 GB" row is honest; 72 GB is short.
                                     Per the standing decision the recipe is NOT
                                     bent (no EMA-off, no bf16): NEXT = a bigger
                                     machine — ideally a multi-GPU node so
                                     fsdp_devices>1 shards the state AND batch 256
                                     becomes possible (a true reproduction).
                                     Records: results/pi05_libero_20261010/
                                     l4_smoke.log, l4_smoke_bs{32,16,8}.log.
                                     Norm stats for pi05_libero computed (assets/).
L5  score ours, one table            LoRA side DONE 2026-10-12 15:08Z. Every
                                     checkpoint, 200 episodes, L2 loop, seed 7:
                                       step   success   CI95        fails/task
                                       10000  195/200   94.3-98.9   1:2 5 6 8
                                       12500  195/200   94.3-98.9   1:2 4 7 8
                                       15000  198/200   96.4-99.7   4 6
                                       17500  195/200   94.3-98.9   3 5 7 8 9
                                       20000  199/200   97.2-99.9   7
                                       22500  190/200   91.0-97.3   4:5 7:2 8:2 1
                                       25000  197/200   95.7-99.5   4:2 5
                                       27500  197/200   95.7-99.5   4:2 9
                                       29999  195/200   94.3-98.9   4:3 8:2
                                       pooled 1761/1800 = 97.8%
                                     their full FT (L2): 200/200. Their published
                                     98.8 lies inside every interval except
                                     22.5k's. All failures are 230-step timeouts;
                                     task 4 ("bowl in the top drawer of the
                                     cabinet") accounts for 14 of 39 and gets
                                     worse late (0 fails ≤12.5k, 12 from 22.5k).
                                     No monotone trend after 15k: 99.0, 97.5,
                                     99.5, 95.0, 98.5, 98.5, 97.5 — consistent
                                     with ±2 points of n=200 noise plus a mild
                                     late drift on one task. 30k is not better
                                     than 15-20k; openpi's 30k default bought
                                     nothing measurable here.
                                     L4's row (our full FT) still pending.
                                     FILMED 2026-10-12 (results/.../videos/): drawer
                                     task @22.5k 17/20 on re-run (15/20 original),
                                     @15k 19/20 (19/20); all tasks trial 0 @20k
                                     10/10. Every drawer failure is the same: arm
                                     reaches into the drawer, grips the bowl, never
                                     lifts it out before the 230-step cap. Not a
                                     perception/instruction failure; a grasp-and-
                                     extract failure in the one confined-space task.
                                     L5b DONE 2026-10-12 23:52Z — second 200
                                     layouts (trials 20-39), pooled with the first:
                                       15k    198 + 194 = 392/400 = 98.0  [96.1,99.0]
                                       20k    199 + 197 = 396/400 = 99.0  [97.5,99.6]
                                       22.5k  190 + 195 = 385/400 = 96.2  [93.9,97.7]
                                     drawer task per set: 15k 19|19, 20k 20|18,
                                     22.5k 15|19. ⇒ 20k is the checkpoint to keep.
                                     The 22.5k dip was mostly one bad layout set
                                     (190→195); at n=400 it still trails 20k by
                                     ~3 points with intervals barely touching —
                                     a mild late wobble, not a collapse. Their
                                     98.8 sits inside 15k's and 20k's intervals.
                                     Rerun logging added to the loop (--rerun
                                     save|serve): cams, 8 state + 7 action series,
                                     inference latency per chunk, outcome. One .rrd
                                     per episode; open with `rerun <file>`. Covers
                                     LIVE_VIZ_PLAN.md phases 1-2 for the sim path.
                                     2026-10-13: + infer/chunk (full 10x7 predicted
                                     chunk per call), plan/* series, 3D ee/path with
                                     the planned chunk overlaid (ee/plan). Channel
                                     list and arm follow-ups in LIVE_VIZ_PLAN.md.
```

## What we will do, in order

### 1. (L1) Get openpi running on this machine — first time ever

openpi is checked out at `~/sim/openpi` but has never been run here. It is a
JAX stack, and whether its pinned jax works on the 5090 (Blackwell) is
unknown. This is the first gate and it is cheap: build the environment, see
the GPU, run one forward pass.

```text
passes → everything below runs on openpi's own stack
fails  → try openpi's PyTorch port; if that fails too, the LoRA side falls
         back to LeRobot's PEFT LoRA (already proven here on the orange data)
         and we say so in the result
```

### 2. (L2) Score THEIR full fine-tune, in OUR simulator

Download `gs://openpi-assets/checkpoints/pi05_libero`. Run it on LIBERO
Spatial, 200 episodes, fixed seeds.

```text
expected  ~98.8%, their own number
near it   our simulator agrees with theirs → the comparison is fair
far below our setup is wrong somewhere → fix before anything else
```

### 3. (L3) Train LoRA on LIBERO, here

openpi's LoRA variants from `pi05_base`, 30k steps, on the same LIBERO data
their full fine-tune used. Save checkpoints along the way.

### 3b. (L4) Train the FULL fine-tune ourselves, on a big GPU — added 2026-10-10

Scoring their checkpoint proves their checkpoint works. It does not prove
the full-fine-tune ROUTE works when we run it: our data, our norm stats, our
launch, our harness. Reproducing their number ourselves validates the whole
pipeline end to end, and it gives the LoRA row a fair partner.

```text
where     GPU 1 of this machine since 2026-10-14 (RTX PRO 5000 72GB); the
          5090 stays free for scoring / the orange recorder
recipe    openpi's pi05_libero config AS PUBLISHED — fp32 weights, fp32
          AdamW, EMA 0.999, 30k steps — with ONE forced change: batch size.
          Their 256 is a multi-GPU number; one card runs what fits.
data      the same physical-intelligence/libero dataset
output    checkpoints copied back here; scored in the SAME simulator as
          steps 2 and 4, same seeds, n=200
```

**If it does not fit on 72 GB we find a machine that does. We do not bend
their recipe to fit.** Switching EMA off or dropping to fp16 would make it a
different recipe, and the point of this step is reproduction. The one
exception already granted is batch size, because no single card runs 256.

```text
first action   a 50-step smoke on the 72 GB card. My arithmetic from their
               training script says ~83 GB persistent (weights 16.6 +
               grads 16.6 + Adam 33.1 + EMA 16.6) before activations; their
               table says >70 GB. One of those is off. Measure, don't argue.
fits           run 30k steps there.
does not fit   rent or borrow a bigger box (operator, 2026-10-10).
               scripts/runpod/ exists in this repo. PREFER A MULTI-GPU NODE
               over a single bigger card: fsdp_devices>1 shards the model,
               batch 256 becomes possible, and the run is a TRUE
               reproduction rather than a reduced-batch one — the last
               confound against their checkpoint goes away. One run of
               about a day: rent, don't buy.
```

The 72 GB machine needs its own openpi environment, so step 1's gate runs
there too. LoRA stays on the 5090: that row exists to show what the 32 GB
card can do.

### 4. (L5) Score OUR LoRA and OUR full FT, same simulator, same seeds

200 episodes at 10k, 20k and 30k steps for each, so we see the curve and not
just the end.

### 5. (L5, the table) Put all three on one line

```text
                                     LIBERO Spatial, n=200   examples seen
openpi full FT (their checkpoint)    100.0 %  reference 98.8  7.7M
full FT (ours, big GPU, 3b)          ____ %                   30k x batch   ← L4 pending
LoRA (ours, 5090) best @20k          99.5 %   final @30k 97.5  960k
                                     pooled over 9 ckpts 97.8
```

**Reading (pre-registered bands):** LoRA ≥ 70% → "yes, LoRA works here" —
it landed at 97.5-99.5. Gap to their checkpoint: 0.5-2.5 points, inside
n=200 noise; reported, not attributed (they saw 8x the examples). The
L4 row decides whether full FT at OUR volume does any better.

Rows 2 and 3 at the SAME batch and steps differ only in the adapter route.
Row 1 vs row 2 measures what their extra data and batch bought.

---

## What the result will and will not tell us

```text
WILL   whether LoRA on a 32 GB card gives a working LIBERO policy
WILL   whether the full-fine-tune route works when WE run it, and whether
       it reproduces their 98.8 (or how far off, and at what batch)
WILL   LoRA vs full at matched batch and steps — the clean comparison
WON'T  separate "their extra data" from "their batch 256" in the row-1 vs
       row-2 gap, unless 3b lands on a multi-GPU box at batch 256
```

If row 1 vs row 2 is large and matters, the follow-up is matched examples
on the big machine. Long, but straightforward. Not scheduled.

---

## Real-Time Chunking — OFF for every row (decided 2026-10-10)

```text
two things share the name:
  guided RTC   inference-time only, no retraining (PI, arXiv 2506.07339):
               steer the denoiser so the new chunk's overlap matches the
               actions already committed. LeRobot has it (RTCConfig), default
               OFF (rtc_config=None). openpi does NOT have it at all.
  trained RTC  training-time (PI, arXiv 2512.05964): simulate the delay in
               training, condition on the committed prefix, no inference
               overhead. Not in openpi, not in LeRobot's trainer. VLASH has it.

their 98.8 was measured SYNCHRONOUSLY: 10-step chunk, execute 5, replan
(examples/libero/main.py). openpi has no RTC to switch on.
⇒ every row in this plan is scored RTC OFF, synchronous, same replan rule.
  Turning LeRobot's guided RTC on for our rows only would add a second
  variable to the table. Record the setting beside the step-5 table, and
  confirm rtc_config=None at every LeRobot policy load.
```

## Decisions already made

```text
openpi's stack first, LeRobot as fallback   operator, 2026-10-10
RTC off for every row, synchronous eval      matches their protocol; openpi has no RTC
their checkpoint evaluated, not retrained    their recipe does not fit here
one simulator for all policies               or the numbers are not comparable
n = 200 per eval                             n=40 cost us a 5-point error once
August full-FT results not compared          operator, 2026-10-10
full FT reproduced by us on a big GPU        operator, 2026-10-10
their recipe is NOT bent to fit a card       if 72 GB is short, get a bigger
                                             machine; only batch size may move
LoRA runs on the 5090, full FT elsewhere     each row answers its own question
```

---

## Cost, roughly

```text
1   openpi setup + gate (5090)       ~1 h, no GPU time to speak of
1b  same gate on the 72 GB machine   ~1 h
2   score their checkpoint           ~15 min GPU
3   LoRA training (5090)             ~7 h GPU  (re-estimate after a smoke)
3b  full FT smoke (72 GB)            ~15 min — decides fit / find a machine
3b  full FT 30k steps                unknown until the smoke; expect a day
4   score ours, 6 checkpoints        ~1.5 h GPU here
5   write-up                         desk work
```

Disk: their checkpoint plus the LIBERO dataset, a few tens of GB. Host RAM:
nothing special. DYNUS can keep running at its 16 GB cap.

---

## Run record — how the steps were actually executed (2026-10-10/11)

```text
execution path   the Bash tool was dead all session (/tmp tmpfs quota
                 exhausted, see diag_tmp.log). Every step ran as a script
                 under results/pi05_libero_20261010/ launched through
                 .claude/launch.json + the preview launcher, logs watched
                 with Monitor. Each script sets TMPDIR=/home/kiran/tmp.
L1  l1_gate.sh        uv sync → jax.devices → pi05_libero forward pass
L2  l2_run.sh         probe venv client (l2_eval_openpi.py) ↔ openpi server
                      --port BEFORE policy:checkpoint; server needs
                      XLA_PYTHON_CLIENT_PREALLOCATE=false beside other tenants
L3  l3_prep.sh        config gate (trainable-set breakdown) → dataset +
                      compute_norm_stats → bs32/bs16 smoke with VRAM sampling
                      ⚠ MEM_FRACTION=0.6 made bs32 OOM at 18.9 GB — the cap,
                        not the card; 0.92 with the GPU empty → bs32 fits
    l3_train.sh       setsid-detached trainer, pid file, 30 s GPU sampler
    l3_resume_5k.sh   wait for 10k → stop → --resume with 5k saves
L5  l5_eval_lora.sh   serve each checkpoint on :8001, score with the L2 loop,
                      print the table
GPU tenants      a 3.5-day-old lerobot_policy_server (Oct 7 rtc-remote-draft,
                 10 GB) was stopped with operator approval before L3
                 (stop_stale_policy_server.sh). Desktop holds ~1.7 GB.
                 ★ DYNUS FLIGHTS SHARE THE GPU (measured 2026-10-11 14:17Z,
                 diag_gpu2.log): while a flight runs, gzserver's sensor
                 rendering is a GRAPHICS context at 29-59% SM; the trainer
                 drops to 39-69% SM and its step time goes 3.5 → 5.5-5.8 s.
                 With gzserver idle the trainer is back at 99% SM. CPU is
                 NOT the cause (all-core 21% busy; trainer main thread at
                 99% of one core; loaders at 4.5%). `--query-compute-apps`
                 does not list graphics contexts — use `nvidia-smi pmon`
                 or the full `nvidia-smi` table (type G). The interference
                 is two-way: a saturating trainer also slows the flight's
                 camera rendering. Budget ~1.6x step time during flights.
openpi edits     ONE local addition to src/openpi/training/config.py
                 (pi05_libero_low_mem_finetune), marked, nothing else touched.
```

## Appendix — the how, for when we get there

Facts already checked on disk, so the next person does not re-derive them:

```text
openpi pins       jax[cuda12]==0.5.3, torch 2.7.1, python>=3.11, flax 0.10.2
                  (~/sim/openpi/pyproject.toml). lerobot pinned by git rev.
their LoRA        gemma_2b_lora rank 16, gemma_300m_lora rank 32, attn+ffn
                  (models/gemma.py:88-108). No pi05 LoRA config shipped; the
                  pi0 one (config.py:669-689) is the template: *_lora
                  variants + get_freeze_filter() + ema_decay=None.
                  ★ ADDED 2026-10-10 as `pi05_libero_low_mem_finetune` in
                  ~/sim/openpi/src/openpi/training/config.py (local edit,
                  marked). MEASURED (l3_prep.log, gate L3.1): openpi's "LoRA"
                  is NOT pure LoRA — get_freeze_filter() freezes only
                  '.*llm.*', so the trainable set is 467.0M of 3.403B (13.7%):
                    414.8M SigLIP vision encoder   (left trainable by openpi)
                     50.0M LoRA adapters           (Gemma attn+ffn)
                      2.2M action/time projections (trainable)
                  Same filter as their published pi0 low_mem config, so this
                  IS their table row — but call it "LoRA + vision encoder".
                  Also: openpi's pi0.5 instantiates 3.40B params, not the
                  4.14B LeRobot's port reports; the port carries ~0.74B of
                  LM-head/untied weights that openpi does not build.
their full FT     pi05_libero config (config.py:734-754), batch 256, EMA
                  0.999, lr 5e-5, 30k steps. Memory, from scripts/train.py:
                  trainable params stay fp32 (only FROZEN ones are cast to
                  bf16, line 104); fp32 AdamW state for all of them (line
                  111); a full EMA copy (line 113); fp32 grads (line 158).
                  For 4.14B params that is ~83 GB persistent before
                  activations. No gradient accumulation exists; batch_size
                  is global; fsdp_devices>1 shards across GPUs.
                  Their eval: examples/libero/
                  main.py — 256px render, 180° rotate, pad-resize to 224,
                  replan every 5 steps, 10 settle steps, 220-step cap on
                  Spatial, 50 trials/task, seed 7.
our simulator     lerobot 0.6.1 LIBERO env in the probe venv, LIBERO package
                  installed (~/.libero/config.yaml points into that venv).
                  Differences to note: 280-step cap on Spatial (theirs 220),
                  360px render, success from env.check_success().
harness, as run   results/pi05_libero_20261010/l2_eval_openpi.py — a port
                  of their main.py (256px, 180° rotate, pad-resize 224,
                  replan 5, 10 settle steps, 220 cap, env seed 7, init state
                  = trial index) run in the PROBE venv against openpi's
                  websocket server (serve_policy.py; --port must precede
                  policy:checkpoint). 20 trials x 10 tasks = 200. Every
                  episode logged. Their checkpoint: 200/200 (L2). Later rows
                  go through the SAME script by pointing the server at the
                  new checkpoint dir. Server needs
                  XLA_PYTHON_CLIENT_PREALLOCATE=false beside other GPU
                  tenants, else cuBLAS fails to get a workspace.
                  Their checkpoint ships its own norm stats; LoRA needs
                  compute_norm_stats.py run first (done in l3_prep.sh).
LoRA gate         (corrected 2026-10-10) no Gemma weight outside lora_a/lora_b
                  may train; vision encoder + projections DO train under
                  openpi's own definition. If the trainable count reads the
                  full 3.40B, it is not LoRA — stop. Gate passed at 467M.
rules             E1 preflight before any run >1 h · n=200 · every lever
                  explicit (dtype and grad-ckpt both default OFF in lerobot)
                  · setsid for long runs · check compute-apps before launch
```
