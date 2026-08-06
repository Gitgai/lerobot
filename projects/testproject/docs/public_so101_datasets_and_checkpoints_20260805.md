# Public SO-101 Datasets And Checkpoints, And What We Can Test In Sim

Last updated: 2026-08-05
Answers: what other datasets exist? do fine-tuned SO-101 models exist that we
could run in OUR simulator? and is "match the real rig to sim" the right plan?
Related: `sim_first_strategy_20260805.md`, `s1_s2_results_20260805.md`,
`groot_vs_pi05_comparison_plan_20260804.md`.

---

## 1. Datasets (all LeRobot format, all SO-100/SO-101)

```text
izuluaga/finish_sandwich          80 eps  70,277 frames  v3.0  front+wrist
   NVIDIA's own example for GR00T SO-101. INSPECTED THE FRAMES 2026-08-05:
   orange 3D-printed SO-101 over a white table, grey compartment tray of TOY
   FOOD (cheese, lettuce, patty), red tray holding bread. The arm picks pieces
   out of the compartments and STACKS THEM ONTO THE BREAD.
   => it is a genuine PICK-AND-PLACE dataset with an unambiguous place target.
   *** ITS `front` CAMERA IS MOUNTED TOP-DOWN *** - same key name as ours,
   completely different geometry. See the warning in Section 4.

lerobot/svla_so101_pickplace      50 eps  11,939 frames  v2.1  up+side
   OFFICIAL LeRobot. Most-downloaded pick-place set (2.63k). robot_type is
   so100_follower despite the name.
orsoromeo/so101_pick_and_place    22.2k rows   (697 downloads)
gpudad/so101_pick_cube_chunked    1.46M rows   (556) - by far the largest
xinjiehu76/so101-pick-place-dataset  120 rows  (521)
jinseonylee/SO101_PickAndPlace_Fruit 551 rows  - FRUIT, closest to our task

allenai/MolmoAct2-SO100_101-Dataset
   an INDEX of 1,222 public SO-100/101 datasets from 377 users:
   38,059 episodes, 19.8M frames, ~184 hours, WITH per-episode language
   annotations. The map to everything else.
```

---

## 2. Fine-tuned checkpoints - YES, THEY EXIST, AND WE CAN RUN THEM

```text
GR00T
  robocurve/gr00t-n1.7-so101-molmoact2      3B, 145 downloads
     *** N1.7 - the SAME base version the current Isaac-GR00T repo ships ***
  SGPatil/GR00T-N1.5-SO101-finetune-table-cleanup   (no model card)
  shenjianliang/so101_pick_GR00T-N1.5-3B

PI0.5
  hjkso1406/pi05-peft-so101-4tasks-aug      4B, PEFT, four tasks
  felixmayor/pi05_so101_orange_cube (+batches)   <- ORANGE
  SkieyFly/pi05-so101_block_to_container_all-*   <- PLACE
  Sakits/so101_clean_the_table_new_pi05_*        <- PLACE

SMALLER ARCHITECTURES (cheap to test, often ignored)
  yen-0/smolvla-so101-digits-0707           0.5B, 543 downloads (most popular)
  Sa74ll/smolvla_so101_pickandplace         0.5B
  orange5546/act_cylinder_pick_so101        51.7M
  => SmolVLA is 8x SMALLER than our Pi05 (0.5B vs 4.14B) and ACT is 80x
     smaller. Both would load and run far faster than 012000's 60 s / 9.5 GB.
```

### The harness for this already exists

```text
We BUILT and VALIDATED the machinery on 2026-08-05:
  scripts/policy_server_leisaac_shim.py     serve any LeRobot checkpoint to
                                            LeIsaac over gRPC
  scripts/sim_policy_eval_instrumented.py   run it, score from GROUND TRUTH
  scripts/sim_action_path_check.py          prove the action path first

Testing a downloaded checkpoint = pointing --policy_checkpoint_path at it.
LeIsaac also has NATIVE GR00T support (--policy_type=gr00tn1.5 / gr00tn1.6);
whether it accepts N1.7 is UNVERIFIED.
```

### THE ACTUAL GOAL (user, 2026-08-05): use someone else's checkpoint AS IS

```text
"if the models fine tuned by others run well in simulators, there's a chance
they will work on the real arm as well. so here i am just trying to use their
work as is instead of me spending hours on finetuning. because all so101 arms
are similar. and because pi0.5 and groot are large models, we expect them to
generalize and not be too brittle."
```

**Worth testing.** A few hours of evaluation against many hours of fine-tuning is
good expected value even at low odds. But two things temper it, and one is
decisive.

**1. Our own evidence is the strongest counterargument to "large models
generalize".**

```text
012000 IS a large model - 4.14B, pi0.5, exactly the class described. And it
produces 145 EMPTY SQUEEZES when an onion moves a few INCHES on its own table.
Size did not buy robustness. The arm is not the variable - SO-101s are identical
- the SCENE is: camera placement, table height, lighting, object appearance.
That is precisely the axis this project has measured the model failing on.
```

**2. ABSOLUTE vs RELATIVE ACTIONS - the decisive technical issue.**

```text
012000 config:  use_relative_actions: False   <- ABSOLUTE joint targets

Absolute joint targets are tied to A SPECIFIC ARM'S CALIBRATION. Our calibration
files encode OUR arms' zero offsets. Someone else's pi05 checkpoint emits joint
angles calibrated to THEIR arm. Same robot model, different zero points - so a
downloaded pi05 checkpoint will likely command positions SYSTEMATICALLY OFFSET
from ours. Not subtly; the sort of error that reaches the wrong place entirely.

GR00T DEFAULTS TO RELATIVE ACTIONS (gripper excluded) - see its README, and
groot_vs_pi05_comparison_plan_20260804.md Section 2b finding 3. Relative actions
describe movement FROM WHERE YOU ARE, so they carry no calibration assumption.

=> GR00T IS STRUCTURALLY FAR BETTER SUITED TO THE "USE SOMEONE ELSE'S CHECKPOINT"
   PLAN THAN PI05. Test robocurve/gr00t-n1.7-so101-molmoact2 FIRST.
```

**3. TEST THEM ALL ANYWAY - do not stop early (user, 2026-08-05).**

```text
An earlier version of this doc advised: if GR00T stalls, skip the pi05
candidates because they are unlikely to do better. THAT WAS A PREDICTION
SUBSTITUTING FOR A MEASUREMENT, which is the thing this project's culture exists
to prevent. Testing is cheap; the prior is not worth much.

Reasons the prior could be wrong: a pi05 candidate may have been trained WITH
relative actions; calibrations may happen to be close; a different architecture
may behave unexpectedly.

AND A UNIFORM NEGATIVE IS ITSELF A FINDING: if NO public checkpoint transfers,
that redirects effort to fine-tuning with evidence instead of assumption.

REAL COST IS BANDWIDTH, NOT COMPUTE: ~3B + ~4B + 0.5B of weights is roughly
15 GB, and this machine's link runs ~2 MB/s (weak Wi-Fi, -77 dBm; the ethernet
port is physically broken). That is a couple of hours of DOWNLOADING. GPU time
per evaluation is ~20 minutes. Batch the downloads, read the results together.
```

### SCREENING RESULTS 2026-08-05 - 3 candidates, 1 survived, ~1 GB spent

**Screen candidates on FORMAT and OBSERVATION SPACE before downloading weights.**
This eliminated two of three for roughly one API call and 1 GB.

```text
felixmayor/pi05_so101_orange_cube          RUNNABLE AS-IS - DO NOT CONVERT
  files: assets/so101/norm_stats.json, metadata.pt, model.safetensors, optimizer.pt
  That is OPENPI layout, not LeRobot - so it will NOT load in our LeRobot policy
  server, and no lerobot->openpi converter exists.

  *** CORRECTION 2026-08-05: an earlier version of this doc concluded "convert
  it (a day's work) or skip it". BOTH WRONG. LEISAAC SPEAKS OPENPI NATIVELY. ***

    source/leisaac/leisaac/policy/service_policy_clients.py:338
      class OpenPIServicePolicyClient(WebsocketServicePolicy)
        camera_keys = ["front", "wrist"]   <- matches our sim exactly
        task_type   = "so101leader"
        port        = 8000
    scripts/evaluation/policy_inference.py supports --policy_type=openpi
    leisaac/policy/openpi/  ships msgpack_numpy.py + image_tools.py
    LeIsaac even PINS A TARGET OPENPI COMMIT:
      github.com/Physical-Intelligence/openpi @ 5bff19b0c0c447c7a7eaaaccf03f36d50998ec9d
      reference fork: github.com/EverNorif/openpi tree lerobot-v0.3.3

  => RUN IT IN ITS OWN FRAMEWORK. Clone openpi at that commit, install it, start
     its websocket policy server on the checkpoint, point LeIsaac at it with
     --policy_type=openpi --policy_port=8000.
     Cost: an install over a 2 MB/s link (hours of DOWNLOADING), NOT a day of
     writing conversion code.
     Bonus: the pinned commit partly solves the Era 1 pairing problem - LeIsaac
     has tested against a specific openpi version rather than leaving it open.
     Bonus 2: assets/so101/norm_stats.json is openpi's own normalisation format,
     read natively by its server - exactly the piece a hand-written converter
     would be most likely to get subtly (and silently) wrong.

yen-0/smolvla-so101-digits-0707            OUT - IMPOSSIBLE OBSERVATIONS
  input_features: observation.state, observation.images.wrist,
                  observation.images.top, observation.target_drawing
  It is a DIGIT-DRAWING task needing `observation.target_drawing` - an image of
  the digit to draw. Our pick-orange env cannot supply that at all. Also wants
  wrist+top, not front.
  CHECKED: the repo has NO MODEL CARD - no task description, no environment, no
  dataset, no code. Just weights.

*** SIM-TRAINED CHECKPOINTS EXIST - AND BLACKWELL BLOCKS THEM (2026-08-05) ***

```text
Checkpoints trained INSIDE LeIsaac, on our exact task, all ungated:
  LightwheelAI/leisaac-pick-orange-v0      GR00T N1.5   (the LeIsaac authors)
  12e21/gr00t_n1d6_leisaac_pick_orange     GR00T N1.6
  tshiamor/groot-n1.6-leisaac-pick-block   GR00T N1.6
  omkarmayekar555/act_leisaac_orange       LeRobot ACT, 51.6M params
Also: LightwheelAI/leisaac_env ships the kitchen_with_orange scene assets.

LightwheelAI/leisaac-pick-orange-v0 SCREENS PERFECTLY: motor units (arm +/-100,
gripper 0..100), "absolute": true (no relative trap), front+wrist at 640x480 -
exactly what our scene exposes - and N1.5 is driven NATIVELY by LeIsaac, so no
adapter of ours would sit in the path. Downloaded, 7.1 GB.

*** BUT NONE OF THEM CAN BE SERVED ON THIS MACHINE TODAY. ***
  our Isaac-GR00T ships ONLY gr00t_n1d7 - zero references to n1_5/n1_6, and it
    is a SHALLOW clone (1 commit) so there is no older revision to check out
  act_leisaac_orange loads on our LeRobot but SILENTLY DROPS its normalization:
      "Unexpected key(s): normalize_inputs.buffer_observation_state.mean ..."
    Old-style embedded norm buffers; our lerobot is 0.6.1 (project repo 0.5.2),
    both NEWER than the checkpoint. Serving it as-loaded = garbage, and it would
    have looked like a harness failure.

THE STRUCTURAL PROBLEM, worth remembering:
  Era 1 says serve a checkpoint on TRAINING-ERA code.
  Blackwell/sm_120 needs torch >= 2.7 + cu128.
  Old checkpoint eras pin OLD torch, which has NO sm_120 support.
  => on a 5090 these two rules CONFLICT. Old checkpoints are not simply a
     "download and run"; each needs an era-matched env that also builds for
     Blackwell. Budget for that BEFORE promising a comparison.

This is why the harness positive control was done with LeIsaac's own state
machine instead - no checkpoint, no venv, and it answered the same question.
```

robocurve/gr00t-n1.7-so101-molmoact2   *** EVALUATED IN SIM - SEE BELOW ***
  *** STATUS 2026-08-05 (final) - gate SOLVED, adapter WORKS, and the model has
  now been SCORED in LeIsaac from ground truth. ***

  RESULT: reaches the grasp frame to 0.039 m and closes the gripper (predicate
  TRUE for 80 consecutive steps) - but the orange moves 0.0001 m. It approaches
  far better than Pi05, which never satisfies even proximity+closure, and it
  ACQUIRES NOTHING. No place, ever.
  -> gr00t_n17_sim_evaluation_20260805.md   (full write-up + the 3 adapter bugs)

  WHAT IT WAS ACTUALLY TRAINED ON (checked the model card 2026-08-05, because
  an earlier draft of the eval doc got this WRONG and said "table cleanup"):
    SO-101 subset of allenai/MolmoAct2-SO100_101-Dataset
    2,242 episodes / 1.8M frames, filtered from 39 public community repos
    task family: tabletop pick/place, stacking, sorting
    THE CARD PUBLISHES NO INSTRUCTION STRINGS. So no instruction we send can be
    called "the training string", and phrasing experiments must be reported as
    sensitivity, not as matching.

  THREE SCREENING CRITERIA THIS CHECKPOINT ADDED (apply to the NEXT one BEFORE
  spending an hour on an adapter):
    1. UNITS. Read experiment_cfg/dataset_statistics.json FIRST. Arm ~ +/-100
       and gripper ~ 0..100 means LeRobot MOTOR units, NOT the sim's radians.
       LeIsaac's LeRobot client converts; a hand-written client must too.
    2. ABSOLUTE vs RELATIVE. conf.yaml `use_relative_action` + the per-modality
       `reps:` list. Here [RELATIVE, ABSOLUTE] - arm is a delta, gripper is not.
    3. CAMERA COUNT. conf.yaml video.modality_keys is the authority. Sending a
       view it never trained on is actively harmful (S2 proved that on Pi05).

  SOLVED:
    gated backbone nvidia/Cosmos-Reason2-2B: access granted (gated: auto - a
      licence click, free, instant). User authenticated as `kgaikwad`.
      Backbone cached at ~/.cache/huggingface/hub/models--nvidia--Cosmos-Reason2-2B
      (4.6 GB) - OFFLINE FROM NOW ON, and it unblocks the ENTIRE GR00T track
      including S3 and S5 fine-tuning.
    GR00T server runs: 1,091,722,240 DiT params + 201,433,088 SelfAttn params
      loaded, ZMQ REP bound on :5555.
      ./.venv/bin/python -m gr00t.eval.run_gr00t_server \
        --model_path=~/lerobot_assets/checkpoints/gr00t_n17_so101 \
        --embodiment_tag=new_embodiment --port=5555
    sim venv needed pyzmq (LeIsaac's [gr00t] extra); `uv pip install pyzmq
      msgpack` - verified it does NOT disturb torch 2.7.0+cu128/sm_120.
    checkpoint schema is CORRECT: new_embodiment -> action ['single_arm',
      'gripper'], state ['single_arm','gripper'] - exactly what LeIsaac wants.

  *** SOLVED 2026-08-05: N1.7 NOW WORKS via a written adapter. ***
    scripts/gr00t_n17_client_adapter.py  ->  Gr00tN17Client
    Returns [16, 6] float32 = 16 timesteps x 6 DoF, IN SIM RADIANS.

    WARNING - an earlier note here quoted a smoke test of "(1, 96), first row
    [0.0971, 2.724, -0.7633, ...]". Those numbers came from the BUGGED adapter
    (raw motor-space deltas passed through as absolute radians) and mean
    nothing. "The server replied with varied numbers" is NOT a working adapter;
    it only proves the wire format parses. The real gates are units, relative-
    vs-absolute, and camera count - all three were wrong while that smoke test
    was passing.

    Current smoke test, from a plausible rest pose, is checkable BY SCALE:
      rest [0.1,-0.5,0.3,0.2,-0.1,0.4] rad -> motor [5.2,-28.7,23.4,12.1,-3.6,29.9]
      which sits mid-distribution for this checkpoint (arm +/-100, gripper 0..100)
      returned actions stay within ~0.5 rad of the current state
      round-trip motor_to_sim(sim_to_motor(x)) == x to 1.5e-7

  THE N1.6 -> N1.7 WIRE FORMAT MAP (seven differences, one probe each):

```text
    LeIsaac n1.6 client sends        GR00T N1.7 server wants
    -------------------------------  ------------------------------------------
 1  data = obs                       data = {"observation": obs}
 2  flat keys "video.front"          nested {"video": {"front": ...}}
 3  groups video./state./annotation. groups "video" / "state" / "LANGUAGE"
 4  video ndim 4  [B,H,W,C]          video ndim 5  [B,T,H,W,C]
 5  state dtype float64              state dtype float32
 6  (n/a)                            "language": {"annotation.human.task_description":
                                                  [[str]]}  <- FULL key inside
 7  response: dict                   response: TUPLE (action, info)
 +  arrays may arrive as RAW msgpack_numpy envelopes with BYTE keys
    {b'nd':True, b'type':'<f4', b'shape':[...], b'data':b'...'} - decode manually

    SYMPTOM -> CAUSE (hit in this exact order):
      KeyError: 'action.single_arm'                       -> wrong annotation key (n1.5)
      ValueError: zero-dimensional arrays cannot be concatenated -> n1.6 shapes
      "got an unexpected keyword argument 'video.front'"  -> #1
      "Observation must contain a 'video' key"            -> #2/#3
      "State key 'single_arm' must be ... np.float32"     -> #5
      "Language key 'annotation.human.task_description'   -> #6
        must be in observation"
      TypeError: float() argument must be ... not 'dict'  -> undecoded envelope
```

```text
HONEST COST: this was ~an hour of protocol archaeology. Against the stated goal
- "use someone else's work AS IS instead of spending hours" - this checkpoint
was NOT as-is. The adapter is reusable and the checkpoint is now genuinely
testable, which is worth having, but it was not free. Weigh that before
attempting the same for other non-matching checkpoints.
```

  ORIGINAL FAILURE ANALYSIS (kept - LeIsaac supports gr00tn1.5 / gr00tn1.6 only):
    gr00tn1.5 client -> KeyError: 'action.single_arm'
      cause: it sends annotation.human.ACTION.task_description; the checkpoint
      declares annotation.human.task_description. (line 65 vs the checkpoint's
      experiment_cfg). FIX: use --policy_type=gr00tn1.6, which sends the right
      key at service_policy_clients.py:136.
    gr00tn1.6 client -> ValueError: zero-dimensional arrays cannot be concatenated
      the keys now EXIST but the returned values are 0-d where the client does
      np.concatenate([action_chunk["action.single_arm"],
                      action_chunk["action.gripper"]])
      i.e. a RESPONSE-SHAPE gap between an n1.6 client and an N1.7 server.

  HONEST COST NOTE: the goal was "use someone else's work AS IS instead of
  spending hours". Bridging n1.6 -> N1.7 means writing a client adapter, which
  is exactly the hours that goal was meant to avoid. The FINE-TUNE path (S3/S5)
  uses GR00T's OWN tooling end to end, with no version bridging, and produces a
  checkpoint whose format matches its server by construction - now unblocked by
  the same gated access.

robocurve/gr00t-n1.7-so101-molmoact2       (original screening notes)
  *** 2026-08-05: DOWNLOADED (6.1 GB, both shards verified, 1030 tensors) AND
  THE SERVER WILL NOT START: ***
    RuntimeError: Cannot download the VLM backbone 'nvidia/Cosmos-Reason2-2B',
    which is a gated Hugging Face repo. EVERY GR00T CHECKPOINT (including the
    base nvidia/GR00T-N1.7-3B) loads this backbone, so BOTH zero-shot inference
    AND FINETUNING require access.

  => THIS BLOCKS THE WHOLE GR00T TRACK, not just this checkpoint. S3 (fine-tune
     on NVIDIA's data) and S5 (fine-tune on our sim data) need it too.
  => USER ACTION: request access at huggingface.co/nvidia/Cosmos-Reason2-2B,
     then `~/sim/Isaac-GR00T/.venv/bin/hf auth login` (the user types the token;
     it must not appear in a transcript - project hard rule #3).
  => UNLIKE PaliGemma, this CANNOT be recovered from the old laptop's cache -
     GR00T was never run there.
  The 6.1 GB we hold is the ACTION EXPERT + adapters only; the vision-language
  backbone is a separate gated download.

  Protocols DO match, so this is purely an access problem:
    GR00T PolicyServer binds ZMQ REP on port 5555 (gr00t/policy/server_client.py)
    LeIsaac Gr00tServicePolicyClient connects ZMQ to 5555
    run_gr00t_server.py defaults embodiment_tag=new_embodiment - matches the ckpt
  Start command once unblocked:
    ./.venv/bin/python -m gr00t.eval.run_gr00t_server \
      --model_path=~/lerobot_assets/checkpoints/gr00t_n17_so101 \
      --embodiment_tag=new_embodiment --port=5555

robocurve/gr00t-n1.7-so101-molmoact2  (original screening notes)
  embodiment_tag: new_embodiment              <- the SO-101 path
  video modality_keys: front, wrist           <- EXACTLY what LeIsaac exposes
  action space: xdof_relative_eef_relative_joint  <- RELATIVE, gripper separate
  Complete checkpoint: model-0000{1,2}-of-00002.safetensors + adapters/ +
  experiment_cfg/ + processor/  (~6 GB)
```

### THE CHEAPEST SCREEN: does its observation space match an env we HAVE?

```text
A downloaded checkpoint is only TESTABLE if its observation space matches an
environment we already possess. LeIsaac gives us: state + front + wrist.
Anything needing extra or differently-named inputs is untestable no matter how
good the policy is.

AND YOU CANNOT JUST DOWNLOAD THE MISSING ENVIRONMENT. People publish MODELS
constantly - it is one command. Publishing a working ENVIRONMENT means packaging
scene assets, task logic, and termination/reward code. That is what LeIsaac IS,
and why there is essentially only one of it for the SO-101.

=> SCREEN ORDER, cheapest first:
     1. observation space vs an env we have   (one API call, free)
     2. checkpoint FORMAT vs a loader we have (one API call, free)
        *** AND CHECK ALL THREE SERVING PATHS, not just LeRobot: LeIsaac
        supports lerobot-<type>, gr00tn1.5/1.6, AND openpi. A format we cannot
        load is not the same as a format we cannot RUN. ***
     3. action space absolute vs relative     (config file, free)
     4. only then download weights
```

```text
LESSON FROM GETTING THIS WRONG: the first pass rejected the openpi checkpoint on
"we have no loader", when LeIsaac ships THREE policy clients and one of them is
openpi. Check what the HARNESS supports before declaring a checkpoint unusable -
the constraint is the set of serving paths available, not the LeRobot format.
```

Not a coincidence that the survivor fits: it was trained on the MolmoAct2 SO-101
corpus, which uses the same `front`+`wrist` convention LeIsaac does.

### Two conditions that still apply

```text
1. ERA 1 RULE. Each downloaded checkpoint needs its TRAINING-ERA code version
   identified before its result means anything. Our own 012000 scored corr
   0.197 on the wrong lerobot vs 0.826 on the right one. Most of these repos
   have NO model card, so that information may simply not exist.
2. READ FAILURE ASYMMETRICALLY. These were trained on other people's real rigs.
   Evaluating them in our sim kitchen is a huge domain shift.
     works in sim -> STRONG evidence
     fails in sim -> WEAK evidence, tells us little
```

---

## 3. Assessment Of The Plan ("match the real rig to sim")

The proposal: get everything working in sim, then build the real environment -
cameras, task setup - to match sim, so we can train and test fast in sim and go
to hardware only when needed.

```text
THE CORE OF IT IS RIGHT, and it is already the recorded strategy
(sim_first_strategy_20260805.md): sim is the reference, the rig matches it.
The iteration-speed argument is real - we ran six scored evaluations in an
afternoon; the equivalent on the arm is six sessions with a human present.
```

### But S2 sharpened what "match" has to mean

```text
S2 added a `top` camera with an INVENTED pose and made things WORSE
(time near the object 86% -> 23%). A masked view the model ignores; a WRONG
view it cannot. So "match the cameras" is not a checkbox - a mismatched match
is worse than no match.
```

### And there is a stronger alternative worth weighing

```text
STRATEGY A (proposed): make ONE sim scene, then build the real rig to match it.
  + exact correspondence, easy to reason about
  - brittle: every unmatched dimension (lighting, texture, table height, object
    appearance) is a silent gap
  - it optimises for ONE environment, which is the failure mode we already
    have on the real table

STRATEGY B: make SIM DIVERSE ENOUGH THAT THE REAL RIG FALLS INSIDE ITS
DISTRIBUTION. Vary scenes, lighting, camera poses, object positions in sim;
train on that spread; then the real setup does not have to match anything
exactly - it just has to be within the range seen.
  + this is what PI's own ablation argues for: removing environment diversity
    hurt WORST (OOD success -> 31%), worse than removing cross-embodiment (49%)
    or web data (80%)
  + LeIsaac declares SIX scenes and object positions are config values, so the
    diversity is cheap to generate
  - needs more training data and more compute (both now free-ish locally)

OUR OWN VERIFIED FAILURE IS THE ARGUMENT AGAINST A: 012000 was trained on ONE
table and is welded to it - 145 empty squeezes when an onion moved a few
inches. Building a sim that matches one real setup risks reproducing exactly
that brittleness in a new place.

RECOMMENDATION: aim at B, and use A only where it is cheap. Concretely - do NOT
try to replicate the sim kitchen physically. Match the things that are hard for
a model to be robust to (camera COUNT and rough placement, task structure,
object type) and randomise the rest in sim rather than replicating it in the
world.
```

---

## 4. A Trap Worth Naming: Camera Key Names Lie

```text
izuluaga/finish_sandwich's `front` camera is TOP-DOWN.
Ours is a forward-facing view. SAME KEY NAME, different geometry.

So a dataset "having front+wrist" does NOT mean its views match ours. Any
co-training or cross-evaluation must check the actual camera POSE, not the key.
This is the same failure S2 demonstrated, arriving from a different direction.
```

---

## 4b. THE THREE SERVING PATHS LEISAAC SUPPORTS

Worth stating once, because getting this wrong cost a wrong conclusion above.

```text
--policy_type=lerobot-<model_type>   gRPC       -> a LeRobot policy server
   ours: scripts/policy_server_leisaac_shim.py (needs the pickle shim; see
   new_machine_local_serving_20260804.md). Used for Pi05 012000.

--policy_type=gr00tn1.5 | gr00tn1.6  ZMQ        -> GR00T's inference service
   Gr00t16ServicePolicyClient. Whether it accepts N1.7 is UNVERIFIED.

--policy_type=openpi                 websocket  -> openpi's own policy server
   OpenPIServicePolicyClient, port 8000, camera_keys ["front","wrist"],
   task_type "so101leader". Pinned commit 5bff19b0c0c447c7a7eaaaccf03f36d50998ec9d,
   reference fork EverNorif/openpi tree lerobot-v0.3.3.

=> A checkpoint only needs ONE of these to be testable. Screen against all three.
```

---

## 5. Suggested Next Actions

```text
CHEAP AND HIGH INFORMATION
  1. Test a DOWNLOADED SO-101 checkpoint in our sim, using the harness we
     already have. Start with SmolVLA (0.5B - loads in seconds vs 60 s for
     Pi05) or robocurve/gr00t-n1.7-so101-molmoact2 (matches our GR00T version).
     Any of them performing well in sim would be a strong signal.
  2. GR00T pipeline validation on izuluaga/finish_sandwich - SO-101, v3.0,
     front+wrist, a real place task. Structurally identical to what we would
     produce, so it is a genuine dry run, not a generic smoke test.

THEN
  3. Pull jinseonylee/SO101_PickAndPlace_Fruit - closest public data to our
     actual task.
  4. Download more LeIsaac scenes and start building the DIVERSITY of
     Strategy B.
  5. Measure our real top-camera pose, so a third view can help rather than
     hurt (S2).
```
