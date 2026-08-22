# Plan: fine-tune GR00T N1.6 on the 89 real episodes

Created 2026-08-17. Status: **OPTION C SELECTED — train BOTH camera variants,
then A/B on the arm. See section 9 for the execution plan.**

---

## 0. Why — the evidence this rests on

The four instrumented hardware runs plus the confirmed provenance establish:

```text
  the checkpoint is SIM-TRAINED (its README + the LeIsaac dataset is renders)
  same checkpoint, same day:  sim 89% (8/9)   real arm 0%
  run 4: full pick choreography executed ON AIR - gripper closed to width 14
         (an orange holds at 28-33), all three oranges pixel-identical
  four-run dose-response: behaviour becomes monotonically more task-shaped as
         inputs approach the training distribution, never object-grounded
```

**And the decisive precedent, from this rig's own history:** the July π0.5 work
produced real grasp→lift→carry on this arm using a checkpoint fine-tuned on
`orange49_plus_grasp_focus` — **the same 89 episodes this plan uses**
(`agent_handoff_pi05_20260803.md:321`). The one intervention that has ever
produced a real grasp on this hardware is fine-tuning on this data. It also
answers "is 89 episodes enough": it was, once.

Honest bound: π0.5 with this data still carry-slipped. Expect real grasps at an
imperfect rate, not perfection.

## 1. The recipe — reuse the author's, swap the dataset

The current checkpoint ships its own training script
(`gr00t_n16_leisaac_orange/scripts/finetune.sh`), which is the recipe already
proven to produce a working fine-tune of this exact model:

```text
  gr00t/experiment/launch_finetune.py            <- exists in ~/sim/Isaac-GR00T-n16
  --base_model_path nvidia/GR00T-N1.6-3B
  --dataset_path    <OURS: so101_orange_49_plus_grasp_pick_move_focus>
  --modality_config_path configs/so101_config.py <- ships with the checkpoint
  --max_steps 10000  --save_steps 1000  --save_total_limit 5
  --learning_rate 1e-4  --warmup_ratio 0.05  --weight_decay 1e-5
  --global_batch_size 32
  --color_jitter_params brightness 0.3 contrast 0.4 saturation 0.5 hue 0.08
```

Changes from the author's invocation, each with a reason:

```text
  dataset_path        the 89 real episodes                      the entire point
  global_batch_size   32 -> whatever fits in 32 GB (8 likely,   author's GPU unknown;
                      with gradient accumulation to keep the    pi0.5 precedent: batch 8
                      effective batch at 32 if throughput       + checkpointing fits in
                      allows)                                   26 GB on this card
  --use_wandb         DROP                                      offline machine habit;
                                                                HF_HUB_OFFLINE=1 likewise
  save_total_limit    5 -> 10                                   keep every checkpoint;
                                                                disk is cheap (8.8 GB x10),
                                                                early ones are the probes
```

Keep the colour jitter — it is domain-randomisation the author already tuned,
and it helps a small real dataset.

### Open questions the smoke test answers (S2 below)

```text
  Q1  does nvidia/GR00T-N1.6-3B need downloading? (~6 GB - NOT in the HF cache)
      FALLBACK if download is a problem: warm-start from the current sim-trained
      checkpoint instead of the base model. Also scientifically interesting
      (sim+real curriculum) but changes the experiment; base-model start is the
      default because it reproduces the author's recipe.
  Q2  peak VRAM at batch 8 -> decides batch size and whether pause-free eval fits
  Q3  steps/min -> the real ETA
```

## 2. Dataset gate (S1) — verify before any GPU time

The 89-episode set differs from what the recipe expects in known ways; each
needs an explicit check, not an assumption:

```text
  D1  THREE cameras (front, top, wrist) vs the modality config's two.
      Check: does the gr00t loader select by modality.json keys and ignore
      `top`, or does it choke? If it chokes: generate a two-camera view of the
      dataset (metadata-level, no video re-encode).
  D2  the corpus units history. This dataset is REAL teleop (state and action
      both from the arm, motor units) - the varied_corpus rad/motor bug was a
      SIM-corpus defect and should not apply here. Verify anyway: action minus
      state should be small per step; ranges must match the -100..100 and 0..100
      motor conventions. (Spot-checked 2026-08-16: ranges look right.)
  D3  fps 30 vs the recipe's expectation; episode lengths; no NaN/truncated
      episodes; videos decode (ffmpeg present).
  D4  the task string in meta. The policy will be conditioned on whatever
      sentence the dataset carries - confirm it is "Grab orange and place into
      plate" (the string every eval and the client already use).
```

Gate: all four pass -> proceed. Any fail -> fix the dataset copy, never the original.

## 3. Smoke test (S2) — 100 steps, ~15 min

Run the real invocation with `--max_steps 100`. Read off:

```text
  peak VRAM        -> final batch size; whether eval can run alongside training
  steps/min        -> firm ETA for 10,000 steps (pi0.5 reference: 49.8/min)
  loss curve       -> decreasing, not NaN
  checkpoint-100   -> loads in the policy server, answers a get_action call
```

That last check catches format drift between training output and the serving
path before 12 hours are spent, not after.

## 4. The full run (S3)

```text
  launch via a script under backup_staging/rebuild-logs/ (the battery pattern:
  setsid nohup, own log, no pkill-by-name - kill by PID with /proc comm check)
  10,000 steps, checkpoint every 1,000
  ETA from S2; pi0.5-based guess: 3.5 h (batch 8, no accumulation) to
  ~13 h (accumulation x4) - overnight either way
  GPU guard: refuse to start if < 21 GB free (protects against a stray server)
  monitor: checkpoint-directory mtimes, the pattern that caught the pi0.5
  cadence; a stalled cadence = a hung run, kill -9 and investigate
```

## 5. Early-checkpoint probes (S4) — the pause-and-test loop

One 32 GB GPU cannot hold training (~26 GB) + server (8.5) + Isaac Sim (13)
simultaneously, so testing is checkpoint-gated unless S2 shows otherwise:

```text
  at checkpoint-2000:
    PAUSE training            (resume is proven on this GPU - pi0.5 14k -> 20k)
    5-min OFFLINE PROBE       bias_at_scale.py against checkpoint-2000:
                              per-joint error vs ground truth on held-out
                              episodes. Learning = errors shrinking vs the
                              sim-trained checkpoint's (pan -1.04 etc.)
    25-min SIM SANITY n=3     NOTE the inversion: for a REAL-trained model the
                              SIM is now out of distribution. Expect sim scores
                              to DROP as real competence grows. The sim battery
                              here checks only "loads and acts coherently",
                              not quality. Do not repeat the wrong-yardstick
                              mistake in reverse.
    RESUME
  looks broken at 2000 -> stop having lost ~1 h, not 12
```

**The real quality gate after training is the ARM, not the simulator.**

## 6. Evaluation on hardware (S5)

```text
  serve the best checkpoint (by offline-probe error, not sim score)
  the instrumented client, unchanged: --jpeg_quality=92, overhead C270,
  wrist via proxy
  scene per the training data: plate LEFT, fruit clustered right  <- matters
  n>=5 runs; success = the flight-success definition: goal + zero
  penetrations, one verdict
  compare against the four-run baseline table (never closed / closed on air)
  KEEP the sim-trained checkpoint-10000 untouched for A/B
```

## 7. Risks, stated

```text
  base-model download        ~6 GB, needs working HF access; fallback in Q1
  VRAM                       author's batch 32 may not fit; S2 decides
  89 episodes                enough for pi0.5's grasps, but N1.6 may differ
  catastrophic forgetting    real-only tuning may lose sim skills; acceptable -
                             the sim checkpoint is kept; sim+real co-training is
                             the v2 if real-only underwhelms
  wrist camera               STILL degraded (median 24 in run 4, staring at the
                             arm's own parts when raised). The model will train
                             on GOOD wrist frames from the demos but be served
                             marginal ones. Fix before S5 if possible.
  the pan runaway            if it persists after real-data tuning, it was never
                             a domain-gap artefact and becomes its own
                             investigation
```

## 8. Timeline

```text
  S1 dataset gate        ~20 min      nothing at the bench
  S2 smoke test          ~15 min      -> firm ETA
  S3 full run            overnight
  S4 probes              during S3 pauses
  S5 arm eval            next session, operator present
```

---

## S1 RESULTS — 2026-08-17

```text
  D1  three cameras vs two     DEFERRED TO S2 - the smoke test settles it at
                               zero extra cost (a loader that chokes on `top`
                               fails at step 0)
  D2  units                    PASS. |action-state| mean 1.1-4.7 per joint,
                               ranges +/-105 - real motor-unit teleop, coherent
  D3  structure                PASS, after understanding it: videos are 30 fps
                               CFR, 990.8 s = 29,724 frames/camera. The 89
                               episodes = 49 originals + 40 FOCUS episodes that
                               reference the SAME video by timestamp windows
                               (grasp_focus_windows.csv), so 40,712 data rows >
                               29,724 unique frames, by design. Loader reads by
                               timestamp range - consistent.
  D4  task string              FINDING: the dataset's instruction is
                               "pick up the orange and move it to another place"
                               - the July-era invented sentence. NOT
                               "Grab orange and place into plate".
  Q1  base model               huggingface.co reachable (HTTP 200) - the 6 GB
                               download is available. Base-model start stands.
```

### D4 consequence — instruction discipline after training

The fine-tuned model will be conditioned on the DATASET's sentence. After
training, every consumer must switch to it:

```text
  n16_realarm_client.py  --lang_instruction  "pick up the orange and move it to another place"
  sim eval               --policy_language_instruction likewise
```

Note the irony recorded for posterity: the eval harness comment (2026-08-05)
called this exact sentence "an INVENTED sentence that appears nowhere in the env
or any dataset". It appears in this dataset, which was recorded with it. It was
invented, then demonstrated under, which makes it real training vocabulary now.
Do NOT edit the dataset's string instead - the demos were recorded under it and
consistency between training and serving is all that matters.

---

## S2 RESULTS — 2026-08-17. Five rounds to green; all gates now passed.

```text
  round 1  FAIL 16 s   dataset is v3, loader wants v2.1 (meta/episodes.jsonl)
           -> wrote scripts/convert_v30_to_v21_orange89.py. 89 episodes, 178
              frame-accurate clips, ZERO verification failures. `top` camera
              dropped by construction (resolves D1). Original untouched.
  round 2  FAIL 60 s   OOM by 48 MB at Adam state creation, 29.57 GB
  round 3  FAIL 60 s   batch 4 changed nothing (29.81 GB) - the floor is
              STRUCTURAL: fp32 model (launcher sets load_bf16=False) + fp32
              Adam states. Batch size is not the lever.
  round 4  FAIL        my error: `pip` does not exist in a uv venv; bitsandbytes
              never installed. Relaunched before verifying the install.
  round 5  PASS        8-bit Adam via env-gated launcher patch (N16_OPTIM,
              default behaviour unchanged, .pre-optim backup beside it).
              100/100 steps in 2:09 = 46.5 steps/min, peak 24.9 GB.
  serve check PASS     checkpoint-100 loads in the policy server and answers
              get_action with finite (1,16,5) chunks.
```

Also learned from the launcher defaults: **the author's recipe tunes only the
projector + diffusion head** (tune_llm and tune_visual default False). The Eagle
vision backbone - a VLM pretrained on real photos - stays frozen in both their
sim fine-tune and ours. We are re-fitting the same action mapping, on real data.

## S3 LAUNCH — 12:24

```text
  output    ~/lerobot_assets/checkpoints/n16_real89_20260817
  settings  batch 4 x accum 8 (effective 32), 8-bit Adam, lr 1e-4,
            author's colour jitter, save every 1000, keep 12
  measured  46.5 steps/min, peak 24.9 GB (6.4 GB headroom)
  ETA       ~215 min -> ~16:05, an afternoon not an overnight
  monitor   per-checkpoint events + error watch, persistent
```

---

## S4 FIRST PROBE — 2026-08-17. Real-data training works, measured at 40%.

Training died at step 4,025/10,000 when the session ended (checkpoints 1000-4000
intact and resumable). Before spending more GPU, the operator asked to test what
exists. Correct instinct, and it produced the first hard evidence that the whole
diagnosis-and-fix chain is right.

**Method** — head-to-head, offline. Both checkpoints predict the next 16 actions
from the SAME real states and real images; both scored against what the human
demonstrator actually did. 64 samples across 8 episodes.

Deliberately NOT tested in the simulator: the model has moved domains, so sim is
now the out-of-distribution world for it and its scores would mislead in the
opposite direction. The plan's own S4 warning, honoured.

```text
                shoulder   shoulder   elbow    wrist    wrist
                pan        lift       flex     flex     roll    gripper  OVERALL
  sim-trained    4.23       7.63       9.79     5.97     2.87    4.66     5.857
  real @40%      1.50       2.42       3.43     3.32     1.74    3.29     2.618
  change         -65%       -68%       -65%     -44%     -39%    -29%     -55%
```

**Error more than halved, every joint improved, at 40% of training.**

The headline is `shoulder_pan`: **-65%**. That is the joint whose systematic
negative bias (-1.04 offline, CI excluding zero) walked the arm from -11 to -117
in run 1 and drove every hardware failure. The bias was an artefact of a model
that had never seen a photograph, and real data is dissolving it. That closes the
loop between the diagnosis and the fix with a number.

**Caveat, stated before the numbers were read:** training used all 89 episodes,
so there is no held-out set. This measures FIT, not generalisation. It answers
"is it learning" - the right question at 40% - and not "will the arm work".
Only the arm answers that.

## Decision pending: which camera view the final model should expect

```text
  A  resume checkpoint-4000 (side-on front)   ~1h45   re-aim the rig to side-on later
  B  restart on the topfront dataset          ~3h     matches the C270 mounted today
  C  both, then A/B on the arm                ~5h     settles it empirically
```

`so101_orange_89_v21_topfront` is already built (89 overhead clips, 0 verification
failures), so B and C carry no preparation cost.

---

## S4 ADVERSARIAL RE-TEST — 2026-08-17. All four checks pass. One reveals more.

The operator, correctly, refused to accept the first probe on trust: this
investigation has produced six retractions, all of the same kind - a measurement
read past what it could support. So the claim was re-tested with checks designed
to FAIL. Script: `scripts/rigorous_checkpoint_check.py`.

```text
                              SIM-TRAINED      REAL-TRAINED 40%
  C3 honest score              5.717 deg        2.604 deg
  C1 with WRONG images         5.783            6.952
     penalty                   +0.066           +4.348
  C4 vs "don't move"           -0.020           +3.093
```

**C3, sampling.** 8 hand-picked episodes gave 5.857 vs 2.618; ALL 89 at random
seed-fixed frames gives 5.717 vs 2.604. The selection was not flattering
anything.

**C1, the cheat check.** Correct state, images from a DIFFERENT episode:

```text
  sim model    error moves 0.066 deg  -> it is NOT LOOKING AT THE CAMERAS
  real model   error moves 4.348 deg  -> it is reading them, and breaks without
```

**C4, the sanity floor.** Against the dumbest predictor, "the arm does not move":

```text
  sim model    WORSE than not moving (-0.020) on real data
  real model   beats it by 3.093
```

## What this establishes, and what it does not

**Established, measured, not inferred:** the sim-trained checkpoint is
functionally BLIND on real photographs and performs worse than inaction. That
is no longer a behavioural inference from four hardware runs - it is a direct
measurement over 89 episodes with a falsifiable check. And it explains every
hardware run exactly: a model that ignores its cameras and emits roughly
"stay put, drifting left" produces smooth, unmotivated motion.

**Established:** the real-trained checkpoint uses vision. The failure mode most
feared - memorising state->action and ignoring images - is ruled out by C1.

**NOT established, and this limit is real:** C1 proves the model USES the images;
it does not prove it GENERALISES. A model that memorised "these pictures ->
these actions" would also break with wrong images. Separating those requires
data it never trained on, and none exists - all 89 episodes were used.

⇒ Honest ceiling: **it learned this data, and it uses its eyes to do so.**
Whether it picks up an orange is answerable only by the arm.

### A note for the next session

Future work should hold out ~10 episodes before training so generalisation can be
measured directly. Not doing so here was an oversight; the recipe trains on
everything given to it and nobody carved out a test split.

---

## 9. OPTION C — train both variants, A/B on hardware (selected 2026-08-17)

### What is being trained — NOT a full fine-tune

Confirmed from the run's own `experiment_cfg/conf.yaml`:

```text
  tune_llm              false    language model FROZEN
  tune_visual           false    vision backbone FROZEN
  tune_projector        true     TRAINED
  tune_diffusion_model  true     TRAINED (the action head)
```

Deliberate, and correct for this job. The Eagle vision backbone is a VLM
pretrained on REAL photographs - it never needed fixing. What was broken is the
mapping from perception to motor commands, which the sim fine-tune fitted to
renders. That mapping is exactly what the projector and diffusion head are. With
89 episodes, unfreezing the backbone would likely overfit rather than help.

The S4 evidence says the frozen-backbone approach is working: error halved, and
image-sensitivity went from 0.07 deg (blind) to 4.35 deg (dependent on vision).

### The two runs

```text
  RUN-SIDE   dataset so101_orange_89_v21            front = laptop-webcam view
                                                    (low, side-on)
  RUN-TOP    dataset so101_orange_89_v21_topfront   front = overhead C270 view
```

Everything else identical: base model, 10,000 steps, batch 4 x accum 8, 8-bit
Adam, lr 1e-4, the author's colour jitter. One variable - the front camera view.

Sequential, ~3 h each (measured 46-55 steps/min). RUN-SIDE cannot resume from
checkpoint-4000 if the held-out split below is adopted, since that changes the
training set; fresh starts for both keeps them comparable anyway.

### Held-out episodes — RECOMMENDED, not yet approved

All 89 episodes were used in the first run, which is why S4 can prove the model
USES vision but not that it GENERALISES. Holding out 10 episodes fixes that:

```text
  train on 79, hold out 10 (fixed list, same 10 for BOTH runs)
  cost      ~11% of the data
  buys      a real generalisation number, and a fair A/B: both variants
            scored on episodes NEITHER has seen
```

Without it, the A/B compares two models on their own training data - which
measures fit, and fit alone would favour whichever variant memorises more easily.
**Strongly recommended. Say no and I will run without it.**

### Sequence

```text
  1. build the 79/10 split (metadata only, minutes)          if approved
  2. RUN-SIDE   ~3 h, detached (setsid - the last run died with its session)
  3. probe RUN-SIDE on the held-out 10
  4. RUN-TOP    ~3 h, detached
  5. probe RUN-TOP on the same held-out 10
  6. A/B ON THE ARM - the only test that decides anything:
       serve RUN-SIDE, re-aim front camera SIDE-ON,  n>=5 runs
       serve RUN-TOP,  re-aim front camera OVERHEAD, n>=5 runs
       success = the flight-success definition: goal + zero penetrations
  7. keep the loser; both are evidence
```

Step 6 needs the operator and a working arm; steps 1-5 need neither.

### What could still make all of this fail

```text
  - the wrist camera is STILL degraded (median 24 in run 4, staring at the arm's
    own white parts when raised). Both models train on GOOD wrist frames from the
    demos and would be served marginal ones. FIX BEFORE STEP 6.
  - 89 episodes is small; pi0.5 managed real grasps on it, N1.6 may not
  - the instruction string must switch to the dataset's own sentence,
    "pick up the orange and move it to another place", in client AND eval
```

## 10. Full fine-tune: asked, checked, answered (2026-08-17)

Question: "Are you sure we should not do full finetune?" Rather than restate the
earlier argument, two checks were run that could have overturned it. Neither did.

**Check 1 - what did the one successful real-arm fine-tune train?**
The July pi0.5 run is the only intervention that has ever produced a real
grasp-lift-carry on this arm, on these same 89 episodes. Its config
(`docs/pi05_active_work_tracker.md:1284`):

```
train_expert_only=true
```

That is pi0.5's term for: train the action expert, leave the vision-language
backbone frozen. The precedent that worked was also a partial fine-tune.

**Check 2 - did the render training ever damage the vision backbone?**
Direct weight comparison, base `nvidia/GR00T-N1.6-3B` vs the sim-trained
checkpoint-10000, 1106 tensors each:

| group                                | result                                                     |
| ------------------------------------ | ---------------------------------------------------------- |
| vision backbone (40 sampled)         | **40 identical, 0 changed**, max abs difference `0.00e+00` |
| action head / projector (40 sampled) | **0 identical, 40 changed**, max abs difference `9.33e-02` |

The simulator fine-tune never touched vision. The backbone in our starting
checkpoint is bit-identical to NVIDIA's, pretrained on real photographs and
never exposed to a render. The damage is confined to the action head and
projector - exactly the two components we are retraining.

A full fine-tune would therefore spend its extra capacity repairing a component
that was never broken.

**Check 3 - would it even fit?**

|                                  | params          | optimizer state (fp32 master + 8-bit Adam) |
| -------------------------------- | --------------- | ------------------------------------------ |
| trainable now (head + projector) | 1.419 B (43.2%) | 8.5 GB                                     |
| full fine-tune (everything)      | 3.287 B (100%)  | 19.7 GB (+11.2 GB)                         |

Measured peak during the current frozen run: **24.4 GB of 31.8 GB**. Adding
11.2 GB does not fit. Full fine-tuning on this card would need gradient
checkpointing plus a smaller batch, i.e. a materially slower and different run.

**Honest limit of this answer.** Full fine-tuning has not been run head-to-head
against the frozen run, so this is a reasoned case from three measurements, not
a measured comparison. It is two flags away (`tune_llm`, `tune_visual`) if the
frozen run plateaus. It is not the thing to try first.
