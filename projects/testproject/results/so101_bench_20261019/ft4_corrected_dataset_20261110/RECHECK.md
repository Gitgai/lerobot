# FT4B derivative recheck

Date: 2026-11-10
Status: corrected dataset passes; 20-step smoke passed; full training not started

## What was rechecked

- Exact original task strings from both source `tasks.parquet` files.
- All 35 accepted opening sequences using front-camera contact sheets; representative wrist sequences as well.
- Every selected action and state row against the immutable source rows.
- Train/validation source-episode separation.
- Beginning, midpoint and final paired camera samples for every derived entry.
- The deployed PI05 dataset loader's 50-action query and episode-end padding behavior.
- All 35 final two-second sequences to confirm that the task outcome and return segment are retained.

## Important correction

The prior 54-entry proposal repeated 25 shortened approach-through-lift windows. The deployed PI05 model requests 50
future actions. LeRobot clamps action indices beyond an episode to the final action and emits an `action_is_pad` mask,
but the deployed PI05 loss averages all action positions without applying that mask. In the proposed shortened
windows, 1,225 input positions would have contained at least one artificial terminal target, and the cut occurred
during an active task phase.

Those 25 shortened entries were removed before training. The corrected training set has 29 naturally ending entries:
25 orange and four matchbox. Its 28,494 frames all come from complete retained demonstrations after reviewed opening
setup cuts. The six held-out naturally ending entries contain 5,907 frames.

The authoritative GPU-host loader opened all 29 training and six validation entries with the exact 50-action query.
It decoded 87 training and 18 validation samples across the beginning, midpoint and end of every entry. Both cameras
were `(3, 480, 640)`, actions were `(50, 6)`, and the task tables matched exactly. Padding appeared only in the final
49 possible input positions of each naturally ending recording, as expected. No input before that boundary was
padded.

## Opening review

All 35 front-camera openings were inspected. Thirty-four show a stationary start with the object already placed.
Orange episode 6 shows the human moving the orange from the tray to its table position; its retained start begins
after the hand clears. The derivative retains five frames immediately before the first three-degree arm-command
displacement. Original source recordings are unchanged.

All 35 ending sequences retain the successful object-in-receptacle outcome. Most are already stationary at rest in
the last two seconds. Six orange episodes are visibly completing their return during that interval; by the final
frames they are folded back or close to the recorded terminal pose. Unlike the rejected focus windows, none ends
during acquisition, lift or transport.

## Active instruction

`pick up the orange and place it on the plate`

## Smoke result

The corrected training dataset completed a 20-step smoke on AI90 GPU 0 using batch 4 with two-step gradient
accumulation, an effective batch of 8. It processed 160 samples, or 0.0056 of one dataset pass. Checkpoint `000020`
was written successfully. Saved model, adapter and optimizer states contained zero non-finite tensors, and 656 of
666 LoRA-B tensors were nonzero after optimization. No OOM or decode failure occurred. The logging interval was 25
steps, so this 20-step run emitted no scalar loss line; the finite checkpoint and updated adapter tensors are the
recorded smoke evidence.

Remote output: `/home/kiran/lerobot_assets/training/ft4b_corrected_smoke20_20261110_02`.

The planned 9,000-step run would process 72,000 samples, equivalent to 2.53 effective passes over the 28,494-frame
training derivative. That full run has not started.

## Result

The corrected derivative passed its alignment, split, deployed-loader and pipeline-smoke checks with zero errors.
No full training is running. Qwen was restored after the smoke and passed its local health check.
