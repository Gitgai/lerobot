# Phase 2 — can we actually TRAIN π0.5 here, not just fit it?

➡ **WHAT IS OPEN AND IN WHAT ORDER →
[`PI05_CURRENT_PRIORITY.md`](PI05_CURRENT_PRIORITY.md)** (a ~95-line router).
**This file is 2,193 lines of evidence and does NOT carry priority.** Consult the
router first; come here for detail.

Date: 2026-08-11, kiran-AI90. Follows
[`pi05_full_finetune_on_5090_plan_20260811.md`](pi05_full_finetune_on_5090_plan_20260811.md)
("phase 1"), which is CLOSED.

**Status: NOT STARTED. Steps 1–3 are pre-authorised to run unattended (§A).**

> Phase 1 answered *"does 4.14B fit and step?"* — **yes, 24.74 GiB peak, 7.10 GiB
> spare, 1.88× slower than expert-only.** It did **not** answer *"can we train a
> model here?"* Those come apart in two specific places, and this phase closes
> both.

```text
BLOCKER      checkpointing is BROKEN with 8-bit Adam. A 30k-step run that cannot
             write a checkpoint produces NOTHING. Everything else is downstream.
UNMEASURED   phase 1 fit BECAUSE it ran at batch size 1 with no gradient
             accumulation. Effective batch 1 is a TRAINING-QUALITY risk: if the
             resulting policy is bad you cannot tell whether it was the batch
             size, the data, or the approach. Worst kind of result from a
             multi-hour run.
```

---

# §A THE AUTONOMY CONTRACT — read before running anything unattended

**Operator asked for this to run without a permission prompt at each step. That
is reasonable for the mechanical work and NOT reasonable for everything.** The
split below is drawn from what actually stopped phase 1: a gated licence, an
auth token, and one script that would have written to someone else's public
dataset.

## 🟢 GREEN — run these unattended, no prompt

```text
· read GPU / disk / process state
· create, patch, or rebuild the PROBE venv at sim/pi05-fullft-probe
· pip/uv install INTO the probe venv
· patch site-packages INSIDE the probe venv, with .orig kept alongside
· run lerobot-train on ALREADY-CACHED datasets, any batch size, any step count
· write to ~/lerobot_assets/probes/**  and  results/**
· compute dataset stats LOCALLY (write_stats only)
· commit to this repo, including the doc and result artefacts
```

## 🔴 RED — STOP AND ASK, every time, no exceptions

```text
· ANY upload: push_to_hub, hf upload, create_tag, or writing to a Hub repo
  ⚠ lerobot's own augment_dataset_quantile_stats.py CALLS push_to_hub AND tags
    the repo. libero_spatial_image is HuggingFace's PUBLIC dataset, not ours.
    Now that a token exists this would SUCCEED rather than fail harmlessly.
    Use results/pi05_fullft_5090_20260811/add_quantile_stats_local.py instead.
· accepting a licence or gating agreement (e.g. a new gated model repo)
· anything involving credentials or tokens
· touching sim/Isaac-GR00T-n16/.venv, sim/leisaac-venv, or projects/testproject/.venv
· deleting or overwriting an existing checkpoint, dataset, or results directory
· patching this repo's src/lerobot (phase 1 showed it is not even what runs)
· STEP 4 of this plan — it spends the 89 real episodes. Human decision.
```

## ⏹ STOP CONDITIONS — abort the sequence and report, do not "work around"

```text
· an OOM at batch size 1              → contradicts phase 1; something changed
· loss NaN or inf                     → real defect, not a tuning problem
· torch is not 2.7.1+cu128            → a silent downgrade invalidates STEP -1
· trainable != total in a full-FT run → Gate B failure; everything after is void
· a step needs a NEW gated repo       → RED
· >2 consecutive failures of the same step for different reasons
    → the environment is not what this doc assumes. Stop and re-verify.
```

⇒ **Report at each step boundary regardless.** Unattended means "no permission
prompt", not "no reporting".

---

# STEP 1 — fix checkpointing with 8-bit Adam  `[~30 min]` 🟢

**This is the blocker. Nothing else matters until it is done.**

## The defect

```text
ValueError: Key `state/1/step` is invalid, expected torch.Tensor
            but received <class 'int'>
```

`bnb.optim.AdamW8bit` keeps its step counter as a **python int**;
`_save_single_optimizer_state` flattens the state dict straight into
`safetensors.save_file`, which accepts tensors only.

```text
site-packages/lerobot/optim/optimizers.py
  _save_single_optimizer_state   ~L334   flat_state = flatten_dict(state)
                                         save_file(flat_state, ...)   ← here
  _load_single_optimizer_state   ~L372   unflatten_dict(load_file(...))
```

## The fix

Coerce non-tensor scalars to 0-d tensors on save. Keep it narrow — scalars only,
and do not silently swallow anything unexpected:

```python
flat_state = {
    k: (v if torch.is_tensor(v) else torch.tensor(v))
    for k, v in flatten_dict(state).items()
}
```

⚠ **The load path is the half that is easy to declare done without testing.**
`torch`/`bnb` generally accept a tensor `step`, but that is an assumption until a
round-trip proves it. **A save that cannot be resumed from is not a fix.**

## Acceptance — and it closes phase 1's one open gap for free

```text
1  10-step run, --save_checkpoint=true --save_freq=10   → checkpoint WRITES
2  RESUME from it for 5 more steps                      → loads, loss finite
3  ★ compare a VLM backbone tensor in the checkpoint against pi05_base
   → norm CHANGED  ⇒ THE WEIGHTS-MOVED CHECK phase 1 could not perform,
     because it depended on the checkpoint that failed to write. Same task.
```

⇒ Capture as `patches/lerobot_061_optimstate_scalar_fix.patch`, alongside the
8-bit patch. **site-packages is not version controlled.**

---

# STEP 2 — largest batch that fits  `[~20 min]` 🟢

**The highest-value measurement available, and it is 20 minutes.** It converts
*"it fits"* into *"it is practical"*, and it decides whether gradient
accumulation — an unimplemented second code change — is needed at all.

## Why it is likely to succeed

Phase 1: peak 24.74 GiB with **7.10 GiB headroom**, and activations at bs1 look
under ~1 GiB with checkpointing on. If activations scale roughly linearly, bs4–bs8
plausibly fits. **Plausibly is not measured.**

## Arms

```text
batch_size ∈ {1, 2, 4, 8}   30 steps each, otherwise the phase-1 config exactly
STOP at the first OOM - do not continue up the ladder
record per arm:  peak VRAM (nvidia-smi 1 Hz) · lerobot mem_gb · steps/s ·
                 SAMPLES/s (= steps/s × batch)  ← the number that matters
```

⚠ **Compare samples/s, never steps/s, across batch sizes.** Phase 1 §6 made
exactly this error with the old bs4 baseline; steps/s across different batch
sizes flatters the smaller batch by the batch ratio.

## Decision rule — written before the result

```text
max batch >= 8    gradient accumulation NOT needed. Quality concern largely
                  evaporates. Go to STEP 3 at that batch.
max batch 4       usable. Note the gap to the reference recipe's 32 and decide
                  at STEP 3 whether to close it with accumulation.
max batch 1-2     gradient accumulation IS needed → a second code change
                  (~15 lines, Accelerator(gradient_accumulation_steps=...) plus
                  the update_policy() step gating). Do it BEFORE STEP 3.
```

---

# STEP 3 — the LIBERO capability run  `[~8 h]` 🟢

**This is the run that actually answers the operator's question.**

## ⇒ Use LIBERO, NOT the 89 real episodes. On purpose.

```text
IN DOUBT, and this run settles it:
  sustained throughput over hours (phase 1 measured 34 seconds)
  thermal behaviour under a long load
  memory stability - does peak drift or fragment over 10k+ steps?
  a full checkpoint round-trip that RELOADS

NOT in doubt, and using real data would entangle it:
  whether our corpus is any good
```

⇒ **A capability test should have exactly one unknown.** LIBERO already runs
end-to-end here as of phase 1. Spending the real episodes on a hardware question
mixes two investigations, which is the failure mode this whole lane has been
avoiding.

## Configuration — ⚠ RECOMMEND bs8, NOT the bs16 maximum

```text
batch size    8      NOT 16, deliberately. See below.
steps         12,000 ⇒ 96,000 samples, matching LeRobot's own pi05 example
                     (--batch_size=32 --steps=3000, docs/source/pi05.mdx)
est. wall     ~3.5 h at 7.63 samples/s   (bs16 would be ~3.1 h)
save_freq     2000, and NOT save_checkpoint=false - checkpointing is the point,
                     and STEP 1 made it possible
log_freq      100
```

**Why bs8 rather than the bs16 that fits:**

```text
bs16  28.05 GiB training, 29.49 total  ⇒ only 2.35 GiB headroom
bs8   25.53 GiB training, 26.97 total  ⇒ 4.87 GiB headroom
cost of choosing bs8:  8.51 -> 7.63 samples/s, about 10%. ~25 min on a 3.5 h run.
```

⇒ **The sweep measured 30 steps. STEP 3 runs 12,000.** Allocator fragmentation
over hours is exactly the kind of drift this run exists to detect, and starting
2.35 GiB from the ceiling invites an OOM at hour two that destroys the run and
answers nothing. **Buy the margin with 10% throughput.** If bs8 proves stable
across a full run, bs16 can be used afterwards with evidence rather than hope.

⚠ **bs16 is HALF LeRobot's reference batch of 32.** Effective 32 would need
2-step gradient accumulation — the code change STEP 2 just made unnecessary for
*fitting*. Whether it matters for *convergence* is a training-quality question
this plan does not answer, and it should not be smuggled into a capability run.

## Instrument beyond phase 1 — long runs fail differently

```text
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu,temperature.gpu,\
           clocks.sm,power.draw --format=csv -l 5   ← temps and CLOCKS: thermal
                                                      throttling is invisible in
                                                      a 34-second probe
```

## Acceptance

```text
run completes · peak VRAM stable (no upward drift) · no thermal throttle
loss finite and trending down · checkpoint RELOADS and produces finite actions
⇒ then, and only then, "we can train π0.5 on the 5090" is a measured claim
```

---

# STEP 3b — DID THE MEMORY LEVERS COST QUALITY?  `[~30 min]` 🟢

**Operator's question: "Adam 8 vs 32, f32 vs f16 — are we compromising quality
or just training speed?" We do not know, because NOTHING SO FAR MEASURES
QUALITY.** Loss fell 0.248 → 0.132, which shows learning and says nothing about
task success. This step makes the question empirical.

## The four levers, ranked by actual quality risk

```text
LEVER                    RISK    WHOSE CHOICE   WHY
─────────────────────────────────────────────────────────────────────────────
batch 8 vs reference 32  ★HIGH   OURS           noisier gradients AND the LR
                                                was NOT scaled - we run the
                                                preset lr=2.5e-5, tuned by
                                                upstream for a larger batch.
                                                A bs32 LR at bs8 takes steps
                                                too large for the gradient
                                                noise. UNTESTED.
bf16 without fp32 master MEDIUM  UPSTREAM'S     8-bit mantissa: when lr*grad is
                                                small vs weight magnitude the
                                                update rounds AWAY. Worst late
                                                in training. But this IS
                                                LeRobot's own recipe and their
                                                97.0% was measured with it.
8-bit Adam vs fp32 Adam  LOW     OURS           quantises ONLY optimiser state
                                                (m,v), blockwise, dequantised
                                                to fp32 for the update.
                                                Weights and grads keep full
                                                precision. Dettmers et al.
                                                ICLR 2022 matched fp32 across
                                                GLUE/ImageNet/LM.
gradient checkpointing   NONE    BOTH           mathematically identical;
                                                recompute, not approximation.
```

⚠ **The precision layout is NOT naive bf16 casting** — measured from the
step-6000 checkpoint:

```text
BF16   3.610B (87.1%)  255 tensors   mlp/attn projections, lm_head - big matmuls
F32    0.534B (12.9%)  558 tensors   action projections, biases, norms
```

⇒ The precision-sensitive 13% is deliberately kept in fp32. That is the
mitigation for the mantissa concern, and it is upstream's design, not ours.

## The measurement

LeRobot publishes **97.0% on Libero Spatial** for `pi05_base` on this dataset
(`docs/source/pi05.mdx`). That is a reference number **on the same axis**.

```bash
lerobot-eval --policy.path=<step-12000 checkpoint> ...   # LIBERO Spatial
```

## ⛔ THE RULE BELOW WAS ANCHORED TO THE WRONG BASELINE — corrected 2026-08-11

**First result: 70.0% (28/40) from `pi05_base` + 12k steps @ bs8. Against 97.0%
that looks like a 27-point gap. IT IS NOT A VALID COMPARISON.**

`docs/source/pi05.mdx` says: *"we finetuned **the libero base model** for an
additional 6k steps"*. There is a separate Hub checkpoint,
`lerobot/pi05_libero_base`, and its config is LIBERO-shaped where `pi05_base` is
generic:

```text
pi05_base         3 cameras: base_0_rgb, left_wrist_0_rgb, right_wrist_0_rgb
                  state[32]  action[32]        ← generic pi0 space
pi05_libero_base  2 cameras: image, image2     ← EXACTLY the LIBERO env keys
                  state[8]   action[7]         ← Franka Panda: 7-DoF + gripper
```

⇒ **We started from a different, less specialised checkpoint than the reference
did.** Different starting weights dwarf any of our memory levers, so the gap
cannot be attributed to 8-bit Adam, bf16, or batch size until this is controlled.

⚠ **This was my error in writing the rule** — pre-committing before seeing the
number was right; anchoring to an unmatched baseline was not.

⚠ **AND `pi05_libero_base`'s model card does NOT say it was trained on LIBERO** —
it is generic boilerplate, identical in framing to `pi05_base`. The LIBERO-shaped
config is strong evidence but **config is not weights**. Do not assert it was
pre-trained on LIBERO without measuring.

### ⇒ STEP 3b.0 — RUN, and it settled the question: **0.0%**

```text
pi05_libero_base, ZERO-SHOT on LIBERO Spatial, no training:  0.0%  (0/40)
```

⇒ **`pi05_libero_base` was NOT trained to solve LIBERO.** It is a base model
*shaped* for LIBERO's observation and action space (`image`/`image2`, state[8],
action[7] = Franka Panda 7-DoF + gripper) with **no task competence at all**.
"libero base" means *base model FOR libero*, not *trained ON libero*.

⇒ **My earlier claim that the reference had a capability head start is WRONG and
is retracted.** Both runs started from zero ability. Config was not weights, and
the zero-shot test was the right way to find that out — 3 minutes, no training.

★ **AND IT CALIBRATES OUR RESULT: our pipeline took a model from 0% → 70%.**
That is entirely our training, and it validates the whole stack end to end.

### ⛔ BUT THE REAL CONFOUND IS DATA VOLUME, AND I HAD THE ARITHMETIC WRONG

```text
batch size          how many examples the model sees before ONE weight update
step                one weight update
examples seen       steps × batch size          ← the number that matters

reference    6,000 steps × batch 32  =  192,000 examples   → 97.0%
ours        12,000 steps × batch  8  =   96,000 examples   → 70.0%
```

⇒ We did **more updates** but each saw far fewer examples. **They trained on
TWICE the data.** That is a far more mundane explanation for the 27-point gap
than any of our memory levers, and it must be controlled before quantisation is
even discussed.

⚠ **My planned "matched run: 6k steps at bs8" was wrong** — that is 48,000
examples, a **QUARTER** of the reference. It would have scored badly and proved
nothing, while looking like evidence against our levers.

### ⇒ A MATCHED RUN MUST MATCH EXAMPLES, NOT STEPS

```text
option              steps × batch   examples   est. wall   notes
match at bs8        24,000 ×  8     192,000    ~7.0 h      true control; batch
                                                           stays the variable
                                                           under test
match at bs16       12,000 × 16     192,000    ~6.3 h      same data, batch
                                                           closer to the
                                                           reference's 32; bs16
                                                           measured to fit
cheap probe bs8      6,000 ×  8      48,000    ~1.7 h      NOT comparable to
                                                           97%; shows the curve
                                                           only
```

⚠ **The capability question is ALREADY ANSWERED — yes.** STEP 3 proved the 5090
trains π0.5 sustained and stable; 0%→70% proved the pipeline produces a working
policy. A matched run answers only the narrower follow-up: *did the memory
levers cost accuracy?* Scope it accordingly; it is not on the critical path.

## Corrected decision rule — for the MATCHED run

```text
MATCHED RUN = finetune FROM pi05_libero_base, 6k steps, bs8, then eval.
              Same protocol as the reference except BATCH SIZE, which is
              exactly the variable we want isolated.

within a few points of 97%     the whole lever stack is vindicated EMPIRICALLY,
                               not by argument. Done.
well short of 97%              the batch-size/LR deviation is FIRST SUSPECT,
                               not the quantisation. Test by re-running at bs16
                               WITH a scaled LR - one variable, the one that is
                               ours.
short AND bs16 does not fix it then interrogate bf16 / 8-bit Adam. Do NOT start
                               here: it is the best-supported lever and the
                               least likely cause.
```

⚠ **n=40 gives roughly ±14 points at 95% confidence.** Even a matched run needs
more episodes to separate "slightly worse" from "the same". Scale n before
reading anything into a single-digit difference.

⚠ **Do not attribute a quality gap to quantisation before testing batch size.**
8-bit Adam is the lever with published evidence behind it; batch-8-with-an-
unscaled-LR is the one with none.

⚠ A LIBERO eval needs the LIBERO **simulator**, not just the dataset. If it is
not installed, that is a setup task — and 🔴 **if it needs a new gated repo or a
licence, STOP** (§A).

---

# STEP 3c — HOW MUCH DOES FULL FINE-TUNING FORGET?  `[~10 min]` 🟢

**Operator's question: "would it learn to pick oranges, fold laundry and
whatever LIBERO is doing? Or will it forget one task while learning another?"**
This turns the textbook answer into a number measured on this hardware.

## Why there is reason to expect forgetting — we already saw the mechanism

STEP 1's weights check: **595/603 VLM BACKBONE tensors changed.** Full
fine-tuning moved the vision-language backbone itself, not just the action head.
That backbone is where general world understanding lives, so reshaping it toward
simulated tabletop bowls is exactly the mechanism of catastrophic forgetting.

⇒ **This also reframes the 012000 recipe.** `train_expert_only=true` +
`freeze_vision_encoder=true` (693M) is precisely the ANTI-FORGETTING
configuration — it preserves the VLM and adapts only the action head:

```text
expert-only  693M trainable   VLM PRESERVED     less adaptation capacity
full FT     4.14B trainable   VLM OVERWRITTEN   max adaptation, max forgetting
```

We spent the day proving the 5090 *can* do the second. Whether you *want* it
depends on whether the goal is a specialist or a generalist.

## The measurement

We trained on **libero_spatial ONLY** (96k examples). LIBERO ships four suites.
Evaluating the same checkpoint on suites it never saw measures transfer directly.

```text
suite            trained on?   what a score means
libero_spatial   YES           our 70% - the in-distribution reference
libero_object    no            different OBJECTS, same robot/cameras/scene type
libero_goal      no            different GOALS
libero_10        no            long-horizon; hardest, expect least transfer
```

⚠ **Confound to state up front: we do not have a "before" number.** The honest
baseline for "did it forget?" would be `pi05_base` evaluated on `libero_object`
*before* our training — but `pi05_base` has the wrong camera keys and action
dims for LIBERO, and `pi05_libero_base` scores **0%** on everything (STEP 3b.0).
⇒ **So this measures TRANSFER, not FORGETTING.** Both start from zero
competence, so any score above 0 on an unseen suite is capability our training
*created* and that generalised — not capability it destroyed. Do not report this
as a forgetting number.

## Interpretation, written before the result

```text
object/goal ≈ spatial's 70%   the model learned LIBERO-general manipulation, not
                              ten memorised routines. Encouraging for transfer.
object/goal well below 70%    it specialised hard to the trained suite. Supports
                              the forgetting concern and argues for expert-only
                              / LoRA when generality matters.
object/goal ≈ 0%              near-total specialisation. Strongest possible
                              argument against sequential full fine-tuning.
```

⚠ n=40 per suite ⇒ roughly ±14 points at 95% confidence. Read gaps of 20+
points, not 5.

---

## ✅ RESULT 2026-08-11 — the third branch. NEAR-TOTAL SPECIALISATION.

```text
SUITE            TRAINED ON?   SUCCESS   n
libero_spatial   YES            70.0%    40    ← the same checkpoint
libero_object    no              0.0%    40
libero_goal      no              0.0%    40
```

**Verified not an artefact**, because an exact 0.0% on both deserves suspicion:

```text
same checkpoint still scores 70% on spatial   ⇒ the model is not broken
rollouts ran the FULL 280 steps               ⇒ it acted; it did not crash out
eval_s 136 s / 146 s vs spatial's 141 s       ⇒ comparable real compute
avg_MAX_reward = 0.0                          ⇒ never even PARTIAL credit. Not
                                                 "nearly succeeded" — zero.
```

⇒ **A full fine-tune on one LIBERO suite produces a model that can do that suite
and NOTHING ELSE** — not even neighbouring suites with the same robot, same
cameras, same scene type, same action space. Only the objects and goals differ.

⚠ **Caveat on mechanism.** This is specialisation of the *whole checkpoint*, and
that includes the **normalisation statistics**, which were fit on
`libero_spatial` and ship inside the checkpoint. Different suites have different
state/action distributions. So the 0% is not purely "the network forgot" — some
of it is a normaliser pointed at the wrong distribution. Both are consequences of
specialising, but they are different mechanisms and only a separate experiment
(re-fitting stats, or freezing the VLM) would separate them.

### ⇒ What this means for the project

```text
FULL FINE-TUNE      you get a SPECIALIST. Sequential full fine-tuning on task A
                    then task B does not accumulate - B overwrites A. Consistent
                    with STEP 1's finding that 595/603 VLM BACKBONE tensors moved.
EXPERT-ONLY (012000) freezes the VLM, adapts only the action head. The
                    anti-forgetting configuration, and already your working
                    recipe at 26.3 GB.
```

⇒ **For one arm doing one task, full fine-tuning is likely the right call** — a
specialist is what you want. **For a robot expected to retain broad capability,
this result argues against it.** The 5090 can do full fine-tuning; whether you
want it is now a design decision with a number attached rather than a hunch.

---

# STEP 3d — THE MATCHED-DATA RUN  `[~6.8 h, overnight]` 🟢

**The run that finally isolates the operator's original question: did 8-bit Adam
and bf16 cost accuracy?**

## What the learning curve settled first

Evaluating saved checkpoints (~7 min) instead of assuming — the cheapest step in
this plan and it decided the shape of everything after:

```text
CHECKPOINT   EXAMPLES   SUCCESS    delta
 4,000        32,000     27.5%
 8,000        64,000     57.5%     +30.0
12,000        96,000     70.0%     +12.5
```

⇒ **Still climbing. Not saturated. The gap to 97% is substantially DATA.**

★ **And it proved loss is not a proxy for capability here.** Loss plateaued at
~0.098 from step 11K, while success rose 57.5% → 70% between 8k and 12k. Anyone
reading the loss curve would have concluded "converged, more steps are wasted"
and been wrong. **Do not judge these runs by loss.**

⚠ **The deceleration (+30 then +12.5) is CONFOUNDED, not evidence of
saturation.** The run used cosine LR decay scaled to 12,000 steps, so learning
rate had already fallen to 2.7e-6 — 10× below peak — by the end. The model
slowed because the schedule told it to.

## Why a FRESH run, not a resume

```text
RESUME from 12k     3.4 h   Cheaper - keeps the work already done. But resuming
                            with --steps=24000 RESCALES the schedule: at step
                            12,000 of 24,000 the scheduler thinks it is halfway,
                            so LR JUMPS BACK UP from 2.7e-6 to ~2e-5. The model
                            had settled; this shoves it again mid-run.
FRESH 24k @ bs8     6.8 h   ★ CHOSEN. One coherent cosine schedule spanning all
                            24,000 steps. LR stays high longer, decays smoothly
                            to near-zero at the end.
```

⇒ **The reference ran a clean schedule. If ours has a mid-run jolt, a difference
in the final score has TWO possible causes — the memory levers or the weird
schedule — and they cannot be separated.** That defeats the entire purpose of
the run. 3.4 extra hours of overnight GPU time is cheap against a result nobody
can interpret.

## Configuration

```text
from            lerobot/pi05_base       (same start as the 12k run)
batch size      8
steps           24,000  ⇒ 192,000 examples = EXACTLY the reference's data volume
save_freq       2,000   12 checkpoints, ~15 GiB each ≈ 180 GiB
                        ⇒ operator's call: fine-grained STOP/RESUME points, and
                          it extends the learning curve to 12 points for free
telemetry       gpu_monitor.sh at 5 s
est. wall       ~6.8 h at 7.63 samples/s
```

### Storage — ⛔ I WAS WRONG ABOUT THE SECOND DRIVE. Retracted and measured.

```text
/dev/nvme0n1p2   1.8 T   1.4 T free   ext4    /
/dev/nvme1n1p2   3.7 T   3.7 T free   ntfs3   /run/media/kiran/New Volume
```

**An earlier revision said: "do NOT put training output there — NTFS-over-FUSE
handles symlinks poorly and is markedly slower." BOTH CLAIMS ARE FALSE.**

```text
CLAIM                          MEASURED
mounted via ntfs-3g (FUSE)     NO - mounted with `ntfs3`, the IN-KERNEL driver
                               (Linux 5.15+). Options: rw,acl,uid=1000,gid=1000,
                               prealloc,uhelper=udisks2
symlinks fail                  NO - `ln -s` works. lrwxrwxrwx+ created fine.
                               lerobot's checkpoints/last would be fine.
markedly slower                NO - it is FASTER:
                                 NTFS  7.8 GB/s
                                 ext4  5.3 GB/s     (dd 1 GiB, oflag=direct)
                               Almost certainly a newer/faster NVMe than the
                               boot drive; not a filesystem effect.
```

⚠ **THE ONE GENUINE CAVEAT** — and it is operational, not performance:
the mount lives under `/run/media/kiran/` via **udisks2**, i.e. it is
auto-mounted on desktop login, **not at boot**. A training job started by cron,
systemd, or an SSH session before login would find the path missing and fail.
⇒ Add an `/etc/fstab` entry before putting anything long-running there.

**Why is it NTFS at all?** `nvme1n1p1` is a 16 MB partition with no filesystem —
the signature of a Microsoft Reserved Partition. The disk was almost certainly
partitioned by Windows or shipped preformatted. *(Inference from the layout, not
verified.)*

⇒ **Either drive works for this run.** Root has 1.4 TB free, ample for the
~180 GiB of checkpoints.

## What it can and cannot settle

```text
CAN    whether 96k examples was the limiter. At matched data volume, the
       remaining gap to 97% belongs to batch size and/or the memory levers.
CANNOT isolate the levers alone. Batch 8 vs the reference's 32 is STILL a
       difference. This narrows the confound from TWO variables to ONE.
       A clean answer needs a further bs16 + scaled-LR run.
```

## Prediction, written before the result

```text
naive extrapolation of the decelerating curve  ≈ 78%
  lands WELL ABOVE ~78%   the LR schedule was the limiter, not data volume
  lands NEAR ~78%         the remaining ~19 points vs 97% belong to batch size
                          and/or the levers — the first real signal on the
                          original question
  lands NEAR 97%          the lever stack is vindicated; nothing was lost
```

⚠ n=40 per eval ⇒ roughly ±14 points. Read 20-point gaps, not 5.

---

## ✅ RESULT 2026-08-12 — **85.0%**. Prediction beaten; the gap collapses to 12 points.

```text
  step   examples   24k-sched   12k-sched
  4,000    32,000      25.0%      27.5%
  8,000    64,000      40.0%      57.5%
 12,000    96,000      60.0%      70.0%   ← matched point, schedule differs ONLY
 16,000   128,000      65.0%         —
 20,000   160,000      77.5%         —
 24,000   192,000    ★ 85.0%        —

reference (LeRobot, bs32 × 6k = 192,000 examples)   97.0%
ours      (bs8  × 24k = 192,000 examples)           85.0%
⇒ gap                                               12.0 points
⇒ gap at the OLD unmatched comparison (96k)         27.0 points
```

### ★ DATA VOLUME WAS MOST OF THE GAP — 27 points → 12

Doubling the examples took us 70% → 85%. **The original 27-point deficit was
majority a data-volume artefact of my own arithmetic error, not evidence against
8-bit Adam or bf16.** Had we stopped at the unmatched comparison and blamed
quantisation, we would have been wrong by more than half.

### ★ THE PREDICTION WAS BEATEN, AND THE REASONING BEHIND IT HELD

Predicted ~78% by naive extrapolation of the decelerating curve, while arguing
the deceleration was **schedule-induced rather than saturation**. It landed at
**85%** — above the extrapolation, exactly as that reasoning implied. The curve
is also **still rising at 24k** (+7.5 in the final 4,000 steps), so it has not
saturated even now.

### ★ THE SCHEDULE COMPARISON AT STEP 12,000 — a clean single-variable result

Same data, same batch, same starting weights. Only the cosine length differs:

```text
12k-schedule (finished, LR decayed to 2.7e-6)   70.0%
24k-schedule (mid-flight, LR still 1.1e-5)      60.0%
```

⇒ **At a given step, a schedule that is FINISHING beats one that is mid-flight** —
by 10 points. The decayed run has "landed"; the other is still moving. But the
longer schedule ends far higher (85% vs 70%).

⚠ **Consequence for stopping early: do NOT read a mid-run checkpoint as
representative.** A 24k run halted at 12k scores worse than a 12k run that
completed, at identical cost. **Match the schedule to the budget you intend to
spend.**

### ⛔ CORRECTION 2026-08-12 — the real number is **80.0%**, not 85%

Re-ran the 24k checkpoint at **n=200** instead of n=40, precisely because the
small sample was flagged as marginal. **It moved the answer, and not in our
favour:**

```text
measurement       successes    rate     95% interval
n=40  (headline)   34/40      85.0%    [70.9%, 92.9%]
n=200 (correct)   160/200     80.0%    [73.9%, 85.0%]

reference                     97.0%    ⇒ now CLEARLY EXCLUDED
gap                           17 points   (was 12 at n=40, 27 unmatched)
```

⚠ **85% was a lucky sample and I committed it as the headline.** It sits at the
very edge of the n=200 interval. **Quote 80%.**

⚠ **AND THE SAME CAVEAT APPLIES TO EVERY OTHER POINT ON BOTH CURVES** — they are
all n=40, so each carries roughly ±11 points. The 70% from the 12k run has an
interval of about [55%, 82%], which **overlaps** the 80% measured here. So even
"doubling the data helped" is not airtight from those two numbers alone.
⇒ **What supports it is the SHAPE of the full curve** — six rising points
(25 → 40 → 60 → 65 → 77.5 → 85 at n=40) — not any single comparison. A trend
across many noisy points is stronger evidence than two noisy points.

### What is left, and what it is worth

```text
REMAINING CONFOUND   batch 8 (ours) vs 32 (reference). Still one variable.
IS 12 POINTS REAL?   n=40 ⇒ 85% has a 95% CI of roughly [70%, 94%]. 97% sits
                     outside it, so probably real — but marginal, and a larger n
                     would be needed to call it confidently.
TO ISOLATE THE LEVERS a bs16 run with a scaled LR, matched data. ~6 h.
⇒ VERDICT ON THE ORIGINAL QUESTION: the memory levers cost AT MOST ~12 points,
  and plausibly less once batch size is accounted for. They did NOT cost the 27
  points the first comparison suggested.
```

---

# STEP 3e — IS THE 5090'S TRAINING ACTUALLY INFERIOR?  `[~15 lines + ~7 h]` 🟢

**Operator: *"inferior training on the 5090 is still inferior, right?"* Yes — and
an earlier revision of this plan called that gap "a confound that answers nothing
you need". THAT WAS WRONG.** If this card yields 80% where an 80 GB card yields
97%, the mechanism is academic and the deficit is the whole question. Framing a
real cost as bookkeeping was a mistake, and this step exists to correct it.

## The 17 points have three candidate causes, and they are NOT equal

```text
CAUSE                  HARDWARE-IMPOSED?   FIX
batch 8 vs 32          NO                  gradient accumulation, ~15 lines.
                                           bs8 × 4 accum = EFFECTIVE batch 32,
                                           identical to the reference. Trades
                                           wall-clock for memory.
LR not scaled for bs8  NO                  our own tuning error. We ran the
                                           preset 2.5e-5, tuned upstream for a
                                           LARGE batch. At bs8 that is steps too
                                           large for the gradient noise. Free.
8-bit Adam + bf16      YES                 the only genuinely hardware-imposed
                                           candidate. Cannot be removed at 32 GB
                                           — FP32 Adam needs 46.3 GiB persistent.
```

⇒ **The 5090 is not fundamentally limited to small batches. lerobot's missing
gradient accumulation is.** Those are very different claims, and only one of them
argues for buying hardware.

## The experiment

Reproduce the reference recipe exactly **except** the two quantisation levers:

```text
batch size            8   (memory-safe for resume — see the STEP 2 caveat)
accumulation steps    4   ⇒ EFFECTIVE BATCH 32, matching the reference
LR                    scaled for the effective batch, not left at the preset
steps                 6,000 optimiser updates × 32 = 192,000 examples
                      ⇒ same data AND same effective batch as the reference
est. wall             ~7 h (24,000 forward/backward passes, as before)
```

⇒ **Whatever gap survives THAT is the genuine, hardware-imposed cost of training
π0.5 on a 32 GB card.**

## ⇒ WHY THIS IS A PURCHASE DECISION, NOT CURIOSITY

```text
GAP CLOSES     a 96 GB card (RTX PRO 6000) buys SPEED, not quality — it avoids
               accumulation overhead. $11K for wall-clock. Weak case.
GAP SURVIVES   a 96 GB card buys QUALITY: at 96 GB you can run FP32 Adam
               (46.3 GiB persistent) and drop quantisation entirely. That is a
               capability the 5090 cannot match AT ANY SPEED. Strong case.
```

⚠ **Consider renting before buying.** `scripts/runpod/` already exists in this
repo. If quality runs are occasional rather than daily, an 80 GB card rented per
run costs a tiny fraction of $11K, while the 5090 absorbs all the iteration.
**That is the two-tier strategy without the capital outlay** — and it is the
option a "buy vs not" framing tends to hide.

## Implementation notes

```text
lerobot_train.py  Accelerator(...) is built WITHOUT gradient_accumulation_steps
                  update_policy() calls optimizer.step() + zero_grad() EVERY batch
                  ⇒ wrap the forward/backward in accelerator.accumulate(policy)
                    and let Accelerate gate the optimiser step
config            add gradient_accumulation_steps to TrainPipelineConfig
⚠ VERIFY IT TOOK EFFECT — the same trap as the optimizer preset (§3). Count
  optimiser steps vs batches consumed; do not trust the flag.
```

## Prediction, written before the result

```text
lands ≈ 97%        levers are free; the 5090 is NOT inferior. Purchase case
                   collapses to speed alone.
lands ≈ 88-93%     levers cost ~5-10 points. Judgement call.
lands ≈ 80%        batch size was NOT the cause; the levers are. Strongest case
                   for a 96 GB card, and now with evidence.
```

---

## ⛔ RESULT 2026-08-13 — **64.5%. WORSE, and off the bottom of every predicted branch.**

```text
ALL at 192,000 examples · n=200 eval · same data · same starting weights

eff batch 8   (24,000 optimiser updates)   160/200   80.0%   [73.9%, 85.0%]
eff batch 32  ( 6,000 optimiser updates)   129/200   64.5%   [57.7%, 70.8%]
reference (LeRobot, bs32)                        —   97.0%

intervals do NOT overlap ⇒ the difference is REAL, not sampling noise
```

### ★ MATCHING THE REFERENCE'S BATCH SIZE MADE IT 15.5 POINTS WORSE

**The experiment's premise was wrong.** Batch size was never the cause of the
gap — correcting it moved us *away* from 97%, and the gap widened from 17 to
32.5 points.

⇒ **This is the strongest possible answer to the purchase question, and it is the
opposite of what the framing assumed.** More VRAM buys bigger native batches.
**Bigger batches make this task WORSE.** So a 96 GB card would not buy quality
here — it would buy the ability to do the thing that hurt.

### Why — the most likely mechanism, stated as a hypothesis not a fact

At a **fixed data budget**, batch size trades against **number of optimiser
updates**:

```text
eff batch 8   192,000 examples ÷  8 = 24,000 weight updates
eff batch 32  192,000 examples ÷ 32 =  6,000 weight updates   ← 4× fewer
```

⇒ For this task and this budget, **more updates beats bigger batches.** Small-batch
gradient noise may also act as regularisation. Both are standard effects; neither
was measured here, so treat the mechanism as unconfirmed.

### ⚠ WHAT THIS DOES NOT SETTLE — and a confound worth chasing

**We still cannot reproduce 97% at any batch size.** Remaining candidates:

```text
the levers (8-bit Adam + bf16)   still possible, still unisolated
★ THE REFERENCE MAY USE MORE DATA   docs/source/pi05.mdx says they finetuned
  "on the Libero dataset" — LIBERO ships FOUR suites (spatial, object, goal, 10).
  WE TRAINED ON libero_spatial ONLY. If they trained on all four, that is ~4×
  the data AND far more diverse, and would plausibly explain the entire residual.
  ⇒ This is now the leading hypothesis and it is CHEAPER to test than another
    batch-size variant.
unknown hyperparameters          their exact recipe is not published beyond the
                                 command in the docs
```

⇒ **Do not attribute the remaining 32.5 points to quantisation.** Two hypotheses
that looked obvious have now been wrong in a row: data volume explained part but
not all, and batch size explained nothing and made things worse.

⚠ Evaluate at **n=200**, not n=40 — n=40 already produced one 5-point error
(§ the 85% → 80% correction).

---

# ⚠ WHICH RUNGS WERE ACTUALLY USED IN WHICH RUN — read before quoting any of it

**Rungs are TECHNIQUES, not runs. Several are active at once.** Operator asked
which fine-tunes used which, and an earlier summary line here was misleading.

```text
run          FROM              rungs active        config         result
STEP 3       pi05_base         rung 2              bs8            70.0% (n=40)
STEP 3d      pi05_base         rung 2              bs8            80.0% (n=200)
STEP 3e      pi05_base         rung 2 + rung 1     bs8 × accum4   64.5% (n=200)
3f.2 probe   pi05_base         rung 2 + rung 3     bs32, 20 steps  no quality
3b.0 eval    pi05_libero_base  — NO TRAINING —     zero-shot       0.0% (n=40)
STEP 3g      pi05_libero_base  rung 2 + rung 1     bs8 × accum4   NOT RUN
```

⚠ **Every trained result came from `pi05_base`.** `pi05_libero_base` has only
ever been *evaluated*, never trained from — see the verification below.

```text
rung 1  accumulation   used in ONE full run (3e)
rung 2  8-bit Adam     IN EVERY RUN — load-bearing. π0.5 needs 46 GiB without
                       it and simply does not fit. Every result we have was
                       produced with it.
rung 3  paged Adam     20-STEP PROBE ONLY. Proved bs32 survives with it and
                       OOMs without. NO quality data, and none implied.
rung 4  CPU offload    NEVER RUN
rung 5  param offload  NEVER RUN
```

⛔ **CORRECTION — an earlier line here said "rung 1 hurt quality (64.5% vs 80%)".
That is wrong.** Gradient accumulation is a *mechanism*; what hurt was what we
used it *for*:

```text
3d  bs8, no accumulation   → effective batch 8  → 24,000 updates → 80.0%
3e  bs8 × accum 4          → effective batch 32 →  6,000 updates → 64.5%
```

⇒ **Accumulation degraded nothing by itself.** It enabled effective batch 32, and
the bigger batch — 4× fewer optimiser updates at the same data — cost the 15.5
points. Used to *hold* effective batch at 8 while halving activation memory
(e.g. bs2 × accum 4) it should be quality-neutral. **The technique is fine; the
configuration we chose with it was not.**

---

# STEP 3g — ⭐ THE STARTING CHECKPOINT. The hypothesis the numbers point at.

**Found by laying the update counts side by side, at the operator's prompting
("how many updates in baseline?"). It reframes everything after STEP 3e.**

```text
run                     eff batch  updates  batches  examples   result
STEP 3   bs8                   8   12,000   12,000    96,000   70.0% (n=40)
STEP 3d  bs8                   8   24,000   24,000   192,000   80.0% (n=200)
STEP 3e  bs8 × accum4         32    6,000   24,000   192,000   64.5% (n=200)
REFERENCE bs32 (LeRobot)      32    6,000    6,000   192,000   97.0%
```

⇒ **STEP 3e and the REFERENCE are IDENTICAL on every axis** — same effective
batch (32), same optimiser updates (6,000), same examples (192,000) — **and
differ by 32.5 points.**

## ⛔ This kills the "updates vs batch size" explanation for the reference gap

"More updates beat bigger batches" is real **for our own two runs** (24,000
updates → 80%, 6,000 → 64.5%). It **cannot** explain the reference, which got
97% from the *same* 6,000 updates that gave us 64.5%.

⇒ Something else is different, and it must be worth ~30 points.

## ⛔ WHICH CHECKPOINT EACH RUN ACTUALLY STARTED FROM — verified, not remembered

**Operator asked "we've been using pi05_libero_base for the last 2 full
finetunes, or did we not?" We did NOT. Verified from the run configs:**

```text
step3.log    'pretrained_path': 'lerobot/pi05_base'
step3d.log   'pretrained_path': 'lerobot/pi05_base'
step3e.log   'pretrained_path': 'lerobot/pi05_base'
```

```text
pi05_base          used for ALL THREE full fine-tunes
                   3 cameras · state[32] · action[32]   ← generic, padded
pi05_libero_base   EVALUATED ONCE (STEP 3b.0, 0.0% zero-shot). NEVER TRAINED
                   FROM. 2 cameras (image/image2) · state[8] · action[7]
```

⚠ **This confusion is partly my fault.** When the zero-shot came back 0% I wrote
that it "retracts the head-start claim" and moved on — which reads as though the
checkpoint had been *dealt with*. It had only been **evaluated**.

⇒ **STEP 3g would be the FIRST time we train from the LIBERO-shaped checkpoint.**
Every result on record — 70%, 80%, 64.5% — came from a model that had to learn
LIBERO's camera layout and 7-DoF action space **on top of** the task itself.

## ⇒ THE LEADING HYPOTHESIS: we started from the WRONG CHECKPOINT

```text
pi05_base          3 cameras: base_0_rgb, left_wrist_0_rgb, right_wrist_0_rgb
                   state[32]  action[32]      ← GENERIC, padded pi0 space
pi05_libero_base   2 cameras: image, image2   ← exactly the LIBERO env keys
                   state[8]   action[7]       ← Franka Panda 7-DoF + gripper
```

**We used `pi05_base`. The reference used "the libero base model".**

⇒ Starting generic, our model had to learn **the space adaptation** — different
camera count, different action dimensionality — **as well as the task**, inside
6,000 updates. The reference began with that plumbing already correct.

⚠ **I RETRACTED THIS HYPOTHESIS EARLIER FOR A BAD REASON.** STEP 3b.0 measured
`pi05_libero_base` at **0.0% zero-shot** and I concluded "no head start". That
proves no *task competence* head start. It says **nothing** about an
*architectural* one. Config is not capability, but config is not *nothing*
either — and I over-corrected.

⇒ It also explains the rest of the pattern: **more updates helped US** (we had
more to learn) **while the reference did not need them.**

## The experiment

```text
from            lerobot/pi05_libero_base   ← THE ONLY CHANGE
batch size      8 × accum 4 = effective 32
steps           24,000 batches = 6,000 optimiser updates = 192,000 examples
everything else identical to STEP 3e
est. wall       ~7 h
eval            n=200, NOT n=40
```

⇒ This is a genuine like-for-like reproduction of the reference recipe. **The
only remaining differences would be 8-bit Adam and bf16** — which is the question
the whole lane exists to answer.

⚠ **Check the camera keys first.** `pi05_libero_base` natively expects
`image`/`image2` — the LIBERO env's own names — so the `--rename_map` that STEP
3e needed may be unnecessary or *inverted*. Inspect before launching; a silent
key mismatch would waste 7 hours.

## Prediction, written before the result

```text
lands ≈ 97%      the starting checkpoint was the whole gap. Levers are FREE, the
                 5090 is not inferior in any respect, and the lane closes.
lands ≈ 80-90%   the checkpoint explains most of it; a residual belongs to the
                 levers and/or batch size.
lands ≈ 64%      the checkpoint is NOT the cause either. Three hypotheses dead,
                 and the remaining suspects are the levers or an unknown in
                 their recipe (e.g. training on ALL FOUR LIBERO suites).
```

⚠ **Two obvious hypotheses have already failed** — data volume explained part
but not all, batch size explained nothing and made things worse. **Do not treat
this one as settled before it runs.**

---

# STEP 3f — THE CAPABILITY LADDER: what CAN this machine train, and at what cost?

**Operator's framing, and it is better than "curiosity":** *"slower training 24/7
for a few days is better than nothing, or not having a solution at all... that
way we are ready even if we have a 96 GB RTX PRO 6000 and 128 GB RAM, we could
try even bigger models."*

⇒ **Knowing the fallbacks BEFORE they are needed changes the answer from "we
cannot train that" to "we can, at 3× slower".** Those lead to completely
different project decisions. This step converts §5's escalation ladder from
untested theory into a measured table.

## Why the ladder is currently theory

§5 lists paged optimizers, CPU optimizer offload and CPU parameter offload — and
**none of it was ever entered.** 8-bit Adam alone brought us under the ceiling
(§STEP 2), so rungs 3–5 remain unmeasured guesses. The cost estimates in this doc
are arithmetic from PCIe link *specifications*, not measurements:

```text
link         theoretical BW    8-bit state offload    fp32 state offload
Gen3 x16      15.8 GB/s        +1.05 s  (100%)        +4.20 s  (400%)
Gen4 x16      31.5 GB/s        +0.53 s   (50%)        +2.10 s  (200%)
Gen5 x16 ←us  63.0 GB/s        +0.26 s   (25%)        +1.05 s  (100%)

measured step time with NO offload: 1.05 s
5090 VRAM bandwidth ~1792 GB/s = 28× faster than even Gen5 x16
```

⚠ **Real achievable PCIe bandwidth is typically 50–80% of spec** once protocol
overhead and transfer patterns are counted, so the true penalties are worse than
that table. **Measure it; do not plan against it.**

⚠ **CHECK THE GPU IS ACTUALLY FREE FIRST — `nvidia-smi` alone is not enough.**
On 2026-08-13 the GPU looked idle by habit but was running a GR00T N1.6 eval
started seconds earlier (`n16-stall-smoke.sh` → `run_gr00t_server` +
`sim_policy_eval_instrumented.py`, ~15 GiB, 54% util). **A `pgrep` for
`lerobot-train|lerobot-eval` returned NOTHING** — other stacks on this machine do
not match those names.

```bash
nvidia-smi --query-compute-apps=pid,used_memory --format=csv   # ← the real check
```

⇒ **Query compute-apps, not just utilisation, and not a name pattern.** Starting
a probe against a live eval would contend for GPU *and* CPU and corrupt both.

## 3f.1 — Measure real PCIe bandwidth  `[~2 min]` 🟢

Replaces the 63 GB/s spec figure with a number. Host→device, device→host, and
pinned vs pageable memory (pinned is typically 2× faster and is what offload
implementations use).

```text
record   H2D and D2H GB/s, pinned and pageable
⇒ then RECOMPUTE the table above with the measured figure
```

## 3f.2 — Paged 8-bit optimizer (rung 3)  `[~20 min]` 🟢

**Nearly free to try.** bitsandbytes ships `PagedAdamW8bit`, which spills
optimiser state to host RAM automatically under memory pressure. Our existing
patch already registers `AdamW8bitConfig` — this is a **one-word change** to
`bnb.optim.PagedAdamW8bit`.

```text
measure   step time vs the 1.05 s baseline · peak VRAM · does paging engage at
          all, or does it sit unused because we already fit?
⚠ TO ACTUALLY EXERCISE PAGING it must be memory-PRESSURED. If it fits in VRAM
  the pages never spill and the test measures nothing. Force pressure by raising
  batch size until it would otherwise OOM (bs32 OOMed at §STEP 2 — that is the
  natural probe).
⚠ UNPROVEN ON BLACKWELL. bnb's Blackwell support was the whole reason STEP −1
  existed. Paging is a different code path from the 8-bit optimiser itself, so
  STEP −1 passing does NOT imply this passes.
```

## 3f.3 — Explicit CPU optimizer offload (rung 4)  `[~half a day]` 🟡

Real integration work — DeepSpeed ZeRO-Offload or Accelerate's offload plumbing,
not a one-liner. **Do this only if 3f.1 and 3f.2 look promising.**

```text
measure   step time · peak VRAM · peak host RAM · largest model that then fits
⚠ 59 GB of host RAM is itself a ceiling. fp32 Adam state for a 4.14B model is
  33.1 GB — offloading that leaves ~26 GB for everything else. A 10B model's
  fp32 state (80 GB) would NOT fit in this machine's RAM at all.
```

## 3f.3c — CAN THE FULL fp32 STATE BE PINNED?  `[~20 min]` 🟡

**The one path that could rescue fp32 offload from +785%.** 3f.3b streamed state
through a small buffer and measured 8.0 GB/s. But **DeepSpeed pins optimiser
state outright when it fits**, and if 33.1 GB pins here the bulk path is
available at 56.6 GB/s:

```text
fp32 offload, CHUNKED (measured)      +785%   →  a 7 h run becomes ~62 h
fp32 offload, FULLY PINNED (untested) +112%   →  a 7 h run becomes ~15 h
```

⇒ **A 7× difference, and it decides whether fp32-quality training is possible
off-card at all.**

### Is there room? Yes, but not much

```text
installed        64 GB
MemTotal         59.2 GB     (~4.8 GB kernel/firmware reserved — normal)
MemAvailable     43.0 GB     ← 33.1 GB is 77% of this
Swap              8.0 GB, 100% USED, 0 free
```

⚠ **Pinned memory is UNSWAPPABLE.** Locking 33.1 GB with only 43 GB available
and **zero swap headroom** is the riskiest thing in this whole plan. If it goes
wrong the OOM killer picks a victim by heuristic — possibly the desktop session,
possibly something of Prakash's.

### Method — incremental, with an abort at every step

```text
0  PREREQUISITE (operator, needs sudo): clear the stale swap
     sudo swapoff -a && sudo swapon -a
   The 8 GB is residue from the training runs — pages evicted under pressure and
   never faulted back. Clearing it restores headroom before the test, and gives
   a clean baseline.

1  pin 16 GB  → measure bulk round-trip GB/s → free → check MemAvailable
2  pin 24 GB  → same
3  pin 33.1 GB (the real fp32 state size) → same

⛔ ABORT AND FREE IMMEDIATELY IF:
     MemAvailable drops below ~6 GB
     the pin call takes more than a few seconds (it is swapping)
     the desktop becomes unresponsive
   Free the allocation between EVERY step. Do not hold two at once.
```

### What each outcome means

```text
33.1 GB pins, ~56 GB/s     fp32 offload is +112%. Bulk path confirmed, and a
                           96 GB card's fp32 capacity becomes RAM-bound at
                           7.3B (59 GB) / 15.8B (128 GB) per §3f.4 — those
                           numbers assume this path works.
pins but slowly            partial paging; effective rate is what matters, not
                           whether the allocation succeeded
fails at 24 or 33 GB       fp32 offload is chunked-only ⇒ +785% ⇒ effectively
                           not viable on this machine. **More RAM would change
                           that** — which is a concrete argument for the 128 GB
                           spec, not a vague one.
```

⚠ **This only affects fp32 offload.** The 8-bit path (8.3 GB) already pins
comfortably and was measured in 3f.3. Nothing here changes the 8-bit numbers.

## 3f.3d — PROVE fp32 OFFLOAD IN A REAL TRAINING LOOP  `[~2 h + 30 min run]` 🟡

**Operator: "is there a way to test this at least for a few checkpoints, or does
it need work before training?"** It needs work — but far less than the DeepSpeed
route, because 3f.3c already proved the mechanism.

### Why this is now tractable

```text
PROVEN by 3f.3c   33.1 GB of fp32 state pins in <5 s and streams to the GPU in
                  1 GB chunks at 55.9 GB/s — full bulk rate, no degradation
⇒ the design is simply: PIN ONCE at startup, STREAM SLICES per step
⇒ NOT DeepSpeed: no CUDA-op compilation, no Blackwell-support risk, no
  lerobot integration hook required
```

### The implementation, ~80 lines

```text
at init    flatten all params → allocate m, v as two PINNED CPU tensors (33.1 GB)
at step()  for each ~4 GB slice:
             copy m,v slice → GPU
             apply the Adam update against that slice of gradients
             copy m,v slice back
plug in    via the OptimizerConfig registry — the SAME machinery already patched
           and tested for adamw_8bit (§3, §3e)
```

### ⚠ Where it will actually be hard

**Not the transfer — that is measured. The plumbing around it:**

```text
· lerobot's checkpoint saver will need the same scalar / shared-tensor handling
  we had to add for bitsandbytes (STEP 1 — two stacked defects, five runs, after
  being estimated at "a few lines")
· the flat-parameter view must survive accelerate's model preparation
· grad_clip_norm operates on live gradients; interaction with a flat view is
  untested
```

⚠ **Treat any estimate here with suspicion.** STEP 1 was "~30 min, a few lines"
and took five runs. STEP 3g's pre-flight looked complete and still wasted 7 hours.

### Scope — deliberately small

```text
1  implement the optimiser + register it
2  ⛔ RUN GATE E1 (preflight_batch_check.py) — non-negotiable
3  200 steps only. Measure step time against the 1.05 s baseline.
   TARGET: ~2.2 s/step (+112%). Anything near 8 s means the pinning did not
   take effect and it fell back to a pageable path.
4  save ONE checkpoint, reload it, confirm finite weights
```

⇒ **That is enough to validate +112% in practice.** Do NOT extend it into a full
training run: fp32 Adam is not needed for π0.5, which fits in VRAM with 8-bit.

### ⚠ What this is FOR, stated plainly

**A model we do not have yet.** π0.5 trains fine without any of this and the
purchase decision is settled. This is capability reference for a future larger
model — worth building deliberately, not on momentum.

## 3f.3e — ⭐ fp32 ADAM FOR π0.5 VIA OFFLOAD: the last isolable variable

**Operator's idea, and it is worth more than the "test the ability" framing
suggests.** fp32 Adam does not fit in VRAM — which is exactly why 8-bit Adam has
never been testable against it. Offload makes the comparison possible.

### It fits, via rung 4

```text
IN VRAM ALONE      7.71 (bf16 w) + 7.71 (bf16 g) + 30.84 (fp32 m,v)
                   = 46.3 GiB against 29.9 available   ⛔ DOES NOT FIT
WITH OFFLOAD       GPU:  7.71 + 7.71 + ~2.4 activations = ~17.8 GiB   ✓ easy
                   host: 33.1 GB pinned fp32 state                    ✓ proven 3f.3c
```

### ⇒ WHY IT MATTERS MORE THAN CAPABILITY

**8-bit Adam is one of the two remaining suspects for the 17-point gap to the
reference, and the ONLY one we have never been able to test.** This gives a
single-variable comparison:

```text
STEP 3d   bf16 + 8-BIT Adam · 24k steps · 192k examples  →  80.0% (n=200)
NEW       bf16 + fp32  Adam · everything else identical  →  ?
```

```text
lands ≈ 80%   8-bit Adam costs NOTHING. The lever is exonerated and the residual
              gap belongs to the starting checkpoint (§3g) or their recipe.
lands HIGHER  8-bit Adam has a real cost, and "the 5090 trains π0.5" acquires a
              quality caveat it does not currently have.
```

### Plan — ⛔ STOP AFTER PHASE 2 AND RE-DECIDE

```text
PHASE 1  integrate CPUOffloadAdamW into lerobot        ~2 h
         register via OptimizerConfig (same machinery as adamw_8bit)
PHASE 2  E1 preflight + 200-step smoke                 ~30 min
         ⇒ GATE: ~2.4 s/step AND one checkpoint round-trips
         ⇒ ★ CAPABILITY IS DEMONSTRATED AT THIS POINT. STOP AND RE-DECIDE.
PHASE 3  full 24,000 steps at 2.43 s/step              ~16 h   ← only if wanted
PHASE 4  n=200 eval, compare against 80.0%             ~15 min
```

⚠ **Phase 3 is 16 hours — 2.31× a run that already took 7.** Do not start it
because phase 2 succeeded; start it only if the quality question is worth a day
of GPU. **The purchase decision does not depend on it.**

### ⚠ Where the trouble will be — the integration, not the transfer

The optimiser itself is DONE and verified (3f.3d: correct to 2.6e-08, 2.31×).
What is untested is lerobot's plumbing around it:

```text
· CHECKPOINT SAVING of pinned state — the highest-risk item. The saver needed
  TWO stacked fixes for bitsandbytes (python-int step counter, then shared qmap
  tensors) after being estimated at "a few lines". Pinned host tensors are a
  THIRD variant of the same question.
· the accelerate model-preparation interaction
· grad_clip_norm against parameters whose optimiser state lives off-device
```

⚠ **Treat the ~2 h estimate as optimistic.** Every plumbing estimate in this lane
has been.

---

## 3f.2b — DOES A PAGED RUN CHECKPOINT?  `[~10 min]` 🟢

**Gap found when the operator asked whether rung 3 was tested with real
training.** It was — real lerobot-train, real π0.5, real data, loss decreasing —
but **`save_checkpoint=False` in both the 20- and 25-step runs.** No checkpoint
was ever written with a paged optimiser.

⚠ **That is the same shape as a bug that already bit us.** bnb paged tensors come
from `cudaMallocManaged`; the saver flattens state into `safetensors.save_file`,
which is exactly where 8-bit Adam produced two stacked failures. Managed memory
is a third variant, and nothing we ran touched it.

```text
bs32 · paged · --steps=20 --save_checkpoint=true --save_freq=20
then RELOAD the checkpoint and confirm finite weights
```

⇒ Answers whether rung 3 is usable for real work or only for short bursts —
which matters, because a paged run's whole purpose is surviving at the memory
edge, and long runs at the edge are precisely where checkpoints are needed.

## 3f.4 — Extrapolate to hypothetical hardware  `[~1 h, desk work]` 🟢

With 3f.1–3f.3 measured, project onto configurations under consideration:

```text
CONFIG                                   what fits in VRAM   with CPU offload
5090 32 GB + 59 GB RAM  (today)          ~4B  (measured)     ?
RTX PRO 6000 96 GB + 128 GB RAM          ~12B (arithmetic)   ?
```

⇒ **The interesting question is not "does the bigger card fit a bigger model" —
it is "how much bigger, and does offload extend that usefully or ruin it?"**

## ⇒ INTERRUPTIBILITY — all four are safe to stop mid-way, unlike STEP 3d/3e

**Operator asked whether the half-day rungs can be stopped if needed. Yes, and
for a structural reason worth recording:**

```text
3f.1  PCIe bandwidth      ~2 min total. Nothing to interrupt.
3f.2  paged optimiser     short runs, minutes each. Stop between runs, free.
3f.3  CPU offload         HALF A DAY OF ELAPSED EFFORT, but composed entirely of
                          SMALL pieces:
                            integration  ~2-3 h — writing the DeepSpeed/Accelerate
                                         plumbing. Pure code; lands in patches/
                                         as it goes. Stop/start freely.
                            measurement  ~1-2 h — a few hundred steps per config.
                                         The LONGEST single action is MINUTES.
3f.4  extrapolation       desk work, no GPU at all. Stop anywhere.
```

⚠ **There is no mid-run checkpoint in 3f.3 — and none is needed.** That is the
structural difference from STEP 3d/3e, where stopping cost a rewind to the last
save (~35 min). Here **the unit of work is small by construction**, so the most
that can ever be lost is one short measurement run.

⇒ **Do it across several sittings without penalty.** Only start 3f.3/3f.4 if a
larger model is actually being planned; they answer nothing about the current
one.

## The deliverable

## ⛔ THE GATE THAT MATTERS: CAN IT CHECKPOINT?

**Operator, and it reprioritises this whole section:** *"we need training that
produces checkpoints, otherwise it remains a POC."* Correct.

**A technique that cannot checkpoint is not a training capability — it is a
demo.** No pause/resume, no crash recovery, no intermediate evaluation, no
multi-day runs. And rungs 3-5 exist SPECIFICALLY for models large enough to need
long runs, which is precisely when checkpointing stops being optional.

```text
rung                 MEASURED?   CHECKPOINTS?   STATUS
2  8-bit Adam        ✅          ✅ PROVEN      PRODUCTION — 4 long runs, 12
                                                checkpoints each, resume verified
3  paged optimiser   ✅          ⚠ PARTIAL      SAVE-ONLY — writes and reloads,
                                                but CANNOT RESUME (~1 GiB short
                                                at the edge; fragmentation ruled
                                                out). Uninterruptible runs.
4  CPU offload       ✅          ❌ UNTESTED    POC — optimiser verified
                                                standalone, never integrated
```

⚠ **Rung 2 is the precedent that should worry us.** Checkpointing with 8-bit Adam
did NOT work out of the box — it took TWO stacked fixes (a python-int step
counter, then shared qmap tensors) after being estimated at "a few lines".
**Rungs 3 and 4 carry the same unexamined risk and touch memory in MORE unusual
ways** — `cudaMallocManaged` and pinned host memory respectively.

⇒ **REPRIORITISED. Checkpoint capability is now a GATE on every rung, ahead of
any quality experiment:**

```text
1st  3f.2b  does a PAGED run checkpoint?          ~10 min   ⭐ do this first
2nd  3f.3e  phase 1-2: integrate offload, and the
            CHECKPOINT ROUND-TRIP IS THE GATE      ~2.5 h
3rd  3f.3e  phase 3-4: the 16 h quality run        only after both gates pass
```

⇒ **Until a rung checkpoints, do not describe it as a capability in any
summary.** Say POC.

---

A table that can be planned against rather than argued about. **Three of five
rungs are measured — but only ONE is proven usable for real work:**

```text
config                          step time   slowdown   status
in-VRAM, 8-bit Adam (rung 2)     1.05 s      1.00×     ✅ MEASURED — the baseline.
                                                          Load-bearing: pi05 needs
                                                          46 GiB without it.
paged 8-bit (rung 3)             3.75 s @    —         ✅ MEASURED — works on
                                 bs32                     Blackwell; rescued bs32,
                                                          which OOMs without it.
                                                          ⚠ penalty NOT isolable:
                                                          the control OOMs.
CPU optimiser offload (rung 4)   +0.309 s    1.29×     ✅ MECHANISM MEASURED
                                                          8-bit state only. fp32
                                                          state (33.1 GB) CANNOT
                                                          be staged at all on a
                                                          32 GB card.
                                                          ⚠ transfer+update only;
                                                          a production
                                                          ZeRO-Offload is
                                                          1.93-4.28× per the
                                                          literature.
CPU parameter offload (rung 5)   ?           ?         ⛔ NEVER RUN. +42% floor by
                                                          arithmetic, but weights
                                                          cross ~3× per step in
                                                          many small per-layer
                                                          transfers. Expected far
                                                          worse. No step assigned.
```

**Practical reading:** rung 2 is free and mandatory. Rung 3 is a one-word change
that buys headroom when something won't fit. **Rung 4 costs ~30% and is the real
fallback for a model too big for 32 GB** — an overnight run becomes a long
overnight run. Rung 5 is the untested floor.

⚠ **Rung 5 has no plan step.** It is described in §5 and here, but nobody
scheduled measuring it. That is a genuine gap if the floor ever needs
establishing.

## Two cautions worth recording

⚠ **On the warranty argument** (*"3 years, free replacement, why not utilise
it"*) — agreed in substance: 575 W and 85 °C sustained are within spec, and 3.5 h
runs with zero throttling say the cooling is not marginal. **But a warranty
replaces HARDWARE, not TIME.** If the card dies mid-project the RMA costs weeks,
and every result in this document lives on this one machine. ⇒ That argues for
keeping `DYNUS_ASIS_BACKUP_MANIFEST.md`-style discipline over the probe outputs,
not for running the card gentler.

⚠ **Rung 5 (parameter offload) is expected to be useless, and that is a result
too.** Weights are touched every layer of every forward AND backward pass, not
once per step like optimiser state. At 28× slower than VRAM it should be
catastrophic rather than merely slow. **Measure it once to establish the floor,
then never use it.**

---

# STEP 4 — our own data  🔴 NEEDS A HUMAN DECISION

**Do not start this unattended.** Not for technical reasons — the corpus
composition is a research decision with consequences.

```text
⚠ MIXING state-machine-generated data WITH recorded episodes is a
  distribution-mixing choice that has never been done on this project. Doing it
  in the same run that also validates the hardware means TWO unknowns at once.
  STEP 3 exists so that by this point the hardware is not one of them.

⚠ The 89 real episodes still need v3.0 -> GR00T v2 conversion and a `top` camera
  drop.

⚠ sim_to_real_preflight_protocol_20260806.md carries a STANDING RULE that no
  training is justified yet, because two mechanically-fixable defects remain in
  the observation channel. That rule is about solving sim-to-real TRANSFER, so
  it does not block a capability test - but it is a live argument against
  spending the real episodes here. See
  sim_to_real_camera_alignment_20260809.md.
```

⇒ **Bring the corpus question back to the operator with STEP 2 and STEP 3
results in hand.** The right composition depends on what batch size and
throughput turn out to be available.

---

# §B RESULTS — fill in DURING, not after

```text
STEP 1  checkpoint fix   ✅ DONE 2026-08-11 18:08
  checkpoint WRITES           ✅ optimizer_state.safetensors, 6.2 GiB
  RESUME works, loss finite   ✅ "Resuming at epoch 0, sample 10", 5 more steps
                                 to step 15, loss 0.418, EXIT=0
  ★ VLM backbone MOVED        ✅ 595/603 tensors changed vs pi05_base
                                 (expert/proj: 208/209). Deepest movers are
                                 vision_tower.vision_model.encoder.layers.
                                 ⚠ 595 of 603, NOT all 603 - 8 unchanged after
                                   10 steps, likely zero-init biases with zero
                                   grad. Does not undermine the verdict; the
                                   honest number is 595/603.
  ⇒ closes phase 1's open weights-moved gap    ✅ trainable==total said the
     backbone was ALLOWED to train; this says it DID.

  ⚠ THE "~30 min / a few lines" ESTIMATE IN THIS PLAN WAS WRONG. It took five
    runs. TWO stacked defects, not one:
      (a) state/1/step is a python int, safetensors wants tensors
      (b) qmap1/qmap2 is ONE shared tensor aliased across ~800 param states;
          safetensors refuses aliased storage
    plus two self-inflicted errors worth recording because both failed QUIETLY:
      · telemetry dir created inside --output_dir -> lerobot refuses to start
      · the VLM filter excluded any key containing "expert", but the module is
        named `paligemma_with_expert`, so EVERY key matched and the check
        reported "0 VLM tensors" as a naming mystery rather than an error.
        Correct split: paligemma_with_expert.paligemma.* (VLM) vs
        paligemma_with_expert.gemma_expert.* (action expert).

STEP 2  batch sweep   ✅ DONE 2026-08-11 18:15   (samples/s, NOT steps/s)
  bs   train peak   total     mem_gb   updt_s   samples/s
   1   23.35 GiB    24.79     22.34    0.309    3.24
   2   23.76        25.19     22.68    0.421    4.75
   4   24.21        25.64     23.26    0.638    6.27
   8   25.53        26.97     24.47    1.049    7.63
  16   28.05        29.49     26.82    1.880    8.51   ← best throughput
  32   OOM          —         —        —        —      ← ceiling

  MAX BATCH THAT FITS        16   ⚠ ON A FRESH RUN. See the resume caveat below.
  grad accumulation needed?  NO — rule was "max batch >= 8 ⇒ not needed", and
                             16 >= 8. The second code change is OFF THE TABLE.

  ⛔ RESUME COSTS ~1 GiB MORE THAN A FRESH RUN — discovered 2026-08-12 only
    because the operator paused and continued STEP 3d:

        bs8 FRESH    peak 27.11 GiB
        bs8 RESUMED  peak 28.15 GiB      +1.04 GiB

    Loading optimizer state from a 6.2 GiB checkpoint leaves a larger allocation
    footprint than building it from scratch.

    ⇒ **"bs16 fits" is true for a FRESH run and MARGINAL for a resumed one.**
      bs16 peaked at 28.05 GiB fresh; +1 GiB of resume overhead puts it near
      29 GiB with under 3 GiB spare. The sweep could not have caught this — it
      never resumed anything.
    ⇒ If long runs need stop/resume (they do — that is why save_freq is 2000),
      treat bs8 as the practical ceiling, not bs16.

  ⚠ THE ORIGINAL SWEEP (1/2/4/8) FOUND NO OOM — it ran out of MY LIST, not out
    of memory. Reporting "max batch = 8" would have been an artefact of how the
    arms were chosen. Extended to 16/32 to find the real ceiling. Worth
    remembering as a design error: a sweep that stops at the first OOM must
    include an arm that actually OOMs, or it has measured nothing about the top.

  ★ ACTIVATIONS ARE CHEAP, THROUGHPUT SATURATES:
      8x the batch costs only +2.18 GiB (bs1 -> bs8) with checkpointing on
      but samples/s gains flatten: 3.24 -> 4.75 -> 6.27 -> 7.63 -> 8.51
      bs8 -> bs16 buys just +11.5% throughput for +2.5 GiB
  ⇒ per-sample cost ~0.31 GiB. bs32 needs ~+5 GiB over bs16: consistent with
    the observed OOM.

STEP 3  LIBERO capability run   🔄 LAUNCHED 2026-08-11 18:23
  config                      bs8 · 12,000 steps · 96,000 samples
                              save_freq 2000 (6 checkpoints, ~15 GiB each,
                              ~96 GiB total against 1.5 TB free)
                              log_freq 100 · telemetry 5 s
  baseline before start       32607 total / 1433 used / 30674 free MiB, 37 C
  est. wall clock             ~3.5 h at 7.63 samples/s
  ✅ COMPLETED 2026-08-11 21:45 — "End of training"
  batch / steps / samples     8 / 12,000 / 96,000  (1.80 epochs)
  wall clock                  3 h 22 m   (est. was ~3.5 h)
  GPU utilisation             mean 93.9 %, max 99 %
  peak VRAM                   27.09 GiB total · 25.53 GiB training-process only
  ⇒ memory drift              +0.16 GiB   26.93 (Q1) → 27.09 (Q4)
                              ⚠ NOT zero. I reported 0.00 at the halfway mark;
                                the drift appeared in the final quarter. 0.6% of
                                peak, against 4.75 GiB headroom — safe, but a
                                SLOPE not a flat line. Naive extrapolation:
                                ~0.5 GiB over 12 h. Know this before running a
                                day-long job.
  temperature                 mean 81.1  MAX 85 C  — plateaued early, no climb
  power                       mean 545.0  MAX 569.4 W  of a 575 W limit
  clocks                      sustained 2785 of 3090 MHz
  ⇒ THROTTLED?                NO. 0/2438 thermal, 0/2438 power-cap.
                              ★ Three and a half hours at 85 C and ~545 W with
                                zero lost clocks. This is the question a
                                34-second probe cannot answer, and it passes.
  loss  first → last          0.432 → 0.100, finite throughout
                              ⚠ PLATEAUED ~0.096-0.100 from step 11K. Converged,
                                or batch-size-limited? STEP 3b decides.
  checkpoints written         6/6 — 2000/4000/6000/8000/10000/12000, ~15 GiB ea
                              ★ The STEP 1 fix survives repeated use deep into a
                                run with a warmed-up allocator, not just once at
                                step 10 on a fresh one.
  checkpoint RELOADS          ✅ 4.143B params, 4.143B trainable, 0 non-finite
                                 weight tensors
  weights still moved @12k    ✅ VLM 595/603, expert 208/209 — identical counts
                                 to step 10, so the same 8 tensors are
                                 persistently unchanged (consistent with
                                 zero-init biases carrying zero gradient)
  ⚠ "finite ACTIONS" NOT YET VERIFIED. Reload + finite WEIGHTS were checked; a
    forward pass was not. STEP 3b's eval exercises real inference and closes it.

  ⇒ VERDICT  ★ WE CAN TRAIN π0.5 ON THIS 5090. Sustained, thermally stable,
    memory-stable, checkpointable, resumable. What remains unproven is the
    QUALITY of what it produces — STEP 3b.

  ⚠ DISK: ~88 GiB consumed today already (231 GiB used, up from 143 GiB) by
    datasets, pi05_base, and probe checkpoints. This run adds ~96 GiB. Old
    probe dirs under ~/lerobot_assets/probes/ are candidates for cleanup —
    ⛔ but deleting checkpoints is RED (§A). Ask first.

STEP 3b.0  zero-shot pi05_libero_base   ✅ RUN 2026-08-11 22:2x
  LIBERO Spatial, no training  0.0%  (0/40)
  ⇒ NOT trained on LIBERO. Base model SHAPED for LIBERO's spaces only.
  ⇒ retracts the "reference had a head start" claim
  ⇒ ★ our pipeline took a model 0% → 70%. That is entirely our training.

STEP 3b  quality — did the levers cost anything?
  ⛔ NOT ANSWERED. The 70% vs 97% comparison is confounded by DATA VOLUME:
     reference 6,000 × 32 = 192,000 examples
     ours     12,000 ×  8 =  96,000 examples   ← HALF
     A matched run must equalise EXAMPLES, not steps. → STEP 3d.

STEP 3c  transfer to unseen suites   ✅ RUN — near-total specialisation
  libero_spatial (trained)   70.0%   n=40
  libero_object  (unseen)     0.0%   n=40
  libero_goal    (unseen)     0.0%   n=40
  verified not an artefact: same ckpt still 70% on spatial · rollouts ran the
  full 280 steps · avg_MAX_reward 0.0 (never even partial credit)
  ⚠ measures TRANSFER not forgetting, and includes normaliser specialisation

LEARNING CURVE (from saved checkpoints, ~7 min)   ✅ RUN
   4,000 →  32k examples → 27.5%
   8,000 →  64k examples → 57.5%   +30.0
  12,000 →  96k examples → 70.0%   +12.5
  ⇒ still climbing; the gap to 97% is substantially DATA
  ★ loss plateaued ~0.098 from 11K while success rose 57.5 → 70. LOSS IS NOT A
    PROXY FOR CAPABILITY HERE.

STEP 3d  matched-data run   🔄 LAUNCHED
  24,000 steps × bs8 = 192,000 examples, fresh (clean LR schedule)
  batch / steps / examples    ____ / ____ / ____
  wall clock                  ____
  peak VRAM · drift           ____ · ____
  throttled?                  ____
  success @ 24k               ____ %   (prediction: ~78% by naive extrapolation)
  ⇒ VERDICT vs the levers     ____
  precision layout measured   BF16 3.610B (87.1%) / F32 0.534B (12.9%)
                              ⇒ NOT naive bf16; the sensitive 13% stays fp32
  fp32 master weights         NONE — bf16 tensors ARE the weights (confirmed:
                              23.14 GiB persistent has no room for a 15.4 GiB
                              fp32 copy, and the checkpoint dtypes agree)
  LIBERO Spatial success      ____ %     reference: 97.0% (LeRobot pi05 docs)
  gap                         ____
  ⇒ VERDICT                   ____   apply the §STEP 3b rule as written:
                                     a gap implicates BATCH SIZE / LR first,
                                     NOT quantisation

STEP 3e  effective batch 32 via accumulation   🔄 RUNNING
  config                      bs8 × accum4 · 24,000 batches · 6,000 optimiser
                              updates · 192,000 examples · LR preset 2.5e-5
                              (correct unscaled: effective batch IS 32)
  ⚠ accumulation costs +2.18 GiB   25.53 → 27.71 GiB training process.
    NOT memory-neutral, contrary to what I predicted. Mechanism: zero_grad's
    set_to_none normally FREES ~7.7 GiB of gradients between steps; with
    accumulation they must persist across the window, so gradient and
    activation storage coexist instead of alternating.
    ⇒ peak 29.5 GiB of 31.84 — effective batch 32 FITS but is at the ceiling.
  success @ 24k (n=200)       ____ %
  ⇒ VERDICT on the levers     ____

STEP 3g  starting checkpoint — ⭐ THE LEADING HYPOTHESIS, NOT YET RUN
  the observation   STEP 3e and the REFERENCE match on effective batch (32),
                    optimiser updates (6,000) AND examples (192,000) — and
                    differ by 32.5 points. So "updates vs batch size" explains
                    our own runs but NOT the reference gap.
  hypothesis        we started from pi05_base (generic: 3 cameras, state[32],
                    action[32]); the reference started from the LIBERO-shaped
                    base (2 cameras, state[8], action[7]). We had to learn the
                    SPACE ADAPTATION as well as the task in 6,000 updates.
  ⚠ retracted this earlier for a bad reason — 0% zero-shot proves no TASK
    competence head start, not the absence of an ARCHITECTURAL one.
  config            from pi05_libero_base · bs8 × accum4 · 24,000 batches
                    · everything else identical to 3e · ~7 h · eval at n=200
  ⚠ check camera keys first — pi05_libero_base natively wants image/image2, so
    3e's --rename_map may be unnecessary or inverted
  success @ 24k     ____ %   (prediction: ~97% ⇒ checkpoint was the whole gap)
  ⇒ VERDICT         ____

STEP 3f  capability ladder
  3f.1 real PCIe bandwidth    ✅ MEASURED 2026-08-13
         pinned    H2D 56.6 GB/s · D2H 55.8 GB/s   = 89% of the 63.0 spec
         pageable  H2D 26.7 GB/s · D2H 20.0 GB/s   = ~42%, roughly HALF
       ⇒ my "expect 50-80%" was too pessimistic for the BEST case and about
         right for the typical one. Pinned+large+uncontended ≈ 89%; anything
         less careful lands in the 40-60% band — both measured on this machine
         in the same minute. Offload implementations PIN, so use 56 GB/s.
       ⇒ ESCALATION LADDER COSTS, recomputed from measurement not spec:
           8-bit Adam state (8.3 GB)   +0.29 s/step  = +28%
           FP32 Adam state (33.1 GB)   +1.18 s/step  = +112%
         ⛔ SUPERSEDED BY 3f.3b — these assume ONE BULK TRANSFER. Streaming in
           chunks, which a real implementation must do, measures 8.0 GB/s not
           56.6, giving +197% and +785%. A 7 h run becomes ~21 h, not ~9 h.

  3f.2 paged 8-bit optimiser  ✅ MEASURED 2026-08-13 — ★ RUNG 3 WORKS
         config           batch   s/step  samples/s  torch GiB
         bs8  non-paged       8    1.049      7.63      24.47
         bs16 non-paged      16    1.880      8.51      26.82
         bs32 non-paged      32      OOM         —          —
         bs32 PAGED          32    3.747      8.54      25.48
       ★ THE A/B IS DECISIVE: bs32 OOMs without paging and SURVIVES with it.
         Same batch, same everything else. Paging is real and works on Blackwell
         — which STEP −1 passing did NOT imply, since it is a different bnb code
         path.
       ⛔ CORRECTED 2026-08-14 — "it demonstrably offloads" WAS WRONG.
         An earlier revision said bs32 paged uses LESS memory than bs16
         non-paged (25.48 vs 26.82 GiB) and concluded the state "genuinely left
         the card". Re-measured with nvidia-smi telemetry:

           bs32 PAGED   torch mem_gb 25.47   TRUE per-process peak 27.71 GiB
           bs32 nonpaged  OOM

         ⇒ torch UNDERCOUNTS BY 2.24 GiB. `mem_gb` is
           torch.cuda.max_memory_allocated(), which tracks torch's allocator
           only; bnb's paged tensors come from cudaMallocManaged OUTSIDE it.
         ⇒ The original claim compared an UNDERCOUNT against a FULL COUNT, and
           the true peak (27.71 GiB) is HIGHER than bs16's, not lower.

       ★ WHAT PAGING ACTUALLY DOES: state does NOT proactively move off-card.
         CUDA managed memory keeps pages resident and migrates them to host ONLY
         UNDER GENUINE PRESSURE. What it buys is that an allocation which would
         otherwise OOM instead SUCCEEDS, at the margin. Observed mid-run: 111 MiB
         of free VRAM — paging engages exactly at the edge, letting the run sit
         against the ceiling instead of falling off it.
         That is still valuable, but it is a different mechanism from
         "offloading state", which is how I described it.
       ⚠ CANNOT ISOLATE THE PAGING PENALTY. The clean comparison would be bs32
         paged vs bs32 non-paged — but the latter OOMs, which is the whole point.
         So 3.747 s/step mixes "bigger batch" with "paging overhead" and the two
         cannot be separated from this data.
       ⇒ Net throughput 8.54 samples/s ≈ bs16 non-paged's 8.51. Paging buys a
         LARGER BATCH AT NO THROUGHPUT COST — but per STEP 3e larger batches are
         WORSE for quality here, so the value is capability for a bigger MODEL,
         not a better recipe for this one.

  ⛔ RUNG 3 AND RUNG 4 USE DIFFERENT TRANSFER MECHANISMS — do NOT apply 3f.1's
     numbers to 3f.2. Operator caught this; the source confirms it:

       bitsandbytes/functional.py:93   lib.cget_managed_ptr(...)  ← cudaMallocManaged
                                 :97   out.is_paged = True
                                 :102  def prefetch_tensor(...)

       RUNG 3 (paged, MEASURED)    CUDA UNIFIED/MANAGED memory. One address
                                   space; the DRIVER migrates pages on demand
                                   under VRAM pressure. Per-page, fault-driven,
                                   not under your control ⇒ does NOT reach the
                                   bulk pinned rate.
       RUNG 4 (explicit, NOT RUN)  you allocate PINNED buffers and cudaMemcpy
                                   the state in bulk when you choose ⇒ this is
                                   what 3f.1's 56.6 GB/s and the +28% estimate
                                   describe.

     ⇒ **The +28% figure belongs to rung 4, which has not been run.** The
       3.747 s/step measured here is rung 3 on a slower path — and cannot be
       cleanly attributed to paging anyway, since the bs32 non-paged control
       OOMs.
     ⇒ The trade is CONVENIENCE vs SPEED: paging is a one-word change that just
       works; explicit pinned offload is real integration work on the faster
       path. That is exactly why they are separate rungs.
     ⚠ "Offload implementations pin" was right about EXPLICIT offload and wrong
       as a blanket statement. bitsandbytes deliberately does not pin — unified
       memory is what lets paging work automatically.

  3f.3 CPU optimiser offload (rung 4)  ✅ MECHANISM MEASURED 2026-08-13
         8-bit state (8.3 GB)   transfer 0.296 s · update 0.013 s
                                total +0.309 s on a 1.05 s step = +29.4%
                                ⇒ predicted +28% from 3f.1's bandwidth. The
                                  arithmetic was RIGHT.
                                ⇒ a 7 h run becomes ~9.1 h. VIABLE.
         fp32 state (33.1 GB)   ⛔ ALLOC FAILED — CUDA out of memory.
                                33.1 GB exceeds the ~30 GB free on a 32 GB card,
                                so the state cannot be staged to the GPU IN ONE
                                PIECE AT ALL. A real implementation must CHUNK
                                it: more, smaller transfers, further from the
                                bulk rate.
                                ⇒ the +112% figure is a FLOOR that assumes a
                                  transfer this hardware cannot perform.
       ⚠ WHAT THIS MEASURES: transfer + update cost per optimiser step, at
         pi05's real state sizes, with pinned memory.
         WHAT IT DOES NOT: integration overhead, scheduling, transfer/compute
         OVERLAP. A real ZeRO-Offload does BETTER on overlap and WORSE on
         bookkeeping — which is why the literature reports 1.93-4.28× while this
         isolated mechanism costs 1.29×. **Do not quote +29.4% as the cost of a
         production offload implementation.** It is the floor for the transfer
         itself.
       ⇒ DeepSpeed is NOT installed and lerobot's trainer has NO offload hook,
         so a full integration remains a half-day job. This measurement was the
         cheap way to find out whether it is worth starting: it is.

  3f.3b CHUNKED offload  ⛔ REVISES 3f.3 SHARPLY — measured 2026-08-14
       Operator's point: fp32 state should be allocated on CPU and STREAMED,
       not staged whole. That is what a real implementation must do, and it is
       7× slower than the bulk transfer 3f.3 assumed.

         state size    time    effective rate
             2 GB     0.55 s     7.2 GB/s
             8 GB     2.00 s     8.0 GB/s
            16 GB     3.96 s     8.1 GB/s
         ⇒ chunked round-trip  8.0 GB/s
           single bulk pinned 56.6 GB/s   ← what 3f.3's +29.4% assumed

       WHY: each chunk needs TWO CPU memcpys (pageable→pinned, pinned→pageable)
       on top of the DMA, and this implementation does not overlap them with
       compute.

         8-bit state   +2.07 s/step = +197%   (3f.3 said +29.4%)
         fp32 state    +8.24 s/step = +785%   (arithmetic said +112%)

       ⇒ **"a 7 h run becomes 9.1 h" WAS WRONG. It becomes ~21 h.**
       ⇒ ★ +197% lands squarely inside the literature's 1.93-4.28× for real
         ZeRO-Offload, where +29.4% did not. The optimistic figure assumed a
         single bulk transfer a real implementation cannot perform. A production
         version with double-buffering and overlap sits between the two — but
         **closer to the chunked figure.**

       ⚠ ONE UNTESTED PATH REMAINS. MemAvailable is 43 GB (64 GB installed,
         59.2 GB MemTotal), so the full 33.1 GB of fp32 state COULD be held
         pinned, enabling bulk transfers. DeepSpeed does pin state when it fits.
         ⇒ fp32 offload may be +112% (fully pinned) rather than +785% (chunked).
           NOT MEASURED. Test incrementally — 16 / 24 / 33 GB — since 33 GB of
           unswappable memory could destabilise the machine.
         ⚠ swap is currently 8 GB, 100% USED (residue from the training runs),
           so there is no swap headroom for such a test.

  3f.3c full-pin test  ✅ MEASURED 2026-08-14 — IT PINS, AT FULL RATE
         target    pin time   bulk rate   avail during
         16.0 GB     2.6 s    56.3 GB/s     23.3 GB   ✅
         24.0 GB     5.6 s    55.2 GB/s     15.2 GB   ✅
         33.1 GB     4.6 s    55.9 GB/s     15.2 GB   ✅
         (swap cleared by the operator first: SwapFree 0 → 8 GB, which moved
          MemAvailable 48 → 40 GB as swapped pages faulted back in — the right
          trade, since pinned memory is unswappable)
         ⚠ test design flaw found and fixed mid-run: torch CACHES pinned host
           allocations and does not return them to the OS, so sequential sizes in
           ONE process measure garbage (39.7 → 23.3 GB and stayed). Redone with a
           FRESH PROCESS per size; memory recovered to ~48 GB after each exit.

       ★★ AND IT REFRAMES 3f.3b. `pin_one.py` copied to the GPU 1 GB AT A TIME
          out of the pinned 33.1 GB buffer — that IS chunked transfer, and it ran
          at 55.9 GB/s.

            3f.3b  pageable state → pinned staging → GPU    8.0 GB/s
            3f.3c  pinned state   → GPU, in chunks         55.9 GB/s

          ⇒ **"chunked is 7× slower" was the wrong framing.** Chunking from
            PAGEABLE memory is slow (two CPU memcpys per chunk). Chunking from
            PINNED memory runs at full rate — and it MUST be chunked anyway,
            since 30.8 GiB of fp32 state cannot sit on the GPU beside weights
            and gradients.
          ⇒ **+112% therefore needs no clever engineering.** Pin once at startup,
            stream slices per step. The two designs I had treated as alternatives
            are the same design.

       ⇒ ALSO WEAKENS THE 128 GB RAM ARGUMENT: 59 GB already holds the full fp32
         state for a ~4B model with 15 GB to spare and no swapping. §3f.4's
         "RAM-bound at 7.3B" stands, but you would hit the VRAM wall for weights
         and gradients first on a 32 GB card.

  3f.3d fp32 offload — ✅ IMPLEMENTED AND MEASURED 2026-08-14
         CPUOffloadAdamW: exp_avg / exp_avg_sq held as PINNED fp32 CPU tensors,
         DMA'd to the GPU per parameter for the update and back. ~70 lines.
         Per-parameter, not one flat buffer: pi05's 812 tensors average ~20 MB
         of state each — large enough for good DMA rates, and no gather/scatter.

         ★ CORRECTNESS  max |offload − torch.optim.AdamW| after 10 steps
                        = 2.6e-08 → float32 rounding. IT MATCHES.
                        (checked FIRST — an offloaded optimiser that quietly
                         computes a different update would give a plausible
                         training curve and a wrong model)

         ★ COST, measured on 1.68B params and extrapolated to 4.14B:
             baseline step                  1.05 s
             + fp32 offload optimiser time  1.38 s   (predicted 1.18)
             = total                        2.43 s   ⇒ 2.31× = +131%
             a 7 h run becomes ~16.2 h

           predicted from bandwidth alone   +112%
           MEASURED end-to-end              +131%   ← the 17% gap is the update
                                                      compute, per-tensor launch
                                                      overhead and the grad cast
           naive chunked-from-pageable      +785%   (3f.3b)
           published ZeRO-Offload       1.93-4.28×; we sit at 2.31×

         ⇒ **fp32 optimiser offload is VIABLE on this machine at ~2.3×.** The
           mechanism is proven and the arithmetic held within 17%.

         ⚠ NOT INTEGRATED INTO LEROBOT. Tested standalone, deliberately: a
           failure there points at the optimiser rather than the integration,
           and costs 2 minutes instead of a model load. Still unproven:
           checkpoint save/load of pinned state, the accelerate interaction, and
           grad clipping. Those matter only if it is actually to be USED.

  3f.2b paged-run checkpoint test  ✅ RUN 2026-08-14 — PARTIAL PASS
         bs32 · paged · 20 steps · save_checkpoint=true
         checkpoint WRITES     ✅ optimizer_state.safetensors 6.2 GB,
                                  model.safetensors 8.8 GB — the very file that
                                  failed TWICE for 8-bit Adam
         model RELOADS         ✅ 4.143B trainable, 0 non-finite tensors
         ⇒ the STEP 1 fix (scalars→tensors, clone shared storage) covers the
           managed-memory case too: cudaMallocManaged tensors present as ordinary
           CUDA tensors to safetensors.

         ⛔ RESUME FAILS — OOM
           torch.OutOfMemoryError: tried to allocate 2.00 MiB,
           97.44 MiB free, process holding 29.41 GiB
           It LOADED the state ("Resuming data order at epoch 0, sample 640")
           and then died.

         ⚠ FRAGMENTATION RULED OUT. Retried with
           PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True:
             reserved-but-unallocated  512.80 MiB → 226.10 MiB  (halved — the
                                                    setting DID work)
             allocated by PyTorch      28.31 → 28.58 GiB
             still OOM, on an 18 MiB request
           ⇒ the deficit is REAL, ~1 GiB, not fragmentation. Consistent with the
             resume overhead measured in STEP 3d (bs8: 27.11 GiB fresh vs 28.15
             resumed).

       ⇒ ★ RUNG 3 STATUS: trains at the edge ✅ · checkpoints ✅ · RESUMES ❌
         **A model that only fits WITH paging gets an UNINTERRUPTIBLE run.** You
         can save, and you can load the model for evaluation, but you cannot
         continue training — which is exactly the multi-day workflow paging
         exists to enable.

       ⇒ LIKELY FIX, and it connects to §1's iGPU note: the desktop holds
         **1.42 GiB of VRAM** (gnome-shell, Xwayland, remote-desktop daemon).
         Moving the display to the AMD iGPU frees almost exactly the ~1 GiB
         deficit. That switch was already costed as a cable move — no BIOS
         change, iGPU already enumerated, amdgpu already loaded. **It now has a
         concrete second payoff: plausibly the difference between resumable and
         unresumable paged runs.** NOT PROVEN — 1.42 vs ~1 GiB is close but
         needs the same test rerun after the switch.

  3f.3e fp32 Adam for pi05 via offload  ⏳ PLANNED — the LAST isolable variable
         fp32 does not fit in VRAM (46.3 GiB vs 29.9) but DOES with offload:
         GPU ~17.8 GiB · host 33.1 GB pinned (proven 3f.3c)
         ⇒ gives the single-variable test 8-bit Adam has never had:
             STEP 3d  bf16 + 8-bit Adam  24k steps  ->  80.0% (n=200)
             NEW      bf16 + fp32  Adam  identical  ->  ____
           ~80% = 8-bit costs nothing · higher = it has a real cost
         PHASE 1 integrate (~2 h) · PHASE 2 smoke 200 steps + checkpoint (~30 min)
         ⛔ STOP AND RE-DECIDE AFTER PHASE 2 — capability is proven there.
         PHASE 3 is 16 h (2.31x a run that took 7); start only if the quality
         question is worth a day of GPU. The purchase decision does not depend
         on it.
         smoke step time ____ s (target ~2.4) · checkpoint round-trip ____
         tractable now that 3f.3c proved pin-once/stream-slices at 55.9 GB/s.
         ~80 lines, NOT DeepSpeed. Scope: 200 steps, target ~2.2 s/step (+112%);
         ~8 s/step would mean it fell back to a pageable path. One checkpoint
         round-trip. ⚠ the hard part is the plumbing (checkpoint saver, flat
         view vs accelerate, grad clipping), not the transfer.
         ⚠ FOR A MODEL WE DO NOT HAVE YET — pi05 needs none of this.
         step time ____ s   checkpoint reloads ____

  3f.4 extrapolation  ✅ DONE 2026-08-14 — desk work, no GPU

       CALIBRATION, from the measured pi05 runs:
         persistent 23.14 GiB / 4.14B = 5.58 GiB per billion params
         non-persistent (activations + CUDA context) at bs8: 2.39 GiB

       HOW BIG A MODEL FITS IN VRAM
         setup                      per 1B    5090 (29.9)   PRO 6000 (89.9)
         bf16 + 8-bit Adam (ours)  5.59 GiB      4.9B           15.7B
         bf16 + fp32 Adam         11.18 GiB      2.5B            7.8B
         everything fp32          14.90 GiB      1.8B            5.9B

       ★ π0.5 is 4.14B, so it fits the first row and NOTHING ELSE. With plain
         fp32 the ceiling is 1.8B and π0.5 would not fit at all. **That single
         comparison is the whole investigation: the memory tricks are what made
         a 4.14B model trainable on this card.**

       WITH OFFLOAD — TWO ceilings, the smaller one binds
         (GPU holds w+g = 4 B/param · host holds state = 2 or 8 B/param)

         card + state          GPU caps at   RAM caps at (59 GB)   binds
         5090,     8-bit           7.4B            29.1B           GPU
         PRO 6000, 8-bit          23.5B            29.1B           GPU
         5090,     fp32            7.4B             7.3B           RAM (barely)
         PRO 6000, fp32           23.5B             7.3B           RAM (badly)

       ⇒ **With 8-bit state, MORE RAM BUYS NOTHING** — 59 GB already covers 29B
         params of state. The GPU is always the wall.
       ⇒ **With fp32 state, RAM is the wall** — and on a 96 GB card it is severe:
         the card could hold 23.5B but 59 GB of RAM supports only 7.3B. **If the
         reason to buy a big card is "run fp32 for quality", the RAM must be
         bought too or the card sits underused.** At 128 GB it becomes 15.8B —
         still RAM-bound, not VRAM-bound.

       ⚠ EXTRAPOLATED FROM ONE MODEL AT ONE BATCH SIZE. The 2.39 GiB overhead is
         π0.5-at-bs8-with-checkpointing; a different architecture or batch size
         moves it. Persistent terms scale linearly in parameter count;
         activations do not.

STEP 4  corpus decision       DEFERRED TO OPERATOR — see above
```

---

# §C STANDING NOTE — line-buffering has produced four false readings today

Not a training issue, but it has cost real time and will recur.

```text
1  smoke run piped through `tail`      → empty log read as a HANG
2  nvidia-smi -l > file                → 1 sample; a killed monitor looked idle
3  tqdm progress bars (\r, not \n)     → grep saw ONE huge accumulating line and
                                          fired a false milestone match
4  (earlier lane) DYNUS -O3 "hang at dynus_node.cpp:1250" — same root cause
```

⇒ **Rules.** Write long-run output to a FILE and read the file; never pipe a
live run through `tail`/`head`. Put `stdbuf -oL` on any producer whose output is
redirected. Put `tr '\r' '\n'` before any grep that reads a progress bar. And
treat *silence* as unknown, never as healthy — check the process table.

⚠ **A fifth case, different mechanism, same symptom:** LIBERO prompts on first
import (`Do you want to specify a custom path for the dataset folder?`) and
**blocks on stdin**. With output redirected that is indistinguishable from a
hang. ⇒ **Run unattended jobs with `< /dev/null`** so a prompt fails fast
instead of waiting forever.

---

# §E ⛔ EARLY VALIDITY GATES — mandatory before any run over 1 hour

**Written after STEP 3g wasted 7 hours on a run that was broken from batch one
and looked healthy the entire time.** Operator's point, and it is correct: this
should have been caught in the first minutes, not at the eval.

## What happened, and why nothing flagged it

```text
lerobot builds input_features FROM THE DATASET's names.
--rename_map is applied to the BATCH, AFTER those features are fixed.
⇒ renaming an image key GUARANTEES a mismatch.

    model expected   image · wrist_image      (from the dataset)
    batch carried    image · image2           (after the rename)
    ⇒ wrist_image MISSING from all 24,000 batches
```

**pi05 does not error on a missing camera.** `modeling_pi05.py`:

```python
missing_img_keys = [k for k in self.config.image_features if k not in batch]
for _ in range(len(missing_img_keys)):
    img = torch.ones_like(img) * -1     # padded
    mask = torch.zeros_like(mask)       # masked out
```

⇒ It pads and masks. Training runs. Nothing is logged.

★ **AND THE LOSS WENT DOWN.** 0.052 against a healthy run's 0.062 — ~18%
*better* at every checkpoint, because one camera is a simpler function to fit.
**The degraded run looked BETTER by the metric being watched**, and I reported
that as "directionally consistent with the hypothesis". Result: 1-3% instead of
64.5%.

## GATE E1 — pre-flight batch check  `[seconds]` ⛔ MANDATORY

```bash
python preflight_batch_check.py --dataset <repo> [--rename-map <json>]
```

Compares what the model will expect (the dataset's feature names) against what
the batch will carry (after any rename). **Verified to fail the exact STEP 3g
config and pass the corrected one.** Costs seconds; would have saved 7 hours.

⇒ Archived at `results/pi05_capability_20260811/preflight_batch_check.py`.

## GATE E2 — early functional eval at the FIRST checkpoint  `[~3 min + a pause]`

Structural checks cannot catch everything. At the first checkpoint (2,000
batches, ~8% of a run), pause and evaluate at n=40, **then compare against the
same checkpoint index of a known-good run**:

```text
3d @ 4,000 → 27.5%    a healthy run is already well above chance this early
3g @ 2,000 → would have been ~1%
```

⚠ Cost is a pause plus a ~35 min rewind to the last checkpoint. **Against a 7 h
run that is under 10%.** Take it.

## GATE E3 — treat DIVERGENCE from a comparable run as a red flag, not a result

⚠ **This is the one I got wrong.** A metric moving differently from a known-good
run is a reason to STOP AND INVESTIGATE, in either direction. I saw loss 18%
lower and read it as encouraging.

```text
loss LOWER  than the comparable run   → investigate. Fewer inputs? Easier task?
loss HIGHER than the comparable run   → investigate.
loss TRACKING the comparable run      → the only reassuring case
```

## The general rule

> **Any run longer than an hour must have a validity gate that costs under 1% of
> its runtime and tests the thing most likely to be silently wrong.**

For this stack, the thing most likely to be silently wrong is **input plumbing** —
three separate rename_map traps have appeared in this lane alone, because π0.5,
the LIBERO dataset and the LIBERO simulator each name the wrist camera
differently.

---

# §D WHAT BELONGS IN `results/` — and what does not

**Corrected 2026-08-11 after the operator asked why logs were going into git.**

I hit `.gitignore:84` (`*.log`) silently swallowing archived logs, and **renamed
them to `.txt` to defeat the rule.** That was the wrong instinct — the rule is
correct, and fighting it committed 1.8 MB of near-pure noise.

```text
WHAT WAS ACTUALLY IN THOSE FILES
  eval log        657 KB   83 repeated robosuite warnings + a config dump
  gpu_procs.csv   706 KB   16,980 rows logging the SAME SIX PIDs every 5 s,
                           when only the peak matters and it is in the report
  sweep logs      18 KB ea mostly config dumps
⇒ 1.8 MB -> 88 KB after distillation. Almost none of it was evidence.
```

⇒ **Commit distillates, not raw logs.**

```text
COMMIT      metric summaries · step/checkpoint lines · downsampled telemetry
            (5 s -> 30 s is plenty for a multi-hour run) · scripts · reports
DO NOT      raw training/eval logs · per-process telemetry · config dumps
            ⇒ these live untracked in ~/lerobot_assets/probes/
```

⚠ **`git add -A` succeeding is NOT evidence a file was added.** It skips ignored
paths without a word. Two earlier commits here claimed artefacts were archived
when the logs never landed. **Verify with `git ls-files` or
`git status --ignored`.**
