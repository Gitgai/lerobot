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

Retired / not in use: `n16_real79_top` (Brain B, lost the camera A/B),
`gr00t_n16_leisaac_orange` (simulator-trained; blind on photographs),
`n16_real89_20260817` (aborted run).

## Lineage in one view

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
