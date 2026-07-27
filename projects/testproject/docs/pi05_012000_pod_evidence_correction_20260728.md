# CORRECTION: 012000 Did Learn To Grasp - The Local Probes Were The Broken Harness

Last updated: 2026-07-28

This document retracts the model-collapse conclusion of the 2026-07-25 and
2026-07-26 local CPU probes, based on decisive evidence recovered from the
RunPod pod on 2026-07-28.

## 1. The Decisive Evidence

A 003000-vs-012000 offline comparison ALREADY RAN on the pod on 2026-07-22
(after training finished, before the real-arm tests) and was never documented:

```text
/workspace/outputs/offline_compare_focus_003000_vs_012000_20260722/
script: /workspace/testproject/scripts/runpod/pi05_episode29_offline_compare.py
method: official make_pre_post_processors + policy.predict_action_chunk
        (same method as the local probes; no teacher forcing; read-only)
frames: 40 focus-window frames (one per focus episode, t=1.667s)
```

Result on the pod (GPU, training-time environment):

```text
012000, 21 closed-ish frames (recorded first gripper <=30, mean 21.4):
  predicted first gripper mean 24.1, range [12.8, 37.5], MAE 4.41
012000, 19 mid frames (recorded 30-45, mean 34.7):
  predicted mean 34.0, MAE 3.14
correlation(recorded, predicted) first gripper: 0.826

003000 on the same frames: gripper MAE 5.76 / corr 0.812
012000 beat 003000 on every joint (e.g. wrist_flex MAE 7.1 vs 12.3).
```

Meaning:

```text
012000 predicts close when the demo closes, tracks the gripper value with
r=0.83, reproduces grasp posture, and is BETTER than 003000. The model
learned. Training was working.
```

## 2. What Was Wrong With The Local Probes

The local laptop probes (2026-07-25 rebuilt-pipeline probe and 2026-07-26
saved-pipeline probe) showed total collapse to the dataset median (~41
predicted everywhere). That result was an artifact of the local replay
environment, not a property of the checkpoint.

Environment forensics:

```text
same on both sides: transformers 5.5.4, dataset, checkpoint, method
different: LEROBOT CODE VERSION
  pod:    upstream e40b58a8 (training-time code; registers
          "relative_actions_processor"; runs the checkpoint correctly)
  laptop: much newer tree (rename to "delta_actions_processor" plus other
          pi05/processor changes; runs the checkpoint as input-blind garbage)
also different (untested as the cause): GPU bf16 vs CPU float32,
  torch 2.11.0+cu128 vs 2.10.0+cpu
```

The failure mode of the broken local replay - input-independent predictions
pinned at the dataset median - is what a flow-matching policy produces when
its conditioning (images/state/text) is corrupted somewhere in the newer
code path. The exact breaking change has not been isolated.

Lesson recorded for all future offline gates:

```text
A checkpoint must be replayed with the code version that trained it, or the
replay harness must first pass a control (predict on frames where the right
answer is known AND a second checkpoint or known-good environment agrees).
"The pipeline loaded without errors and the stats match" is NOT sufficient
validation - the 2026-07-26 probe passed both checks and was still wrong.
```

## 3. Additional Facts Recovered From The Pod

```text
Training loss log survived: /workspace/logs/pi05_orange49_focus_bs4_from003000_restart_012000_20260722_061701.log
Speed: ~1.4 s/step; the 12000-step run took ~4h50m on the RTX 3090.

LR schedule was AUTO-SCALED by LeRobot: warmup 1000->400, decay 30000->12000.
The run was a complete 12k schedule, not a 30k schedule stopped early. The
under-training argument from the 2026-07-27 plan is therefore weaker than
stated (and moot, given the model demonstrably learned).

Pod migration broke /workspace/venv312: its python symlinks point to a uv
interpreter under /root that no longer exists (system python is now 3.11).
Repair when needed: install uv, `uv python install 3.12.13`, which restores
the exact interpreter path; site-packages on /workspace are intact.

Pod state: RTX 3090, ~92 GB of the 100 GB volume used, balance was ~$1.53
at $0.50/hr. All checkpoints intact: restart run 003000/006000/009000/012000/last,
plus the expert 003000 baseline.
```

## 4. What This Changes

```text
RETRACTED: "012000 collapsed / did not learn" (July 25 + 26 probe docs)
ON HOLD:   the retrain plan (pi05_training_investigation_retrain_plan_20260727.md)
           - no evidence the model needs more training
BACK ON:   live deployment mismatch as the leading explanation for the two
           real-arm failures:
             start pose / start gripper state
             camera geometry vs training views
             camera key mapping (top/front/wrist) in the live client
             timing/latency and chunk switching
           plus on-distribution vs live distribution shift (the model tracks
           training frames; live states drift off-distribution and it may
           not recover)
```

## 5. The Next Decisive Experiment

The traces recorded the LIVE observations the policy server received. So:

```text
Feed the recorded trace observations (not dataset frames) through 012000 on
the pod, in the training-time environment, and compare with the chunks the
server returned live.

If offline(trace obs) == live chunks: the model behaved deterministically on
  its inputs; the live inputs themselves were the problem -> compare trace
  images/state geometry against training frames (camera mapping, start pose).
If offline(trace obs) != live chunks: the live serving path altered
  something -> inspect the policy server's processing.
```

This isolates deployment questions with zero robot movement and modest GPU
minutes.

## 6. Bookkeeping

```text
The 2026-07-26 probe doc and the 2026-07-27 retrain plan carry correction
notices pointing here. Local artifacts under
offline_compare_012000_focus_20260726_cpu_probe2_v2/ are kept as a record of
the broken-harness output, clearly labeled by the correction notice in the
probe doc. Pod July 22 comparison CSVs were copied to the local scratchpad
for analysis; the authoritative copies remain on the pod.
```
