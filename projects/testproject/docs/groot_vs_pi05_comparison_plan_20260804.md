# GR00T N1.5 vs Pi05: Architecture Comparison Plan

Last updated: 2026-08-05
Status: **PARTLY OVERTAKEN BY EVENTS — read this box before following the plan.**
Slots into: `pi05_generalization_roadmap_20260802.md` as **Stage 3b**, after the
Stage 2 recording session.

```text
WHAT ACTUALLY HAPPENED, 2026-08-05
This plan assumed the comparison required FINE-TUNING GR00T on our data. It did
not. A PUBLIC GR00T N1.7 checkpoint (robocurve/gr00t-n1.7-so101-molmoact2) was
served locally and scored against Pi05 in the SAME sim scene, on the SAME
ground-truth metrics, with NO fine-tuning and NO robot time.

  Pi05 012000  hovers 13-18 cm, never satisfies even proximity+closure
  GR00T N1.7   reaches the grasp frame to 0.039 m and closes for 80 steps,
               but the orange moves 0.0001 m - it acquires NOTHING

  -> gr00t_n17_sim_evaluation_20260805.md

SO THE VERSION IS N1.7, NOT N1.5, and Sections 3-6 below (dataset conversion,
fine-tuning, VRAM budgeting) are NOT prerequisites for a first comparison. They
remain the plan for a FINE-TUNED comparison, which is a different question.

READ THE COMPARISON CAUTIOUSLY: it is not apples-to-apples. Pi05 is a
single-task specialist trained on THIS task and doing only a sim-transfer;
GR00T is a broad generalist (2,242 eps / 39 repos) doing task-transfer AND
sim-transfer at once.

*** AND THE PLAN'S REAL QUESTION GOT ANSWERED A DIFFERENT WAY ***
A GR00T N1.6 checkpoint fine-tuned INSIDE LeIsaac grasped, lifted 0.173 m and
carried the orange 0.260 m in the same scene, scored identically - the project's
first real manipulation success. So:

  the 1.09B model trained on THIS SIMULATOR beats
  the 4.14B Pi05 trained on real frames of THIS TASK, and
  the broad 2,242-episode community generalist,
  decisively, in this scene.

=> TRAINING DOMAIN DOMINATES MODEL SIZE AND BREADTH. That is the architecture
   comparison this document set out to run, arrived at without fine-tuning
   anything ourselves.
-> gr00t_n16_sim_trained_SUCCESS_20260805.md
```

---

## 1. Why This Exists

The handoff (`agent_handoff_pi05_20260803.md`, Section 3) concludes:

```text
"Every gap on that list is a DATA problem (Stage 2), not a model or
 infrastructure problem."
```

That is a strong claim and it is currently **untested**. It rests on one
architecture. Everything we know about place-failure and position-failure comes
from Pi05 012000 and nothing else.

A second architecture trained on identical data tests it directly:

```text
BOTH fail the same way  -> the data hypothesis is CONFIRMED. Stage 2 was the
                           right call and the roadmap stands.
GR00T succeeds          -> the claim is WRONG. Architecture mattered, and the
                           roadmap needs rethinking before more recording.
Pi05 succeeds, GR00T not-> our data suits flow-matching specifically; useful to
                           know before adopting anything new.
```

Every outcome is informative. That is the test worth running.

**Pre-register the reading before running it.** This project's habit of writing
down wrong turns is what makes its docs trustworthy; deciding what an outcome
means *after* seeing it is how that habit fails.

---

## 2. Why This Is Newly Affordable

Verified on this machine 2026-08-04, not assumed:

```text
GPU ................. RTX 5090, 32 GB, sm_120, driver 595.84
torch 2.7.0+cu128 ... sm_120 in arch list, 181.3 TFLOPS bf16 (real kernel)
Pi05 012000 ......... loads locally, 4.14B params, 9.5 GB VRAM,
                      153 ms per 50-action chunk
```

From the NVIDIA post (**unverified on our hardware**): GR00T N1.5 fine-tuning
needs **~25 GB VRAM**, demonstrated on an RTX 4080.

```text
25 GB needed vs 32 GB available -> fine-tuning runs LOCALLY.
```

This is the change that makes the comparison cheap. Every previous fine-tune
went to RunPod because the old laptop was CPU-only. Training is now GPU hours we
already own, with no pod, no tunnel, and no balance to watch.

The scarce resource is no longer compute. **It is robot time.** Both models
consume the same recording session, which is the entire argument for running
them as one experiment rather than two.

Corollary worth testing separately: Pi05 trained on the pod's 24 GB 3090 at
batch size 4. A 32 GB card should train it too. If that holds, RunPod leaves the
project completely.

---

## 2b. THE NVIDIA BLOG IS OUTDATED — USE THE REPO'S OWN DOCS (checked 2026-08-05)

Cloned `NVIDIA/Isaac-GR00T` at `b995540` (2026-07-31). The HuggingFace tutorial
(`huggingface.co/blog/nvidia/gr00t-n1-5-so101-tuning`) references files and flags
that **no longer exist**. Follow `examples/SO100/README.md` in the repo instead.

```text
BLOG SAYS                               CURRENT REPO
  model GR00T N1.5                        nvidia/GR00T-N1.7-3B     <- N1.7
  getting_started/examples/...json         examples/SO100/modality.json
  --data-config so100_dualcam              --modality-config-path examples/SO100/so100_config.py
  scripts/gr00t_finetune.py                examples/finetune.sh launcher
  dataset youliangtan/so101-table-cleanup  izuluaga/finish_sandwich (repo example)
  python / pip                             uv run --project ...    <- they use uv
requires-python >=3.12,<3.13 | torch==2.9.0 | torchvision==0.24.0 | torchcodec==0.8.0
```

### THREE FINDINGS THAT CHANGE THIS PLAN

**1. The v3 -> v2 conversion problem is SOLVED UPSTREAM.**

```text
scripts/lerobot_conversion/convert_v3_to_v2.py  SHIPS IN THE REPO.
Section 3 below flagged a backward v3->v2 conversion as possibly the largest
single task in this plan. It is not - NVIDIA provide it, with its own pyproject
so it runs in an isolated env:
  uv run --project scripts/lerobot_conversion \
    python scripts/lerobot_conversion/convert_v3_to_v2.py --repo-id <id> --root <dir>
```

**2. GR00T's SO-101 config is TWO cameras - `front` + `wrist`.**

> **UPDATE 2026-08-05: two cameras is their EXAMPLE, NOT A LIMIT.** Checked in
> the code: no `max_views`/`num_views` constant exists, `modality_keys` is a
> plain list, and the loader iterates whatever is declared;
> `getting_started/data_config.md` shows adding cameras by extending the list.
> So GR00T can take three, and the "identical inputs" concern below **largely
> dissolves** - we can give both models the same three views.
> Honest caveat: no config limit is not proof the MODEL handles three views
> well. Every shipped example is 1-2 views, and the ~25 GB VRAM figure is from a
> TWO-camera setup (we have 32 GB). Treat 3-camera GR00T as a measurable
> question, not an assumption.
> Because `modality_keys` is per-config, view selection is a CONFIG SWAP rather
> than a re-record: record once with three cameras, then evaluate GR00T-2cam,
> GR00T-3cam and Pi05-3cam off the SAME episodes.
> -> `sim_first_strategy_20260805.md` Section 4

```text
examples/SO100/modality.json
  state  -> single_arm, gripper
  action -> single_arm, gripper
  video  -> ['front', 'wrist']        <- NO top camera
  annotation -> human.task_description

CONSEQUENCE: this matches the LeIsaac SIM output EXACTLY (the sim scene exposes
front + wrist, no top). Our Pi05 declares front/top/wrist and must pad and mask
the missing view.
=> For SIM-GENERATED data GR00T is the BETTER-FITTING architecture. That
   strengthens the case for this comparison - but it also means the two models
   would NOT see identical inputs on sim data, weakening "identical data" as a
   controlled variable. SAY SO when scoring. Does not affect the REAL-robot
   comparison, where we have three cameras.
```

**3. GR00T defaults to RELATIVE ACTIONS, gripper excluded.**

```text
Repo README: "this will use relative actions by default for all axes except
the gripper."

That is EXACTLY what our Stage 3 plan decided to adopt for Pi05:
  --policy.use_relative_actions=true
  --policy.relative_exclude_joints='["gripper"]'
(handoff Section 6: absolute joint targets literally encode the practiced table
position - our verified failure mode.)

GR00T ships as its DEFAULT the thing we independently identified as a fix.
Convergence from a different team on the same idea. Worth weighting.
```

---

## 3. Blocking Prerequisite: Dataset Format

**This is the one thing that can stop the plan, and it needs checking first.**

```text
VERIFIED 2026-08-04:
  fork main        CODEBASE_VERSION = "v3.0"   (src/lerobot/datasets/dataset_metadata.py:53)
  training-era     CODEBASE_VERSION = "v3.0"   (e40b58a8, same constant)
  repo converter   convert_dataset_v21_to_v30.py  <- FORWARD ONLY (v2.1 -> v3.0)

FROM THE POST (unverified):
  GR00T N1.5 supports LeRobot datasets "v2.0+", current implementation targets
  v2; v3 handling exists via community tooling, not first-party.
```

So our datasets are almost certainly **v3.0**, GR00T wants **v2**, and the only
converter we ship runs the wrong direction. Resolve before anything else:

```text
1. Confirm the actual version string in a real dataset's meta/info.json
   (datasets are NOT on this machine - they were on the old laptop at
   /data/lerobot_datasets/. Locate them first.)
2. Determine what GR00T's loader accepts TODAY, from its repo, not the blog.
3. If a v3 -> v2 step is needed, treat writing it as part of this plan's cost,
   not a footnote. It may be the largest single task here.
```

If this turns out to be expensive, that is a legitimate reason to defer the
whole comparison. Say so rather than absorbing it silently.

---

## 4. The Protocol

One recording session, two fine-tunes, identical scoring.

```text
DATA
  The Stage 2 dataset, unchanged and shared. 40-60 episodes, varied object
  positions, varied plate positions, varied scene, every episode driven through
  to a completed PLACE. Spec in agent_handoff_pi05_20260803.md Section 9 item 2.
  Neither model gets data the other does not. No re-recording between arms.

TRAIN
  Pi05  - Stage 3 settings as already decided: new lerobot code, init from BASE
          not 012000, use_relative_actions=true, image_transforms on.
  GR00T - N1.5, SO-101 as new_embodiment, modality.json for the 6-DoF state and
          action. Start from the tutorial's 10k steps; community reports suggest
          20k and denoising 16 / action horizon 16 rather than the default 4.
  Record VRAM, wall-clock and final loss for each. Both should fit locally; if
  either does not, say so - that is a result too.

EVALUATE
  Five-run counts per object x phase (grasp / lift / carry / PLACE), scored with
  scripts/analyze_grasp_from_trace.py. Not by eye. Not from video.
  Include one object absent from training (e.g. a lemon) as the true
  generalization test.
  The obs-rate gate applies unchanged: below 0.8 obs/s the run is BLIND and its
  behavioural result is discarded as infrastructure.
```

Rules that do not relax for this experiment:

```text
- THREE CAMERAS OR IT DOESN'T COUNT.
- The user must be physically present for any robot motion.
- ONE VARIABLE AT A TIME. The variable here is THE MODEL. Everything else -
  data, scene, scoring, cameras, task strings - is held fixed. If the scene
  drifts between the two evaluations, the comparison is void.
- Never commit checkpoints, traces, videos or datasets.
```

---

## 4b. WHAT "VALIDATE THE PIPELINE" ACTUALLY MEANS (clarified 2026-08-05)

The phrase was used loosely. To be exact - **there is no checkpoint of NVIDIA's
involved.**

```text
"their dataset"  = izuluaga/finish_sandwich. Just DATA.
"the pipeline"   = GR00T FINE-TUNING, i.e. these four steps:

   dataset (LeRobot v2)
     -> convert_v3_to_v2.py if needed
     -> fine-tune  nvidia/GR00T-N1.7-3B   (NVIDIA's BASE model)
     -> OUR OWN new checkpoint
     -> evaluate it (gr00t/eval/open_loop_eval.py)

The resulting model is USELESS to us - it makes sandwiches. That is not the
point. The point is proving, on THIS machine:
   does the conversion emit a dataset GR00T can load?
   does training actually start?
   does ~25 GB VRAM hold on our card (32 GB, and the tutorial's figure is from
     a TWO-camera setup)?
   does the eval script run?

WHY FIRST, rather than going straight to our own sim data:
   our sim episodes need TWO conversions (HDF5 -> LeRobot v3 -> v2), neither
   tested by us. If we feed those through an UNPROVEN pipeline and it fails, we
   cannot tell whether the fault is our conversion or the pipeline.
   Known-good data first. Same rule as validating a measuring tool against a
   known-good answer before believing it (Era 1).
```

---

## 5. Stage 3b-0: Pipeline Dry Run On NVIDIA's Own Dataset

**Do this first. It needs no robot time, no Stage 2 data, and no conversion.**

The tutorial ships `so101-table-cleanup` - a real SO-101 dataset already in
whatever format GR00T currently accepts. That makes it a free harness test.

```text
WHAT IT ANSWERS, before we spend anything of our own:
  does Isaac-GR00T install and run on Ubuntu 26.04 / this 5090?
  is ~25 GB VRAM real, or does our card run out?
  what does a working modality.json look like for a 6-DoF SO-101?
  what format does the loader ACTUALLY want (settles Section 3 empirically,
    by example, rather than from documentation)?
  how long does 10k steps take locally?
```

This directly attacks the plan's biggest risk. Section 3 asks whether a v3 -> v2
conversion is needed; a dataset that already works tells us the target format by
inspection instead of by reading release notes.

It is also a **harness validation**, which is this project's hardest-won rule:

```text
ERA 1 cost a month to a broken harness that looked fine. The rule that came out
of it: SUSPECT THE HARNESS BEFORE THE MODEL, and validate any new measurement
tool against a known-good answer before believing it.

Training GR00T on OUR data first would mean a brand-new, unvalidated pipeline
meeting brand-new data. If the result is bad we would not know which half
failed. NVIDIA's dataset IS the known-good answer.
```

Relevance bonus: "table cleanup" is pick-and-**place**. If the tutorial
checkpoint places reliably on its own data, that alone is evidence the
architecture can express the skill our Pi05 has never performed - before we
train anything ourselves.

```text
COST     one evening, GPU only, no robot, no recording
OUTPUT   a working pipeline + a reference modality.json + a measured VRAM
         figure for OUR hardware
GATE     if this fails, the comparison is deferred and Section 3's conversion
         work is not started
```

Note the caveat from Section 7: the tutorial uses **two** cameras and we need
three. The VRAM figure measured here is therefore a floor, not our number.

---

## 6. Sequencing

```text
ANY TIME     Stage 3b-0 - GR00T pipeline dry run on so101-table-cleanup
                          (GPU only, no robot; do it whenever the GPU is idle)
NEXT         Stage 2    - recording session (robot time; the expensive part)
THEN         Stage 3    - Pi05 generalist fine-tune, local
THEN         Stage 3b   - GR00T fine-tune, same Stage 2 data, local
THEN         Stage 4    - scoring matrix, both models, same protocol
```

Stage 3b-0 is deliberately unblocked - it touches no robot and no shared data,
so it cannot confound anything and can fill any evening.

**Do not run the COMPARISON on the current 49-episode dataset.** That data has
one scene, one table position and no completed place phase. Both models would
likely fail the same way, and the result would be predictable rather than
informative - paying setup cost to learn something already suspected.

That restriction is about our own data. It does not apply to Stage 3b-0, which
uses someone else's dataset purely to prove the plumbing.

Hard rule #8 still governs the comparison itself: the Pi05 subtask-switching
probe (handoff Section 9 item 1) is still unanswered, and the two should not be
in flight at once on the robot.

---

## 7. What Is Verified vs Assumed

```text
VERIFIED ON THIS MACHINE (2026-08-04)
  5090 has 32 GB and sm_120 works on torch 2.7.0+cu128
  Pi05 012000 loads and runs locally at 153 ms/chunk, 9.5 GB
  Our lerobot code writes CODEBASE_VERSION v3.0
  Only a forward v2.1->v3.0 converter ships in the repo

FROM THE NVIDIA POST - NOT VERIFIED HERE
  GR00T N1.5 needs ~25 GB VRAM to fine-tune
  LeRobot v2.0+ datasets are supported
  10k steps is a reasonable starting point
  SO-101 works as a new_embodiment

VERIFIED 2026-08-05 (serving, not fine-tuning)
  GR00T N1.7 SERVES locally in ~8 GB VRAM: 1,091,722,240 DiT + 201,433,088
    SelfAttn params, ZMQ REP on :5555
  The gated backbone (nvidia/Cosmos-Reason2-2B, 4.6 GB) is cached and OFFLINE
  LeIsaac's n1.5/n1.6 clients do NOT speak N1.7 - seven wire-format differences,
    bridged by scripts/gr00t_n17_client_adapter.py
  A checkpoint's UNITS, ABSOLUTE-vs-RELATIVE actions and CAMERA COUNT must all
    be read out of experiment_cfg/ BEFORE trusting any number. All three were
    wrong on the first run and it produced a convincing false "grasp".

UNKNOWN
  Whether GR00T's loader accepts v3.0 today
  Whether 25 GB is the real figure for OUR 3-camera, 6-DoF configuration
    (the tutorial used a dual-camera setup; we use three)
  Whether GR00T's action representation suits a 6-DoF tabletop arm as well as
    it suits the humanoids it was built for
  Whether Pi05 itself can be trained on 32 GB
```

The three-camera point deserves emphasis. The tutorial's VRAM figure comes from
a **two**-camera setup. We require three, which raises the observation payload
by half. The 25 GB number may not survive contact with our configuration, and
32 GB is not a large margin over 25 GB.

---

## 8. Open Questions

```text
Is a v3 -> v2 dataset conversion needed, and what does it cost?
Does 25 GB hold with three cameras at 640x480?
Can the 5090 train Pi05 as well as GR00T? (retires RunPod entirely)
Does GR00T's pre-training help or hurt on a tabletop arm, given it was built
  for humanoids?
If both models fail to place, is the next variable the data or the task
  formulation (compound instruction vs subtask strings)?
```

That last one connects to the pi05 architecture finding in handoff Section 6:
Physical Intelligence released only the low-level half of Pi05, so our compound
instruction goes straight to a motor expert never meant to plan multi-step.
**If GR00T ships an intact high-level component, it may not share that
limitation** - which would make the place comparison a test of hierarchy, not
just of architecture. Worth checking against GR00T's docs before running, since
it changes what the result means.

---

## 9. References

```text
NVIDIA post   huggingface.co/blog/nvidia/gr00t-n1-5-so101-tuning
GR00T repo    github.com/NVIDIA/Isaac-GR00T
Roadmap       pi05_generalization_roadmap_20260802.md
Handoff       agent_handoff_pi05_20260803.md   (Sections 3, 6, 9)
Scorer        scripts/analyze_grasp_from_trace.py
```
