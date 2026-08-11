# Can we FULL fine-tune π0.5 on one RTX 5090 (32 GB)?

Date: 2026-08-11, kiran-AI90. Purpose: answer one question before any hardware
purchase is discussed.

> Can all ~4B π0.5 parameters receive gradients and be updated, on a single
> 32 GB 5090, by trading speed for memory — without silently becoming LoRA or
> expert-only?

**Status: NOT YET ATTEMPTED.** The enabling config was described but never run.

**⛔ THE WHOLE PLAN RESTS ON ONE UNVERIFIED ASSUMPTION: that `bitsandbytes`
8-bit optimizer states work on this Blackwell (sm_120) card.** The precedent we
believed we had does not survive checking (§0.0). ⇒ **STEP −1 of §3.5 tests
exactly that, in ~5 minutes, and gates everything else.** If it fails, the ~25 GB
arithmetic in §1 collapses and the answer is "not by this route" — reached for
five minutes of work instead of ninety.

Dataset and venv are now pinned. Nothing else is outstanding.

> **Reading order:** **§0.–1 (what this experiment IS — start here if the setup
> is not already familiar)** → §0.0 (what was verified) → §3 (the trap) → §3.5
> (the runbook, start at STEP −1) → §4 (the gates) → §8 (record as you go).
> §1/§2 are the reasoning; §5/§6/§7 are only needed if Gate A fails or when the
> decision is made.

---

## 0.–1 What this experiment actually is, in plain terms

**Everything below assumed this and never said it. Stated here so nobody has to
infer it from the arithmetic.**

### The model

`lerobot/pi05_base` — Physical Intelligence's π0.5, via LeRobot's port. **4.14B
parameters**, in two parts:

```text
VLM backbone            ~3.45B   sees the camera image, reads the instruction
action expert + proj.    ~693M   turns that into robot joint commands
                        ───────
                         4.14B
```

We start from the **base** model, not from our own `pi05_012000` fine-tune.

### Full fine-tuning — and NOT LoRA. The three modes are easy to blur

```text
MODE                  TRAINABLE   MEMORY        STATUS
full fine-tune          4.14B     UNKNOWN       ← THE QUESTION. All 4.14B get
                                                  gradients and get updated.
expert-only (012000)     693M     26.3 GB       already works. VLM frozen
                                                  entirely; only the action
                                                  expert trains.
LoRA / PEFT            ~1% adapt. >22.5 GB      would fit easily - NOT the
                                                  question, not in dispute
```

⇒ **LoRA is not the answer here because it was never in doubt.** OpenPI lists it
at >22.5 GB and it obviously fits in 32. The $11K question is specifically about
**full-parameter** training. LeRobot's `peft` config field must stay `None`, and
Gate B checks it.

### ⇒ Therefore: what "693M" means at Gate B, and why the run stops

**693M is the number you get when the whole VLM is frozen** — our existing,
already-measured recipe. If the trainable counter reads 693M, the run is training
**17% of the model**, will comfortably fit, and would be read as *"the 5090
handles full fine-tuning"* — **when full fine-tuning was never tested.** That is
re-measuring August's result and then declining an $11K purchase on it.

⚠ **This is not paranoia.** `train_expert_only` and `freeze_vision_encoder` can
arrive from the **pretrained checkpoint's own config**, not only from the command
line. Passing `--policy.train_expert_only=false` states an *intention*; counting
parameters is what confirms it **took effect**. Exactly the same shape as the
optimizer trap in §3: flag accepted, value overridden, nothing warns you.

### What this run is, and is not

```text
IS      a MEMORY PROBE. 100 steps, checkpointing off. The output is a VRAM
        number, not a model. Nobody should expect a usable policy from it.
IS NOT  proof that pi05 can be practically trained on this card. Gate A passing
        means 4.14B params FIT - at batch size 1, with no gradient accumulation
        available (§3). Whether that is fast enough to be a real recipe is a
        SEPARATE question, which is why §6 scores slowdown alongside peak VRAM.
```

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
`install/` trap. Three routes were considered:

```text
A  install THIS repo (0.5.2) editable into a venv with accelerate+transformers
   ⇒ the edit takes effect, but it is a VERSION CHANGE on top of a memory
     experiment. Two variables at once. REJECTED.
B  patch the 0.4.4 copy inside sim/Isaac-GR00T-n16/.venv in place
   ⇒ version matches the OOM ladder, but it mutates the venv that produced the
     GR00T results, and `pip install bitsandbytes` into it could drag a torch
     reinstall. REJECTED - that venv is not disposable.
C  ★ FRESH venv, pinned:  torch==2.7.1+cu128  +  lerobot==0.4.4  +  bitsandbytes
   ⇒ same lerobot version as the OOM ladder, ZERO risk to the GR00T track,
     and the patch has somewhere honest to live. CHOSEN.
```

**Why those exact pins** — both verified 2026-08-11:

```text
torch 2.7.1+cu128   the build in the GR00T venv. arch list includes sm_120 and
                    compute_120; the GPU reports capability (12, 0). A default
                    `pip install torch` may NOT carry Blackwell kernels, so this
                    is pinned deliberately, not incidentally.
lerobot 0.4.4       present on PyPI (checked), and the version that produced the
                    §0 OOM ladder. Holds the version fixed against those numbers.
```

⚠ **Re-check §2 and §3 against the fresh tree once built** — the optimizer
registry differs between 0.4.2 / 0.4.4 / 0.5.2 (below), so confirm what 0.4.4
actually registers rather than trusting the count here.

### ⛔ The 8-bit precedent does NOT exist — this is the real risk

§0 previously cited the GR00T result — `adamw_bnb_8bit`, 23.1 GB, zero OOM — as
proof that 8-bit Adam works on this card. **It is not reproducible from current
machine state:**

```text
searched   all three venvs · /opt · /usr/lib/python3* · the uv cache
found      NOTHING. The only hits are transformers/ and diffusers/ INTEGRATION
           SHIMS that are merely named bitsandbytes - not the package.
```

Either the GR00T venv was rebuilt since (there is an `N16_REBUILD_RUNBOOK.md`,
so this is plausible) or the claim is wrong. **Either way we cannot lean on it.**

⇒ **`bitsandbytes` has never been demonstrated on this Blackwell card**, and the
whole ~25 GB figure in §1 assumes it works. bnb's Blackwell support has
historically lagged. **That is why §3.5 now opens with STEP −1**: prove one
`AdamW8bit` step runs on sm_120 before spending anything else.

⇒ **Correct the §0 wording when this is settled** — replace "proven on this card"
with whatever STEP −1 actually measures.

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
recipe.

⚠ **The 8-bit claim below is UNDER DISPUTE — do not cite it until STEP −1
settles it.** `REALARM_RESULT_20260808.md` records the GR00T track breaking its
ceiling with `adamw_bnb_8bit`: 100 probe steps, 4.15 it/s, **23.1 GB, zero OOM**.
**But `bitsandbytes` is nowhere on this machine** (§0.0), so that result cannot
currently be reproduced or confirmed. Treat 8-bit-on-Blackwell as **unproven**,
not as validated prior art.

```text
CONFIRMED on this GPU   torch 2.7.1+cu128 carries sm_120 / compute_120 kernels;
                        device capability reads (12, 0)
NOT CONFIRMED           that bitsandbytes has working sm_120 kernels here
```

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
`--optim adamw_bnb_8bit` — which does not apply here. And **`bitsandbytes` is
not present anywhere on this machine** — no venv, no uv cache (§0.0) — so that
result is also **not currently reproducible**. STEP −1 exists because of this.

So this needs a small code change, not a flag:

```text
1. pip install bitsandbytes into the fresh probe venv (§0.0 route C)
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
# the FRESH venv from §0.0 route C — NOT the GR00T venv
source /home/kiran/sim/pi05-fullft-probe/.venv/bin/activate

lerobot-train \
  --dataset.repo_id=lerobot/libero_spatial_image \
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

**PINNED: `lerobot/libero_spatial_image`** — 6.60 GB, 75 files, from the LeRobot
org itself. Sizes checked 2026-08-11 against 1.6 TB free:

```text
lerobot/libero_spatial_image    6.60 GB   ★ chosen - LeRobot org, pi05 docs
                                            report 97.0% on Libero Spatial
lerobot/libero_goal_image       6.31 GB     marginally smaller, equivalent
lerobot/libero_object_image     9.25 GB
physical-intelligence/libero   (the openpi-side set - different stack)
```

⚠ **`rename_map` is UNVERIFIED for this dataset and is the most likely cause of
a step-5 smoke failure.** `pi05_base` uses pi0 camera naming, which is why the
real-arm run needed `--rename_map front->base_0_rgb, wrist->left_wrist_0_rgb`.
Inspect the LIBERO feature keys before the smoke run, and **do not let a startup
failure here be misread as a memory result.**

⚠ LeRobot's own `docs/source/pi05.mdx` shows the full-FT command with
`--policy.compile_model=true`. **We use `false`** — compile adds its own memory
and time overhead and would confound a memory measurement. Note it, don't copy it.

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
STEP                                     CHECK IT WORKED                  COST
──────────────────────────────────────────────────────────────────────────────
-1 ⭐ DOES bitsandbytes WORK ON sm_120?   a real AdamW8bit step completes  ~5 min
   THE GATE ON EVERYTHING ELSE (§0.0).    and the param CHANGES:
   Fresh venv, torch==2.7.1+cu128,
   bitsandbytes. Toy model, one step:       import torch, bitsandbytes as bnb
                                            m = torch.nn.Linear(4096, 4096).cuda()
   ⛔ IF THIS FAILS, STOP AND REPORT.       o = bnb.optim.AdamW8bit(m.parameters())
   §1's ~25 GB assumes 8-bit states.        m(torch.randn(8,4096,device='cuda')
   No 8-bit -> persistent stays 49.7 GB       ).sum().backward(); o.step()
   -> 32 GB is hopeless -> the answer
   is "not by this route", for 5 min      ⚠ a CUDA kernel/arch error here is
   instead of 90.                            THE RESULT, not a setup bug.

0  finish the venv: lerobot==0.4.4        python -c "import lerobot,torch;print(
   (§0.0 route C, at                        lerobot.__version__, torch.__version__)"
   /home/kiran/sim/pi05-fullft-probe)     -> 0.4.4 and 2.7.1+cu128
   ⇒ NOTHING here touches the GR00T       ⚠ if installing lerobot DOWNGRADES
     venv. No snapshot, no revert.           torch off 2.7.1+cu128, reinstall the
     That whole hazard is designed out.      pin and re-run STEP -1.

1  confirm what 0.4.4 registers          grep register_subclass on the FRESH
                                          tree - the count differs by version

2  add AdamW8bitConfig (§2)               adamw_8bit now listed

3  point get_optimizer_preset at it       one line changed
   ⛔ NOT the CLI flag - see §3 trap

4  capture 2+3 as a patch into            the .patch file exists and applies
   projects/testproject/patches/          clean
   ⛔ site-packages is NOT version
      controlled. Skip this and the
      work is lost on the next sync.

5  dataset: inspect feature keys,         key names known BEFORE the run
   then smoke at --steps=2                it starts, loss prints, no OOM
                                          ⚠ a rename_map failure here is NOT a
                                            memory result. See §3.       ~15 min
                                            (6.6 GB + pi05_base download)

6  GATE B, before the real run            trainable ~4.14B (§4). If 693M,
   cheap, and it voids everything           STOP - everything after is void.
   downstream if it fails

7  the 100-step run + VRAM logging        §4 Gate A                      ~40 min

7b bs1 EXPERT-ONLY reference run          the ONLY like-for-like slowdown ~5 min
   same venv, same session, 100 steps,      denominator (§6). Without it,
   train_expert_only=true                    "Nx slower" mixes batch size and
   ⇒ gives peak VRAM AND steps/s for         trainable set and must not be
     the recipe we already run                quoted.

8  fill in §8 and apply §6 as written     the results block has no blanks
```

⇒ **The ordering is the point.** Three things can each make this experiment
produce a confident wrong number, and **none of them announces itself**: 8-bit
silently unavailable on Blackwell (STEP −1), the optimizer silently overridden by
the preset (§3), and the fine-tune silently partial (Gate B). Each is checked
before the expensive step that depends on it, cheapest first.

---

## 4. Acceptance — two gates, both required

### Gate A: it fits

```text
peak VRAM < 31 GB, 100 steps complete, loss FINITE throughout
```

⛔ **"loss decreasing" was the wrong criterion and has been removed.** At
**batch size 1** the per-step loss is dominated by per-sample variance; 100 steps
is far too few for a trend to be visible. **A flat or noisy loss curve here is
EXPECTED and is not a failure** — reading it as one would throw away a valid
memory result.

```text
PASS   no NaN, no inf, at any step
FAIL   NaN/inf  -> a real defect (bf16 overflow, or 8-bit optimizer instability).
                   Investigate; do NOT record a VRAM number from that run.
IGNORE whether the loss went down. This run is not learning anything and is not
       meant to. See §0.-1: it is a memory probe, not a training run.
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
       ⇒ the VLM backbone IS training. This is a real full fine-tune.

FAIL   trainable ~0.69B (ratio ~0.17)   -> THE 012000 RECIPE. The VLM is frozen
                                           and only the action expert trains.
                                           This is the already-measured 26.3 GB
                                           configuration - it WILL fit, and that
                                           fact means nothing. VOID THE RUN.
FAIL   vlm list EMPTY                   -> expert-only by another route
FAIL   trainable << total, not 0.69B    -> check cfg.peft is None. LoRA also
                                           fits, and also is not the question.
```

⇒ **Why this runs BEFORE the 40-minute measurement:** it costs one model load,
and it decides whether that measurement means anything at all. See §0.–1.

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

⛔ **THE SLOWDOWN DENOMINATOR IS CONFOUNDED — fix it before applying this table.**
The obvious baseline, `1.4 steps/s`, is **bs4 expert-only**. Comparing full-FT at
**bs1** against it varies **two things at once** — batch size *and* which
parameters train — so the resulting "Nx" is not a slowdown, it is a mixture.

```text
⇒ REQUIRED: a bs1 EXPERT-ONLY reference run, same venv, same session, ~5 min.
  That is the only like-for-like denominator: same batch size, only the
  trainable set differs. Added as runbook step 7b.
⇒ AND report samples/s, not steps/s. bs4 at 1.4 steps/s is 5.6 samples/s;
  bs1 at 1.4 steps/s is 1.4. Comparing steps/s across batch sizes overstates
  the full-FT result by 4x in our favour.
```

⚠ If step 7b is skipped, **write "slowdown not measured" in §8 and apply the
table on peak VRAM alone** — do not quote a confounded ratio. A fabricated 2x
lands in a different row than a fabricated 5x, and that row is an $11K decision.

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

STEP -1  bitsandbytes on Blackwell sm_120   ⭐ gates everything
  bitsandbytes version     ____
  AdamW8bit step ran       PASS / FAIL
  param actually changed   ____
  if FAIL, the error       ____
  VERDICT                  if FAIL: §1's 25 GB is void, persistent stays
                           49.7 GB, answer is "not by this route". STOP HERE
                           and record it - that IS the deliverable.

tree used                  fresh probe venv (§0.0 route C)
  lerobot.__version__      ____   expected 0.4.4
  torch.__version__        ____   expected 2.7.1+cu128
  __file__                 ____
8-bit route                ____   preset-patch | CLI flag  (§3 trap)
dataset repo_id            lerobot/libero_spatial_image
  rename_map needed?       ____   feature keys seen: ____
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
  steps/s                  ____      samples/s ____ (= steps/s x batch)
  loss FINITE throughout   ____      ⚠ do NOT score whether it decreased
                                        (§4 - meaningless at bs1)

STEP 7b  bs1 expert-only reference       the like-for-like denominator
  peak VRAM                ____ GB
  steps/s                  ____
  ⇒ SLOWDOWN               ____x    full-FT bs1 / expert-only bs1
  if 7b was skipped        write "slowdown NOT MEASURED" and apply §6 on peak
                           VRAM alone. ⛔ Do not quote the bs4 1.4 steps/s
                           figure as a denominator - different batch size.
  if OOM, WHERE            load / optim init / forward / backward / optim step

DECISION (§6 rule, applied without renegotiating it)   ____
venv reverted (step 8)     ____
```

⇒ **Write the decision from the §6 table as-is.** The rule was fixed before the
result specifically so the $11K call is not re-argued once a number is in hand.
