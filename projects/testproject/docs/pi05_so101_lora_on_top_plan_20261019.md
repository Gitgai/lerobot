# R5 — LoRA on top of the public SO-101 π0.5 checkpoint with OUR real orange episodes

Date: 2026-10-19. Status: **GO 2026-10-21 (operator: "choose whichever GPU, SSD you like") — BUILDING.**
Choices made 2026-10-21: **GPU 1** (RTX PRO 5000 72 GB; empty at 04:4xZ — the operator's 66 GB openpi job has
ended; GPU 0 keeps the operator's LoRA server :18916 and our bench wrapper :8080, untouched). **Storage:**
/mnt/data4tb/so101-lora-on-top-20261021/ (2.9 TB free; DISK_LEDGER §10); the repo keeps only configs, logs
summaries and small JSON under results/so101_lora_on_top_20261019/. Control row on the bench: pending the
C270 move to the low-front position (R3 record).
Parent: pi05_so101_real_base_audit_plan_20261019.md (R5 row). Tracker: PI05_CURRENT_PRIORITY.md.

## What "LoRA on top" means (plain)
dongyoonkim/so101-pi05-base was trained on ~14,000 public SO-101 episodes, orange picking among them. We do
NOT retrain it. We freeze it and add small LoRA adapter weights (rank 16 in the author's own recipe) trained
only on our 109 unique real episodes, recorded on OUR arm, OUR two cameras, OUR tray, with OUR instruction. The bet:
the reaching and grasping skill is already in the base (simulator ladder: touch 88% / lift 26% even in an
unseen renderer; Isaac orange 76%); what it lacks is our rig — camera placement, fruit, tray, wording.
That is exactly what our episodes contain. LoRA, not full fine-tuning, because 109 episodes is small and the
point is to add our rig without erasing what the base knows.

What the bench has shown so far (trials 1–2, 2026-10-19): the base reaches the fruit every time and fails at
the grasp. Two trials are NOT evidence for this step — the R3 reading rule needs 20, and both failures may be
an object-size problem (the citrus looks wider than the jaws; unmeasured). R5 is the step the bench result
FEEDS; it is not justified by the bench result yet.

## Data (what we train on)
```text
set                        episodes  frames   fps  cameras        instruction(s)
so101_orange_89_v21           89     40,712   30   front, wrist   "pick up the orange and move it to another place"
plate_demos_v21               20     14,948   30   front, wrist   "pick up the orange and place it on the plate"
total UNIQUE                 109     55,660                       (/home/kiran/lerobot_assets/datasets/, so101_follower, LeRobot v2.1)
NOT 188 (corrected 2026-10-21 before training): orange79_plus_plate20 (99 ep) is the 79-episode train split of
so101_orange_89_v21 PLUS plate_demos_v21 — its first 79 episodes are byte-identical in length to the train79
split (checked), so counting both sets double-counts 79 episodes. Training set = a fresh v2.1 merge
orange89_plus_plate20 (89 + 20 = 109; scripts/merge_orange89_plus_plate20.py, videos symlinked, no re-encode).
front camera in ALL 109: the LOW FRONT view at table height (frame check 2026-10-21) — the bench must match it.
```
Decisions to take at build (each is a knob, not a guess — record the choice):
- instruction: keep the recorded strings (two of them) — the model sees our wording as the dataset wrote it;
  the bench client then sends the SAME string ("pick up the orange and place it on the plate" for the tray
  task). Do not train on one wording and test with another.
- camera slot map: front → base_0_rgb, wrist → left_wrist_0_rgb, third slot empty — the same map the wrapper
  uses (scripts/so101_base_policy_server.py), so train and serve agree.
- fps: both sets are 30 fps; the base was trained on 30 fps sources (the 10 fps ones were dropped, audit R4.3).
- hold-out: 10 episodes of orange_89 (the baseline's own hold-out ids 2,8,13,14,16,54,56,60,75,80) stay out
  for an open-loop sanity check (action MAE on unseen episodes); everything else trains.

## Recipe (the author's own LoRA config, read from /home/kiran/sim/vlash/examples/train/pi05/async_lora.yaml)
```text
base              pretrained_path = dongyoonkim/so101-pi05-base (their yaml says lerobot/pi05_base; we start
                  from the SO-101 checkpoint — that is the whole point)
LoRA              peft, r 16, alpha 16, dropout 0; targets q/k/v/o_proj, gate/up/down_proj, out_proj, fc1, fc2;
                  extra trainable: action_in/out_proj, time_mlp_in/out, state_proj, state_mlp_in/out,
                  embeddings, input/post_attention layernorm
what trains       NOT the same trainable set as the LIBERO LoRA (operator's point, 2026-10-21). openpi's LoRA
                  freeze filter (pi0_config.get_freeze_filter) freezes only the ".*llm.*" transformer weights;
                  the SigLIP vision encoder trained FULLY there (415M of 467M trainable, RESULTS doc §open items).
                  VLASH's config puts LoRA on the vision tower too (fc1/fc2/out_proj are SigLIP module names) and
                  fully trains only the small projections, embeddings and layernorms → far fewer trainable
                  parameters. Our rig gap is visual (cameras), so the vision-encoder choice is the knob most
                  likely to matter. Row 1 = the author's recipe as published (rule: never bend a published
                  recipe on the first run). Row 2, only if row 1 is partial = LIBERO-style: vision encoder fully
                  trainable + LoRA in the transformers. With 109 episodes (56k frames vs LIBERO's ~270k) row 2
                  carries a real overfitting/forgetting risk — the Isaac gate is what catches it.
optimiser         adamw lr 5e-5, betas (0.9, 0.95), wd 1e-10; cosine with 1k warm-up → 2.5e-6
batch             1 × grad_accum 8 = 8 (their consumer-GPU setting); steps 50,000 in the template
dtype             bfloat16 (their recipe; the openpi "no half precision" rule is openpi's recipe, not VLASH's —
                  we follow each stack's own published recipe, never bend one to the other)
async knob        max_delay_steps 8 trains the future-state-awareness head (VLASH's pipelined inference).
                  Our bench client is NON-PIPELINED. Two options: (a) sync.yaml + LoRA — no delay training,
                  matches how we serve; (b) keep async_lora.yaml — harmless for a non-pipelined client and
                  keeps the door open for VLASH's own pipelining later. DECIDE AT BUILD; default (b) only if
                  the wrapper already serves the base with the delay head present (it does — it is the
                  author's checkpoint), else (a).
steps             50k is the template for a large set; 109 episodes = 55,660 frames; at batch 8 one pass is ~7k steps
                  per 1.4k steps → 50k steps = ~4.4 passes… check the maths against the loader at build and
                  set steps from frames, as the LeIsaac plan does (target ~25-30 passes, record it)
checkpoints       every 2.5k steps (standing rule); smoke first (E1 preflight, 200 steps, resume test)
GPU               the 5090 (GPU 0 or 1): LoRA fits under 12 GB per the author; pick whichever GPU is free of
                  the operator's own jobs at the time (GPU 0 holds the LoRA server :18916, GPU 1 the 66 GB
                  openpi job as of 2026-10-19) — never evict either without the operator's word
time              hours, not days (LoRA, batch 8, one 5090) — measure from the first 500 steps and write it here
serving           the same wrapper loads the base + adapter (VLASH apply.py / checkpoint.py) behind :8080;
                  nothing changes on the Acer except the instruction string
```

## Build record (2026-10-21)
```text
data        orange89_plus_plate20 built (109 ep, 55,660 frames, 2 tasks; videos symlinked; 89 per-episode stats
            carried, plate_demos_v21 has none). scripts/merge_orange89_plus_plate20.py.
stats       our v2.1 stats carry only action/state/timestamp → VLASH's ImageNet-stats step raised KeyError on
            observation.images.front (first smoke, 14:39Z). Fix: dataset.use_imagenet_stats=false — VISUAL
            normalisation is IDENTITY in the checkpoint's config.json, so those stats were never used.
normalise   the checkpoint's model.safetensors carries its own MEAN_STD buffers (state mean [-0.4, -30.3, 37.3,
            55.3, -4.5, 13.8], std [27.6, 50.2, 48.8, 36.8, 36.2, 16.6]; action likewise). from_pretrained loads
            them over the dataset-initialised buffers → training normalises with the CORPUS stats, the same ones
            the bench wrapper uses (it loads the checkpoint with no dataset stats). Train and serve agree. Our
            dataset's stats.json is therefore not on the maths path. (Verify once on the smoke checkpoint: the
            saved buffers must equal the values above.)
video       torchcodec fails to load in vlash-venv → video_backend pyav (15.1.0).
smoke       PASSED 14:46Z. unit r5-smoke, GPU 1, 60 steps, save every 30: loader OK (v2.1 compat), 154M learnable
            of 3.77B (LoRA + the listed extra modules), loss 0.037 → 0.023, 1.1–1.3 s per optimizer step (batch 1
            × accum 8). Checkpoint = 8.6 GB: model.safetensors is the MERGED model (824 tensors, no LoRA keys —
            directly servable by the bench wrapper) + lora_adapters/ (571 MB, 1,332 tensors) + 1.2 GB optimizer
            state. Normalisation buffers in the checkpoint == the corpus stats (checked tensor-equal). Resume
            test: unit r5-smoke-resume auto-resumed from step 60 (adapters reloaded), ran to 90, saved. Host
            memory peak 30.7 GB + 5.4 GB swap during the save. Smoke outputs deleted (ledger §4).
run         ROW 1 first launch 2026-10-21 18:47Z (14:47 local; journal stamps are LOCAL = UTC−4): batch 1 × accum 8 as
            published → 13 of 72 GB, 76% util, 1.18 s/step, loss 0.016 @500, 0.012 @2k, ckpt at 2,500 (19:35Z).
            STOPPED at ~2.6k on the operator's go (micro-batch change, 19:38Z); that run's dir row1_author_lora/
            (one 8.6 GB ckpt) is kept for the record (ledger §10).
            RELAUNCHED 19:40Z as batch 8 × accum 1 (same effective batch, same recipe otherwise), output
            row1_author_lora_b8/: 34 of 72 GB, 70% util, 0.62 s/step (1.9× faster) → 25k steps ≈ 4.3 h,
            ETA ≈ 00:00Z 2026-10-22. Loss at step 100: 0.035 (warm-up, lr still 2.6e-6).
            Monitor: checkpoints, errors, a HEALTH line (latest step/loss/speed, swap, RAM, dir size, GPU) every 30 min.
DONE        ROW 1 TRAINING FINISHED 2026-10-22 00:07Z: 25,000 steps in 4 h 27 min (0.62 s/step), loss 0.035 (warm-up)
            → 0.014 @0.8k → 0.010 @4k → 0.006 @9k → 0.004 @20–25k; 10 checkpoints, 86 GB (dir total 94 GB incl. the
            stopped first launch). No errors, no resume needed; swap peaked ~35 GB (file-cache driven), RAM never short.
            Isaac gate launched 00:09Z on checkpoint 025000 (unit r5-gate → so101-lora-server :8081 on GPU 1 + Isaac
            headless on GPU 1; rows corpusA then plateC, 50 episodes each).
gate bugs   (1) 00:08Z launcher used a relative script path under systemd → exit 127; (2) 00:08Z the Isaac runner
            looked for sim_eval_logged.py in OUTDIR → rc=2; (3) 00:10Z the LeIsaac client crashed decoding the first
            reply: since the 2026-10-19 bench change the wrapper tagged reply pickles with the SERVER's module name
            (lerobot.async_inference.helpers), which LeIsaac's venv cannot import (lerobot 0.4.2 + transformers 5.14
            + huggingface_hub 0.35 clash on import). The R2 runs never hit it because they were served by the older
            wrapper process that was never restarted. Fix: the wrapper reads the module path from the client's own
            pickle bytes (custom Unpickler.find_class) and tags replies with that. Gate relaunched 00:16Z.
serving     BUG FOUND AND FIXED before the gate (21:30Z): LoRA checkpoints save image features as observation.images.
            front/.wrist (our dataset's names); the wrapper hard-coded base_0_rgb/left_wrist_0_rgb → both slots would
            have been "missing" and the model blind. Wrapper now reads slot names from the checkpoint config in order.
            Served the 010000 checkpoint on :8082 beside the training: slots mapped front→front, wrist→wrist; one real
            frame pair + state from episode 0 → a0 within 1.8 units of the state and 1.7 of the recorded next action;
            300 ms per call uncompiled on the busy GPU. The bench wrapper (base) is unaffected (same names as before).
config      results/so101_lora_on_top_20261019/row1_author_lora.yaml; launcher run_r5.sh (systemd user units
            r5-smoke / r5-row1; CUDA_VISIBLE_DEVICES=1, HF_HOME on data4tb, TMPDIR on /home).
```

## Gate (before any bench time): Isaac orange task, R2 harness
Score the adapted model on the LeIsaac pick-orange task with the same harness that scored the base
(results/so101_base_sim_test_20261020/, 100 seeded episodes, non-pipelined, chunk 20).
```text
control   the base itself: 76% with the corpus wording, 32% with ours (R2, 2026-10-19)
what the gate IS      a "did not break it" check: Isaac is in the base's training distribution, so a large
                      drop there means the fine-tune damaged the base (forgetting) — found for free, before
                      anyone stands at the arm
what the gate IS NOT  a prediction of bench success: Isaac is not our rig; passing it says the model still
                      works, not that it now works on our table
readings  ≥ ~65% (within the 95% CI of 76 at n=100)   → base intact; go to the bench
          40–65%                                      → partial forgetting; try lower lr / fewer steps / freeze more before the bench
          < 40%                                       → broken; do not bench; check the slot map and the instruction first
also      open-loop MAE on the 10 held-out real episodes vs the base's MAE on the same (sanity floor, not success)
```
Pre-registered rows (2026-10-21, launcher results/so101_lora_on_top_20261019/run_isaac_gate.sh, everything on GPU 1,
LoRA server :8081, Isaac headless, 50 seeded episodes per row, the SAME seeds as the base's control rows):
```text
row      instruction                                        seeds     control (base)   what it tests
corpusA  "Grab oranges and place into plate."               100–149   38/50 = 76%      forgetting (the gate proper)
plateC   "pick up the orange and place it on the plate"     300–349   none scored      our own plate wording on the Isaac task
oursB    "pick up the orange and move it to another place"  200–249   16/50 = 32%      optional (WITH_OURSB=1): our other wording
which ckpt  the final one (025000) first; a second checkpoint (012500) only if the final fails the gate
reading     corpusA ≥ ~65% → go to the bench; 40–65% → partial forgetting, see recipe row 2 / fewer steps; < 40% → broken
```

### Gate results (2026-10-22)
```text
ckpt 025000  corpusA  0/5, all five timed out at the 100 s cap (base: 4/5 on the same seeds 100–104; 38/50 overall).
             Server log: the arm reaches out over the oranges and cycles the gripper for the whole episode — the
             bench behaviour, now in the scene where the base scored 76%. Row STOPPED at 5 by me (00:53Z): each
             timeout costs 7 min and 0/5 against 4/5 is already far below the pre-registered < 40% "broken" line.
             DEVIATION from the 50-episode pre-registration, recorded here; the 5 episodes are the result.
ckpt 025000  plateC   0/5, all timed out (seeds 300–304; our own trained wording). Stopped at 5 (01:32Z), same rule.
             → cause (b), the instruction, is ruled out: a wording it was trained on fails identically.
ckpt 012500  corpusA  0/5, all timed out (seeds 100–104; base 4/5). Stopped at 5 (02:10Z). FRAMES (montage_012500_ep1.jpg):
             the scene renders correctly in both cameras (plate, three oranges, arm), so cause (c) serving is ruled
             out. Behaviour: the arm goes to the oranges, hovers with the gripper pointing down, nudges them, never
             closes on one — the bench behaviour reproduced in the scene where the base scored 76%.
open-loop    (02:0xZ, openloop_mae.py, 302 probe frames from the 10 August hold-out episodes of orange_89, every 15th
             frame; next-10 actions vs the recorded ones; LeRobot units) — did the fine-tune move the model toward OUR
             demonstrations? Yes, monotonically with steps. NOTE these 10 episodes are inside the R5 training set, so
             for the LoRA rows this is a seen-data floor; for the base they are unseen.
               model     arm-joint MAE (°)   gripper MAE   gripper open/close agreement at step 10
               base            5.97              8.34               0.725
               lora 5k         3.77              3.45               0.818
               lora 12.5k      3.13              2.56               0.871
               lora 25k        2.66              2.09               0.877
             Reading: the adapters learned our rig's motions (the gripper timing above all: 8.3 → 2.1) while the
             Isaac skill was lost. Whether "learned our motions" turns into grasps on the bench is exactly what the
             bench row will measure — the Isaac gate cannot answer that for a model trained only on our table.
reading      the final checkpoint FORGOT the Isaac scene. Candidate causes, to be separated by the next rows:
             (a) too many steps for 109 episodes of one rig (25k = 3.6 passes; the base's own skill drifted away) →
                 earlier checkpoints 012500 and 005000 on corpusA, 20 episodes each;
             (b) the instruction: "Grab oranges…" never appeared in our 109 episodes and the recipe trains the
                 token EMBEDDINGS (extra_trainable_modules) → plateC (a trained wording) tells us if the language
                 channel still works at all;
             (c) nothing wrong with the model, only with serving → the slot/layout checks passed and the server
                 answers every call; the same wrapper scores the base at 76%, so (c) is unlikely but the
                 recorder will be on for the next rows (RECORD_EVERY=25) to see the frames.
```

## Bench after the gate
Same R3 protocol, same client, same 20-placement grid, same fruit as the base's trials (so the two 20-trial
sets compare), instruction = the dataset's own string. The base's 20 are the control row. Reading: the
difference in successes out of 20, with its CI — two rows, one table, contacts/knock-overs counted.

## What it will and will not tell us
WILL  whether our 109 episodes close the rig gap on top of a competent base — the cheapest path to a working
      bench policy, and the first real number for "public base + our data"
WON'T whether full fine-tuning would do better (that is the LIBERO/LeIsaac comparison's job, in sim); whether
      more of our data helps (a second row later, if R5 is partial)

## Outputs
results/so101_lora_on_top_20261019/{config.yaml, train.log, smoke/, isaac_gate.jsonl, holdout_mae.json,
bench_runs.md (row 2 beside the base's)}; adapter weights on /mnt/data4tb (ledger entry before the run).
Cost: ½ day build (loader + slot map + instruction check + smoke), hours of training, 2 h Isaac gate.

## Not started. Blocking: operator's go; a free 5090; the bench's base row (R3) in hand or at least underway.
