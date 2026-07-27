# Pi05 Live Deployment Mismatch Investigation Plan

Last updated: 2026-07-28

Active plan. Supersedes the retrain plan (on hold) and the offline comparison
plan (answered). Evidence basis:

```text
projects/testproject/docs/pi05_012000_pod_evidence_correction_20260728.md
```

## 1. The Question

```text
012000 predicts close/hold/lift correctly on training-style focus frames
(pod evidence, gripper corr 0.83, better than 003000 on every joint).
The same checkpoint failed twice on the real arm:
  trace 230756: no strong close at all near the orange
  trace 233341: strong close only at t=0-84 (too early), open near the orange
Why does a model that grasps correctly offline fail live?
```

Candidate explanations, in current likelihood order:

```text
A. Live observations differ from training observations
   (camera geometry/angles, camera key mapping top/front/wrist, image
   resolution/format, start pose, start gripper state)
B. Live state drifts off-distribution and the policy cannot recover
   (compounding error: small early deviations lead to states never seen in
   the 89 training episodes)
C. Live serving path alters observations or actions
   (policy server processing, chunk switching, timing/latency)
```

## 2. Phase 0 - Pod Prerequisites

```text
1. Repair the migrated venv (interpreter died with the old container):
     install uv on the pod, then: uv python install 3.12.13
     verify: /workspace/venv312/bin/python -V  -> 3.12.13
     (site-packages on /workspace are intact; do NOT reinstall packages)
2. Do NOT update /workspace/lerobot. It is the training-era code (e40b58a8)
   and the only environment proven to replay this checkpoint correctly.
3. Disk cleanup per user decision 2026-07-28: keep only restart 009000 and
   012000 checkpoints on the pod; expert 003000 archived to the laptop at
   projects/testproject/artifacts/checkpoints/pi05_orange49_plus_grasp_focus_expert/003000/;
   logs and compare outputs archived at
   projects/testproject/artifacts/pod_archive_20260728/.
4. Pod costs $0.50/hr while running. Stop it between work sessions;
   /workspace persists.
```

## 3. Phase 1 - Trace Replay (the decisive experiment, no robot)

The two failure traces recorded the observations the live policy server
received. Replay them through 012000 on the pod, in the training-era
environment, and compare with the chunks the server returned live.

```text
inputs: projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_230756
        projects/testproject/artifacts/traces/official_async_3cam_012000_trace_20260722_233341
        (upload the observation payloads to the pod)
method: for each traced observation, run the saved pre/post processors +
        predict_action_chunk with 012000, same as the July 22 comparison
        script; compare with the live-returned chunk stored in the trace
```

Interpretation:

```text
offline(trace obs) == live chunks (within sampling noise):
  -> the model answered its inputs faithfully; the INPUTS are the problem
  -> go to Phase 2 (input comparison)

offline(trace obs) != live chunks:
  -> the live serving path altered something
  -> inspect policy server processing, versions, dtype, chunk handling (C)
```

Secondary check in the same run: for trace observations near the orange,
does 012000 predict close when given those images? If it never closes on
live images but closes on training images, the images differ in a way that
matters (strong evidence for A).

## 4. Phase 2 - Input Comparison (laptop, free)

Compare traced live observations against training frames, feature by feature:

```text
images:
  camera key mapping: does live "top" look like training "top", etc.
    (a swapped top/front mapping would explain a lot and is cheap to check)
  geometry: camera positions/angles/crops vs training views
  format: resolution, color order, exposure
state:
  start gripper state: live vs training start (~40-55 open expected)
  full start pose vector vs training episode starts
  wrist_flex trajectory divergence point: when does live state leave the
    training distribution? (earlier analysis: live wrist_flex ~-1 vs demo ~91)
task:
  exact task string equality between live client and dataset
timing:
  observation->chunk->execution latency; how many actions execute per chunk
  before a new chunk arrives (fresh-obs rate vs training fps)
```

Output: a table of concrete mismatches, each marked fixable-by-setup vs
needs-data/training.

## 5. Phase 3 - Corrected Live Re-Test (only after Phases 1-2)

One real-arm run fixing every mismatch found, under the standing gates:

```text
official LeRobot async, three cameras (top /dev/video0, front /dev/video2,
wrist /dev/video6 via Pi bridge), robot.max_relative_target=null, read-only
trace enabled, arm in original-episode start pose, gripper visibly open
(first observed gripper state ~40-55)
```

If it still fails with verified-matching inputs, the remaining explanation is
distribution drift (B) - then the fix IS training-side (e.g., more varied
demos, noise-augmented starts), and the retrain plan comes off hold with a
different goal than "train longer".

## 6. Side Track (optional, laptop): Fix Local Replay

The laptop cannot currently gate checkpoints (newer lerobot code breaks this
checkpoint's replay). Two options, low priority:

```text
1. Pin a laptop venv to lerobot e40b58a8 for replay/gating only.
2. Bisect upstream between e40b58a8 and current main to find the breaking
   change; report upstream if it is a real backward-compat bug.
```

Until fixed, all offline gating runs on the pod, in the training-era env.

## 7. Standing Rules (unchanged)

```text
No real-arm runs before Phases 1-2 produce findings, unless the user
explicitly approves a diagnostic run.
No 2-camera evaluations as clean results.
Official LeRobot defaults; no custom movement scripts without approval.
No committing artifacts; no tokens anywhere.
```
