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
   teaches the plate. Position blocks updated accordingly.
3. The 15-trial baseline grid re-runs properly at the START of the next
   session (invisible marks, ~40 min) before plate demos.

## Trial index
tape condition: p0_A1 A2 B1 B2 C1 (void as baseline; distractor data)
clean condition: p0_C2 C3 D1 D2 E1
traces/frames: laptop ~/trace_p0_*.jsonl, ~/run_frames_p0_*
