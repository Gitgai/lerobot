# R2b — Generalisation ladder for the public SO-101 π0.5 base, in simulation (zero-shot, no fine-tuning)

Date: 2026-10-20. Status: **running** (orange scored run in progress; cube and toy-table queued; MuJoCo rungs being set up).
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
  nexus PickLift, PickAndPlace, StackCube, Touch → results_mj_*.jsonl / results_nexus_*.jsonl, log sim_mujoco.log.

## Outputs
results/so101_base_sim_test_20261020/results_<tag>.jsonl per rung (tags: corpusA, oursB, liftcube, toytable, mj_pickplace,
nexus_<task>), frames_scored/, and a ladder table in this doc when all rungs are in.
