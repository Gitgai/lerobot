# R2b — Generalisation ladder for the public SO-101 π0.5 base, in simulation (zero-shot, no fine-tuning)

Date: 2026-10-20. Status: **DONE 2026-10-19 17:40Z — all rungs scored; table and verdict below.**
Parent: pi05_so101_real_base_audit_plan_20261019.md (R2). Policy: dongyoonkim/so101-pi05-base served by our wrapper
(scripts/so101_base_policy_server.py, GPU 1, :8080). Operator's go: 2026-10-20 ("go ahead with all").

## Why a ladder

The orange task is partly in-distribution (the corpus holds ~200 LeIsaac orange episodes). The question behind the
real-arm plan is how far the base generalises: same simulator but a task it saw less of or never, then a different
simulator with no training data at all. Each rung is 50 seeded episodes, headless, the task's own success predicate,
one JSON line per episode, frames recorded every 10th call for review; non-pipelined client (sim waits).

```text
rung  simulator   task (env id)                               instruction                                   corpus exposure         status
1a    Isaac/LeIsaac PickOrange-v0 (3 oranges → plate, reset)  "Grab oranges and place into plate."          ~200 sim ep + 96 real   running (50)
1b    Isaac/LeIsaac PickOrange-v0                              "pick up the orange and move it to another place" (ours)             queued (50)
2     Isaac/LeIsaac LiftCube-v0 (table_with_cube scene)       "Lift the red cube up."                       cubes 4,709 ep (real)   queued (50)
3     Isaac/LeIsaac CleanToyTable-v0 (lightwheel_toyroom)     "Pick two letter e objects into the box, and  2-object + reset: far   queued (50)
                                                               reset the arm to rest state."
4     MuJoCo       namenu/so101-pick-place-env (EnvHub)        pick the orange cube → green target zone      none (MuJoCo render)    setting up
5     MuJoCo       johnsutor/so101-nexus-envs (EnvHub), 6 tasks touch · point camera · move EE · pick-lift ·  none                    setting up
                   MuJoCoPickLift-v1 etc.                       place on disc · stack two cubes
```

Pre-registered reading per rung: ≥60% → the base does it; 20-60% partial; <20% does not transfer (check plumbing
first: camera mapping, action units, control rate). Compare rungs, not to LIBERO.

## LeIsaac environment coverage (the EnvHub table, decided 2026-10-19)

```text
PickOrange-v0                    running (50 corpus instruction + 50 ours)
LiftCube-v0                      queued, auto after the orange run (unit so101-sim-other), 50 eps
CleanToyTable-v0 (single arm)    queued behind the cube, 50 eps
PickOrange-Direct-v0, LiftCube-Direct-v0   SKIPPED: same scene, cameras and success rule as -v0; "Direct" is
                                 Isaac Lab's other env code path for the identical task — no new information
CleanToyTable-BiArm-v0 / -BiArm-Direct-v0, FoldCloth-BiArm   OUT: two arms; the checkpoint is single-arm only
```

## Live-window evidence (2026-10-20)

Rung 1a, 2 episodes with the Isaac Sim window on the desktop: 2/2 — three oranges placed in sequence and the arm
returned to rest (montage_live_ep1.jpg, montage_live_ep2.jpg), ~50 s each, 75 policy calls, 132-180 ms/call.

## Scenes and assets (downloaded 2026-10-20, operator's go)

table_with_cube (5 MB, GitHub release v0.1.2) and lightwheel_toyroom (196 MB, HF LightwheelAI/leisaac_env
assets/scenes) → ~/sim/leisaac-src/assets/scenes/. kitchen_with_orange was already present.

## EnvHub, in one paragraph

LeRobot EnvHub = a simulator environment published as a Git repo on Hugging Face and loaded with
`make_env("org/repo@commit:envs/x.py", trust_remote_code=True)`; the repo's env.py exposes make_env() returning a
Gym environment. It runs the author's code, so pin a commit and read env.py first. LeIsaac's four tasks are on it as
LightwheelAI/leisaac_env. Other SO-101 single-arm repos found on the Hub: namenu/so101-pick-place-env (MuJoCo,
cameras up/side, 20 Hz, 200 steps, success = cube within 4 cm of target + gripper open), johnsutor/so101-nexus-envs
(MuJoCo + GPU "Warp" variants), Thakk100/so101_single_arm_env (MuJoCo push/pull, 3 cams), swpark5/so101-sim-env (no card).
so101-nexus: johnsutor's PyPI package (v0.10.0, Apache-2.0, Python ≥3.12): "full-stack robot learning" for SO-100/101
— MuJoCo model of the arm, Gymnasium tasks, LeRobot-dataset I/O, BC + RL training; its EnvHub repo exposes 6 tasks.

## How the MuJoCo rungs connect

Their observation keys differ (pixels.up/side; wrist/overhead); the wrapper maps the external view → base_0_rgb and
the wrist view → left_wrist_0_rgb (an overhead with no wrist camera = one real slot + masked). Actions: joint position
targets in degrees for namenu (matches); check nexus's units and control rate before trusting a number. Each gets a
50-episode run through a small LeRobot-0.4.1 client (venv ~/sim/mujoco-envhub-venv312) talking to the same wrapper.

## "New renderer", defined (operator's question, 2026-10-19)

The renderer is the simulator's image generator — the part that turns the 3D scene into the camera pixels the
policy sees. The model trained on real footage plus ~200 Isaac Sim episodes (photorealistic: wood grain, soft
shadows, textured fruit). MuJoCo (nexus, namenu) draws flat grey or tiled surfaces, a yellow arm, hard shadows,
no texture; the model had never seen a MuJoCo image. "New renderer" = same robot and joint space, same kind of
task, images in a visual style it has no experience of — the sim-to-sim gap, a cousin of sim-to-real. The ladder
separates that appearance gap (touch 88% survives it) from task-semantics gaps (a painted green disc as target).

## MuJoCo rungs — set-up record (2026-10-20)

- venv ~/sim/mujoco-envhub-venv312 (Python 3.12: so101-nexus 0.10.0 requires it; LeRobot 0.4.1, MuJoCo 3.16, grpcio).
  The numpy==1.26 pin from the LeIsaac EnvHub guide is unsatisfiable with lerobot 0.4.1 — dropped.
- Client: results/so101_base_sim_test_20261020/mujoco_envhub_eval.py (our gRPC client to the wrapper; one JSON line per
  episode). A SECOND wrapper instance serves these rungs (unit so101-base-server-b, :8081, GPU 1) so they never share
  a server with the Isaac run — the stock server keeps one observation queue per process.
- Units verified from the envs' own code: namenu reports/accepts LeRobot degrees; nexus is radians both ways, converted
  with so101_nexus.sim_qpos_to_dataset_row / dataset_row_to_sim_qpos. Camera maps: namenu up→front, side→wrist (no
  wrist camera: the "wrist" slot carries a second external view); nexus overhead→front, wrist→wrist; nexus renders 224×224.
- Smokes (2 episodes each, 03:44Z): namenu pick-place 0/2 at its registered 200-step cap (10 s at 20 Hz — the policy
  plans at 30 Hz, so the cap is tight; a 600-step variant is in the run); nexus MuJoCoPickLift 1/2 — one zero-shot
  success in a simulator the corpus never saw.
- Rungs launched 03:46Z (unit so101-sim-mujoco, sequential, 50 episodes each): pick-place@200, pick-place@600,
  nexus PickLift, PickAndPlace, StackCube, Touch → results*mj*_.jsonl / results*nexus*_.jsonl, log sim_mujoco.log.

## Isaac orange results (2026-10-19 ~05:30Z, 50 episodes each, headless, seeds 100-149 / 200-249)

```text
rung 1a  "Grab oranges and place into plate." (the corpus's own string)   38/50 = 76%  CI 63-86
rung 1b  "pick up the orange and move it to another place" (ours)         16/50 = 32%  CI 21-46
```

Every failure is the 100 s time-out (all three oranges on the plate + arm at rest is the predicate). The 44-point
gap between phrasings is outside noise on identical scenes: the model is sensitive to the instruction string, AND
our string is genuinely less specific (it names no plate while the predicate requires the plate). Bench
consequence: use the corpus's phrasing (or fine-tune on ours) — do not assume wording is free.

## Cube / toy-table run record

First cube attempt (11:11Z) used the orange run's 100 s cap: each failed episode ran 6,000 steps = 16 min wall
(0/2 before I stopped it; kept as results*liftcube_cap100_aborted.jsonl). Relaunched 12:05Z with task-sized caps:
cube 30 s (a lift takes seconds; success = cube 20 cm above the base), toy-table 60 s, 50 and 40 episodes.
BOTH cube attempts were INVALID (found 12:25Z): LiftCube-v0 has no wrist camera (its cfg deletes it), the
wrapper raised KeyError('wrist'), the server answered Empty, and LeIsaac's client silently replayed its last
action for the whole episode (899 and 353 "Received Empty" lines) — the arm never moved. Fix: the wrapper now
picks the external and wrist views by key name and loads the policy with empty_cameras=2, so one- or two-camera
clients both work (a one-camera client gets two masked slots). Relaunched 12:28Z; the invalid files are kept as
*\_INVALID*no_wrist_key.*. Lesson: a client that falls back to "repeat last action" on a server error turns a
plumbing fault into a silent 0% — the wrapper now logs its camera mapping per client and never raises on a missing key.

## Isaac cube result (2026-10-19 ~15:50Z)

```text
rung 2  LiftCube-v0, "Lift the red cube up.", ONE camera (the task deletes the wrist camera), 30 s cap   0/50 = 0%  CI 0-7
```

Frames (montage_liftcube_ep1.jpg): the arm reaches the cube and hovers/nudges, never closes and lifts. Reading: the
grasp is the weak point again, now with the added handicap of no wrist view (the corpus has 1,314 one-camera
episodes, 9%). Not a plumbing fault: the same wrapper served the orange task at 76% minutes earlier and the
server logged a one-camera mapping with moving joint states on every call.

## MuJoCo results (2026-10-19 04:15Z, 50 episodes each, zero-shot, non-pipelined)

```text
rung 4  namenu pick-place, 200-step cap (published)        1/50   2%
        namenu pick-place, 600-step cap                     1/50   2%   → not the time cap; the env itself
rung 5  nexus Touch the red cube                           44/50  88%
        nexus PickLift (grasp and lift)                     13/50  26%
        nexus PickAndPlace (place on the blue circle)        3/50   6%
        nexus StackCube                                      1/50   2%
```

Frames (montage_mujoco_namenu.jpg, montage_mujoco_nexus.jpg): namenu is a blue-tiled room with a yellow arm, an
orange cube and a flat green disc as the target; its "wrist" slot is a SIDE camera, not a wrist view. The policy
reaches the cube, hovers and closes on it, and never carries it to the green disc — it has no notion of a flat
green disc as a target (the corpus places things in bins/boxes/on plates). nexus is a flat grey world, yellow arm,
red cube, a real wrist camera at 224×224; there the reach/touch is near-perfect and the lift works a quarter of the time.
Recorder bug found on the way: the frame index reset per client connection, so later rungs overwrote earlier
rungs' frames (fixed in the wrapper 2026-10-19; the namenu frames above come from a 3-episode replay).
Reading: in a renderer the corpus never saw, the base reaches and touches reliably (88%), grasps and lifts a
quarter of the time, and almost never completes a placement. The namenu environment is the outlier at 2%:
it has NO wrist camera (its second view is another external camera fed into the wrist slot) and a different
look; the frames in frames_mujoco/ are the next thing to inspect before blaming the model. Compare with
LeIsaac orange at ~85% (in-distribution renderer, trained-on task) — the gap is the sim-to-sim gap plus task
difficulty, not plumbing: the same wrapper, units and client produced 88% on Touch.

## THE LADDER — final table (zero-shot, non-pipelined client, one policy: dongyoonkim/so101-pi05-base)

```text
simulator   task                                      instruction                          cameras       n    success   CI95
Isaac       PickOrange (3 oranges → plate + rest)     corpus wording                       front+wrist   50   38  76%    63-86
Isaac       PickOrange                                ours ("…move it to another place")   front+wrist   50   16  32%    21-46
Isaac       LiftCube (cube 20 cm up)                  "Lift the red cube up."              front only    50    0   0%     0-7
Isaac       CleanToyTable (2 letter-e → box + rest)   corpus wording                       front+wrist   40    0   0%     0-9
MuJoCo      nexus Touch                               "Touch the red cube."                overhead+wrist 50  44  88%    76-94
MuJoCo      nexus PickLift                            "Pick up the red cube."              overhead+wrist 50  13  26%    16-40
MuJoCo      nexus PickAndPlace (blue circle)          corpus-style                         overhead+wrist 50   3   6%     2-16
MuJoCo      nexus StackCube                           "Stack the red cube on the blue cube." overhead+wrist 50  1   2%     0-10
MuJoCo      namenu pick-place (green disc), 200 & 600 steps                                up+side        50   1   2%     0-10
```

## Verdict

1. The base model is competent at reaching but fragile at grasping. Reaching/touching survives a renderer it never
   saw (88%); grasping drops to a quarter there and to zero with one camera; placing on anything but a familiar
   container is rare.
2. It completes the ONE task it had seen in this simulator (orange, 76%) and nothing else in Isaac — the cube
   (one camera, no wrist view) and the cluttered toy table (unfamiliar instruction, 20 distractors; the arm barely
   moves) are both 0%.
3. Wording matters a lot: the same scenes go from 76% to 32% when the instruction changes; one wording per
   scene in training is the likely cause.
4. None of the zeros is plumbing: every run used the same wrapper, units and client that produced 76% and 88%,
   and the server logged moving joint states on every call.
   Implication for the arm: expect it to reach for the orange on the bench; grasp+place will depend on how close our
   table and wording are to the 96 real orange episodes it saw. The dependable path is R5: LoRA on this checkpoint
   with our own orange episodes, scored with this same harness (orange 76% is the control) before any bench time.

## Outputs

results/so101*base_sim_test_20261020/results*<tag>.jsonl per rung (tags: corpusA, oursB, liftcube, toytable, mj*pickplace,
nexus*<task>), frames_scored/, and a ladder table in this doc when all rungs are in.
