# Plate Demo Pilot — session record, 2026-08-25

20 usable demonstrations of "pick up the orange and place it on the plate".
Dataset: `~/plate_demos` on the arm laptop (LeRobot v3.0, h264).

## Coverage — measured from each demo's first frame, never from labels

```text
MIDDLE          (camera-x 183-369)   9   target 8   done
operator-RIGHT  (camera-x  60-183)   7   target 8   one short
operator-LEFT   (camera-x 369-500)   4   target 4   done
```

## Pipeline defects found and fixed (each would have wasted a session)

1. `lerobot-record` unusable — 14 packages missing from the venv. Installed;
   arm and policy client re-verified afterwards, no regressions.
2. Default video codec is AV1, which this machine CANNOT DECODE. Forced
   `--dataset.vcodec=h264`, matching what the training pipeline consumes.
3. The HTTP wrist camera is invisible to `lerobot-record`. Fixed by
   `record_wrapper.py`, which imports `http_camera` and the opencv config
   before draccus parses the command line.
4. `--resume` requires an explicit `--dataset.root`; without it each run
   creates a NEW timestamped dataset. Demo 1 was orphaned this way.
5. PORTS ARE NOT STABLE. A dropout renumbers /dev/ttyACM*, so a hard-coded
   port either fails or SILENTLY ADDRESSES THE WRONG ARM. `arm_ports.py`
   resolves both by serial (follower 5B14114209, leader 5B14029688).
6. Auto-retry-on-failure REMOVED. It re-recorded while the operator was still
   resetting and — because a crash can leave the orange IN the gripper —
   produced an episode showing "holding" from frame 0 (ep 6). It passed every
   check except the first-hold test. One attempt per go now.

## Per-demo verification (`scripts/realarm/status.py`)

Every episode is checked for a real grasp (fingers blocked >30 frames), that
the grasp starts mid-episode rather than carried over from a crashed attempt,
and the orange's measured band. Rejected this session: 2 where the gripper
never closed below 30, 1 already-holding.

## The hardware fault — diagnosed

Two days of intermittent "EMI" dropouts traced to ONE FAULTY USB SOCKET.

```text
kernel: usb usb3-port1: disabled by hub (EMI?)
        15 re-enumerations on port 3-1, ZERO on port 3-3
```

Decisive evidence: the arms swapped sockets mid-session and THE FAULT FOLLOWED
THE PORT, not the arm. Before: leader on 3-1 dropped. After: follower on 3-1
dropped. Fix: both arms moved to 3-2 and 3-3 — two clean recordings
immediately, having lost roughly one attempt in three beforehand.
**DO NOT USE PORT 3-1.**

## Housekeeping

The NJ disk hit 100% (1.8 TB) mid-session. Freed 220 GB by deleting the
intermediate checkpoints (1000-9000) of both A/B runs; `checkpoint-10000` of
each was kept, and `orange_pick_baseline_v1` was verified readable afterwards
(1106 tensors). Training saves every 1000 steps — prune intermediates once a
run's analysis is finished.

## Next

- optionally 1 more operator-RIGHT demo to complete that band
- expand to 60-80 demos, proportions ~40/40/20, per the runbook
- convert v3.0 -> v2.1, then fine-tune from `orange_pick_baseline_v1` WITH the
  old 79 orange demos mixed in (anti-forgetting, program addendum A5)
- evaluate orange-pick and plate SEPARATELY; never one blended number

## Pipeline smoke test — PASSED (same day)

Purpose: prove the chain accepts the new data BEFORE more recording time is
spent. Not an attempt at a usable model.

```text
1 transfer      20 demos, 113 MB, arm laptop -> GPU machine
2 convert       v3.0 -> v2.1, 20 episodes, 14,948 frames
                every video's frame count == its parquet row count
                rejects 1/3/6 dropped as intended
3 merge         + the 79 orange demos = 99 episodes, 51,119 frames
                TWO task strings survive (task 0 orange-move, task 1 plate)
                all video symlinks resolve, global index contiguous
4 train         150 steps from orange_pick_baseline_v1, loss 0.059 -> 0.026,
                exit 0, checkpoint written
5 serve         checkpoint loads; answers BOTH instructions with finite
                16x6 action chunks
```

Two things caught by the guards rather than by luck: the GPU still held the
policy server from arm testing (pre-flight refused to start), and the disk had
to be cleared first. Both are now habits the scripts enforce.

The merged set is the first in this project to contain more than one
instruction - the language channel finally has something to carry.

Scripts: `convert_plate_v30_to_v21.py`, `merge_orange_plus_plate.py`.
The smoke checkpoint was deleted; it has no value beyond this test.
