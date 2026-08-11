# Can we FULL fine-tune π0.5 on one RTX 5090 (32 GB)?

Date: 2026-08-11, kiran-AI90. Purpose: answer one question before any hardware
purchase is discussed.

> Can all ~4B π0.5 parameters receive gradients and be updated, on a single
> 32 GB 5090, by trading speed for memory — without silently becoming LoRA or
> expert-only?

**Status: NOT YET ATTEMPTED.** The enabling config was written down in
`pi05_active_work_tracker.md` as "FIX READY TO TRY" and never run.

---

## 0. What is already known — do not re-run these

### Measured on THIS machine (tracker section 13)

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

`src/lerobot/optim/optimizers.py` registers only:

```text
@OptimizerConfig.register_subclass("adam")   -> torch.optim.Adam
@OptimizerConfig.register_subclass("adamw")  -> torch.optim.AdamW
@OptimizerConfig.register_subclass("sgd")
```

and `configuration_pi05.py::get_optimizer_preset()` returns `AdamWConfig`.

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

Plus gradient accumulation to recover an effective batch, if LeRobot's trainer
exposes it; if not, that is a second small addition and should be treated as
such rather than assumed.

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
1. gradient accumulation      recover effective batch at bs1        ~free
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
