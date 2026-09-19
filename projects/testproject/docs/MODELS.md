# Model registry

Every model this project has produced, what it came from, and what it is
known to do. Add a row when a checkpoint is trained; never rename an old one.

## Naming rules

```text
DIRECTORY   checkpoints/<run-name>/checkpoint-<STEP>
            <STEP> is the step counter WITHIN THAT RUN, not a version.
            A newer model can carry a smaller number: today's 6000-step run
            produced checkpoint-6000, the older 10000-step run produced
            checkpoint-10000. This confused us on 2026-08-26.

STABLE NAME checkpoints/<capability>_v<N>   -> symlink to the directory above
            This is what documents, scripts and conversation should use.
            The symlink never moves once published.

LINEAGE     every checkpoint carries LINEAGE.json recording its parent,
            dataset, steps and status - so a model can always answer
            "where did I come from" without weight forensics.
```

## The models

| stable name | directory | parent | data | status |
|---|---|---|---|---|
| `orange_pick_baseline_v1` | `n16_real79_side/checkpoint-10000` | nvidia/GR00T-N1.6-3B | 79 orange demos | **FROZEN.** 9/10 full task on the arm, 2026-08-20. Write-protected. |
| `plate_v1` | `n16_plate_v1/checkpoint-6000` | `orange_pick_baseline_v1` | 79 orange + 20 plate (99 eps, 2 tasks) | Trained 2026-08-26. Regression gate passed (2.50 vs 2.41). One live-camera arm trial: grasped 9 s, grip +5.3, did not carry. |

| `n16_new30_v1` | `n16_new30_v1/n16_new30_v1/checkpoint-6000` | **nvidia/GR00T-N1.6-3B (stock)** | 30 new-camera eps (20 orange + 10 tomato), trimmed, NO hold-out | **Trained 2026-09-16, 12,000 steps, loss 1.115 -> 0.007. checkpoint-6000: PLACE 5/10 on the arm (10 trials, 2026-09-16), every grasp completed; only failure mode is hovering / not descending. checkpoint-12000: PLACE 1/10 - overfit the gripper-closed state, would not release. USE 6000, do not train past ~6000 steps.** Checkpoints at 3000/6000/9000/12000. |

| `n16_recovery_v1` | `n16_recovery_v1/n16_recovery_v1/checkpoint-{3000,6000}` | **`n16_new30_v1` checkpoint-6000** (weights only, fresh step 0) | 60 eps = `new30_merged` (30: 20 orange + 10 tomato) + 30 recovery orange = `new30_plus_recov30`; stats REGENERATED for the 60 | **Training 2026-09-18, 6000 steps, save 3000+6000, effective batch 32, lr 1e-4, 8-bit adam.** Path 2 recovery-data fine-tune: 30 off-target->correct->place demos (30/30 verified on-plate — 24 front cam, 6 wrist cam) folded in to fix the hover / no-descent failure. **ARM RESULT checkpoint-6000: PLACE 5/10 (10 trials, 2026-09-18). HOVER ELIMINATED (10/10 descend) - the recovery data worked; new bottleneck is GRASP precision (successes grasp early <chunk171 at grip~22; failures grasp late >chunk200, miss/fumble). Position does NOT drive outcome. checkpoint-3000: 0/5. **CAVEAT: all these trials ran with the RTC pipeline OFF (~31%% duty) — the old 9/10 baseline used --rtc (95%% duty); true rate pending an --rtc re-test (see EVAL_VIZ sec 8).** See EVAL_VIZ_AND_RECOVERY.md sec 7. |

| `plate_v2` (training) | `n16_plate_v2c` | `plate_v1` via v2/ckpt-1500, v2b/ckpt-1000 | same 99 episodes | DONE. Held-out orange error: 3.08 -> 2.67 -> 2.37 -> 2.46 (global 9500/10500/11500/12000). Curve turns ~11500; the gain over plate_v1's 2.50 is within noise. **Not worth switching to** - plate_v1 remains the model to test. |

Retired / not in use: `n16_real79_top` (Brain B — see the caveat below),
`gr00t_n16_leisaac_orange` (simulator-trained; blind on photographs),
`n16_real89_20260817` (aborted run).

## Lineage in one view

```text
NVIDIA GR00T N1.6 (3B, off the shelf)
  |
  +-- 79 real orange demos (OLD wrist camera) .... orange_pick_baseline_v1  9/10
  |     |
  |     +-- + 20 plate demos ..................... plate_v1
  |
  +-- 30 demos through the NEW wrist camera ...... n16_new30_v1   1 success, 1 trial
        (2026-09-16; a SEPARATE branch from stock, sharing no fine-tuning with
         the baseline - the operator chose not to start from it, because the
         baseline's skill was tied to a camera that no longer exists)
```

```text
NVIDIA GR00T N1.6 (3B, off the shelf)
  |
  +-- LeIsaac simulator renders ....... blind on photographs, never worked on the arm
  |
  +-- 79 real orange demos ........... orange_pick_baseline_v1   9/10 on the arm
        |
        +-- + 20 plate demos ......... plate_v1                  under test
```

## Why this file exists

On 2026-08-26 the operator asked which model that day's fine-tune had started
from. Nothing recorded it - not the config, not training_args, not the logs.
It had to be established by comparing action-head weights against three
candidates (parent 0.0016 vs 0.0032/0.0034 - conclusive, but forensics).
A checkpoint should carry its own history.


## A caveat on Brain B

`n16_real79_top` is listed as retired because the 2026-08-21 A/B recorded
A 10/10 against B 7/10. That document itself questions the verdict: the
comparison ran at stutter tempo, and RTC alone later took Brain A from 4/10 to
9/10, so B's stalls and slips may be the same tempo disease rather than a camera
weakness. Three RTC runs of B were planned to settle it and never happened.

The two models differ ONLY in which second camera was labelled "front" — the
89 demonstrations were recorded with three cameras and split into two datasets.
The wrist footage is identical in both.

    n16_real79_side   so101_orange_89_v21_train79           front = side view
    n16_real79_top    so101_orange_89_v21_topfront_train79  front = overhead
