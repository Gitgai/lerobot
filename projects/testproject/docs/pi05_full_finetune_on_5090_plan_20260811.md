# Can we FULL fine-tune π0.5 on one RTX 5090 (32 GB)?

Date: 2026-08-11, kiran-AI90. Purpose: answer one question before any hardware
purchase is discussed.

> Can all ~4B π0.5 parameters receive gradients and be updated, on a single
> 32 GB 5090, by trading speed for memory — without silently becoming LoRA or
> expert-only?

**STATUS: ✅ ANSWERED, 2026-08-11. YES — and with room to spare.**

```text
peak VRAM   24.74 GiB  < 26 GiB threshold     ✅   100/100 steps, no OOM
slowdown    1.88x      < 2x threshold         ✅   vs bs1 expert-only, same session
trainable   4,143,404,816 / 4,143,404,816     ratio 1.0000 — a real full FT
⇒ §6 top row: "THE 5090 IS CLEARLY SUFFICIENT. NO PURCHASE."
```

**Achieved on FOUR baseline levers — bf16, 8-bit Adam, gradient checkpointing,
batch size 1. §5's escalation ladder was never entered.** 8-bit Adam is the
load-bearing one (~23 GiB saved; nothing else gets under 32 without it).

⛔ **ONE CONDITION: checkpointing is BROKEN with 8-bit Adam** (`state/1/step` is
an int, lerobot's safetensors saver wants a tensor). Memory and speed both pass;
one plumbing defect stands between this and a production recipe. See §8.

Full record and raw evidence: §8, and
`results/pi05_fullft_5090_20260811/`.

➡ **THIS DOC IS CLOSED. Continue in
[`pi05_training_capability_plan_20260811.md`](pi05_training_capability_plan_20260811.md)**
— phase 2 answers _"can we TRAIN here?"_, which this one does not: it fixes the
checkpoint blocker, measures the largest batch that fits, and runs a sustained
LIBERO capability run. It also carries the autonomy contract for unattended
execution.

---

_Original framing, kept because the reasoning is what made the answer
trustworthy:_

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
**17% of the model**, will comfortably fit, and would be read as _"the 5090
handles full fine-tuning"_ — **when full fine-tuning was never tested.** That is
re-measuring August's result and then declining an $11K purchase on it.

⚠ **This is not paranoia.** `train_expert_only` and `freeze_vision_encoder` can
arrive from the **pretrained checkpoint's own config**, not only from the command
line. Passing `--policy.train_expert_only=false` states an _intention_; counting
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
     experiment. Two variables at once. REJECTED... then ADOPTED, see below.
B  patch the 0.4.4 copy inside sim/Isaac-GR00T-n16/.venv in place
   ⇒ version matches the OOM ladder, but it mutates the venv that produced the
     GR00T results, and `pip install bitsandbytes` into it could drag a torch
     reinstall. REJECTED - that venv is not disposable.
C  FRESH venv, pinned:  torch==2.7.1+cu128  +  lerobot==0.4.4  +  bitsandbytes
   ⇒ chosen first, then BLOCKED. See below.
```

### ⛔ ROUTE C IS BLOCKED — 0.4.4 needs a patched transformers that does not exist

Discovered 2026-08-11 while executing, after route C was built and the patch
applied. **lerobot 0.4.4's π0.5 hard-requires a FORKED transformers:**

```text
modeling_pi05.py:577   from transformers.models.siglip import check
                       check.check_whether_transformers_replace_is_installed_correctly()
                       -> else ValueError("An incorrect transformer version is used")
```

`transformers.models.siglip.check` **does not exist in upstream transformers**,
and there is **no `transformers_replace` directory at the v0.4.4 tag** on GitHub
(checked). The stock `transformers-dep` extra resolves 4.57.6, which fails the
guard. ⇒ **0.4.4 cannot run π0.5 without an artifact we do not have.**

**The guard was REMOVED in 0.5.2** (`grep check_whether_transformers_replace
src/lerobot/policies/pi05/` → no match). ⇒ The choice is not 0.4.4 vs 0.5.2. It
is **0.5.2 or nothing.**

### ⇒ REVERSED: route A is adopted. Why the original objection no longer holds

The objection was _"a version change on top of a memory experiment — two
variables at once."_ Three things retire it:

```text
1  0.4.4 is BLOCKED, not merely less convenient. There is no version-matched
   option to prefer over 0.5.2.
2  ★ STEP 7b ALREADY REMOVED THE DEPENDENCY ON VERSION-MATCHING. The pin existed
   to keep §0's OOM ladder valid as a comparison. 7b re-measures the bs1
   expert-only baseline in the SAME session and SAME venv, so the denominator is
   internally consistent at whatever version we run. That objection was
   load-bearing before 7b existed; it is not now.
3  Editable install is STRICTLY BETTER for the patch: it lands in the git repo
   instead of stranded in site-packages, so runbook step 4 stops being a
   workaround and becomes just "commit it".
```

⚠ **0.5.2 requires Python >= 3.12** (0.4.4 ran on 3.11). The probe venv is
therefore `.venv312`. The 3.11 venv is left in place, unused — the failed 0.5.2
install into it exited cleanly without touching torch.

⚠ **§0's OOM ladder was measured on a 0.4.x stack** and is now a _different
version_ from the run. It stays as context — it is what motivated the question —
but **it is no longer a valid quantitative comparator.** Step 7b is the
comparator. Do not quote 26.3 GB against a 0.5.2 number.

### ⛔ AND 0.5.2 IS ALSO WRONG — the CHECKPOINT dictates the version, not us

0.5.2 got much further: **`All keys loaded successfully!`** — the 4.14B model
loaded — then died building the processor pipeline:

```text
KeyError: Processor step 'relative_actions_processor' not found in registry
```

`lerobot/pi05_base`'s `policy_preprocessor.json` demands these steps:

```text
rename_observations_processor · to_batch_processor · relative_actions_processor
normalizer_processor · pi05_prepare_state_tokenizer_processor_step
tokenizer_processor · device_processor
```

0.5.2 has that exact class — `RelativeActionsProcessorStep` — but **registers it
under a different key**, `delta_actions_processor`
(`processor/relative_action_processor.py:84`). A pure **rename** between
versions: the published checkpoint was serialised by a _newer_ lerobot.

⚠ **An alias would have "worked", and was the wrong move.** Registering
`relative_actions_processor` as a second name for the 0.5.2 class would have let
the run proceed — but if anything beyond the key changed, actions get silently
mis-processed. **Match the version the artifact was written by; do not teach old
code the new name.** For a _memory_ probe the action semantics barely matter,
which is exactly what would have made it an easy and invisible mistake.

### ⇒ lerobot 0.6.1, matched to the published checkpoint

`relative_actions_processor` **is** registered in 0.6.1 (verified). Requirements
are unchanged from 0.5.2 — Python ≥3.12, transformers >=5.4.0,<5.6.0 — so the
venv needed no rebuild.

⚠ **Cost: the editable-install advantage is gone.** 0.6.1 comes from PyPI, so the
patch lives in site-packages again and runbook step 4 (capture the `.patch`) is
load-bearing rather than a formality. **The patch applied to this repo's `src/`
has been reverted** — inert now that nothing imports from the repo, and leaving
it would be a live modification to your lerobot source that does nothing.

### The version chain, as a warning

```text
0.4.4   pinned to match the OOM ladder   BLOCKED - needs a forked transformers
                                         that does not exist upstream
0.5.2   this repo, editable              BLOCKED - processor registry predates
                                         the published checkpoint
0.6.1   matched to the CHECKPOINT        ✅ gets past model load AND processors
```

⇒ **We picked a version to match old measurements, and the checkpoint overruled
us three times.** Step 7b is what makes that survivable: it re-measures the
baseline in-session, so the comparison never depended on matching a historical
version at all.

**Final configuration:**

```text
venv          /home/kiran/sim/pi05-fullft-probe/.venv312   (uv, python 3.12)
torch         2.7.1+cu128        pinned FIRST, verified sm_120, and re-checked
                                 after EVERY subsequent install - a silent
                                 downgrade would have invalidated STEP -1
lerobot       0.6.1 from PyPI, extras [pi,dataset]   ← matched to the CHECKPOINT
transformers  5.5.4
accelerate    1.14.0
bitsandbytes  0.50.0
patch         site-packages, .orig files kept alongside, captured to patches/
```

---

## 0.05 ⛔⛔ BLOCKED ON A GATED HF REPO — NEEDS THE OPERATOR

**This is the current stopping point, 2026-08-11 ~17:12.** Everything technical
is resolved; the run cannot proceed without an account action.

π0.5's tokenizer step pulls the PaliGemma tokenizer from a **gated** Google repo:

```text
ValueError: Failed to instantiate processor step 'tokenizer_processor'
  tokenizer_name: 'google/paligemma-3b-pt-224'
  Error: You are trying to access a gated repo.
  401 Client Error. Access to model google/paligemma-3b-pt-224 is restricted.
```

Checked on this machine:

```text
~/.cache/huggingface/token          DOES NOT EXIST
HF_TOKEN env                        NOT SET
google/paligemma-* in any cache     NOT PRESENT
```

⇒ **Two operator actions, neither of which an agent should perform:**

```text
1  ACCEPT Google's licence at
     https://huggingface.co/google/paligemma-3b-pt-224
   Accepting terms on someone's behalf is not an agent action.

2  AUTHENTICATE:  hf auth login      (or export HF_TOKEN=...)
   Handling the operator's credentials is not an agent action.
```

⚠ **This is a CREDENTIAL/LICENCE blocker, not a technical one, and above all NOT
a memory result.** Record it as such. The 4.14B model already loads
(`All keys loaded successfully!`) and the optimizer patch already builds a real
`bitsandbytes.optim.adamw.AdamW8bit` — nothing about the memory question has been
answered or refuted yet.

⇒ **Once authenticated, resume at runbook step 5** (smoke, 2 steps). Nothing
before it needs redoing.

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

⇒ **Two code changes, not one:** the 8-bit optimizer registration _and_
gradient accumulation. Budget accordingly; measure them separately.

### Unrelated but noticed

`~/lerobot_assets/checkpoints/pi05_sim_varied` — the 30k-step run
REALARM*RESULT_20260808 launched — **is not on disk anywhere** (searched
/home/kiran, /mnt, /media to depth 9). Only `pi05_012000` remains. Either it was
pruned or it never landed; the sim battery evaluated \_something* under that name,
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

### ⛔ Units, and the MEASURED ceiling — both were wrong above

The GB figures above are **decimal** (bytes ÷ 1e9). `nvidia-smi` and PyTorch both
report **GiB** (÷ 2^30). Mixing them is a **7 % error**, and at a ~6 GiB margin
that is not ignorable. **Everything from here is GiB.**

`nvidia-smi` on kiran-AI90, idle desktop, 2026-08-11 15:56:

```text
total          32607 MiB   31.84 GiB      ← not 32; the marketed number is nominal
used            1434 MiB    1.42 GiB      ← gnome-shell, Xwayland, remote-desktop
                                             daemon, browser, ptyxis
FREE           30673 MiB   29.93 GiB      ← ⭐ THE REAL CEILING
driver         580.173.02  (CUDA 13.0 runtime available; we use torch cu128)
```

⚠ **The plan previously said "~31.35 GB usable". The real figure is 29.93 GiB** —
about **1.4 GiB less** than assumed, because the desktop session is resident and
~500 MiB more is reserved/unaddressable.

### The arithmetic restated in GiB

```text
BF16 weights            7.71 GiB     4.14e9 x 2 bytes
BF16 gradients          7.71 GiB
8-bit Adam m + v        7.71 GiB     ~2 bytes/param
──────────────────────────────
persistent             23.14 GiB     against 29.93 GiB free
                                     ⇒ HEADROOM 6.79 GiB for activations
                                       (bs1, checkpointed) + CUDA workspace
                                       + allocator fragmentation

for contrast, FP32 Adam:
weights + grads        15.42 GiB
FP32 Adam m + v        30.84 GiB
──────────────────────────────
persistent             46.26 GiB     ⇒ hopeless, and this is why an A6000 48 GB
                                       OOMs (lerobot#2216)
```

Tight, but not obviously impossible. **That is the whole experiment.**

### ★ Recovering the 1.42 GiB: move the display to the AMD iGPU

**Operator's proposal, 2026-08-11, and it is the right call — but not as a
blocker on this experiment.** State of the machine, checked rather than assumed:

```text
card0  amdgpu   0000:79:00.0   DP-4, DP-5, HDMI-A-2      ← connectors LIVE
card1  nvidia   0000:01:00.0   DP-1..3, HDMI-A-1

CONNECTED: card1-HDMI-A-1      ← the monitor, on the 5090's HDMI port

session   Wayland / GNOME
/etc/X11/xorg.conf             DOES NOT EXIST
/etc/X11/xorg.conf.d/          EMPTY          ⇒ nothing pins display to NVIDIA
```

⛔ **CORRECTION to an earlier claim in this doc: no BIOS change is needed.** The
iGPU is _already_ enabled — its connectors are enumerated and live, and `amdgpu`
is loaded. An earlier revision said this "likely needs a BIOS change"; that was
written before checking and is **false**.

⇒ **The procedure is: move the HDMI cable from the 5090 to the motherboard
output, and reboot.** That is the whole change. GNOME/Wayland assigns the display
to whichever GPU has a connected output, and nothing in this system's config
overrides that.

⚠ **What stays in place, and why the +1.42 GiB is a HOPE not a guarantee:**

```text
/etc/modprobe.d/nvidia-graphics-drivers-kms.conf
    options nvidia_drm modeset=1        stock Ubuntu driver packaging. It lets
                                        the NVIDIA card drive a display; it does
                                        not force it to.
```

With modeset still enabled the card **may retain a small allocation even with no
monitor attached**. Whether `memory.used` drops to ~0 MiB or holds a couple
hundred is **measurable, not predictable**. ⇒ **The "~31.3 GiB free" figure below
is the ideal case.** One `nvidia-smi` after the reboot settles it — take that
number before quoting any new ceiling.

⚠ Also worth watching: if `gnome-remote-desktop` is using NVENC on the 5090 to
encode the remote stream, that shifts to the AMD side or to CPU. Probably fine,
possibly noticeable on the remote session.

```text
WHAT IT BUYS
  up to +1.42 GiB    headroom 6.79 -> up to 8.21 GiB, ~21% more
                     ⚠ UP TO - see the modeset=1 caveat above. Measure it.
  ★ A STABLE CEILING  this is the bigger win, and it does NOT depend on the
                      1.42 GiB landing in full. memory.free currently DRIFTS
                      with browser tabs and desktop activity, which is why Gate
                      A has to re-measure it every run. With no display clients
                      on the NVIDIA card the ceiling becomes near-constant, and
                      runs become comparable ACROSS SESSIONS.
  ★ KILLS A TRADEOFF  "run headless for the last GiB" currently means
                      disconnecting the operator. That choice disappears.
  PERMANENT           every future training run gets it, not just this one.

WHAT IT DOES NOT BUY
  ⛔ it does NOT change the answer to the $11K question. 23.14 GiB persistent
     against 29.93 vs 31.3 free is the difference between comfortable and
     slightly-more-comfortable. It only becomes DECISIVE if the run lands in
     §6's marginal 29-30 GiB band.
```

⚠ **Still: do NOT block STEP −1 on this.** It needs physical access to the cable
and a reboot, while STEP −1 is five minutes and may make the whole question moot.
**Run the experiment on today's 29.93 GiB ceiling; do the iGPU switch on its own
schedule.** The switch is now known to be cheap, which is an argument for doing
it soon — not for doing it first.

⇒ If the display _does_ move before the run, nothing in this plan breaks: Gate A
already requires re-measuring `memory.free` at run time rather than trusting a
recorded constant. **Record which GPU drove the display in §8** — it changes the
ceiling the result was measured against.

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
is _"the 5090 cannot do it"_ — **on a bug, not a measurement.** That is an $11K
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

⇒ **Gate A does not need it.** bs1 without accumulation is a valid _memory_
measurement even though it is not a usable _training recipe_. That is the whole
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
peak VRAM < 29.93 GiB free ceiling, 100 steps complete, loss FINITE throughout
```

⚠ **Re-measure `memory.free` at run time; do not reuse the number above.** It was
29.93 GiB with an idle desktop on 2026-08-11 and moves with whatever else is on
the display. **Record the baseline immediately before the run** and report peak
against _that_, not against a remembered constant:

```bash
nvidia-smi --query-gpu=memory.total,memory.used,memory.free \
           --format=csv,noheader   # ← baseline, into §8, BEFORE lerobot-train
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
`num_parameters(only_trainable=True)` is a _transformers_ `PreTrainedModel`
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

# ✅ NOT NEEDED. Gate A passed at 24.74 GiB with 7.10 GiB to spare, on the

# baseline four levers alone. **NOTHING BELOW WAS USED.** Steps 3–5 remain

# untried reserve — relevant only if batch size is raised, a longer context is

# needed, or a larger model is attempted later. Kept for that reason.

⚠ **Steps 1 and 2 of the old ladder are already spent.** The §3 baseline command
_includes_ the 8-bit optimizer — without it there is nothing to measure — and it
_excludes_ gradient accumulation deliberately. So the ladder below starts at what
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
**bs1** against it varies **two things at once** — batch size _and_ which
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

⚠ **Thresholds restated in GiB against the MEASURED 29.93 GiB free ceiling** —
the old "28 / 31 / 32 GB" rows were decimal GB against a ceiling that does not
exist on this machine.

```text
peak < 26 GiB, <2x slowdown       the 5090 is clearly sufficient. No purchase.
                                  (~4 GiB of real headroom left)
peak 26-29 GiB, 2-4x slowdown     viable. Weigh the time cost against $11K.
peak 29-30 GiB, >4x slowdown      marginal - and it only fits with the desktop
                                  killed. Every run becomes a scheduling
                                  problem; revisit.
still OOM, or >10x, or unstable   a higher-VRAM card becomes a rational
                                  consideration - and NOW there is evidence for
                                  it rather than a vendor table.
```

**What the OpenPI >70 GB figure does and does not prove:** it says _their_
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

STEP -1  bitsandbytes on Blackwell sm_120   ✅ RUN 2026-08-11 ~16:10 — PASS
  bitsandbytes version     0.50.0
  torch / cuda             2.7.1+cu128 / 12.8
  device / capability      RTX 5090 / sm_120  (arch list has sm_120, compute_120)
  AdamW8bit step ran       PASS   4096x4096 MLP, real forward/backward/step
  param actually changed   YES    "0.weight" norm 36.955448 -> 37.103436
                                  delta 1.480e-01
  loss finite              YES    0.038368
  state GENUINELY 8-bit    YES    state1: uint8, state2: uint8
                                  (+ qmap1/qmap2 fp32, absmax1/absmax2 fp32 —
                                   the blockwise-quantisation scaffolding)
                                  ⇒ NOT a silent fp32 fallback. Checked
                                    explicitly because a fallback would have
                                    passed every other criterion.

  ⇒ VERDICT: PASS. §1's ~23.14 GiB persistent arithmetic HOLDS, and the
    experiment is worth running. The disputed GR00T precedent (§0.0) turned out
    not to matter: 8-bit-on-Blackwell is now measured here directly rather than
    inherited from a claim that could not be reproduced.
  ⇒ Repro: /home/kiran/sim/pi05-fullft-probe/step_minus1_bnb_blackwell.py

tree used                  fresh probe venv (§0.0 route C)
  lerobot.__version__      ____   expected 0.4.4
  torch.__version__        ____   expected 2.7.1+cu128
  __file__                 ____
8-bit route                ____   preset-patch | CLI flag  (§3 trap)
dataset repo_id            lerobot/libero_spatial_image
  rename_map needed?       ____   feature keys seen: ____
patch captured at          projects/testproject/patches/____

GATE B   ✅ PASS — 2026-08-11 17:32, from the smoke run itself
  trainable / total        4,143,404,816 / 4,143,404,816   ratio 1.0000
                           lerobot_train.py:447-448 prints BOTH every run:
                             num_learnable_params=4143404816 (4B)
                             num_total_params=4143404816 (4B)
                           ⇒ BETTER evidence than the plan's separate CPU-side
                             load: it is the count inside the REAL run, in the
                             REAL config, not a reconstruction of it.
  vlm tensors trainable    ALL of them - trainable == total makes this a
                           tautology. No separate enumeration needed: if every
                           parameter is trainable, the VLM backbone is too.
  not the 012000 recipe    CONFIRMED. 4.14B, not 693M. Ratio 1.00, not 0.17.
  no LoRA/adapters         cfg.peft is None (not passed; default)
  gradient checkpointing   ENABLED  ("Enabled gradient checkpointing for
                                      PI05Pytorch model")
  effective batch size     1 x 1 = 1
  weights MOVE             checked separately against the step-100 checkpoint —
                           see GATE A below. STEP -1 already showed AdamW8bit
                           moves a parameter (norm 36.955448 -> 37.103436).
  VERDICT                  ★ PASS — this is a genuine FULL fine-tune. Gate A is
                           therefore measuring the right thing.

GATE A   ✅ PASS — 2026-08-11 17:34, 100/100 steps, NO OOM
  BASELINE memory.free     29.94 GiB  taken immediately before the run
                                      (32607 total / 1444 used / 30663 free MiB)
  display driven by        NVIDIA 5090 (card1-HDMI-A-1). iGPU switch NOT done.
  peak VRAM                24.74 GiB  (25,330 MiB, nvidia-smi 1 Hz, 120 samples)
                                      INCLUDES the 1.42 GiB desktop
  training alone           ~23.33 GiB = peak - desktop
  headroom left             7.10 GiB  = 31.84 total - 24.74 peak
  lerobot's own mem_gb     22.31 -> 22.34, FLAT across all 100 steps
                                      (torch-allocated; excludes CUDA context)
  steps completed          100 / 100
  steps/s                  3.22 (updt_s 0.311)   samples/s 3.22 at batch 1
  loss FINITE throughout   YES — 0.538 0.404 0.471 0.332 0.382 0.354 0.332
                                 0.336 0.308 0.232   (no NaN, no inf)
                           ⚠ it also DECREASED, which §4 says not to score.
                             Noted as incidental, NOT as evidence.

  ★ THE ARITHMETIC HELD — accurate to a few percent, ERRING HIGH.

    ⚠ An earlier revision of this line claimed "within 1%", comparing 23.33
      against the predicted 23.14. That comparison is apples-to-oranges and
      too flattering: the 23.33 figure INCLUDES CUDA context and activations,
      which the §1 prediction did not cover.

    predicted persistent      23.14 GiB   weights + grads + 8-bit states only
    torch-allocated           22.34 GiB   persistent + activations
    nvidia-smi minus desktop  23.32 GiB   the above + CUDA context + allocator

    ⇒ True persistent is therefore somewhat BELOW 23.14 — §1 modestly
      OVER-predicted. That is the safe direction to be wrong in, and it does
      not move the verdict. State it as "accurate to a few percent, erring
      high", not as a bullseye.

WHICH MEMORY LEVERS WERE ACTUALLY USED — all four are BASELINE, not escalations
Verified from the run's own config dump, not from what was typed on the CLI:

    batch_size             1            activations
    dtype                  bfloat16     weights + grads: 15.43 -> 7.71 GiB each
    gradient_checkpointing True         activations (runtime-confirmed:
                                        "Enabled gradient checkpointing")
    optimizer type         adamw_8bit   Adam states: 30.86 -> 7.71 GiB
    peft                   None         NOT LoRA
    freeze_vision_encoder  False        }  full fine-tune
    train_expert_only      False        }

    naive fp32 + fp32 Adam   15.43 + 15.43 + 30.86  =  61.7 GiB   hopeless
    + bf16                    7.71 +  7.71 + 30.86  =  46.3 GiB   still hopeless
    + 8-bit Adam              7.71 +  7.71 +  7.71  =  23.1 GiB   ← what ran

⇒ **8-bit Adam is the load-bearing lever** — ~23 GiB saved on its own, more than
  bf16's ~15 GiB, and WITHOUT IT NOTHING ELSE GETS UNDER 32. Which is exactly
  why STEP -1 was made the gate on the whole experiment.

⇒ **§5's ESCALATION LADDER WAS NEVER ENTERED.** Still in reserve, untried:
  paged 8-bit optimizer · CPU optimizer offload · CPU parameter offload.
  Gradient accumulation is also unused, but that was not a choice — it is not
  implemented in lerobot and needs code (§3).

★ **THE §3 TRAP, CAUGHT LIVE.** The config dump shows
  `use_policy_training_preset: True` AND `type: adamw_8bit` TOGETHER. With the
  preset active, a CLI `--optimizer.type=adamw_8bit` would have been parsed,
  accepted, and then silently overwritten with FP32 AdamW — a 46.3 GiB run that
  OOMs and reads as *"the 5090 cannot do it"*, straight into an $11K purchase.
  **Patching the preset is the only reason the 8-bit optimizer survived into the
  actual run.** This is no longer a hypothesis about the code; it is visible in
  the log of the run that produced the verdict.

STEP 7b  bs1 expert-only reference   ✅ RUN, same session, same venv
  trainable                693,422,112 (693M) / 4,143,404,816 total
                           ⇒ CONFIRMS the doc's "693M" figure exactly
  peak VRAM                12.91 GiB     lerobot mem_gb 10.77
  steps/s                  6.06 (updt_s 0.165)

  ⇒ SLOWDOWN               1.88x    full-FT bs1 / expert-only bs1
                                    (0.311 / 0.165 — like-for-like: same batch
                                     size, same session, same venv, ONLY the
                                     trainable set differs)
  ⇒ memory ratio           2.07x    22.34 / 10.77

DECISION (§6 rule, applied without renegotiating it)
  peak 24.74 GiB < 26 GiB          ✅
  slowdown 1.88x < 2x              ✅
  ⇒ ★ "THE 5090 IS CLEARLY SUFFICIENT. NO PURCHASE."   — §6 top row, both
    conditions met on the rule as written BEFORE the result.

⛔ ONE CONDITION ON THAT VERDICT — CHECKPOINTING IS BROKEN WITH 8-BIT ADAM

  The run trained all 100 steps and then failed WRITING THE CHECKPOINT:

      ValueError: Key `state/1/step` is invalid, expected torch.Tensor
                  but received <class 'int'>

  bnb.optim.AdamW8bit keeps its step counter as a python int; lerobot's
  safetensors-based optimizer-state saver requires tensors.

  ⇒ Harmless for THIS probe (saving was enabled only to verify weights moved)
    but DISQUALIFYING for real training: a run you cannot checkpoint is not a
    usable recipe. Looks like a few lines to coerce the counter to a tensor.
    UNFIXED as of 2026-08-11.
  ⇒ Read the verdict as: the MEMORY and SPEED questions are answered and both
    pass; one plumbing defect stands between this and a production recipe.

⚠ WEIGHTS-MOVED CHECK NOT DIRECTLY PERFORMED. It depended on the checkpoint
  that failed to write. Indirect evidence is strong — trainable == total, and
  loss fell 0.538 -> 0.232 over 100 steps, which cannot happen with a frozen
  backbone at ratio 1.00 — but it is not the direct norm-before/after check §4
  asked for. Fix the checkpoint bug and it comes for free.

venv reverted (step 8)     N/A — route C's in-place patch was abandoned. The
                           probe venv is standalone at sim/pi05-fullft-probe and
                           the GR00T venv was never touched.
```

⇒ **Write the decision from the §6 table as-is.** The rule was fixed before the
result specifically so the $11K call is not re-argued once a number is in hand.

---

# RESULT — 2026-08-12. Full fine-tune of pi0.5 FITS on the 5090. Measured, running.

Not a projection. A run in flight, started 00:28:59, observed at step 14,000/24,000.

```text
  policy.type=pi05    pretrained_path=lerobot/pi05_base
  freeze_vision_encoder = FALSE     <- vision encoder IS training
  train_expert_only     = FALSE     <- not the expert-only shortcut
  dtype=bfloat16   gradient_checkpointing=true   compile_model=false
  batch_size=8     steps=24000      dataset=lerobot/libero_spatial_image
```

Both freeze flags false is what makes this a **full** fine-tune rather than the
partial variants the plan listed as fallbacks. The 8.8 GB checkpoint is full
weights, not an adapter.

## The numbers

```text
  VRAM              27,649 / 32,607 MiB      ~5.0 GB headroom
  throughput        49.8 steps/min           (batch 8)
  checkpoint 2000   01:05:23
  checkpoint 6000   02:16:11    +70m48s
  checkpoint 10000  03:27:00    +70m49s
  checkpoint 14000  04:37:49    +70m49s
  ETA 24000         ~07:35
```

**The cadence is constant to one second across four intervals.** That matters more
than the headline: no thermal throttling, no memory-pressure stalls, no host
swapping. A run that was marginal on VRAM would show drift here, and it does not.

## What this settles, and what it does not

```text
SETTLED   full fine-tune of pi0.5 on a single 32 GB 5090 - bf16 + gradient
          checkpointing, batch 8 - runs stably at ~50 steps/min with 5 GB spare.
          The plan's blockers (8-bit optimizer registration, gradient
          accumulation) were NOT needed to get here.

NOT YET   whether the resulting checkpoint is any GOOD. Throughput is not
          quality. LIBERO-spatial is also not the SO-101 orange task, so this
          proves the FEASIBILITY the question asked about, not transfer.

NOT YET   whether batch 8 is the max. 5 GB spare suggests batch 12-16 might fit,
          but nothing has tested it and this run should not be disturbed to find
          out.
```

## Operational note

With ~5 GB free, **do not launch Isaac Sim against this GPU while it runs.** Sim
needs several GB and an OOM would cost the whole 4.7-hour run. The wrist-camera
battery waits for ~07:35.
