# Can we FULL fine-tune π0.5 on one RTX 5090 (32 GB)?

Date: 2026-08-11, kiran-AI90. Purpose: answer one question before any hardware
purchase is discussed.

> Can all ~4B π0.5 parameters receive gradients and be updated, on a single
> 32 GB 5090, by trading speed for memory — without silently becoming LoRA or
> expert-only?

**Status: NOT YET ATTEMPTED.** The enabling config was described but never run.

**⛔ ONE THING BLOCKS EXECUTION: the LIBERO `repo_id` in §3 is not pinned.**
Everything else is verified and ordered. Pick it, confirm it downloads, write it
into §3, then follow §3.5 top to bottom.

> **Reading order:** §0.0 (what was verified) → §3 (the trap) → §3.5 (the
> runbook) → §4 (the gates) → §8 (record as you go). §1/§2 are the reasoning;
> §5/§6/§7 are only needed if Gate A fails or when the decision is made.

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

### ⛔⛔ THE SILENT-OVERRIDE TRAP — read this or the run answers the wrong question

`--optimizer.type=adamw_8bit` **is silently discarded by default.** Verified in
the 0.4.4 tree, `lerobot/configs/train.py`:

```python
use_policy_training_preset: bool = True          # L63, the DEFAULT
...
elif self.use_policy_training_preset and not self.resume:   # L134
    self.optimizer = self.policy.get_optimizer_preset()     # -> AdamWConfig, FP32
    self.scheduler = self.policy.get_scheduler_preset()
```

⇒ Pass `--optimizer.type=adamw_8bit` alone and the preset **overwrites it after
parsing**. The run proceeds on FP32 AdamW, OOMs at ~49.7 GB, and the conclusion
is *"the 5090 cannot do it"* — **on a bug, not a measurement.** That is an $11K
mistake and there is no error message.

⇒ **Disabling the preset requires BOTH optimizer and scheduler**, or L132 raises
`ValueError: Optimizer and Scheduler must be set when the policy presets are not
used.` The preset values must therefore be reproduced by hand:

```text
optimizer  AdamWConfig(lr, betas, eps, weight_decay, grad_clip_norm)
           <- from policy.optimizer_* fields
scheduler  CosineDecayWithWarmupSchedulerConfig(peak_lr, decay_lr,
             num_warmup_steps, num_decay_steps)
```

⚠ **Simplest correct route: do not fight the CLI — change the preset.** Edit
`configuration_pi05.py::get_optimizer_preset()` to return the 8-bit config while
the probe runs. It is one line, it cannot be silently overridden, and it is
reverted with the same patch file. **Record which route was used in the results
file** — they are not equivalent and the flag route is the one that fails
quietly.

### The command

```bash
# venv: see §0.0 step 0. Assumed here to be the 0.4.4 tree.
source /home/kiran/sim/Isaac-GR00T-n16/.venv/bin/activate

lerobot-train \
  --dataset.repo_id=<LIBERO repo_id — FILL THIS IN, see below> \
  --policy.type=pi05 \
  --policy.pretrained_path=lerobot/pi05_base \
  --policy.device=cuda \
  --policy.dtype=bfloat16 \
  --policy.gradient_checkpointing=true \
  --policy.compile_model=false \
  --policy.freeze_vision_encoder=false \
  --policy.train_expert_only=false \
  --policy.push_to_hub=false \
  --batch_size=1 \
  --steps=100 \
  --save_checkpoint=false \
  --wandb.enable=false \
  --output_dir=/home/kiran/lerobot_assets/probes/pi05_fullft_5090_20260811
```

```text
--save_checkpoint=false   save_freq defaults to 20_000 but a checkpoint is also
                          written at the LAST step. At 100 steps that is a
                          ~16 GB write for a memory probe. Turn it off.
--wandb.enable=false      no run should be logged upstream for a probe
--output_dir              must not exist, or the run refuses to start
```

⛔ **`--optimizer.type` is deliberately absent above** — per the trap section,
the 8-bit optimizer comes from the patched preset, not the CLI. If the flag
route is taken instead, `--use_policy_training_preset=false` **and** an explicit
`--scheduler.type` are both mandatory.

### Dataset

Start on **LIBERO**, not the 89 real episodes — that separates a memory problem
from a dataset problem. Our real episodes still need v3.0 → GR00T v2 conversion
and a `top` camera drop.

⚠ **The repo_id is not yet pinned and this plan cannot run until it is.** Pick
one, confirm it downloads, and write it back into this file. Note also that
`REALARM_RESULT_20260808.md` needed `--rename_map front->base_0_rgb,
wrist->left_wrist_0_rgb` because `pi05_base` uses pi0 camera naming — **check
whether the chosen LIBERO set needs its own rename_map before blaming memory for
a startup failure.**

### Gradient accumulation is out of scope for this run

⛔ Not available, no flag, verified §0.0. `Accelerator()` is built without
`gradient_accumulation_steps` and `update_policy()` steps every batch.

⇒ **Gate A does not need it.** bs1 without accumulation is a valid *memory*
measurement even though it is not a usable *training recipe*. That is the whole
point: it answers the $11K question with one code change instead of two.

---

## 3.5 RUNBOOK — the ordered steps, each with its own check

**Do these in order. Every step has a check because every step has failed
silently for someone.** Record each result in the results file (§8) as you go —
not at the end.

```text
STEP                                    CHECK IT WORKED
─────────────────────────────────────────────────────────────────────────────
0  choose the tree (§0.0). Default: the  python -c "import lerobot; print(
   0.4.4 venv at sim/Isaac-GR00T-n16       lerobot.__version__, lerobot.__file__)"
                                          -> must print 0.4.4 and a path under
                                             THAT venv's site-packages

0b SNAPSHOT before touching anything.     the .orig files exist
   cp optimizers.py{,.orig}               ⚠ this venv produced the 23.1 GB GR00T
   cp configuration_pi05.py{,.orig}          result. It is not disposable.
                                             Revert = cp back from .orig.

1  pip install bitsandbytes               python -c "import bitsandbytes as b;
                                            print(b.__version__)"
                                          ⚠ additive, but if it drags a torch
                                            reinstall, STOP and revert - that
                                            breaks the GR00T track.

2  add AdamW8bitConfig (§2)               grep register_subclass optimizers.py
                                          -> adamw_8bit now listed (6 total)

3  point get_optimizer_preset at it       read the file back; one line changed

4  capture BOTH edits as a patch into     the .patch file exists and applies
   projects/testproject/patches/          clean to the .orig files
   ⛔ site-packages is NOT version
      controlled. Skip this and the
      work is lost on the next sync.

5  smoke: 2 steps, not 100                it starts, loss prints, no OOM.
   --steps=2                              Catches dataset/rename_map/output_dir
                                          problems in 3 min instead of 40.

6  GATE B FIRST, before the real run      trainable ~4.14B (§4). If this says
   (it is cheap and it invalidates          693M, everything after it is void.
    everything if it fails)

7  the 100-step run + VRAM logging        §4 Gate A

8  revert: cp the .orig files back        the GR00T venv trains again.
                                          ⛔ Do not leave the venv patched.
```

⇒ **Steps 5 and 6 before step 7 is the whole discipline here.** The two ways
this experiment produces a confidently wrong number are a silently-ignored
optimizer (§3) and a silently-partial fine-tune (Gate B). Both are cheap to
check and neither announces itself.

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

⛔ **The snippet previously written here does not exist.**
`num_parameters(only_trainable=True)` is a *transformers* `PreTrainedModel`
method; LeRobot's `PreTrainedPolicy` does not define it (verified — grep in
`lerobot/policies/pretrained.py` returns nothing). It would have raised
`AttributeError` and, in a hurry, been skipped. Use plain PyTorch:

```python
# run against the constructed policy, before step 1 of training
trainable = sum(p.numel() for p in policy.parameters() if p.requires_grad)
total     = sum(p.numel() for p in policy.parameters())
print(f"{trainable/1e9:.2f}B trainable / {total/1e9:.2f}B total")

# name the VLM tensors explicitly so "the backbone" is not a guess
vlm = [n for n, p in policy.named_parameters()
       if p.requires_grad and "expert" not in n and "action" not in n]
print(f"{len(vlm)} trainable non-expert tensors; first: {vlm[:3]}")
```

```text
PASS   trainable ~4.14B, total ~4.14B, ratio ~1.00, and vlm list NON-EMPTY
FAIL   trainable ~0.69B (ratio ~0.17)  -> the 012000 recipe. Void the run.
FAIL   vlm list EMPTY                  -> expert-only by another route
FAIL   trainable << total but not 0.69B -> check cfg.peft is None (LoRA)
```

**Weights must also MOVE, not just require grad.** Frozen-by-optimizer is not
the same as frozen-by-`requires_grad`:

```python
import torch
before = policy.state_dict()[SOME_VLM_KEY].detach().float().norm().item()
# ... 100 steps ...
after  = policy.state_dict()[SOME_VLM_KEY].detach().float().norm().item()
assert abs(after - before) > 0, "VLM backbone did not move - not a full FT"
```

Pick `SOME_VLM_KEY` from the `vlm` list printed above and **write the actual key
into the results file** — "a VLM tensor" is not a record.

⇒ Our existing 26.3 GB run passes Gate A trivially and fails Gate B. **That is
exactly the trap, and Gate B is the only thing standing between it and an
$11K decision.**

---

## 5. Escalation ladder — only if Gate A fails

⚠ **Steps 1 and 2 of the old ladder are already spent.** The §3 baseline command
*includes* the 8-bit optimizer — without it there is nothing to measure — and it
*excludes* gradient accumulation deliberately. So the ladder below starts at what
used to be step 3. Left in place with strikethrough numbering so the ordering is
not silently re-derived later.

```text
~~1. gradient accumulation~~   NOT an escalation - it does not save memory at
                               bs1, it recovers effective batch. Build it AFTER
                               Gate A passes, if a real recipe is wanted.
~~2. 8-bit optimizer~~         ALREADY IN THE BASELINE. 33.1 -> ~8.3 GB.
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

---

## 8. Results — fill this in DURING the run, not after

**Empty means not run.** A blank row is information; a remembered row is not.

```text
date / operator            ____
tree used (§0.0 A or B)    ____   lerobot.__version__ ____  __file__ ____
8-bit route                ____   preset-patch | CLI flag  (§3 trap)
bitsandbytes version       ____
dataset repo_id            ____   rename_map needed? ____
patch captured at          projects/testproject/patches/____

GATE B (do first)
  trainable / total        ____B / ____B    ratio ____
  vlm tensor count         ____
  SOME_VLM_KEY used        ____
  norm before / after      ____ / ____      moved? ____
  VERDICT                  PASS / FAIL — if FAIL, stop, everything below is void

GATE A
  peak VRAM                ____ GB   (nvidia-smi 1 Hz, vram.csv attached)
  steps completed          ____ / 100
  steps/s                  ____      vs 1.4 expert-only baseline = ____x
  loss finite + decreasing ____
  if OOM, WHERE            load / optim init / forward / backward / optim step

DECISION (§6 rule, applied without renegotiating it)   ____
venv reverted (step 8)     ____
```

⇒ **Write the decision from the §6 table as-is.** The rule was fixed before the
result specifically so the $11K call is not re-argued once a number is in hand.
