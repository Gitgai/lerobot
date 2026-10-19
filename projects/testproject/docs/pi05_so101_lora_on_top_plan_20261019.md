# R5 — LoRA on top of the public SO-101 π0.5 checkpoint with OUR real orange episodes

Date: 2026-10-19. Status: **PROPOSED — next build after the bench trials; awaiting go.**
Parent: pi05_so101_real_base_audit_plan_20261019.md (R5 row). Tracker: PI05_CURRENT_PRIORITY.md.

## What "LoRA on top" means (plain)
dongyoonkim/so101-pi05-base was trained on ~14,000 public SO-101 episodes, orange picking among them. We do
NOT retrain it. We freeze it and add small LoRA adapter weights (rank 16 in the author's own recipe) trained
only on our 188 real episodes, recorded on OUR arm, OUR two cameras, OUR tray, with OUR instruction. The bet:
the reaching and grasping skill is already in the base (simulator ladder: touch 88% / lift 26% even in an
unseen renderer; Isaac orange 76%); what it lacks is our rig — camera placement, fruit, tray, wording.
That is exactly what our episodes contain. LoRA, not full fine-tuning, because 188 episodes is small and the
point is to add our rig without erasing what the base knows.

What the bench has shown so far (trials 1–2, 2026-10-19): the base reaches the fruit every time and fails at
the grasp. Two trials are NOT evidence for this step — the R3 reading rule needs 20, and both failures may be
an object-size problem (the citrus looks wider than the jaws; unmeasured). R5 is the step the bench result
FEEDS; it is not justified by the bench result yet.

## Data (what we train on)
```text
set                        episodes  frames   fps  cameras        instruction(s)
so101_orange_89_v21           89     40,712   30   front, wrist   "pick up the orange and move it to another place"
orange79_plus_plate20         99     51,119   30   front, wrist   79 × the same + 20 × "pick up the orange and place it on the plate"
total                        188     91,831                       (/home/kiran/lerobot_assets/datasets/, so101_follower, LeRobot format)
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
steps             50k is the template for a large set; 188 episodes × 91k frames at batch 8 is ~11k frames
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

## Bench after the gate
Same R3 protocol, same client, same 20-placement grid, same fruit as the base's trials (so the two 20-trial
sets compare), instruction = the dataset's own string. The base's 20 are the control row. Reading: the
difference in successes out of 20, with its CI — two rows, one table, contacts/knock-overs counted.

## What it will and will not tell us
WILL  whether our 188 episodes close the rig gap on top of a competent base — the cheapest path to a working
      bench policy, and the first real number for "public base + our data"
WON'T whether full fine-tuning would do better (that is the LIBERO/LeIsaac comparison's job, in sim); whether
      more of our data helps (a second row later, if R5 is partial)

## Outputs
results/so101_lora_on_top_20261019/{config.yaml, train.log, smoke/, isaac_gate.jsonl, holdout_mae.json,
bench_runs.md (row 2 beside the base's)}; adapter weights on /mnt/data4tb (ledger entry before the run).
Cost: ½ day build (loader + slot map + instruction check + smoke), hours of training, 2 h Isaac gate.

## Not started. Blocking: operator's go; a free 5090; the bench's base row (R3) in hand or at least underway.
