# π0.5 / 5090 lane — Current Priority

Last updated: 2026-08-15

**This file is a ROUTER: what is open, in what order, and why. It is NOT a log.**
Detail and evidence: [`pi05_training_capability_plan_20260811.md`](pi05_training_capability_plan_20260811.md) (2,193 lines).
Raw artefacts: `results/pi05_capability_20260811/`.

> **Why this file exists:** priority order previously lived only in chat, so the
> operator's own top priority — the checkpoint gate on rung 4 — got buried as a
> footnote among seven items. **Hard limit ~100 lines.** Follows the pattern of
> `branch1/CURRENT_PRIORITY.md`, which was written after the same failure.

---

## ✅ THE QUESTIONS THAT PROMPTED THIS ARE ANSWERED — do not reopen

```text
can the 5090 full fine-tune π0.5?   YES — 4 long runs, zero throttling, 0%→80%
is the $11K RTX PRO 6000 justified?  NO — and bigger batches, the main thing more
                                     VRAM buys, made results WORSE (64.5 vs 80.0)
```

---

## ✅ P0 — DONE 2026-08-15: rung 4 CHECKPOINTS AND RESUMES

```text
train -> checkpoint -> kill -9 -> RESUME -> train -> End of training, EXIT=0
2.33 s/step steady (2.3x the 8-bit baseline, exactly as predicted)
GPU 20.5 GiB · host 34.1 GB RSS · optimiser state 26.0 GB, all fp32
⇒ rung 4 is the FIRST rung to pass all three. Rung 3 still fails on resume.
detail: results/pi05_capability_20260811/step3f_3e_rung4_gate_PASS.txt
```

⚠ **Two defects had to be fixed and NEITHER appears during training** — torch
casts the state to the param's dtype/device, and accelerate moves it to the GPU
at `prepare()`. The second is invisible on a fresh run and fires only on resume;
the 60-step run passed TWICE while it was live. Proof of the standing rule.

★ **NEW BLOCKER FOR ANY LONG RUN — host RAM.** Rung 4 needs ~34 GB. dynus wants
~47 GB. The box has 59 GB and swap is exhausted. **They cannot coexist**, and
dynus was OOM-killed 9 times in 6 hours on its own. P2 needs the machine.

## P1 — BLOCKED ON OPERATOR: move the display to the iGPU

```text
cable move to the motherboard output + reboot. No BIOS change (iGPU already
enumerated, amdgpu loaded). Frees the desktop's 1.42 GiB of VRAM.
why now  rung 3's paged resume fails by ~1 GiB. This is plausibly the exact fix,
         and would flip rung 3 from SAVE-ONLY back to fully usable.
then     rerun the 3f.2b resume test to confirm
```

## P2 — the last open QUESTION: does 8-bit Adam cost accuracy?

```text
3f.3e phases 3-4   fp32 Adam via offload, 24k steps, then n=200 eval
                   compare against STEP 3d's 80.0% — ONE variable
cost    ~19 h GPU (measured 2.33 s/step) + 15 min eval. NEEDS THE WHOLE BOX:
        ~34 GB host RAM, and dynus wants ~47 GB of the same 59 GB.
⚠ do NOT start on momentum from P0 succeeding. This is the only way to isolate
  8-bit Adam, but the purchase decision does not depend on it.
```

## P3 — 3g rerun: the starting-checkpoint hypothesis

```text
from pi05_libero_base, NO rename_map, E1 preflight first. ~7 h.
The previous attempt blanked the wrist camera for 24,000 batches and measured
nothing. E1 now makes that specific failure impossible.
⚠ Affects no decision. Scientific closure only.
```

## P4 — 🔴 NEEDS AN OPERATOR DECISION: our own data (STEP 4)

```text
Mixing state-machine-generated with recorded episodes is a research decision,
not a technical one. Bring STEP 2/3 results to it. Also: the 89 real episodes
still need v3.0 → GR00T v2 conversion.
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
```
