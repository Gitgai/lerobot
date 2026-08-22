# Feature Backlog: Everything We Are NOT Using Yet (And Whether We Need It)

Last updated: 2026-08-01

Plain-language audit of LeRobot features available to this project but not yet
used. Compiled by sweeping the actual config/code surfaces, not from memory.
Rule that got us here and still applies: ONE change at a time, each validated
offline (exam/gates harness) before touching the robot.

Legend: [NOW] = candidate for the next sessions | [TRAIN] = for the next
fine-tune, if it happens | [LATER] = situational | [SKIP] = known, judged not
useful for us (with reason).

## 1. Serving Speed (attacks the ~0.5 s GPU thinking - the biggest lever left)

[NOW] bfloat16 serving (policy config `dtype`)
What: run the model in "half precision" numbers on the GPU. Same brain,
faster math - RTX 3090 is much quicker at bf16 than float32.
Why care: inference ~0.5 s could drop meaningfully; total response drops
with it; RTC has a smaller gap to bridge.
How to adopt safely: run the trust exam (gate A) in bf16 first - outputs
must still match the recorded answers; then gates B/C; then live.

[NOW] fewer denoise steps (policy config `num_inference_steps`, currently 10)
What: the model refines its plan in 10 rounds; 5-6 rounds = nearly half
the thinking time, slightly rougher plans.
How to adopt: same offline exam first; check gate A correlation holds.

[LATER] torch.compile (`compile_model`, `compile_mode`)
What: GPU code optimizer; can speed inference further.
Why later: adds long warmup + occasional flakiness; try after bf16, and
only if we still need speed.

## 2. Chunk Blending On The Client

[NOW] `aggregate_fn_name` - we use the default `weighted_average`
(0.3*old + 0.7*new). Other built-ins: `latest_only`, `average`,
`conservative` (0.7*old + 0.3*new).
Plain meaning: when a new plan arrives, overlapping actions are BLENDED
with the old plan's. Before RTC, blending smoothed disagreements between
plans. WITH RTC, consecutive plans now agree at the seam - blending may
only be diluting fresh corrections.
Candidate test: A/B `latest_only` vs `weighted_average` under the h35
recipe (one run each). Zero code, one flag.

## 3. RTC's Own Tuning (only if seams/slips persist at h35)

[LATER] `prefix_attention_schedule`: LINEAR (ours) | EXP | ZEROS | ONES -
how firmly the protected prefix fades into free planning.
[LATER] `max_guidance_weight` (10): how hard the new plan is pulled toward
the promised prefix.
Both are one-env-var experiments on the server via our adapter.

## 4. Features For The NEXT Fine-Tune (bank these now so they are not forgotten)

[TRAIN] image_transforms (was DISABLED in our training)
What: during training, randomly jitter brightness/contrast/etc. of the
camera images so the model stops memorizing exact camera conditions.
Why care: our single most repeated failure class was "camera slightly
different -> aim broken". This feature exists precisely to prevent that.
MUST be enabled in any retrain.

[TRAIN] wandb logging (was DISABLED; cost us the loss curve twice)
Enable, or at minimum tee the console to a file (both, ideally).

[TRAIN] varied objects/placements in demos (not a flag - a recording habit)
2-3 fruit sizes, varied positions, slight camera nudges between episodes.
Teaches "squeeze until secure" instead of "squeeze to 23" (see the
fruit-size slip analysis) and camera robustness.

[TRAIN] eval_split (train config)
Hold out a slice of episodes during training to watch validation loss -
tells us when to stop training instead of guessing step counts.

[TRAIN] RA-BC per-sample loss weighting hook (`forward(reduction="none")`)
The training code can return per-sample losses - enables weighting
important samples (e.g. grasp moments) higher. Advanced; consider if
close-timing remains weak after a plain retrain.

[SKIP for now] training new checkpoints on the OLD code
Any retrain happens on the NEW lerobot (code-checkpoint pairing rule),
which also gives native RTC without our adapter.

## 5. Evaluation Process Tooling

[NOW] episode-managed evaluation (lerobot-record driving the policy)
What: instead of one endless run we kill by hand, official recording
tooling can run N discrete episodes with reset pauses between them - and
SAVES each attempt in dataset format.
Why care: makes the five-run count clean and repeatable, and successful
episodes become future training data for free (self-improvement loop).
Cost: one session to wire our async setup into that flow - do after the
first manual five-run count, not before.

[LATER] lerobot-dataset-viz - browse recorded episodes/datasets visually
instead of my contact-sheet scripts.

[LATER] debug_visualize_queue_size (client flag) + RTC debug tracker -
built-in introspection plots if we ever chase queue/guidance mysteries
again.

## 6. Hardware/Setup Features Already Available But Unused

[LATER] camera `rotation` (0/90/180/270) - if a camera must ever be
remounted sideways, rotate in software instead of retraining.
[LATER] `lerobot-find-joint-limits`, `lerobot-calibrate` - recalibration
tools if the arm ever feels off after crashes.
[SKIP] `empty_cameras` (pi05 config) - pads missing cameras with blanks;
we always run true 3-camera or not at all (standing rule).
[SKIP] `max_relative_target` speed cap - exists, works, declined by user
preference for pure defaults; revisit only if RTC path dead-ends.

## 7. What "Not Missing Anything" Means Here

This list was compiled by reading: RobotClientConfig / PolicyServerConfig,
PI05Config, RTCConfig, camera configs, the aggregate-function registry, the
training pipeline options, and the CLI tool list. Features can still land
upstream faster than this doc updates - re-sweep when planning any major new
phase. The discipline stays: measure a problem first, pick the feature that
targets it, validate offline, change one thing.

## 8. Suggested Order For The Next Sessions

```text
1. Five-run reliability count - FROZEN h35 recipe, big orange (baseline first,
   no new features mixed in!)
2. bf16 serving - offline exam, then live if green
3. aggregate latest_only A/B - one run
4. num_inference_steps 5-6 - offline exam, then live if still latency-bound
5. If counts say "retrain": new-code training with image_transforms + wandb
   + eval_split + varied-object demos
```
