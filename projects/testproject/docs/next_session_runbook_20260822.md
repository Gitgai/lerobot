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
          4 demos short left->right | 4 near->far | 4 centre source,
          varied plate | 4 varied source, centre plate | 4 edge-but-safe
        smooth confident motion; abort+redo a hesitant demo
[NJ]  inspect ALL 20 (frames, sync, coverage, grasp quality) BEFORE
      any further recording. Verdict: clean -> plan the 60-80 full set
      with 5-10 held-out combos; not clean -> fix protocol, re-pilot.
```

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
