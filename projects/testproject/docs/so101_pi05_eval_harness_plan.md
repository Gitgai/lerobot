# SO-101 Pi05 Evaluation Harness Plan

Last updated: 2026-06-25

## 0. Why this document exists

We keep arguing about whether the pretrained `zz4321/so101_pi05` checkpoint can
pick the orange. We cannot settle that argument by reasoning. The faithful chunk
test only executed **3 of 50 actions, open-loop, from one camera snapshot, with
no re-query**. That is too weak to conclude "this checkpoint can't grasp."

The core principle this plan is built on:

```text
Testing is the only thing that produces knowledge.
- "pretrained checkpoint can't pick"      -> only knowable by a real test
- "fine-tuning will fix it"               -> only knowable by a real test
- "fine-tuning broke something"           -> only knowable by a real test
```

So the missing asset is not a better model. It is a **trustworthy, repeatable
evaluation**. Build it once; use it on every checkpoint (pretrained now,
fine-tuned later). This plan builds that harness and uses it.

## 1. Does this need a GPU?

Yes for the model, no for the laptop. Split it:

```text
Robot control + cameras + action logging   -> laptop        -> NO GPU
Pi05 inference (the policy server)          -> a GPU machine -> YES GPU
```

Pi05 is ~4B params, so it must run on a GPU somewhere. Two ways:

```text
Option 1: laptop has a capable NVIDIA GPU -> run policy server locally -> FREE
Option 2: no local GPU -> rent an INFERENCE GPU (not a training GPU)
```

Important cost point:

```text
Inference is far lighter than fine-tuning.
Pi05 in bf16 weights ~= 8-9 GB.
A cheap 24 GB card (RTX 4090 / L4 / A10) is ENOUGH for eval inference.
You do NOT need an L40S or A100 just to run these tests.
(The "avoid 24 GB" warning in the handoff was about FINE-TUNING, not eval.)
```

Cost rule for this whole plan:

```text
GPU bills by wall-clock and is the only cost.
So: bring policy server up -> run the WHOLE eval battery back to back -> shut it down.
Never leave the inference GPU idle.
```

## 2. What "evaluation harness" means here

A fixed, repeatable procedure so every run is comparable:

```text
- same start pose every run        (record it once, return to it each run)
- same orange position             (mark the table with tape)
- same 3 camera views              (top / front / wrist, all verified good first)
- same task string                 ("grasp the orange")
- model runs closed-loop with a safety guard, human watching, ready to stop
- ONE explicit success criterion (below)
- every run logs: video + full action CSV + start/end state
```

Success criterion (binary, no interpretation):

```text
SUCCESS = gripper closes on the orange AND lifts it clear of the table.
Anything else = FAILURE, with a noted failure mode
(e.g. "approached but missed", "never approached", "reoriented only").
```

## 3. Pre-flight (local, free, no GPU) — do every session before paying for GPU

```text
1. ./bin/so101 status        # follower (and leader if recording) connect
2. ./bin/so101 positions     # joint readings sane
3. Verify top / front / wrist camera images look good
4. Fix front-cam exposure if needed (v4l2-ctl settings in the handoff doc)
5. Place orange at the taped mark; move arm to the fixed start pose
```

Rule: do not start the inference GPU until all three camera views are confirmed
good. GPU time spent on bad camera frames is wasted money.

## 4. Test 1 — Dry full-chunk inspection (needs inference GPU, NO robot motion)

Goal:

```text
From ONE observation, get all 50 Pi05 actions and inspect the whole chunk
WITHOUT moving the robot. Answer: does a single chunk even contain a grasp
(gripper close + arm lift), or is it all reorientation?
```

This directly answers the "we only executed 3 of 50" objection, at zero robot
risk and minimal GPU time (one inference).

Implementation (small, low-risk):

```text
- New flag --dry-run on pi05_faithful_chunk_test.py (or a tiny sibling script).
- request_actions() ALREADY returns all 50 actions stacked (verified).
- In dry-run: skip robot.connect()/send_action entirely; just log all 50 rows
  to the actions CSV (phase="dry_chunk", action_index 0..49).
- Then plot per-joint trajectories, especially gripper and the position joints.
```

What to read from the 50-action plot:

```text
- Does gripper ever close, then arm lift?        -> grasp signature present
- Do shoulder/elbow trend toward the orange?     -> approach present
- Is wrist_roll a one-time settle then steady?   -> reorientation, not the whole story
- Is it ALL reorientation with no close/lift?     -> weak evidence chunk isn't a grasp
```

Caveat to stay honest:

```text
One open-loop chunk is ~1.5-2 s of motion. Even a "no grasp in chunk 0" result
does NOT prove the model fails, because Pi05 is meant to run CLOSED-LOOP and
correct over many chunks. Test 1 is a cheap screen, not the verdict.
Test 2 is the verdict.
```

## 5. Test 2 — Safe closed-loop rollout (needs inference GPU, robot MOVES)

This is the real test, and the honest answer to "we won't know until we let it
do it." Let Pi05 actually run the task the way it is designed:

```text
loop:
  observe (top/front/wrist + state)
  query Pi05
  execute the first K actions of the chunk
  re-observe and query again
until success, timeout, or human stop
```

Reuse existing verified code:

```text
pi05_guarded_real_action_test.py already has run_multi_step():
  - it re-queries every step (closed-loop)
  - executes actions[0] each step
Extend it for a fair eval:
  - K actions per chunk before re-query (e.g. K = 10-25), not just K=1
  - keep --robot-max-relative-target as a SAFETY GUARD only (e.g. 5-8 deg),
    NOT as behavior shaping
  - run for enough steps to allow a full pick (e.g. 150-300 steps)
  - human hand on stop the whole time
```

Critical distinction (this is the band-aid line the user cares about):

```text
The safety guard limits per-step joint jump so a bad action can't slam the arm.
It does NOT redirect the arm toward the orange or "help" it grasp.
If the model can pick, it picks within the guard. If it can't, the guard
simply makes the failure safe to watch. The guard is for safety, not success.
```

Run the fixed battery (back to back, GPU up once):

```text
- 5 rollouts from the SAME start pose and SAME orange position
- log video + action CSV for each
- record SUCCESS / FAILURE + failure mode for each
```

## 6. Decision logic (what each outcome means)

```text
Test 1 (dry chunk):
  contains clear close+lift  -> promising; go straight to Test 2
  all reorientation, no grasp-> weak negative; still run Test 2 (closed-loop
                                may behave differently). Note it.

Test 2 (closed-loop battery, 5 runs):
  >= ~2/5 success            -> checkpoint is USABLE in our setup.
                                Tune conditions, do NOT fine-tune yet.
  0/5 but clear approach      -> close; small fine-tune or condition fixes likely help.
  0/5 and never approaches    -> checkpoint genuinely doesn't transfer to our setup.
                                NOW fine-tuning on our demos is justified.
```

Only after Test 2 fails honestly do we spend time recording demos and money on a
training GPU. This earns the fine-tune decision instead of assuming it.

## 7. If we reach fine-tuning (separate, later phase)

Not part of this harness, but the harness is the prerequisite for it:

```text
- record successful orange-pick demos (start ~20, scale to 50+)
- fine-tune on a TRAINING GPU (A100 80 GB class), stop GPU immediately after
- evaluate the fine-tuned checkpoint with THIS SAME harness (Section 2-5)
- compare success rate vs the pretrained baseline from Test 2
- this is also how we catch "fine-tuning made it worse" -> only the harness shows it
```

## 8. Build order / checklist

```text
[ ] Pre-flight local checks pass (Section 3)
[ ] Add --dry-run to faithful chunk test (Test 1 code)
[ ] Bring inference GPU / policy server up (local if GPU, else cheap rental)
[ ] Run Test 1, save 50-action CSV, plot trajectories
[ ] Extend run_multi_step for K-per-chunk + safety guard (Test 2 code)
[ ] Run Test 2 battery (5 rollouts), log video + CSV + verdicts
[ ] Shut down inference GPU
[ ] Fill in the decision table (Section 6) and decide next phase
```

## 9. One-line summary

```text
Stop debating the model. Build one repeatable closed-loop eval, run it on the
current checkpoint first, and let measured success rate decide whether to
fine-tune. Eval needs an inference GPU (cheap), not a training GPU.
```
