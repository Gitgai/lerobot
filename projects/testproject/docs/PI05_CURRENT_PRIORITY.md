# π0.5 / 5090 lane — Current Priority

Last updated: 2026-08-16

**This file is a ROUTER: what is open, in what order, and why. It is NOT a log.**
Detail and evidence: [`pi05_training_capability_plan_20260811.md`](pi05_training_capability_plan_20260811.md) (2,454 lines).
Raw artefacts: `results/pi05_capability_20260811/`.

> **Why this file exists:** priority order previously lived only in chat, so the
> operator's own top priority — the checkpoint gate on rung 4 — got buried as a
> footnote among seven items. **Hard limit ~100 lines.** Follows the pattern of
> `branch1/CURRENT_PRIORITY.md`, which was written after the same failure.

---

## ✅ THE QUESTIONS THAT PROMPTED THIS ARE ANSWERED — do not reopen

```text
can the 5090 full fine-tune π0.5?   YES — 4 long runs, zero throttling, 0%→80%
                                     ⚠ "full" = 3.25B of 4.14B. The 2 LM heads
                                     and the output half of PaliGemma's last
                                     layer are UNREACHABLE from an action loss.
is the $11K RTX PRO 6000 justified?  NO — and bigger batches, the main thing more
                                     VRAM buys, made results WORSE (64.5 vs 80.0)
```

---

## ✅ P0 — DONE 2026-08-15: rung 4 trains, checkpoints AND resumes

```text
2.33 s/step = 2.3x the 8-bit baseline · GPU 20.5 GiB · host 34.1 GB · state fp32
⇒ FIRST rung to pass all three. Rung 3 still fails on resume, and now matters
  less: rung 4 does everything rung 3 does, and resumes.
detail: results/pi05_capability_20260811/step3f_3e_rung4_gate_PASS.txt
```

★ **HOST RAM IS THE NEW BINDING CONSTRAINT, not VRAM.** Rung 4 needs ~34 GB;
dynus wants ~47 GB of the same 59 GB; swap is exhausted. Check `pgrep dynus` is
empty before any long run.

## P1 — BLOCKED ON OPERATOR: move the display to the iGPU

**Verified NOT done, 2026-08-15 23:43.** The monitor is still on the 5090:

```text
card0 = amdgpu (AMD Granite Ridge iGPU)   DP-4, DP-5, HDMI-A-2 all FREE
card1 = nvidia (RTX 5090)                 HDMI-A-1  ← CONNECTED
recheck  for c in /sys/class/drm/card*-*/status; do ... done
do       move the cable to a motherboard port + reboot. No BIOS change needed.
frees    ~1.0-1.9 GiB of VRAM (varies with what the desktop is running)
why      rung 3's paged resume fails by ~1 GiB — plausibly the exact fix
then     rerun the 3f.2b resume test to confirm
```

⚠ Lower value than it was: **rung 4 now does everything rung 3 does AND resumes**,
so this rescues a rung we no longer depend on. Still cheap, still worth doing.

## P2 — 🔴 NEEDS AN OPERATOR DECISION before it can start

**The question is still open and still worth answering: does 8-bit Adam cost
accuracy?** Every result this project has was produced with 8-bit Adam, and
nobody has ever compared it to real fp32 Adam — fp32 does not fit in VRAM
(46.3 GiB vs 29.9 available). Rung 4 is what makes the comparison possible.

⛔ **THE BLOCKER IS NOT THE MACHINE — IT IS THE BASELINE.**

```text
STEP 3d's exact command is UNRECOVERABLE. Searched 2026-08-15: no shell
history, no train_config.json, checkpoints deleted.

KNOWN     pi05_base · libero_spatial_image · bs8 · 24k steps · save_freq 2000
          bf16 + gradient checkpointing (it would have OOM'd otherwise)
NOT KNOWN the rename_map, and whether it truly used pi05_base as the doc says
```

⇒ Comparing a new fp32 arm against 3d's 80.0% may be a TWO-variable comparison,
which is the exact failure mode that cost four launches and a 7 h run this week.

```text
OPTION A  both arms fresh from ONE known config      ~24 h   genuinely 1 variable
OPTION B  fp32 arm only, vs 3d's 80.0%               ~17 h   ⚠ baseline unverified
OPTION C  hold                                          —    changes no decision
```

⚠ **The $11K verdict does not depend on this.** P2 closes the original quality
question; it does not reopen the purchase one.

**Launch spec, fully explicit — do NOT reconstruct it from prose:**
see `pi05_training_capability_plan_20260811.md` §3f.3e "P2 LAUNCH SPEC".

## P3 / P4 — dormant, nothing blocking

```text
P3  3g rerun (starting-checkpoint hypothesis)  ~7 h · affects NO decision.
    ⚠ its original premise is RETRACTED — the wrist camera was never blanked.
    See results/.../step3g_INVALID_run.txt before planning it.
P4  🔴 OPERATOR DECISION: our own 89 episodes (STEP 4). Research call, not a
    technical one. Episodes still need v3.0 -> GR00T v2 conversion.
```

---

## Deliberately NOT doing

```text
rung 5 (parameter offload)   operator said ignore
DeepSpeed integration        CPUOffloadAdamW is ~70 lines and already verified;
                             DeepSpeed means compiling CUDA ops with uncertain
                             Blackwell support and no lerobot hook
```

## Standing rules for this lane

```text
E1 preflight before ANY run >1 h    preflight_features.py — seconds
                                    (preflight_batch_check.py is SUPERSEDED: it
                                    encoded a rule, the rule was wrong, and it
                                    returned a FALSE PASS on 2026-08-14)
n=200 for any quoted eval           n=40 already produced one 5-point error
a rung is a POC until it CHECKPOINTS AND RESUMES
loss is NOT a proxy for capability  it has misled us three times
a gate that encodes a RULE inherits every error in that rule — make gates
report what will actually happen, from the same objects the tool itself builds
NEVER rebuild a run command from a Configuration block. State every lever
explicitly, defaults included — dtype and gradient_checkpointing BOTH default
OFF and both silently cost a launch on 2026-08-15.
use setsid for long runs — a bare background job died to a session teardown
```
