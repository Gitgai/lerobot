# SO-101 Orange Pick — Grasp Fix Plan

_Last updated: 2026-07-07_

## The diagnosis (evidence-based)

The pick fails **not** because of the model or the data, but because of **how the policy is deployed**:

- ACT ran with lerobot defaults `n_action_steps=100, temporal_ensemble_coeff=None` = **fully open-loop**: it looks at the orange **once**, predicts a 100-step (~3.3 s) reach→close→lift trajectory, and executes it **blind** before looking again.
- Any small error in that one-shot reach → the pre-scheduled gripper close fires into **empty air** → grips nothing. Consistent across all 3 trials.

**Ruled out (measured, not guessed):**
- Demos are good — 19/19 new + 23/30 original contain real grasps; verified a demo is a clean human pick.
- Gripper closes deep enough — model commands 20–22, demos only need ~29–31.
- Control rate was fine — eval measured 30.0 Hz.

**The hard constraint:** laptop is **CPU-only**; ACT inference = **395 ms/step**. Full closed-loop (re-plan every step) = ~2.5 Hz on CPU = unusable. That's why open-loop was the silent default.

## The core fix

**GPU-served, closed-loop inference.** Same idea as the Pi05 policy-server setup. Fixes correctness *and* speed at once:

| | Now (CPU, open-loop) | Fixed (GPU, closed-loop) |
|---|---|---|
| Inference | 395 ms/step | ~5–15 ms/step (30–80× faster) |
| Mode | blind 100-step chunks | re-plan every step (temporal ensembling) |
| Grasp | closes on schedule → air | closes when it *sees* it's on the orange |

Works with the **existing** ACT checkpoint — no retraining needed to test.

## Plan (cheapest → most expensive)

### Step 0 — FREE partial-closed-loop test (laptop, today, no pod)
Re-run the existing 49-ep model with `--n-action-steps 20` (re-plans ~4–5× per grasp; arm pauses ~0.4 s each). Jerky but zero-cost signal on whether feedback fixes the close-timing.
```
python scripts/act_eval_3cam.py \
  --policy-path /data/act_orange49_checkpoints/020000/pretrained_model \
  --task "pick up the orange and move it to another place" \
  --duration 25 --max-relative-target 5 --n-action-steps 20 \
  --record --run-name eval_49ep_nas20 --i-understand-this-moves-robot
```
- **Success:** gripper closes *while down at the orange*; ≥1 clean pick.
- **If promising →** Step 1. **If no change →** the reach itself is off; go to Step 2.

### Step 1 — GPU policy server, full closed-loop (needs a pod) ← the real fix
Serve ACT from the GPU with temporal ensembling (`--temporal-ensemble 0.01`), robot stays local, target 30 Hz.
- Success target: **≥6/10 clean picks**.
- This is also the Pi05 on-ramp (same serving pattern).

### Step 2 — More grasp data, only if Step 1 plateaus
Record ~30 more consistent grasp demos → ~50 total, varied orange positions. Retrain on grasp-only or a grasp-upweighted mix. Deploy closed-loop (Step 1).

### Step 3 — Pi05 fallback, only if ACT plateaus after 1 & 2
Fine-tune Pi05 on the 50 grasp demos, served on GPU. More capable priors, but 10× the infra to iterate and earlier attempts hit the same wall — so only after feedback + data are proven.

## Model choice: ACT now, Pi05 later
- **ACT** — 52M, trains in ~2 h, iterate cheaply. We're one deploy-mode change from possibly solving it. Keep.
- **Pi05** — stronger priors but GPU-only serving, heavier infra, slower iteration; its advantage (closed-loop on GPU) we can give ACT for free. Fallback only.

## Meta-principle (how to be 10× faster)
We burned a 3 h training run on what was a **one-line deploy setting**. Going forward:
> **Exhaust free config/deploy fixes (inference mode, guard, rate) — testable in minutes — BEFORE recording data or launching training.**

## Assets (all on local `/data`, ready)
- Checkpoints: `/data/act_orange49_checkpoints/020000` (49-ep), `/data/act_orange_checkpoints/{005000,010000,020000}` (30-ep)
- Datasets: `so101_orange_49` (train-ready), `so101_orange_grasp19` (grasp-only, train-ready)
- Eval: `scripts/act_eval_3cam.py` (now supports `--n-action-steps`, `--temporal-ensemble`)
- Calibrations backed up: `/data/so101_calibration_backup/` (follower + leader)
- Pod scripts on `/workspace`: `rebuild_train_env.sh`, `train_act_49.sh`
