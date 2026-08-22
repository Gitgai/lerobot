# SO-101 Generalization Program — reference plan

> Converted from SO101_Generalization_AI_Engineering_Plan_Updated.docx
> (operator-provided, 22 Aug 2026, rev 1.1). Tables are flattened by the
> conversion. READ THE ADDENDUM AT THE BOTTOM FIRST — it corrects this
> document against measured experience on this rig, and states the final
> adopted plan. The execution layer is docs/next_session_runbook_20260822.md.

# SO-101 Generalization Program
From a 90% Specialist to a Measured, Multi-Task Manipulation System
Detailed Engineering & Experiment Plan
22 August 2026
Revision 1.1 — Immediate baseline runbook and 20-demo plate pilot added
Current verified baseline
The current system is a specialist: the same SO-101 arm, cameras, room, table, orange, instruction, and start pose; orange position varies. Under that controlled distribution, the measured result is approximately 9 successes out of 10. The purpose of this plan is to expand capability one controlled axis at a time without losing the ability to diagnose failures.
Primary next milestone:
Pick up the orange and place it on a plate, with both orange and plate positions varied.
# 1. Executive Summary
The project should now transition from proving that sim-to-real deployment works to systematically measuring and expanding generalization. The guiding principle is simple: change one capability dimension at a time, preserve the winning baseline configuration, and require an explicit evaluation gate before moving to the next level.
What we should do next
Freeze the current winning checkpoint and runtime configuration. Re-run a clean orange-picking baseline. Then build the orange-to-plate task as the first source-to-target manipulation benchmark. Do not introduce multiple objects or multiple instructions until orange-to-plate is stable enough to diagnose cleanly.
Priority
Action
Why it matters
Exit criterion
P0
Freeze current baseline
Prevents accidental regression while the new task is developed.
Checkpoint, code commit, calibration, camera settings, RTC/tempo settings and dataset ID are recorded.
P0
Run baseline benchmark
Establishes a trustworthy before/after comparison.
30 quick-gate trials; 100 trials for a milestone claim.
P1
Instrument stage-level evaluation
Turns “failed” into a diagnosable failure category.
Every episode can be labeled: reach, grasp, lift, transport, place, release.
P1
Collect orange-to-plate demonstrations
Adds a destination object and spatial relation while keeping task semantics simple.
Balanced source/target coverage with held-out position combinations.
P1
Train and evaluate orange-to-plate
First deliberate move beyond the current specialist.
>=80% overall on held-out combinations; >=90% successful pickup/lift is a useful initial gate.
P2
Add a second object + instruction contrast
Forces the language channel to matter.
Correct object selection >=90% on paired counterfactual scenes.
## The program in one sentence
Build a reproducible manipulation benchmark around the SO-101, use it to climb a controlled generalization ladder, and use coding agents around the engineering loop—not inside the safety-critical servo loop—to accelerate experiment analysis, dataset quality, code changes, and regression testing.
# 2. Current State and What the 90% Result Means
The current result should be treated as a strong local-generalization result, not a general manipulation result. The policy has demonstrated that it can visually locate the orange across different positions inside the tested workspace and execute the learned skill despite some lighting and deployment-timing shift.
Axis
Current status
Interpretation
Task
Fixed: pick up / move orange
No task generalization measured yet.
Object identity
Fixed: same physical orange
No category or instance generalization claim yet.
Room/table/background
Fixed
Environment generalization not measured.
Arm/calibration
Fixed
Policy is tied to this robot configuration until proven otherwise.
Cameras
Fixed
Camera-placement robustness not measured.
Instruction
Fixed
Language may be ignored because it carries no varying information.
Start pose
Fixed
Start-state robustness not measured.
Orange position
Varied
Real local perception/spatial generalization is demonstrated.
Lighting
Varied somewhat
Some robustness observed, but not yet controlled or benchmarked.
Execution tempo / RTC
Changed during deployment
A deployment-system variable materially affected behavior and must now be versioned.
## Interpretation rule
Every future capability claim should name the distribution it was tested on. For example: “This checkpoint succeeds in 83% of orange-to-plate trials across the defined source/target grid with the current cameras and room.” Avoid broader statements such as “the robot is 83% good at placement.”
# 3. North-Star Capability
The long-term target should be a measured general manipulation testbed rather than an undefined “smart robot.” A useful north-star specification is:
North-star behavior
Given a tabletop containing familiar and unfamiliar everyday objects, the SO-101 should interpret a natural-language command, identify the correct source and destination, execute the manipulation, and fail safely when confidence or reachability is inadequate.
## Capability dimensions
Spatial: source and destination positions change.
Instance: different examples of the same category are used.
Category: apple, orange, cup, ball, etc.
Language: different instructions require different actions in the same visual scene.
Relation: on, in, left of, right of, near, closest to.
Distractors: irrelevant objects are present.
Start state: arm begins from multiple safe poses.
Environment: table/background/lighting change.
Camera robustness: small pose changes are tolerated or recovered by recalibration.
# 4. Map the AI Engineering Skills Framework to SO-101
AI Engineering area
SO-101 implementation
Concrete deliverable
Building & deploying AI applications
Camera capture, preprocessing, VLA/policy inference, action execution, motor interface, runtime timing, logging.
A repeatable inference runner with versioned runtime configuration.
Software engineering fundamentals
Git, configuration management, dataset schemas, calibration management, tests, logging, recovery, tooling.
Repository structure and experiment manifest that can reproduce any benchmark run.
Using coding agents
Failure triage, log/video analysis, dataset QA, code generation, test generation, experiment summaries.
Agent-assisted engineering loop with human approval before physical deployment.
Shaping the build
Define each capability, controlled variable, benchmark, pass gate, and next experiment.
Generalization ladder and milestone matrix.
Evaluation & reliability (recommended fifth area)
Stage-level metrics, holdout scenes, regression suites, confidence intervals, safety failures.
SO-101 benchmark suite and dashboard/report.
# 5. Recommended System Architecture
Keep the learned policy in the manipulation path, but surround it with deterministic engineering infrastructure that makes experiments reproducible and failures observable.
Experiment Config → Episode Runner → Cameras → Policy → Action Adapter → SO-101
↓                ↓                  ↓
Video/State Logs → Evaluator → Report/Failure Triage
## Required logged metadata per run
Git commit or repository revision.
Policy/checkpoint ID and training dataset version.
Arm calibration ID / calibration hash.
Camera serials, resolution, FPS, exposure/white-balance mode, and mounting configuration.
Inference frequency, action horizon/chunking, RTC or temporal execution settings, and any smoothing/interpolation values.
Instruction text exactly as presented to the model.
Source object ID and target object ID.
Source and target region/position labels.
Episode start pose.
Per-camera video and robot state/action logs.
Outcome labels and failure stage.
## Suggested experiment folder
experiments/<experiment_id>/<episode_id>/
manifest.json or yaml
camera_wrist.mp4
camera_external.mp4 (if used)
robot_state.csv
policy_actions.csv
events.json
result.json
# 6. Phase 0 — Freeze and Re-Measure the Current Baseline
Before changing the task, make the current 90% result reproducible. This is the control condition for everything that follows.
## Actions
Tag the winning checkpoint as a protected baseline. Do not overwrite it.
Record the exact code commit, calibration, camera settings, and RTC/tempo configuration used for the best real-world behavior.
Define the current trained orange-placement region on the table using a small coordinate/grid notation.
Run 30 evaluation episodes as a fast reproducibility gate. If this differs materially from the earlier ~90%, investigate before adding a new task.
For a publishable/internal milestone claim, accumulate 100 standardized episodes over more than one session/day.
## Baseline outcome labels
Label
Definition
S0
No meaningful reach / wrong direction.
S1
Reach toward orange but no usable grasp attempt.
S2
Grasp attempted but object not secured.
S3
Object grasped but not lifted cleanly.
S4
Successful lift and task completion.
Decision gate
If the baseline is not reproducible, do not train the plate task yet. First identify whether the cause is mechanical drift, camera/exposure change, calibration, runtime timing, or checkpoint/config mismatch.
# 7. Phase 1 — Orange → Plate: The Immediate Next Experiment
This should be the next capability because it adds exactly one major idea: a destination object. The robot must now localize a source, grasp it, maintain control during transport, localize a target, and release at the correct place.
## Task definition
Instruction
“Pick up the orange and place it on the plate.” Use one canonical sentence for the first plate experiment. Language generalization is deliberately not the variable yet.
## Hold fixed
Same arm and calibration.
Same cameras and mounts.
Same room/table/background.
Same orange instance.
Same plate instance.
Same start pose.
Same deployment runtime and RTC/tempo settings as the frozen baseline.
## Vary deliberately
Orange position.
Plate position.
Orange-to-plate relative direction and distance.
## Position design
Use labeled regions instead of arbitrary hand placement. A simple first pass is five source regions and five target regions that are mechanically reachable and camera-visible. The important point is not the exact number; it is balanced coverage and a recorded holdout set.
Set
Example design
Purpose
Training combinations
Approximately 15–20 source/target combinations sampled across the reachable workspace.
Teach the relation while covering different directions/distances.
Held-out combinations
Approximately 5–10 combinations never shown in demonstrations.
Test interpolation/generalization rather than memorized pairings.
Stress positions
Near edges of the previously successful orange region and farther source-target separations.
Find the capability boundary.
## Demonstration collection target
Start with a 20-demonstration pilot, balanced across the selected source/target combinations. Inspect every pilot episode for camera visibility, grasp consistency, transport trajectory, placement, release, timing, and operator consistency. Only if the pilot is clean should collection expand to roughly 60–100 high-quality demonstrations. If placement is unstable or the demos are inconsistent, fix the collection protocol before scaling the dataset.
## Demo quality rules
Discard episodes with accidental collisions, occluded cameras, operator hesitation that does not reflect intended behavior, or failed grasps unless the training method explicitly benefits from failed trajectories.
Avoid collecting 80% of demonstrations from one comfortable region. Balance the grid.
Include different source-to-target directions: left→right, right→left, near→far, far→near where reachable.
Keep temporal execution behavior consistent with deployment; the previous RTC result shows timing is a first-class variable.
# 8. Phase 1 Evaluation Protocol
Do not score only final success. Record where the chain breaks. This will tell us whether the next data should improve grasping, transport, target localization, or release.
Stage
Pass definition
Typical failure
1. Source selection
Motion is directed toward the orange.
Attends to plate/background or wrong region.
2. Reach
Gripper reaches a graspable pose.
Approach angle/position is unusable.
3. Grasp
Orange is secured.
Slip, miss, premature close.
4. Lift
Orange clears table stably.
Drops immediately after grasp.
5. Target localization
Transport is directed toward plate.
Moves to learned fixed location instead of current plate.
6. Placement
Orange enters acceptable plate area.
Releases beside plate / collision.
7. Release/retract
Object remains on plate and arm exits safely.
Drag, knock, failed release.
## Recommended benchmark split
Benchmark
Trials
Purpose
Quick development gate
20–30
Fast feedback after a checkpoint change.
Milestone gate
40–50
Balanced in-distribution + held-out source/target combinations.
Strong capability claim
100
More stable estimate across sessions and edge cases.
## Initial pass criteria
Pickup/lift success: target >=90% if current grasp skill is retained.
Correct plate-directed transport: target >=85%.
End-to-end orange-on-plate success on held-out combinations: target >=80% as a practical first milestone.
No unsafe recurring collision mode. Any new mechanical-risk failure is a stop condition even if average success is high.
These thresholds are engineering gates, not claims of universal competence. They can be tightened after the first stable plate checkpoint.
# 9. Phase 2 — Force the Language Channel to Matter
Only after the plate task is stable should we introduce multiple commands. The key design principle is that the same visual scene must require different actions depending on the instruction. Otherwise the model can continue ignoring language.
## Minimal language-grounding setup
1.  Place an orange and an apple in the same scene.
2.  Keep one visible plate as the destination.
3.  Use paired commands: “Put the orange on the plate” and “Put the apple on the plate.”
4.  Swap object locations regularly so the command cannot be solved by a fixed spatial rule.
5.  Create counterfactual evaluation pairs: identical scene, different instruction. The first meaningful movement should change with the instruction.
Critical test
Take the exact same initial image/state twice. Run “put the orange on the plate,” then reset and run “put the apple on the plate.” If early action trajectories remain essentially identical, the policy is still instruction-deaf.
## Language phase metrics
Metric
Suggested gate
Correct object selected
>=90%
Instruction-sensitivity on paired scenes
Clearly different source-directed motion for different commands
End-to-end task success
>=75–80% initially
Wrong-object grasp rate
<=5–10%
# 10. Generalization Ladder After Language Grounding
Level
New variable
Example
Why it is informative
L0
Position
Same orange, new table positions.
Already demonstrated locally.
L1
Target relation
Orange → plate.
Adds destination localization and placement.
L2
Instruction/object choice
Orange vs apple in same scene.
Forces language grounding.
L3
Instance
Different oranges/apples.
Tests category perception beyond one specimen.
L4
Distractors
Cup/ball present but irrelevant.
Tests selective attention.
L5
Relations
In bowl, right of plate, closest object.
Tests compositional spatial language.
L6
Start pose
Several safe arm starts.
Tests action-state robustness.
L7
Environment
New table/background/lighting.
Tests scenery dependence.
L8
Novel object
Banana with little/no task-specific data.
Tests semantic transfer from the general backbone.
## Rule for advancing
Do not advance because a few demonstrations look impressive. Advance when the current rung meets its benchmark gate and the dominant failure mode is understood. Preserve at least one regression benchmark from every earlier rung so new training cannot silently destroy old capabilities.
# 11. Build the SO-101 Benchmark Suite
The benchmark suite is the core engineering asset of the project. Checkpoints can change; the benchmark tells us whether the system is actually improving.
Suite
What varies
Primary metric
B0 Orange Pick
Orange position
Successful grasp/lift rate
B1 Orange → Plate
Orange + plate positions
Successful placement rate
B2 Instruction Grounding
Object identity + instruction
Correct object selection + success
B3 Instance Robustness
Physical instance within category
Category transfer success
B4 Distractors
Extra irrelevant objects
Wrong-object and collision rate
B5 Lighting
Controlled dim/normal/bright
Success delta vs baseline
B6 Start Pose
Safe initial arm poses
Completion rate
B7 Environment
Background/table changes
Success delta / failure mode
## Statistics and reporting
Always report numerator/denominator (for example 27/30), not only percentage.
Separate development trials from locked benchmark trials.
Track success by position cell/combo, not just overall average.
Use confidence intervals for milestone reports when comparing close checkpoints; 30 trials is useful for a gate but can be too small to distinguish nearby success rates.
Keep videos of all failures and a small random sample of successes.
# 12. Where Coding Agents Help — and Where They Should Not
Coding agents can substantially accelerate this program if they are used in the outer engineering loop. They should not be trusted to directly improvise real-time servo commands on the physical robot without the policy/safety architecture and human-reviewed deployment path.
Agent role
Inputs
Outputs / benefit
Experiment analyst
Episode videos, logs, result labels
Failure clusters, position heatmaps, likely causes, next-data recommendation
Dataset QA agent
Dataset metadata + sampled episodes
Duplicates, corrupted episodes, imbalance, camera issues, inconsistent instruction labels
Code agent
Repository + issue/acceptance criteria
Instrumentation, evaluation scripts, config plumbing, regression tests
Training analyst
Training curves, checkpoints, benchmark results
Checkpoint comparison, overfitting signals, experiment summary
Review agent
Code diff + tests + runtime constraints
Potential bugs, unsafe changes, missing tests, config drift
Documentation agent
Run manifests + results
Automatically generated experiment report and changelog
## Human approval boundaries
Human approves changes to motor limits, calibration, safety constraints, or action scaling.
Human reviews any code change before first physical execution if it affects the robot-control path.
Agents may freely analyze copies of logs/datasets and draft code/tests in a development branch.
A known-good baseline remains available for immediate rollback.
# 13. Software Engineering Work to Do Now
The fastest way to make future experimentation cheaper is to invest in a small amount of reproducibility infrastructure now.
## Minimum repository additions
Component
Purpose
experiment.yaml
Declares checkpoint, instruction, positions, runtime/RTC settings, camera config and benchmark name.
run_episode.py
Starts one repeatable episode and records all required data.
evaluate_episode.py
Assigns/stores outcome labels and stage results.
summarize_experiment.py
Produces success rate, per-stage failures, per-position heatmap/table and checkpoint metadata.
benchmarks/ definitions
Locked evaluation scene lists so training does not leak into the benchmark.
calibration/ registry
Named calibration files with dates/hashes.
checkpoints/ manifest
Human-readable record of dataset, training config and evaluation results for each checkpoint.
## Regression discipline
Every new plate checkpoint must still run B0 Orange Pick.
Every future language checkpoint must run B0 + B1 + B2.
Never accept a new checkpoint solely because the newest task improved; check earlier capabilities for catastrophic regression.
# 14. Failure Taxonomy and Data-Collection Response
Failure class
Evidence
Likely response
Perception/source error
Moves toward wrong region/object.
Add balanced visual variation; inspect camera framing/exposure; use paired counterfactual tests.
Reach geometry error
Correct object chosen but approach is poor.
Add demos around problematic workspace cells/approach angles.
Grasp error
Miss/slip despite correct reach.
Improve grasp diversity/consistency; inspect gripper mechanics; add targeted demos.
Transport error
Grasp succeeds but object drops/collides in transit.
Add transport trajectories and inspect action timing/smoothing.
Target localization error
Carries object to fixed or wrong location.
Increase target-position diversity and held-out target testing.
Release/placement error
Gets to plate but releases badly.
Add terminal placement diversity and clear success geometry.
Language error
Same action despite different instruction.
Use same-scene/different-command data and balance task labels.
Runtime/tempo error
Offline/sim looks correct; real timing degrades.
Treat RTC/inference/action timing as versioned deployment configuration; reproduce with fixed settings.
Mechanical/calibration drift
Previously good checkpoint degrades everywhere.
Recheck calibration, servo state, gripper, camera mount before retraining.
# 15. Suggested Execution Schedule
The exact calendar depends on how quickly demonstrations and physical trials can be run, but the sequence should remain fixed.
Block
Work
Deliverable
Day 1
Freeze baseline; capture full config; implement/verify experiment manifest.
Reproducible baseline package.
Day 1–2
Run 30 baseline episodes; label failures; fix only reproducibility issues.
Baseline report.
Day 2–3
Define orange/plate grid and held-out combinations; instrument stage labels.
Plate benchmark v1.
Day 3–5
Collect a 20-demo pilot; review all episodes. If clean, expand to 60–100 balanced orange-to-plate demonstrations.
Pilot QA report, then dataset v1.
Next training cycle
Fine-tune from chosen base; preserve general backbone strategy unless evidence argues otherwise.
Plate checkpoint candidates.
Evaluation
20–30 quick gate, then 40–50 balanced milestone test.
Checkpoint comparison and failure report.
After >=80% held-out plate success
Introduce apple + paired instructions.
Language-grounding dataset/benchmark.
# 16. Exact Next-Step Checklist
1.  Create a protected tag/name for the current best checkpoint (“orange_pick_baseline_v1”).
2.  Write down the exact RTC/tempo/inference settings that produced the 9/10 behavior.
3.  Record current calibration and camera settings; photograph/measure camera mounts if useful.
4.  Define a 5-region orange test grid and run 30 baseline trials with position labels.
5.  Add stage/failure labels to the logging workflow.
6.  Choose one plate with clear visual contrast and a placement success region that is easy to score.
7.  Define five reachable plate regions and training vs held-out source/target combinations.
8.  Collect the first 20 pilot orange-to-plate demonstrations and inspect them before collecting the full dataset.
9.  If the pilot data is clean, expand to approximately 60–100 balanced demonstrations.
10.  Fine-tune and run B0 Orange Pick first. If basic picking regresses badly, stop and diagnose before plate evaluation.
11.  Run B1 Orange → Plate on 20–30 quick-gate trials, then held-out combinations.
12.  Only after the plate gate is stable, introduce apple + two instructions to test whether language controls action.
Most important immediate action
Do not start by adding apples, cups, new rooms and new instructions together. First freeze the working specialist and make orange → plate the next controlled experiment. This preserves the scientific value of the work and gives us a clean answer about whether the policy can learn source-to-target manipulation.
# 17. Decision Tree After the First Plate Training Run
Observed result
Interpretation
Next move
Orange picking regresses
New fine-tune damaged an existing capability or runtime changed.
Run B0, compare timing/config, inspect catastrophic forgetting/data imbalance.
Picks orange but ignores plate position
Target concept/location not learned.
Increase plate-position diversity; verify target is visible; inspect demos and target-directed action.
Reaches plate but drops in transit
Manipulation/trajectory robustness issue.
Add targeted transport demos; inspect temporal settings.
Works only on trained source-target pairs
Memorization of pairings.
Increase combinatorial coverage and preserve held-out pairings.
>=80% on held-out pairs
Source-to-target skill is established.
Move to orange+apple paired-language phase.
# 18. Definition of Success for the Program
The program is succeeding when capability grows while earlier benchmarks remain stable and each claim is tied to a clear test distribution. A strong medium-term milestone would be:
Medium-term milestone
One SO-101 can reliably execute at least two language-selected tabletop manipulation tasks, on multiple object instances and varied source/target positions, while retaining the original orange-pick baseline and producing repeatable benchmark reports from a versioned engineering pipeline.
## Final principle
The objective is not to maximize task variety as fast as possible. The objective is to maximize verified capability per experiment. The benchmark, logging, and controlled generalization ladder are what turn a successful robot demo into an engineering program.
# Appendix A — Recommended Experiment Manifest Fields
Field
Reason
experiment_id
Required for reproducibility / analysis.
episode_id
Required for reproducibility / analysis.
date/time
Required for reproducibility / analysis.
benchmark_id
Required for reproducibility / analysis.
git_commit
Required for reproducibility / analysis.
checkpoint_id
Required for reproducibility / analysis.
dataset_id
Required for reproducibility / analysis.
calibration_id
Required for reproducibility / analysis.
camera_config_id
Required for reproducibility / analysis.
instruction
Required for reproducibility / analysis.
source_object
Required for reproducibility / analysis.
target_object
Required for reproducibility / analysis.
source_region
Required for reproducibility / analysis.
target_region
Required for reproducibility / analysis.
start_pose_id
Required for reproducibility / analysis.
inference_hz
Required for reproducibility / analysis.
rtc_mode/settings
Required for reproducibility / analysis.
action_chunk/horizon
Required for reproducibility / analysis.
success
Required for reproducibility / analysis.
failure_stage
Required for reproducibility / analysis.
notes
Required for reproducibility / analysis.
# Appendix B — Benchmark Report Template
Run identification: Checkpoint, dataset, code commit, calibration, camera config, RTC/tempo config.
Test distribution: Objects, positions, instructions, environment, held-out conditions.
Overall result: Successes / total and percentage.
Stage metrics: Source selection, reach, grasp, lift, target localization, placement, release.
Failure clusters: By source region, target region, object, instruction, lighting, or session.
Regression check: Performance on all earlier locked benchmarks.
Decision: Promote checkpoint, collect targeted data, modify runtime, or reject checkpoint.
# Appendix C — Immediate Next Session Runbook
Purpose: establish a reproducible baseline before any new training. This runbook is the exact next action. The plate task should not start until the current orange-picking system has been frozen, re-measured, and logged with stage-level outcomes.
Immediate order of operationsFreeze orange_pick_baseline_v1, verify RTC/tempo + camera + calibration settings, then run the 30-trial five-position baseline. Only after that baseline is trustworthy should we collect the 20-demo orange-to-plate pilot.
## C.1 Pre-flight freeze checklist
Create a protected checkpoint/tag named orange_pick_baseline_v1; never overwrite it.
Record Git commit, training dataset ID, policy checkpoint, calibration file/hash, camera serials/mounts, resolution/FPS, and exposure/white-balance mode.
Record inference frequency, action horizon/chunk size, RTC configuration, smoothing/interpolation, and any action scaling or safety limits.
Mark the exact arm start pose and the five orange test regions on the table.
Verify both cameras see the full intended workspace and the orange is not occluded at the start.
Perform one dry-run / safe motion check before counted trials. Do not count setup or debug runs.
## C.2 Thirty-trial baseline matrix
Use five labeled orange regions (A–E). Run six counted episodes per region for 30 total trials. Randomize the order of regions if practical, but keep all other conditions fixed. Record the stage label for every failure and retain the failure video.
Region
T1
T2
T3
T4
T5
T6
A — far/left
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
B — center-left
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
C — center
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
D — center-right
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
E — far/right
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
✓ / S0–S4
Scoring key: ✓ = successful pickup/lift. S0 = no meaningful reach/wrong direction; S1 = unusable reach; S2 = grasp attempt failed; S3 = grasped but failed to lift; S4 = successful lift/task completion.
Region
Attempts
Successes
Notes / dominant failure
A
6
B
6
C
6
D
6
E
6
TOTAL
30
## C.3 Baseline decision gate
Green: approximately 27/30 or better, with no severe region-specific collapse and no new mechanical-risk behavior. Proceed to plate pilot.
Yellow: 24–26/30, or large variation by region. Repeat targeted trials and diagnose configuration, timing, or workspace coverage before changing the task.
Red: below 24/30, major calibration/configuration drift, camera mismatch, or recurring unsafe motion. Stop. Restore the known-good baseline and identify the cause before any plate training.
These are engineering decision zones, not statistical claims of universal capability. The purpose is to prevent us from building the next task on top of an unstable baseline.
## C.4 Orange → plate 20-demo pilot
After the baseline passes, introduce one plate. Keep the room, table, cameras, calibration, orange instance, plate instance, start pose, instruction, and deployment runtime fixed. Vary only the orange and plate positions. The first dataset is a pilot, not the final dataset.
Pilot block
Demos
Coverage
Review focus
P1
4
short left→right / right→left
grasp + transport
P2
4
near→far / far→near
transport stability
P3
4
center source, varied plate
target localization
P4
4
varied source, center plate
source localization + grasp
P5
4
edge-but-safe combinations
boundary behavior / placement
### Pilot acceptance checklist:
Orange and plate are visible in all required camera views throughout the intended action.
Demonstrator motion is smooth and consistent; avoid hesitant corrective motion unless it is intentionally part of the behavior.
Grasp style and transport height are reasonably consistent across episodes.
Release occurs clearly inside the defined plate success region.
Timing/tempo matches the intended deployment strategy.
No systematic source/target pair dominates the pilot.
Go / no-go for full collectionIf the 20-demo pilot is clean, expand to roughly 60–100 balanced demonstrations. Preserve 5–10 source/target combinations as locked holdouts that are never shown in demonstrations. Train only after the dataset balance and demo quality are verified.
## C.5 What happens immediately after the first plate checkpoint
Run B0 Orange Pick first. If basic grasp/lift regresses badly, do not celebrate plate success; diagnose regression or timing/config drift.
Run 20–30 B1 Orange → Plate quick-gate trials, including held-out source/target combinations.
Log stage success for source selection, reach, grasp, lift, target localization, placement, and release.
If end-to-end held-out performance is approximately >=80% and pickup/lift remains approximately >=90%, promote the checkpoint to a plate milestone candidate.
Only then add apple + paired instructions to test whether changing language changes object selection in the same scene.
---

# ADDENDUM — corrections from measured experience (2026-08-22)

The plan above is adopted as the program reference WITH the corrections below.
Where they conflict, the addendum wins. Each correction cites the measured
event that motivates it.

## A1. Check the LINK before counted trials
The plan versions every setting except the network. Measured 2026-08-21/22:
payload calls 320 ms -> 4,700 ms within hours, identical config (Pune evening
congestion). An unchecked choked window fails any baseline gate for the wrong
reason and the plan's own decision tree then points at five causes, none of
them the real one. Rule: 3 timed payload calls before counted trials;
postpone if median > 600 ms.

## A2. Power-brick pre-flight
Six connect-time motor-bus faults on record (voltage error id6, no-status
id4/id1-6, bad-status id5/id3), never mid-run. Rule: two consecutive connect
faults = stop, reseat/replace the brick, do not burn counted trials.

## A3. Demos MUST use the deployment camera set
The plan never states it. This project lost days to the top-vs-front channel
confusion (2026-08-17) and the A/B exists because camera identity matters.
Rule: plate demos record front = laptop /dev/video0 + wrist = Pi proxy,
identical to the serving config of the checkpoint being extended.

## A4. One exact instruction string, dataset == runtime
Caught once already: client default "Grab orange and place into plate" vs the
dataset's sentence. Rule: the demo task string and the client
--lang_instruction are byte-identical; recorded in the run log.

## A5. Prevent forgetting, don't just detect it
The plan re-runs B0 after training (detection). Prevention is a data
decision: fine-tune FROM the current checkpoint WITH the old 79 orange demos
mixed alongside the new plate demos (approx. balanced replay). Detection
without prevention costs a full retrain cycle per failure.

## A6. The 27/30 green gate is statistically strict
A true-90% system passes >=27/30 only ~65% of the time. Rule: 25-26/30 =
extend to 50 trials, not investigate. Below 24 = investigate (after A1/A2
are re-checked first).

## A7. Baseline trials are region-labeled and DUAL-PURPOSE
We hold 13 fully-traced RTC runs from 2026-08-20; a fresh 30-trial
re-measurement is partly redundant. Rule: 15 trials on a marked 5-region
grid with far-left/far-right at the edge of the trained region - one session
re-verifies the baseline AND probes spatial generalization (ladder L0/L1).

## A8. Infrastructure is built lazily
The manifests/registries/dashboards of sections 5/13/appendices duplicate
working instrumentation (per-cycle traces, scoring scripts, storyboards,
committed docs). Rule: build a formal tool the second time its absence
costs time, not before. Precedent: the trace logger was built after Aug 8
cost four days, and has paid for itself since.

## Metric note
The plan's B0 scores grasp/lift (S4). Our 9/10 headline is FULL TASK (orange
moved + deliberate release). Baseline reports state both numbers explicitly.

---

# THE ADOPTED FINAL PLAN

Standing rules (every phase): one variable at a time; every claim names its
tested distribution; demos use deployment cameras + the exact deployment
sentence; link + power pre-flight before counted trials; earlier benchmarks
re-run after every training; tooling built when needed.

```text
PHASE 0  one rig session (~1 h)
  pre-flight (A1 link, A2 power) -> freeze orange_pick_baseline_v1
  15 trials, marked 5-region grid (3 each, edges included)
     = drift check + spatial probe in one
  optional +5 trials with a different orange = instance probe
  [opportunistic in any good link window: Brain B RTC runs 2-3
   -> closes tempo-vs-camera]

PHASE 1  the plate (2-3 sessions + GPU)
  20-demo pilot (A3/A4 rules) -> full inspection -> 60-80 demos with
  5-10 held-out source/target combos -> train per A5 -> offline probe
  -> B0 regression -> 20-30 plate trials incl. held-out
  gate: >=80% end-to-end on held-out combos, >=90% grasp retained

PHASE 2  language grounding (after plate stable)
  orange + apple, paired sentences, same-scene/different-command demos;
  the counterfactual test (identical scene, two instructions, first
  motion must differ) is the pass/fail

PHASE 3+ the ladder, one rung per gate
  distractors -> instances -> relations -> environments; each rung must
  pass its gate AND re-pass all earlier benchmarks
```

North star (unchanged): a natural-language-commanded tabletop manipulator
whose every capability claim is tied to a measured test distribution.
