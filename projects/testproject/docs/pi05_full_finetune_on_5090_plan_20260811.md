# Can we FULL fine-tune π0.5 on one RTX 5090 (32 GB)?

Date: 2026-08-11, kiran-AI90. Purpose: answer one question before any hardware
purchase is discussed.

> Can all ~4B π0.5 parameters receive gradients and be updated, on a single
> 32 GB 5090, by trading speed for memory — without silently becoming LoRA or
> expert-only?

**Status: NOT YET ATTEMPTED.** The enabling config was described but never run.

---

## 0.0 ⛔ VERIFIED ON DISK 2026-08-11 — read before executing §3

This plan was written from memory of the tracker. Everything below was then
checked against the filesystem. **The arithmetic survived; four claims did not,
and one of them blocks §3 as written.**

### ⛔ BLOCKER: the code change and the training run are in DIFFERENT lerobot installs

```text
WHERE THE PLAN EDITS          projects/git/nvidia/lerobot/src/lerobot/  v0.5.2
  installed editable into     projects/testproject/.venv
  but that venv has           NO accelerate, NO transformers  -> CANNOT train

WHERE TRAINING CAN RUN        /home/kiran/sim/Isaac-GR00T-n16/.venv   lerobot 0.4.4
                              /home/kiran/sim/leisaac-venv           lerobot 0.4.2
  both are                    NON-EDITABLE site-packages COPIES
                              (no __editable__.lerobot .pth in either)
```

⇒ **Editing this repo does not change what trains.** This is the `src/` vs
`install/` trap. **Step 0 of the experiment is deciding where the change lands**
— and the options are not equivalent:

```text
A  install THIS repo (0.5.2) editable into a venv with accelerate+transformers
   ⇒ the edit takes effect, but it is a VERSION CHANGE on top of a
     memory experiment. Two variables at once.
B  patch the 0.4.x copy in the venv that produced the OOM ladder
   ⇒ same version as the measurements, but the patch lives in site-packages
     and must be captured in projects/testproject/patches/ or it is lost
     on the next sync.
```

**B is the honest one** — it holds the version fixed against the numbers in §0.
Take A only if 0.4.x turns out to lack something needed, and say so.

⚠ Whichever is chosen, **re-check §2 and §3 against THAT tree** — the registry
already differs between them (below).

### Corrections to specific claims

```text
CLAIM                              ACTUAL                              IMPACT
"registers only adam/adamw/sgd"    5 in 0.5.2 (+xvla-adamw,            none on the
                                   +multi_adam), 5 in 0.4.4, 4 in      conclusion:
                                   0.4.2 — and they DIFFER by venv     still no 8-bit
"if the trainer exposes grad       IT DOES NOT. Accelerator() at       §3 needs a
 accumulation"                     lerobot_train.py:198 takes no       SECOND code
                                   gradient_accumulation_steps, and    change, not
                                   update_policy() calls               an "if"
                                   optimizer.step()+zero_grad() every
                                   batch (checked in 0.5.2)
"tracker section 13"               the OOM ladder is in                fix the
                                   REALARM_RESULT_20260808.md ~L76-84  pointer
"FIX READY TO TRY" in tracker      that string exists in NO doc but    drop the
                                   this one                            citation
bitsandbytes not installed         CONFIRMED — absent from all three   plan correct
                                   venvs
```

⇒ **Two code changes, not one:** the 8-bit optimizer registration *and*
gradient accumulation. Budget accordingly; measure them separately.

### Unrelated but noticed

`~/lerobot_assets/checkpoints/pi05_sim_varied` — the 30k-step run
REALARM_RESULT_20260808 launched — **is not on disk anywhere** (searched
/home/kiran, /mnt, /media to depth 9). Only `pi05_012000` remains. Either it was
pruned or it never landed; the sim battery evaluated *something* under that name,
so this should be resolved before any of those numbers are re-derived. **Not a
blocker for this experiment** — LIBERO is the recommended dataset anyway.

---

## 0. What is already known — do not re-run these

### Measured on THIS machine (`REALARM_RESULT_20260808.md`, "OOM ladder")

```text
bs16 fp32                          OOM   (fp32 weights = 16.6 GB alone)
bs8 / bs4 fp32                     OOM
bs8 bf16                           OOM   (trainable ALL 4.14B -> 33 GB Adam)
+ train_expert_only=true
  + freeze_vision_encoder          693M learnable - the 012000 recipe
bs8 bf16 expert-only               OOM   (activations)
bs4 bf16 expert-only               TRAINS: 1.4 steps/s, 26.3 GB, GPU 97%
```

⇒ A batch sweep has already been done. Its conclusion, reached independently
here: **"Batch-independence proves it is OPTIMIZER STATE, not activations."**
Reducing batch size alone does not and cannot fix this.

⇒ **The 26.3 GB working run is NOT a full-fine-tuning data point.** It trains
693M of 4.14B. Do not cite it when reasoning about the 32 GB ceiling.

### Already validated on this GPU

`gradient_checkpointing=true` and `dtype=bfloat16` are already in the working
recipe. 8-bit Adam is proven on this card via the GR00T track:
`adamw_bnb_8bit`, 100 probe steps, 4.15 it/s, **23.1 GB, zero OOM**.

### External figures, and what they actually say

```text
OpenPI README        Full >70 GB, LoRA >22.5 GB, Inference >8 GB
                     ^ ONE UNIFIED TABLE for pi0 / pi0-FAST / pi05, and it is
                       the JAX/XLA stack. NOT a pi05-specific measurement, and
                       NOT our framework.
LeRobot pi05 docs    "Sized for a single 80 GB GPU" - for LIBERO at batch_size=64
                     official full-FT command uses freeze_vision_encoder=false,
                     train_expert_only=false, gradient_checkpointing=true, bf16
HF lerobot/pi05_base "4B params", dtype F32
lerobot issue #2216  a user OOMed on an RTX A6000 48 GB; unresolved, no settings
                     given
```

The 48 GB OOM is consistent with the arithmetic below, which is mild
corroboration that the model really is ~4B and that FP32 Adam is the wall.

---

## 1. The arithmetic, at the REAL parameter count

A widely-circulated analysis of this question assumes **2.3B**. HuggingFace and
our own measurement both say **~4B / 4.14B**. That is a 1.8x error and it
changes the conclusion.

```text
                        at 2.3B      at 4.14B (ours)
BF16 weights             4.6 GB        8.3 GB
BF16 gradients           4.6 GB        8.3 GB
FP32 AdamW m + v        18.4 GB       33.1 GB     <- matches our measured "33 GB Adam"
──────────────────────────────────────────────
persistent subtotal     27.6 GB       49.7 GB
```

49.7 GB before a single activation. That is why an A6000 48 GB OOMs, and it is
why this is hopeless with FP32 Adam no matter how small the batch.

**With 8-bit optimizer states (~2 bytes/param instead of 8):**

```text
BF16 weights             8.3 GB
BF16 gradients           8.3 GB
8-bit Adam m + v        ~8.3 GB
──────────────────────────────
persistent              ~25 GB      against ~31.35 GB usable
+ activations (bs1, checkpointed)
+ CUDA/allocator workspace
```

Tight, but not obviously impossible. **That is the whole experiment.**

---

## 2. The blocker: LeRobot has no 8-bit optimizer

⚠ **Counts below are from this repo (0.5.2). Re-run the grep against whichever
tree §0.0 selects — 0.4.2 has four registrations, not five.**

`src/lerobot/optim/optimizers.py` registers five optimizers, none of them 8-bit:

```text
@OptimizerConfig.register_subclass("adam")         -> torch.optim.Adam
@OptimizerConfig.register_subclass("adamw")        -> torch.optim.AdamW
@OptimizerConfig.register_subclass("sgd")
@OptimizerConfig.register_subclass("xvla-adamw")
@OptimizerConfig.register_subclass("multi_adam")
```

and `configuration_pi05.py::get_optimizer_preset()` returns `AdamWConfig`.

⇒ The two extra registrations are good news for effort: the subclass pattern is
well-worn here, so mirroring it for `AdamW8bit` is routine rather than novel.

The GR00T 8-bit result came from a **different stack** — HF Trainer's
`--optim adamw_bnb_8bit` — which does not apply here. Also:
**`bitsandbytes` is not installed in any venv on this machine** (checked
testproject, Isaac-GR00T-n16, leisaac).

So this needs a small code change, not a flag:

```text
1. pip install bitsandbytes into the training venv
2. add   @OptimizerConfig.register_subclass("adamw_8bit")
         class AdamW8bitConfig(OptimizerConfig)  -> bnb.optim.AdamW8bit
         ~15 lines, a direct mirror of AdamWConfig
3. select it from the CLI (draccus choice registry) or override
   get_optimizer_preset
```

---

## 3. The experiment — ONE run, not eleven phases

```bash
lerobot-train \
  --dataset.repo_id=<the 89 real-arm episodes or LIBERO for a clean first try> \
  --policy.type=pi05 \
  --policy.pretrained_path=lerobot/pi05_base \
  --policy.device=cuda \
  --policy.dtype=bfloat16 \
  --policy.gradient_checkpointing=true \
  --policy.compile_model=false \
  --policy.freeze_vision_encoder=false \      # FULL - not the 012000 recipe
  --policy.train_expert_only=false \          # FULL
  --policy.push_to_hub=false \
  --optimizer.type=adamw_8bit \               # the new registration
  --batch_size=1 \
  --steps=100
```

⛔ **Gradient accumulation is NOT available and there is no flag for it** —
verified, §0.0. `Accelerator()` is constructed without
`gradient_accumulation_steps` and `update_policy()` steps the optimizer on every
batch. Recovering an effective batch is a **second code change**, and it should
be landed and measured separately from the optimizer one so we know which bought
what.

⇒ **Gate A can be attempted without it** — bs1 with no accumulation is a valid
memory measurement, it is just not a usable training recipe. Do that first: it
answers the $11K question with one code change instead of two.

Start on **LIBERO**, not the 89 real episodes. That separates a memory problem
from a dataset problem — our real episodes still need v3.0 -> GR00T v2
conversion and a `top` camera drop, per the tracker's parked-work list.

---

## 4. Acceptance — two gates, both required

### Gate A: it fits

```text
peak VRAM < 31 GB, 100 steps complete, loss finite and decreasing
```

Log with `nvidia-smi --query-gpu=memory.used --format=csv -l 1 > vram.csv`.
Record where it fails if it fails: model load / optimizer init / forward /
backward / optimizer step. Those need different fixes.

### Gate B: it is genuinely FULL fine-tuning

**This gate is the one most likely to be skipped, and skipping it makes Gate A
meaningless.**

```text
count trainable params   must be ~4.14B, NOT 693M and NOT adapter-only
                         model.num_parameters(only_trainable=True)
verify weights MOVE      hash or norm a VLM backbone tensor before training and
                         after 100 steps. If only the action expert changed, we
                         have reproduced the 012000 recipe by accident.
```

Our existing 26.3 GB run passes Gate A trivially and fails Gate B. That is
exactly the trap.

---

## 5. Escalation ladder — only if Gate A fails

In increasing order of performance cost. Do NOT skip ahead; each step should be
measured separately so we know what bought what.

```text
1. gradient accumulation      recover effective batch at bs1        ~free at
                              ⚠ NOT free to BUILD - no flag exists    runtime
2. 8-bit optimizer            33.1 GB -> ~8.3 GB of state           small
3. paged 8-bit optimizer      bnb spills optimizer state to host    moderate
                              on pressure spikes
4. CPU optimizer offload      m/v live in the 59 GB of system RAM;  significant
                              PCIe 5.0 in the update path
5. CPU parameter offload      weights staged per-layer over PCIe.   severe -
                              GPU VRAM ~1.8 TB/s vs PCIe5 x16       last resort
                              ~64 GB/s theoretical: ~28x gap
```

Steps 4-5 put PCIe in the inner loop. Given this machine has 59 GB RAM and a
9950X, step 4 is viable; step 5 should be considered a failure mode rather than
a solution.

---

## 6. Decision rule — written before the result

```text
peak < 28 GB, <2x slowdown        the 5090 is clearly sufficient. No purchase.
peak 28-31 GB, 2-4x slowdown      viable. Weigh the time cost against $11K.
peak 31-32 GB, >4x slowdown       marginal. Every run becomes a scheduling
                                  problem; revisit.
still OOM, or >10x, or unstable   a higher-VRAM card becomes a rational
                                  consideration - and NOW there is evidence for
                                  it rather than a vendor table.
```

**What the OpenPI >70 GB figure does and does not prove:** it says *their*
standard JAX configuration needs >70 GB. It does not prove no full-parameter
configuration fits in 32 GB, and it is not measured on our stack. Those are
different claims, and only an experiment separates them.

---

## 7. Why this is worth one run

The alternative under discussion is an RTX PRO 6000 at ~$11K. The experiment
costs a few hours. Even a negative result is worth having, because it converts
"the docs say 80 GB" into "we measured our own configuration and it needs X" —
which is the only form of evidence that should justify that purchase.
