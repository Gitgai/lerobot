# L7 — Full fine-tune with EMA ON, the EMA copy kept in host RAM (LIBERO, 72 GB card)

Date: 2026-10-18. Status: **PROPOSED — awaiting operator go. Not built, not launched.**
Parent: pi05_libero_openpi_vs_ours_plan_20261010.md (L4 row) · results: RESULTS_pi05_libero_lora_vs_fullft_20261013.md §5.1b

## Why
L4 (full FT, EMA off, batch 32) ended level with LoRA (97.0 vs 97.5-99.5) but its checkpoint scores
swing 78.5 → 93.0 → 82.0 → 95.5 between neighbours, while LoRA's stay in 95-99.5 (RESULTS §5.1b).
Two candidate causes, unattributed: (a) EMA off — the published recipe evaluates a weight average
(decay 0.999) that smooths exactly this checkpoint-to-checkpoint noise; (b) batch 32 vs 256. EMA was
switched off only because its 12.7 GiB fp32 copy did not fit beside the 66 GB working set. Keeping
that copy in host RAM removes the reason without changing the arithmetic. This run isolates (a):
if the swings vanish, batch size was not the cause; if they stay, it was (or the seed).
Note: openpi's LoRA configs run EMA OFF, so LoRA (L3/L5) is not touched by this.

## What changes, exactly (vs L4-noEMA)
```text
                      published       L4-noEMA (done)        L7 (this)
EMA                   0.999, on GPU   off                    0.999, identical formula, copy in HOST RAM
batch                 256             32                     32          (only deviation that remains)
everything else       —               as published           as published
row label             —               "full FT, EMA off"     "full FT, EMA on (host), bs 32"
```
Implementation (openpi scripts/train.py + checkpoints.py, local branch, ~50 lines, committed to our mirror):
- config: ema_decay=None for the GPU state (so train_step carries no EMA) + a new flag host_ema_decay=0.999.
- after each step: jax.device_get(new params) → host fp32 numpy copy; ema = 0.999*ema + 0.001*params
  (numpy, multithreaded axpy per leaf). First step initialises ema = params (as openpi does).
- save: replicate checkpoints._split_params — params/ = HOST EMA weights (so the scorer and
  serve_policy evaluate the averaged model exactly as for the published checkpoint), train_state/ =
  raw params + optimizer. resume: reload host EMA from params/ of the latest checkpoint.
- cost model: 12.7 GB device→host per step (~0.6 s) + CPU axpy over 3.4B floats (1-2 s) →
  4.9 → ~6.5 s/step, 30k steps ≈ 54 h (vs 41 h). Host RAM +13 GB resident (+13 GB transient at save:
  measured L4 peak was 39 GB RSS + 37 GB swap → budget it; keep swap).
- NOT taken: EMA in bf16 on the GPU (6.4 GB might fit) — a precision bend; the operator forbade half
  precision. Update-every-k-steps — changes the recipe. Both stay off the table unless asked.

## Gates
G1 smoke 50 steps on GPU 1: step time measured (abort if > 8 s/step → redesign: async copy / pinned
   buffers / update every step but transfer overlapped); checkpoint written; params/ == host EMA
   (checksum); resume from it restores the EMA and continues.
G2 budget before launch (ledger R1): 12 × 31 GB = 372 GB; root has 868 GB free (2026-10-18). RAM/swap
   peak at save ≤ L4's +13 GB.
G3 run: 30k steps, saves every 2500, systemd user unit (never setsid), PYTHONUNBUFFERED=1, health
   watchdog with the 30-min stall window and 45 GB swap line.
G4 score all 12 with the L2 loop (same layouts, n=200), add the row to RESULTS §5.1 table.

## Pre-registered reading
- Swings gone (all 10k-30k checkpoints inside one n=200 band, pooled ≥ 95%) → EMA was the cause of
  L4's noise; the "full FT vs LoRA at matched data" verdict is re-read with this row.
- Swings remain → batch 32 (or seed) is the cause; EMA is exonerated; next lever would be gradient
  accumulation to an effective 256 (a recipe-faithful change, separate decision).
- Final/pooled vs LoRA: same rule as before — overlapping intervals = "no difference shown".

## Appendix — memory budget and the routes to batch 256 on one 72 GB card (2026-10-18)

Why batch 32: it was the largest that fit, not a choice. Measured: published recipe (EMA on GPU)
= 66 GB fixed → OOM even at batch 8; EMA off → batch 32 fits at ~66 GB allocated; the smoke went
32 → 16 → 8 and stopped at the first fit, so 64 was never tried (it cannot fit: see table).

```text
on the card (fp32)                 L4 as run (bs 32)   optimizer + EMA in host RAM
weights                                   13.6 GB            13.6 GB   (needed every step)
gradients                                 13.6 GB            13.6 GB   (needed every step)
AdamW moments                             27   GB             0
EMA                                        0 (off)            0 (host)
fixed                                     54   GB            27   GB
room for activations (~68 GB usable)      ~14 GB             ~41 GB
activations                               ~0.6 GB / example (17-20 GB at bs 32, measured)
largest batch                             32 (tight)         ~64
```
Activations are the binding limit: batch 256 needs ~150 GB of them regardless of where the
optimizer lives. Hence:

```text
route                       batch   memory   step-time       30k steps   arithmetic vs published   status
A  EMA in host RAM (L7)      32     fits     4.9 → ~6.5 s    ~54 h       identical except batch     PROPOSED
B  + AdamW in host RAM       ~64    fits     ~10-14 s        ~5 d        identical except batch     design only; JAX port of
                                                                                                   our PyTorch rung-4 (2.3×)
C  gradient accumulation     256    fits     8× (≈40 s)      ~2 weeks    IDENTICAL (true bs 256)    needs ~30 lines in openpi
   (8 × 32 per update)                                                                             train step; not scheduled
D  activation remat          128-   fits?    +30% / step     3-4 d       IDENTICAL (recompute only)  openpi has nnx remat hooks;
   (+ A, + B)                256                                                                   never run here; own smokes
E  bigger machine            256    —        4.9 s/8 GPUs    ~5 h        identical                  operator's original route
```
Decision rule (pre-registered): run A first because it isolates ONE variable at low cost. If A
removes the swings → batch size was not the problem on LIBERO; B/C/D are not needed for this
question. If the swings survive A → the batch question is live: C is the honest single-card
answer (exact), D the faster one (exact, more engineering risk), E the simplest. B alone does
not reach 256 and is only worth building as a component of D.

## Cost and schedule
GPU 1 ≈ 54 h + 2.5 h scoring; runs unattended beside the orange recorder on GPU 0. Disk 372 GB
(fits). Order proposed: start L7 first (pure compute), build the RTC sweep (L6b) meanwhile.
