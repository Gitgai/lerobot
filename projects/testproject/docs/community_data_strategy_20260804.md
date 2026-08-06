# Community Data And Published Checkpoints: Strategy

Last updated: 2026-08-04
Status: PLAN - nothing downloaded, nothing trained.
Modifies: `pi05_generalization_roadmap_20260802.md` **Stage 2** (does not replace it).
Related: `groot_vs_pi05_comparison_plan_20260804.md`

---

## 1. The Question This Answers

"Do working fine-tuned SO-101 models already exist, and are there public datasets
so we can fine-tune instead of spending an evening collecting our own?"

Both halves have answers. The dataset half turns out to matter far more, and for
a reason better than saving labour.

---

## 2. The Real Argument (read this before the inventory)

From the handoff, Section 6, quoting Physical Intelligence's own ablations:

```text
removing environment diversity hurt WORST (OOD success -> 31%), worse than
removing cross-embodiment (49%) or web data (80%).
Translation for a one-table setup: VARY THE SCENE, not just the object.
```

And from Section 3, our single verified failure mode:

```text
"grasp geometry and goals are welded to the exact scene it trained in."
```

Now hold those next to the Stage 2 plan as written: **40-60 episodes, one room,
one table, one lighting setup.**

```text
You cannot un-weld a model from a scene using more data from that same scene.
```

More episodes on our table buys object variety and position variety within one
environment. It cannot buy environment variety. That is a structural limit of
recording in one room, not a matter of effort or episode count.

The public corpus is ~1,222 datasets from **377 different users** - which means
377 different rooms, tables, lighting setups and camera placements. That is the
one variable our own recording physically cannot produce.

**This is the argument for community data. Not "it saves an evening" - it
supplies the thing PI's ablation ranks as most important and that we cannot
generate ourselves.**

---

## 3. Inventory

### Datasets (unverified - from HF, 2026-08-04)

```text
allenai/MolmoAct2-SO100_101-Dataset
  a curated INDEX of 1,222 public LeRobot SO-100/101 datasets from 377 users
  38,059 episodes | 19.8M frames | ~184 hours
  per-episode annotated language instructions (tasks_annotated.parquet)
  -> this is a MAP to the whole community corpus, not just one dataset

lerobot/svla_so101_pickplace
  OFFICIAL LeRobot. 50 episodes, 11,939 frames, codebase_version v2.1
  2 cameras: observation.images.{up,side}, 480x640 @30fps
  robot_type "so100_follower" despite the so101 name
  6-DoF state/action matching ours

HF search "so101" -> ~9,000 dataset hits
```

The MolmoAct2 index is the most valuable item here. Its language annotations mean
episodes can be filtered by instruction - e.g. everything that is a *place*.

### Published checkpoints (unverified)

```text
pi0.5 on SO-101   30+ repos, e.g.
  felixmayor/pi05_so101_orange_cube (+batch2, batch4)   <- ORANGE
  SkieyFly/pi05-so101_block_to_container_all-*          <- PLACE
  Sakits/so101_clean_the_table_new_pi05_*               <- PLACE
GR00T N1.5 on SO-101   7+ repos, e.g.
  SGPatil/GR00T-N1.5-SO101-finetune-table-cleanup
  shenjianliang/so101_pick_GR00T-N1.5-3B
```

---

## 4. Do NOT Expect Published Checkpoints To Work On Our Arm

Two independent reasons, both from our own evidence.

```text
1. SCENE WELDING. Our verified finding: 145 empty squeezes in 10 minutes on an
   onion that had merely been RELOCATED on our own table - the same onion that
   was carried 40 s that morning. If our own checkpoint cannot survive moving an
   object a few inches in our own room, a checkpoint trained in a stranger's room
   (different camera mounts, table height, lighting, calibration) is very
   unlikely to grasp on ours. Same MODEL of arm; different physical instance.

2. THE ERA 1 TRAP. These are dated Sept-Oct 2025. Our hardest lesson is that a
   checkpoint must be served on TRAINING-ERA code:
       newer lerobot serving 012000 -> gripper corr 0.197 FAIL
       training-era code           -> gripper corr 0.83
   A downloaded checkpoint needs its lerobot version identified before it can be
   trusted. SGPatil's repo has NO MODEL CARD AT ALL, so that information may not
   exist. And unlike 012000, we would have no known-good numbers to validate
   against - no trust exam is possible.
```

**Where they ARE useful:** as harness validators (prove a serving stack runs
before spending robot time), as reference configs (`modality.json`,
hyperparameters, camera counts), and possibly as a fine-tune init that already
carries SO-101 body adaptation. That last one is a hypothesis - it could equally
inherit someone else's scene bias.

### 4a. But TEST them - in simulation, where it costs only electricity

"Do not expect them to work" is a prediction, not a reason to skip the
experiment. Once the simulator is running, evaluating a downloaded checkpoint
costs no robot time, no pod billing, no teleop labour and carries no risk of
overloading a motor. At that price the prediction should be tested, not assumed.

**Read the result asymmetrically. This is the important part:**

```text
WORKS IN SIM   -> STRONG signal. The checkpoint crossed a real->sim domain gap
                  (rendered images, different scene, different camera poses)
                  on top of everything else. Anything that generalises that far
                  is worth serious attention.

FAILS IN SIM   -> WEAK signal, nearly uninformative. The model was fine-tuned on
                  REAL camera frames; simulator renders are out of distribution
                  in the reverse direction. Failure could be the real->sim gap
                  rather than the checkpoint. DO NOT conclude "this checkpoint is
                  bad" from a sim failure.
```

So it is a cheap **positive-only** test: it can promote a candidate, it cannot
fairly eliminate one. Worth running precisely because the cost is near zero.

Three things it buys regardless of outcome:

```text
1. HARNESS VALIDATION with zero risk. Running any checkpoint end-to-end in sim
   exercises the serving stack, observation format and client loop before a
   single real motor turns. Era 1's rule, applied at zero cost.
2. A PLACE OBSERVATION. LeIsaac's so101_pick_orange ends in "put them into the
   plate". If ANY checkpoint completes a place in sim, that is the first place
   this project has ever recorded - simulated, but the first.
3. A BASELINE FOR OUR OWN. 012000 can be run in the same environment under the
   same conditions. Same asymmetry applies to reading its result.
```

**The harness already exists - we do not have to write it.** LeIsaac 0.4.0's
optional extras (read from the installed package, 2026-08-04):

```text
extra == "openpi"         dm-tree, msgpack, numpy<2, pillow, websockets
extra == "gr00t"          pyzmq, pydantic, msgpack
extra == "lerobot"        lerobot==0.4.2
extra == "lerobot-async"  grpcio, protobuf
```

`openpi` is Physical Intelligence's pi0/pi05 stack. So LeIsaac ships integration
points for evaluating **both** policy families in simulation. This section needs
a working simulator, not new code.

```text
UNBLOCKED 2026-08-05 - THE SIMULATOR NOW WORKS LOCALLY.
The deadlock was resolved by downgrading the driver to 580.173.02. Isaac Sim
5.1 + Isaac Lab 2.3.0 + LeIsaac 0.4.0 all run; the SO-101 pick-and-place scene
renders and is controllable.

AND THE HARNESS FOR THIS SECTION IS BUILT AND EXERCISED:
  scripts/policy_server_leisaac_shim.py     serve a LeRobot checkpoint to
                                            LeIsaac over gRPC (checkpoint stays
                                            on its own training-era code, so the
                                            Era 1 pairing rule holds)
  scripts/sim_policy_eval_instrumented.py   run it and SCORE FROM GROUND TRUTH
  scripts/sim_action_path_check.py          validate the action path first

Already used on our OWN checkpoint (Pi05 012000): three clean runs, reaches
5-9 cm, 0/3 grasps, 0/3 places. See sim_place_data_generation_20260805.md.

=> Testing DOWNLOADED community checkpoints is now a matter of pointing the
   same tooling at a different --policy_checkpoint_path. Two caveats carry over:
   (a) the Era 1 rule - each downloaded checkpoint needs its training-era
       lerobot identified before its result means anything;
   (b) the sim exposes only front + wrist, so a 3-camera policy runs with one
       view masked (see sim_capability_and_camera_plan_20260805.md Section 2).
```

---

## 5. Camera Count - ANSWERED 2026-08-04: YES, SUPPORTED

The gating question was whether pi05 can train on datasets carrying fewer (or
differently named) cameras than the policy config declares. **It can.** Answered
by reading the code on 2026-08-04.

```text
OURS (from the 012000 config.json):
  input_features: observation.images.{front,top,wrist}   3 cameras, 3x480x640
  plus HARD RULE #4: "THREE CAMERAS OR IT DOESN'T COUNT" (real-robot runs)

THEIRS:
  lerobot/svla_so101_pickplace has TWO cameras (up, side)
  community datasets vary: 1, 2, sometimes 3, with different names entirely
```

### Finding 1: missing cameras are padded AND MASKED, computed per batch

`src/lerobot/policies/pi05/modeling_pi05.py:1150`

```python
present_img_keys = [key for key in self.config.image_features if key in batch]
missing_img_keys = [key for key in self.config.image_features if key not in batch]
if len(present_img_keys) == 0:
    raise ...
```

Derived **per batch**, not from config. Any subset of the declared cameras is
accepted; the only hard requirement is that at least one is present. Missing
ones are then filled at line 1196:

```python
img  = torch.ones_like(img) * -1     # SigLIP's padding convention
mask = torch.zeros_like(mask)        # masked OUT, not treated as real pixels
```

That is proper masked handling - attention ignores the absent view rather than
learning from blank pixels.

### Finding 2: renaming is available at TRAINING time, not just serving

```text
src/lerobot/configs/train.py:120     rename_map: dict[str, str]   <- top-level
                                     training config field
src/lerobot/scripts/lerobot_train.py:274   rename_map=cfg.rename_map
                                     wired into the training pipeline
```

Previously we had only seen `rename_map` in the client/server path. It is a
first-class training option. Matching is exact (`key in batch`), so
`observation.images.up` must be renamed to one of ours - and that is exactly
what this provides.

### Finding 3: we were already using it

`rename_map` appears in 012000's own `train_config.json` top-level keys. It was
part of the training configuration when this checkpoint was trained.

### What this unlocks

```text
A 2-camera community dataset -> rename_map maps its views onto two of
{front, top, wrist}; the third is padded and MASKED.
Our own 3-camera data supplies all three.
Both can co-train in the same run.

=> The 1,222-dataset corpus is NOT architecturally excluded. The strategy in
   this document survives its gating question.
```

### The honest limit on this answer

```text
This is CODE READING. It establishes the MECHANISM and the INTENT. It does NOT
establish that such a mix trains WELL. Whether a model trained on samples where
the wrist view is sometimes masked learns as well as one with consistent views
is empirical, and should be expected to cost something.

PROOF requires a real training run, which requires the dataset transfer
(see pi05_work_prioritization.md P0 blocker).
```

### A risk this finding surfaces - read before mass-downloading

```text
Our VERIFIED strength is language understanding and transport.
Our VERIFIED weakness is GRASP GEOMETRY.
The wrist camera is the view that matters most for grasp.

Most community datasets do NOT have a wrist view. Training on a corpus that is
mostly wrist-less could dilute the signal for the exact capability we most need
to improve - while adding the environment diversity we want.

=> Filtering the corpus for 3-camera datasets, or weighting them higher, may
   matter MORE than raw episode count. Do not equate "more data" with "better"
   here. Section 8 item 3 (mining the MolmoAct2 index for 3-camera place
   datasets) is therefore the highest-value data task, not an afterthought.
```

---

## 6. Format: Good News

```text
VERIFIED 2026-08-04
  our code       CODEBASE_VERSION = "v3.0"  (fork main AND training-era e40b58a8)
  community      largely v2.1
  converter      src/lerobot/scripts/convert_dataset_v21_to_v30.py
                 runs v2.1 -> v3.0, i.e. THE DIRECTION WE NEED
```

This is the opposite of the GR00T problem, where a backward v3 -> v2 conversion
would be required (see `groot_vs_pi05_comparison_plan_20260804.md` Section 3).
For community data, the tooling already ships.

---

## 7. Proposed Strategy: Restructure Stage 2, Do Not Skip It

```text
WRONG:  "use community data INSTEAD of recording"
        -> a model trained on 377 strangers' rooms and none of ours. Diverse,
           but ignorant of our table, our cameras, our lighting.

WRONG:  "record 40-60 episodes on our table and call it diverse"
        -> the current Stage 2. Cannot produce environment diversity. This is
           what PI's ablation says costs the most.

RIGHT:  CO-TRAIN. Community corpus supplies environment diversity and PLACE
        demonstrations; our own recording supplies our specific scene, cameras
        and task. This is PI's own recipe - broad pre-training plus a small
        task-specific fine-tune - applied at our scale.
```

Consequence for Stage 2:

```text
RECORD FEWER, MORE FOCUSED EPISODES.
  Stop trying to manufacture diversity by hand. Community data does that better.
  Spend our robot time on what only we can record: OUR scene, OUR three cameras,
  and the PLACE phase driven to completion.
  Position and object variety still matter - environment variety no longer has
  to come from us.
```

We currently have **zero** completed place demonstrations. Several community
datasets (`block_to_container`, `clean_the_table`, `svla_so101_pickplace`) are
place data. That gap is fillable without robot time.

---

## 8. Next Actions (all no-hardware)

```text
1. CAMERA-COUNT CHECK (Section 5).  DONE 2026-08-04 - ANSWERED YES.
   Missing cameras are padded and masked per batch; rename_map is a top-level
   TRAINING config field. The strategy is not architecturally blocked.

2. MINE THE MolmoAct2 INDEX - now the highest-value data task (was item 3).
   Filter language annotations for place-style instructions, and count how many
   of those datasets carry a WRIST view. Section 5's risk note is why this is
   promoted: a wrist-less corpus may dilute the exact capability (grasp
   geometry) we most need to fix. Camera composition matters more than volume.

3. Pull lerobot/svla_so101_pickplace. Convert v2.1 -> v3.0 with the shipped
   script. Confirm it loads in our stack. Small, official, real place data.
   Doubles as a pipeline test with a known-good dataset.
   NOTE: it is 2-camera (up, side), no wrist - so it is a PLUMBING test, not a
   model of what good co-training data looks like.

4. Only then: decide co-training mix and revise Stage 2's episode count.

5. PROOF still outstanding: item 1 is code reading, not a training run. A real
   mixed-camera training step is the empirical confirmation, and it needs the
   dataset transfer that currently blocks P0.

IN PARALLEL, once the simulator is up (independent of 1-4):

5. SIM-TEST PUBLISHED CHECKPOINTS (Section 4a). Cost is electricity. Start with
   the place-relevant ones - block_to_container, clean_the_table,
   pi05_so101_orange_cube - plus our own 012000 as the baseline.
   Read results asymmetrically: success promotes, failure proves little.
   Note the Era 1 requirement still applies: each checkpoint needs its
   training-era lerobot identified before its result means anything.
```

---

## 9. Open Questions

```text
Can pi05 train on datasets with fewer cameras than the policy declares?
  -> ANSWERED YES (Section 5). Padded + masked, per batch.
Does rename_map handle differing camera NAMES (up/side vs front/top/wrist)?
  -> ANSWERED YES. Top-level TRAINING config field, already used by 012000.
Does a mostly WRIST-LESS corpus dilute grasp geometry - our weakest skill?
  -> NEW, and the most important open question this direction has.
What co-training ratio - community to own - is sensible at our scale?
Does SO-100 vs SO-101 matter? (svla_so101_pickplace declares so100_follower;
  same 6-DoF structure, but joint ranges and calibration may differ)
Does community data help, or does averaging over 377 rooms produce a model
  mediocre everywhere and good nowhere?
Is a published checkpoint a better fine-tune init than BASE? (Stage 3 currently
  specifies init from BASE)
```

That last-but-one question is the honest risk in this whole plan. PI's ablation
says diversity helps at THEIR scale, with a curated mixture. A community corpus
is not curated, and quality varies by contributor. **Treat co-training as an
experiment with a measurable outcome - Stage 4's scoring matrix - not as an
obviously correct move.**

---

## 10. Sources

```text
huggingface.co/datasets/allenai/MolmoAct2-SO100_101-Dataset
huggingface.co/datasets/lerobot/svla_so101_pickplace
huggingface.co/blog/nvidia/gr00t-n1-5-so101-tuning
handoff Sections 3 and 6 (verified capability state; PI ablation)
pi05_generalization_roadmap_20260802.md Stage 2
```
