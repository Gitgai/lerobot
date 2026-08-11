# Phase 2 — can we actually TRAIN π0.5 here, not just fit it?

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

  MAX BATCH THAT FITS        16
  grad accumulation needed?  NO — rule was "max batch >= 8 ⇒ not needed", and
                             16 >= 8. The second code change is OFF THE TABLE.

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
  batch / steps / samples     ____ / ____ / ____
  wall clock                  ____
  peak VRAM  start → end      ____ → ____   drift? ____
  temp / clocks  max → end    ____ → ____   throttled? ____
  loss  first → last          ____ → ____   finite throughout? ____
  checkpoint reloads          ____   finite actions? ____
  ⇒ VERDICT                   ____

  ⚠ DISK: ~88 GiB consumed today already (231 GiB used, up from 143 GiB) by
    datasets, pi05_base, and probe checkpoints. This run adds ~96 GiB. Old
    probe dirs under ~/lerobot_assets/probes/ are candidates for cleanup —
    ⛔ but deleting checkpoints is RED (§A). Ask first.

STEP 4  corpus decision       DEFERRED TO OPERATOR — see above
```
