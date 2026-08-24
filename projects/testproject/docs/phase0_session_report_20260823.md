# Phase 0 Session Report — 2026-08-23

Runbook executed with one unplanned discovery that voided half the grid and
became the session's most valuable result.

## Conditions
Link 371-388 ms (known-good envelope), RTC timing verified identical to the
9/10 set (periods 172-238 ms, rtt ~321, starvation 1-2). Server
orange_pick_baseline_v1 (frozen this session, commit 00a44cc4). No hardware
faults.

## Finding 1 — DISTRACTOR SENSITIVITY IS NEAR ZERO (accidental, decisive)
The five region marks were made with white tape. Result: 0/5 task
completions (2 meanders, 1 runaway, 2 freezes) - while GRASPS stayed 5/5.
Tape removed: the very next trial (C2) completed in textbook style (grasp
7 s, carry 6.5 s, release +36, home). Four small novel objects in view
take the carry from ~90% to 0% while leaving grasping intact. The carry
decision reads the whole scene; grasping reads the orange.
Consequences: (a) eval tables must contain NOTHING the demos didn't;
(b) ladder rung L4 (distractors) is measured: catastrophic, needs demos;
(c) the plate is safe only because Phase 1 trains it into the scene.

## Finding 2 — THE WORKSPACE IS A ONE-SIDED CORRIDOR
Operator-right regions D and E (camera-left, positive-pan): 0/3, zero
grasps. In every miss the policy searched NEGATIVE pan - D1 -54..-7,
D2 -57..-7, E1 -76..-8 - the side the demos lived on, while the orange
sat in plain view on the other side. Not a vision failure (orange clearly
in frame): the policy has NO trained approach toward positive pan. Its
lost-behaviour is a habitual negative sweep (same signature as R7).
Meanwhile the far NEGATIVE edge (region A, even outside the placement
cluster) grasped 2/2, because it lies along the habitual sweep.

## Finding 3 — today's carries drift LEFT
A1 meander to -35, A2 runaway to -106, C3 drift to -57, D/E hunts to
-56/-76. The 9/10 day's carries went RIGHT (+36..+49) or released near
centre. Cause unknown (stochastic share vs something session-linked);
logged, not explained.

## Baseline status (clean-table trials only)
C: C2 COMPLETE (textbook), C3 grasp + left-drift release at -57 (orange
end position unconfirmed). D: 0/2. E: 0/1.
The centre-anchor baseline roughly holds on tiny n; the full 15-trial
gate was consumed by the tape discovery. Verdict: baseline NOT regressed
(C2 + timing evidence), grid INCOMPLETE by design change, corridor mapped.

## Implications folded into the program
1. Runbook amendment: marks must be invisible to the camera; NO novel
   objects on the table at eval time. (This session's own lesson.)
2. PHASE 1 DEMO DESIGN CHANGE (important): pickups must cover the D/E
   side and both edges - the plate round now fixes the corridor AND
   teaches the plate. (CORRECTION: blocks were NOT updated when this
   line was written; the real update landed in the runbook 2026-08-24
   rev 2 with measured camera-x bands. Gap flagged by the operator.)
3. The 15-trial baseline grid re-runs properly at the START of the next
   session (invisible marks, ~40 min) before plate demos.

## Trial index
tape condition: p0_A1 A2 B1 B2 C1 (void as baseline; distractor data)
clean condition: p0_C2 C3 D1 D2 E1
traces/frames: laptop ~/trace_p0_*.jsonl, ~/run_frames_p0_*

---

## POST-SESSION RE-ANALYSIS (same day) — Finding 1 RETRACTED

Measured every trial's actual orange position from the front-camera start
frame (tight HSV mask, detector visually verified against the frames).

```text
9/10-day placements (all 10):   camera x 183-369, y 248-324   TIGHT CLUSTER
today:  A1 551  A2 551  B1 447  B2 451  C1 347  C2 341
        C3  61  D1 182  D2 182  E1  59
```

EIGHT of ten trials today sat OUTSIDE the training cluster; only C1 and C2
were inside it. That reframes everything:

1. RETRACTION — "distractor sensitivity is near zero" is WITHDRAWN as a
   conclusion. The tape claim rests on exactly one in-distribution pair:
   C1 (tape, froze) vs C2 (clean, completed). n=1 vs n=1 is not evidence;
   I called it decisive and that was wrong. Tape remains a live hypothesis,
   untested.
2. THE DOMINANT VARIABLE IS PLACEMENT. Performance tracks distance from the
   trained cluster, not tape: inside it 1/2 completed; outside it 0/8.
3. THE ASYMMETRY IS REAL AND SURVIVES. High-x side (operator LEFT: A,B,
   x 447-551): 4/4 GRASPED, 0/4 carried. Low-x side (operator RIGHT: D,E
   and the mislabeled C3, x 59-182): 1/5 grasped. So the policy can still
   SEE and GRAB well outside its zone on one side, and cannot even approach
   on the other. Note r10 completed from x=183 - the low-x edge is not
   categorically unreachable, so this is a gradient, not a wall.
4. REGION LABELS DRIFTED MID-SESSION. The trial called "C3" was measured at
   x=61 - i.e. in E territory, not C. Labels were operator-reported and
   unverified at the time. Future sessions: the agent measures and reports
   the actual position from the start frame BEFORE the run is scored.

### What still stands from the original report
- The baseline is not regressed: C2, the one clean in-distribution trial,
  completed in textbook form with timing identical to the 9/10 day.
- Scene/setup unchanged vs the 9/10 day (camera shift 8 px, brightness
  100 -> 104, arm base within 9 px).
- Phase 1 demo design change stands, and is now better justified: demos
  must cover BOTH sides and a wider placement range, because the trained
  cluster is provably narrow (x 183-369 of a 640 px view).

### Corrected next-session protocol
1. Agent measures orange position from the start frame and states it
   before scoring; trials outside a declared band are labeled as such.
2. The tape question, if we want it answered, needs its own controlled
   test: 3 trials at the SAME in-cluster position with tape, 3 without.
   Cheap, and it settles a real ladder rung (L4 distractors).
3. The 15-trial baseline grid must use positions INSIDE the trained
   cluster to measure the baseline, plus deliberate outside positions
   labeled as generalization probes - not mixed silently.
