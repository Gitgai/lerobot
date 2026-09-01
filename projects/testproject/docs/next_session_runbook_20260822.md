# Next-Session Runbook — Phase 0 + Plate Pilot

One page. Follow top to bottom. Agent-side steps are marked [NJ]; operator
steps are marked [rig]. Program reference: so101_generalization_program_20260822.md
(read the addendum, not the body, if in doubt).

## 0. Pre-flight (before ANY counted trial)

```text
[NJ]  link check: 3 timed payload calls. median <600 ms = proceed.
      choked = postpone the session, nothing else is trustworthy.
[rig] arm plugged, orange ready.
[NJ]  arm connects cleanly (goto rest). ONE bus fault = retry once.
      TWO consecutive faults = STOP, reseat/replace the power brick.
[NJ]  freeze (first session only): tag checkpoint n16_real79_side/
      checkpoint-10000 as orange_pick_baseline_v1 with its full config:
      RTC on, jpeg 92, /dev/video0 front + Pi wrist, instruction string,
      commit hash. Never overwrite.
```

## 1. Baseline grid — 15 trials (~40 min at the rig)

```text
[rig] mark 5 orange positions with pencil/tape:
        A far-left EDGE of trained region   B left   C centre
        D right   E far-right EDGE
[both] 3 trials per region, A..E, the usual loop:
        reset to rest -> place orange on the marked region -> go ->
        score from trace -> operator confirms where the orange ended
[NJ]  score: full-task success AND grasp/lift, per region.
```

Gate (per addendum A6/A7): 13+/15 clean = green, proceed any time.
11-12/15 = extend +10 trials before judging. <11 = stop; re-check link,
power, camera aim vs references, THEN compare configs.

Bonus if time (+10 min): 5 trials, regions B-D, with a DIFFERENT orange
= instance probe. Score separately.

## 1b. Plate visibility check (~10 min, BEFORE recording anything)

Added 2026-08-24 at operator request. Recording 20 demos around a target the
cameras cannot see would waste the session AND the 3 h training that follows.

```text
[rig] put the plate at 3-4 candidate spots, one at a time, across the
      intended drop area
[NJ]  at each spot: capture the front camera, and drive the arm to the
      release pose to capture the WRIST view as it would look mid-place
[NJ]  PASS = plate clearly in the front frame at every spot, not hidden
      behind the arm, and visible in the wrist view at the release pose.
      FAIL = move the plate area (or the camera) and re-check before
      any recording.
```

## 2. Plate pilot — 20 demos (~45 min at the rig, separate session is fine)

```text
[rig] one plate, high visual contrast, placed on the table.
[rig] record 20 teleop demos with the leader arm:
        pick the orange -> place it ON the plate -> release -> retreat
      RULES (addendum A3/A4 - non-negotiable):
        cameras: front = laptop /dev/video0, wrist = Pi (deployment set)
        sentence: ONE exact string for all demos (decided at recording,
                  recorded in the log, reused verbatim at serving)
        vary BOTH orange and plate positions per the block table:
          ORANGE POSITIONS - measured design (rev 2026-08-24; replaces the
          original qualitative blocks). Grounded in the Phase 0 finding that
          the trained cluster is only camera-x 183-369 of a 640 px view:
             8 demos  x 183-369  familiar band ....... protect what works
             8 demos  x  60-183  operator's RIGHT .... THE MEASURED GAP
                                 (1/5 grasps there, 2026-08-23)
             4 demos  x 369-500  operator's LEFT ..... grasps work there,
                                 the CARRY does not
          PLATE: vary its position within every group - never park it in one
          spot, or the policy learns a fixed drop point, not a target.
          The agent measures each demo's actual orange camera-x from its
          first frame and reports coverage before the full set is recorded.
        smooth confident motion; abort+redo a hesitant demo
[NJ]  inspect ALL 20 (frames, sync, coverage, grasp quality) BEFORE
      any further recording. Verdict: clean -> plan the 60-80 full set
      with 5-10 held-out combos; not clean -> fix protocol, re-pilot.
      FULL SET keeps the pilot's proportions: ~40% familiar band,
      ~40% operator-right, ~20% operator-left.
```

ONE-VARIABLE NOTE: this round deliberately teaches TWO things (the plate,
and a wider pickup zone) because operator recording time is the scarce
resource and both ride in one session. The rule is preserved in EVALUATION,
not in the data: orange-pick trials measure whether the zone widened; plate
trials measure whether the target was learned. Never report a single blended
success number for this checkpoint - it would be uninterpretable.

```text
```

## 2b. Early arm check of plate-v1 (added 2026-08-26, operator chose this)

Off the written order: we trained on the 20-demo pilot rather than waiting for
the full 60-80. This 10-run check is the same "verify cheaply before scaling"
logic the pilot itself used - 30 min of arm time can redirect two recording
sessions.

```text
checkpoint  n16_plate_v1/checkpoint-6000   (regression gate passed:
            held-out orange error 2.50 vs 2.41 baseline)
instruction "pick up the orange and place it on the plate"  (byte-exact,
            the string the plate demos were recorded with)
runtime     --rtc=true, jpeg 92, ports resolved by SERIAL, arms NOT on USB 3-1
scene       plate in its validated position, one orange, nothing else

TWO SEPARATE SCORES, never blended:
  A) grasp    - did it pick the orange up? Which band was the orange in?
                the right-side band is the open question (baseline: ~1/5 there)
  B) place    - did the orange end ON the plate? carried toward it at all?
```

Decision after 10 runs:
- grasps improve on the right AND some plate-seeking -> record the full 60-80
- grasps improve, no plate-seeking -> plate needs more/better demos; consider
  whether the plate is visible enough at release (section 1b found it is)
- no improvement anywhere -> stop and diagnose before recording more

## 2c. Current bench state and what unblocks it (2026-09-01)

The 10-run check in 2b has NOT happened yet. plate_v1 has exactly ONE honest
arm trial - it grasped in 9 s with a firm grip and did not carry. Every other
trial ran with a frozen wrist camera and measures nothing.

```text
BLOCKER   the OV5647 wrist ribbon dies under arm vibration. It has frozen
          mid-session twice and cost five trials. A replacement RIBBON is the
          cheap fix - same sensor, so the policy sees the world it learned.

READY     arm on USB 3-2 (never 3-1, which is faulty)
          ESP32 wrist camera works but changes the images - adopt only when
          re-recording, see docs/plate_v2_and_hardware_20260901.md
          client guard still TODO: abort a run when wrist frame age > ~1 s
```

WHEN RECORDING THE FULL 60-80 SET, TWO CHANGES:
  1. HOLD 5-10 PLATE DEMOS OUT of training. Without a held-out plate set,
     "did the plate skill improve?" cannot be answered offline at all - which
     is exactly the wall plate_v2 hit.
  2. Switch to the ESP32 wrist camera at that session, not before. The demos
     and the camera then match, and the ribbon problem retires permanently.

## 3. What happens after (no operator needed)

```text
[NJ] dataset conversion + validation (existing v3.0->v2.1 pipeline)
[NJ] training: FROM orange_pick_baseline_v1, old 79 demos MIXED IN
     (addendum A5), ~3 h GPU
[NJ] offline probe on held-out combos -> B0 regression check
[both] next session: 20-30 plate trials incl. held-out positions
```

## Opportunistic (any good link window, ~10 min)

Brain B RTC runs 2-3: plug C270, aim overhead (agent verifies vs July
blend), 2 runs, server swap handled by agent. Closes tempo-vs-camera.

## Session log

Every counted trial gets: trace file, frames dir, region label, operator
outcome confirmation. The agent commits the session record same-day.
