# LoRA vs full fine-tune of π0.5 on LIBERO — what we are doing

Date: 2026-10-10, kiran-AI90. Status: **PLANNED, NOT STARTED.**
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
L1  openpi runs on the 5090          next
L2  score their checkpoint           todo
L3  train LoRA here                  todo
L4  reproduce full FT on 72 GB       blocked — operator to name the machine
L5  score ours, one table            todo
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
where     a 72 GB GPU the operator will point to (a different machine)
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
openpi full FT (their checkpoint)    ____ %  reference 98.8   7.7M
full FT (ours, big GPU, 3b)          ____ %                   30k x batch
LoRA (ours, 5090)                    ____ %                   30k x batch
```

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

## Appendix — the how, for when we get there

Facts already checked on disk, so the next person does not re-derive them:

```text
openpi pins       jax[cuda12]==0.5.3, torch 2.7.1, python>=3.11, flax 0.10.2
                  (~/sim/openpi/pyproject.toml). lerobot pinned by git rev.
their LoRA        gemma_2b_lora rank 16, gemma_300m_lora rank 32, attn+ffn
                  (models/gemma.py:88-108). No pi05 LoRA config shipped; the
                  pi0 one (config.py:669-689) is the template: *_lora
                  variants + get_freeze_filter() + ema_decay=None.
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
harness plan      run OUR LIBERO loop with two backends: lerobot policy
                  in-process, openpi policy via its websocket server
                  (serve_policy.py + openpi-client). Settle the step cap and
                  image handling so both policies see what they were trained
                  on. Their checkpoint ships its own norm stats; LoRA needs
                  compute_norm_stats.py run first.
LoRA gate         the trainable set must be only lora_a / lora_b tensors.
                  If the learnable count reads 4.14B, it is not LoRA — stop.
rules             E1 preflight before any run >1 h · n=200 · every lever
                  explicit (dtype and grad-ckpt both default OFF in lerobot)
                  · setsid for long runs · check compute-apps before launch
```
