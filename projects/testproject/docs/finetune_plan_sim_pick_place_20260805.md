# Fine-tuning plan: GR00T first, then Pi05 — sim pick-and-place

> # ⚠️ SUPERSEDED 2026-08-06 by `PLAN_real_arm_via_gr00t_20260806.md`
>
> **Phase 1 (reproduce their fine-tune on their dataset) is DROPPED.** It answers
> "could we train one if we needed to", but we already have a working sim
> checkpoint and the real blocker is HARDWARE, not sim capability.
>
> Kept because its findings are still load-bearing: **Phase 0's measured
> baseline** (5/5 runs, 15/15 oranges, first-place ranging step 228–1832), the
> **AV1 codec trap**, and the **32 GB memory ceiling** — that last one blocks the
> new plan too, and is now its first step. The data-prep work is done and
> committed, so Phase 1 can be resumed cheaply if ever wanted.

Date: 2026-08-05. Written after a sim-trained GR00T N1.6 checkpoint completed
the whole PickOrange task, which is what makes this plan worth running.

---

## 0. Read this before planning anything

```text
THE PREMISE THAT MOTIVATED THIS PLAN IS ALREADY OUT OF DATE.

"N1.6 grasps but never places" was OUR RUN LENGTH, not the policy. At 3,000
steps it picks and places ALL THREE oranges (lifts 0.162/0.190/0.187 m, 33
place-term steps vs the scripted state machine's 16).
-> gr00t_n16_sim_trained_SUCCESS_20260805.md section 1b

SO THE GOAL IS NOT "TEACH IT TO PLACE". IT PLACES.
The honest open questions are:
  1. RELIABILITY. n=2 runs, NO SEED CONTROL, and they differed. We do not know
     the success rate. This is the cheapest and most valuable thing to measure
     and it needs NO training at all.
  2. Whether OUR OWN fine-tune can match 0.17-0.19 m of lift and 3 place cycles.
     That is a pipeline-validation goal, not a capability goal.
```

**Recommendation: measure reliability BEFORE training anything.** Five seeded
3,000-step runs cost ~1 hour of GPU and tell us what "working" actually means
here. Fine-tuning to beat an unmeasured baseline is how you end up unable to
tell improvement from variance.

---

## 1. What already exists, verified today

```text
DATA
  LightwheelAI/leisaac-pick-orange        v2.1, 60 eps, 36,293 frames, 30 fps,
                                          front+wrist, so101_follower, ungated
                                          task: "Grab orange and place into plate"
  LightwheelAI/leisaac-pick-orange-mimic-v0   60 eps / 41,891 frames (Mimic-made)
  our own sim place data                  4 episodes / 12 place operations, HDF5

GENERATION (no hardware, no teleop)
  state machine   scripts/datagen/state_machine/generate.py   PickOrange ONLY
  Isaac Lab Mimic scripts/mimic/{annotate_demos,generate_dataset}.py
                  PickOrange AND LiftCube - a few demos in, many out

CONVERSION
  leisaac scripts/convert/isaaclab2lerobot.py     HDF5 -> LeRobot v2  <- what GR00T wants
                        isaaclab2lerobotv3.py     HDF5 -> LeRobot v3.0
                        lerobot2isaaclab.py       the reverse

TRAINING
  Isaac-GR00T-n16/gr00t/experiment/launch_finetune.py  +  examples/finetune.sh
  defaults: GLOBAL_BATCH_SIZE=32, MAX_STEPS=10000, SAVE_STEPS=1000
  tune_diffusion_model=True, tune_projector=True   (trained)
  tune_llm=False, tune_visual=False                (frozen)  <- keeps VRAM down
  NO LoRA flag found in n1.6 - it is full fine-tuning of the action head.
```

---

## 2. THE TWO REAL BLOCKERS (both found by inspection, neither is fatal)

### 2a. The public dataset is NOT GR00T-flavored

GR00T needs **"GR00T-flavored LeRobot v2"**, which is standard LeRobot _plus_
extra meta files. Compare:

```text
LightwheelAI/leisaac-pick-orange   meta/: episodes.jsonl  episodes_stats.jsonl
                                          info.json  tasks.jsonl
GR00T demo_data/cube_to_bowl_5     meta/: episodes.jsonl  info.json  tasks.jsonl
                                          modality.json       <- MISSING
                                          stats.json          <- MISSING
                                          relative_stats.json <- MISSING
```

`modality.json` is trivial — `examples/SO100/modality.json` maps **exactly** onto
this dataset (single_arm 0:5, gripper 5:6, front/wrist, task_index) and can be
copied verbatim. `stats.json` / `relative_stats.json` must be **computed** from
the data; `gr00t/data/stats.py` is the code that reads them, so check whether it
can also generate them before writing anything by hand.

> **Do not assume the v2.1 tag means compatible.** The version matched and three
> required files were still absent. This is the same class of trap as the ACT
> checkpoint that loaded fine while silently dropping its normalization.

### 2b. LeIsaac's converter needs ITS OWN era-matched venv

`isaaclab2lerobot.py` docstring: **`pip install lerobot==0.3.3`,
`numpy==1.26.0`**. Ours are LeRobot 0.6.1 / 0.5.2. So converting _our own_ sim
HDF5 costs another venv — the fourth today.

**This is avoidable at first.** The public dataset is already in LeRobot format;
only our own generated data needs the converter. Sequence the plan so the
converter is not on the critical path.

---

## 3. The plan

### Phase 0 — MEASURE THE BASELINE — **_ DONE 2026-08-06 _**

```text
run                     steps  placed          lifts (m)      placeSteps  1stPlace
run1_seed1001            3000   3/3   [0.145, 0.146, 0.160]        20        552
run2_seed1002            3000   3/3   [0.167, 0.130, 0.146]        23        784
run3_seed1003            3000   3/3   [0.188, 0.160, 0.162]        33        421
run4_seed1004            3000   3/3   [0.173, 0.286, 0.171]        19        228
run5_seed1005            3000   3/3   [0.180, 0.163, 0.141]        19       1832

  full task (3/3 placed)  : 5/5  = 100%      placed per run: mean 3.00, stdev 0.00
  real grasps (lift>0.10) : 15/15 = 100%     every single grasp is REAL, not a
                                             proximity artefact

INCLUDING the two earlier UNSEEDED 3,000-step runs (one of which placed 2/3):
  full task 3/3   6/7 = 86%
  oranges placed  20/21 = 95%
```

**The baseline is not "variable". It is ~86-100% and stdev 0.00 across the
seeded sweep.** My earlier "the policy is stochastic" call came from n=2 with one
unlucky run; five controlled runs do not reproduce it.

```text
*** AND THE FINDING THAT MATTERS MOST ***
first place occurred anywhere between step 228 and step 1832.

A 900-STEP RUN WOULD HAVE MISSED THE SUCCESS IN run5 ENTIRELY.

That is exactly how this project concluded "N1.6 grasps but never places", and
it is a warning about every 900-1500 step verdict recorded here - including
Pi05's. Time-to-first-success varies by 8x between runs of the SAME policy on
the SAME task.
```

**Consequence for the rest of this plan: there is no capability gap to close.**
The reference policy performs the full task essentially every time. Phases 1-2
are therefore PIPELINE VALIDATION - can _we_ produce a checkpoint this good? -
and not an attempt to beat a weak baseline.

### Phase 1 — IN PROGRESS 2026-08-06. Data ready; training BLOCKED on a GPU leak.

```text
DONE
  dataset downloaded            667 MB, 60 eps -> ~/lerobot_assets/datasets/leisaac_pick_orange
  meta/modality.json            written from examples/SO100 - it maps EXACTLY
                                (state/action [6] = single_arm 0:5 + gripper 5:6,
                                 video front/wrist). Kept in the repo at
                                 configs/leisaac_pick_orange_modality.json
  meta/stats.json               generated by gr00t.data.stats
  meta/relative_stats.json      needed a REGISTERED modality config first ->
                                configs/leisaac_so101_gr00t_config.py
                                (single_arm RELATIVE, gripper ABSOLUTE - the same
                                 pair the working 12e21 checkpoint declares)
  base model                    nvidia/GR00T-N1.6-3B, 6.2 GB, UNGATED
  training                      launches, builds 35 shards, starts stepping

BLOCKED
  A hard-killed earlier run LEAKED 10 GB that the driver has not reclaimed:
      PID 2617365 -> 10,020 MiB, process state [Not Found] (dead)
  That leaves ~21 GB, and the fine-tune OOMs even at GLOBAL_BATCH_SIZE=8 while
  trying to allocate 20 MB - so it is the leak, not the batch size.
  FIX (needs the user, sudo):   sudo nvidia-smi --gpu-reset -i 0
  A reboot also clears it.

  DO NOT work around this by shrinking the model config. Phase 1 exists to
  reproduce a reference checkpoint; a different config makes the comparison
  meaningless.
```

#### **_ THE AV1 TRAP — three failures, none of which mention video _**

`LightwheelAI/leisaac-pick-orange` stores its video as **AV1**. On this machine
that breaks GR00T's dataloader three separate ways:

```text
torchcodec (the DEFAULT)  fails to IMPORT. torchcodec 0.4.0 links FFmpeg 4-6
    (libavutil.so.56/57/58); this machine has FFmpeg 8. Even torchcodec 0.8.0
    only claims FFmpeg 4-7.
    -> resolve_backend() falls back to pyav, which get_frames_by_indices does
       NOT implement, so training dies on a BARE NotImplementedError with no
       mention of video, codecs or backends.
decord                    imports fine, cannot demux AV1:
    "cannot find video stream with wanted index: -1"
ffmpeg (CLI)              WORKS but spawns a subprocess PER FRAME
    (ffmpeg -vf select=eq(n\,502) -vframes 1 ...) = 153 ms per 3-frame fetch.
    Symptom: GPU at 4-5% utilisation and ZERO steps completed. It looks like a
    hang, not a decode problem.

FIX: transcode once. scripts/transcode_dataset_av1_to_h264.sh
     120 files, ~2 min, frame counts verified per file.
     After: decord 15.8 ms/fetch vs ffmpeg 196 ms - 12x faster.
```

> **Generalise this:** a dataset can be the right LeRobot version, the right
> robot, the right cameras — and still be unusable because of its CODEC. Check
> `ffprobe -show_entries stream=codec_name` before trusting a training run that
> appears to hang.

### Phase 1 — original plan (pipeline validation, ~half a day)

```text
1. Download LightwheelAI/leisaac-pick-orange (v2.1, 60 eps).
2. Add meta/modality.json (copy examples/SO100/modality.json).
3. Generate meta/stats.json + relative_stats.json - check gr00t/data/stats.py
   for a generator before hand-rolling.
4. Fine-tune GR00T N1.6 from the BASE model (nvidia/GR00T-N1.6-3B), 10k steps,
   batch 32, tune_diffusion_model+projector only.
5. Score with sim_policy_eval_instrumented.py at 3,000 steps.
GATE: does OUR fine-tune reach ~0.17 m lift and place 3/3, like theirs?
      If yes, the whole training pipeline is ours and verified end to end.
      If no, the gap is in OUR pipeline - and we have their checkpoint as a
      known-good control to diff against. That is a luxury we have never had.
```

**This is the highest-value phase.** It converts "someone else's checkpoint
works" into "we can produce a working checkpoint", using a dataset whose correct
answer we have already seen.

### Phase 2 — OUR OWN DATA (~half a day)

```text
1. Build the lerobot==0.3.3 + numpy==1.26 venv for isaaclab2lerobot.py.
2. Generate a few hundred episodes with the state machine (fully automatic).
3. Convert -> LeRobot v2, add modality.json + stats.
4. Fine-tune again, compare against Phase 1.
GATE: does OUR data match THEIR data's result? This isolates data quality from
      pipeline correctness, because Phase 1 already fixed the pipeline.
Optional: Isaac Lab Mimic to multiply episodes instead of long generation runs.
```

### Phase 3 — PI05, same shape

```text
Only after Phases 1-2 succeed. Pi05 is the harder case and we know why:
  - it is 4.14B vs N1.6's ~1.09B DiT
  - our 012000 is welded to ONE real table and hovers 13-18 cm in sim,
    0 grasps in EVERY run
  - Era 1 applies: it must be trained AND served on matching code
  - LeRobot writes v3.0; GR00T wanted v2.1 - for Pi05 we stay in LeRobot, so
    the version question changes shape, but CHECK IT rather than assume
Same gates: reproduce on the public dataset first, then our own data.
```

---

## 4. What I think (asked directly)

```text
1. MEASURE BEFORE TRAINING. We have exactly two runs of the working checkpoint
   and they disagreed. Every hour of fine-tuning spent before we know the
   variance is an hour we cannot interpret afterwards.

2. PHASE 1 IS THE ONE THAT MATTERS. Reproducing a KNOWN-GOOD result on a
   KNOWN-GOOD dataset is the only experiment here with an unambiguous verdict.
   Skipping straight to our own data confounds "bad pipeline" with "bad data".

3. THE SIM->REAL QUESTION IS STILL COMPLETELY UNTOUCHED. Everything above
   improves a simulator score. Nothing has been tested on the real arm ALL DAY,
   and the project's central bet is that sim results transfer. A working sim
   policy makes that bet TESTABLE for the first time - which is arguably more
   valuable than any further sim tuning.

4. PI05 LAST, AND POSSIBLY NOT AT ALL. N1.6 already does the task at 1/4 the
   parameters. If the goal is a working arm, fine-tuning GR00T further is the
   cheaper road; if the goal is understanding why 012000 fails, that is a
   different investigation and the sim is now a good place to run it.
```

---

## 5. Costs, honestly

```text
Phase 0   ~1 h GPU, no training, no new environments        <- do this first
Phase 1   ~half a day: download + 3 meta files + a 10k-step run + scoring
Phase 2   ~half a day + ONE MORE VENV (lerobot 0.3.3)
Phase 3   unscoped; Pi05 is a bigger model and a harder starting point

VRAM: 32 GB available; N1.6 SERVES in ~8.2 GB. Fine-tuning with tune_llm=False
and tune_visual=False should fit, but this is UNVERIFIED - the NVIDIA post's
~25 GB figure was for a different configuration and has never been checked here.
Measure it on the first run rather than planning around the blog number.
```

**Unchanged, and increasingly load-bearing:** nothing has been tested on the
real arm.
