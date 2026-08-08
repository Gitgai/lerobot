# N1.6 REAL-MIMIC sim battery — decompose the real-arm failure before fine-tuning

Date: 2026-08-08. Status: **PLANNED — runs tonight after the Pi0.5 eval frees
the GPU.** User's proposal: recreate the real rig's appearance *inside* the
simulator and re-test N1.6, so "domain gap" stops being one blob of an
explanation and becomes named ingredients.

Context docs: `REALARM_RESULT_20260808.md` (the failure this decomposes),
`n16_robustness_campaign_20260806.md` (method + the n>=3 rule this battery
inherits), `sim_to_real_preflight_protocol_20260806.md`.

---

## 0. The question

On the real arm N1.6 produced coherent motion with ZERO object-directedness.
The run-2 evidence frames (logs/realarm_frames_run2_20260808/) show exactly
what it saw, and three *content* differences stand out against the sim scene:

```text
1. FRUIT COLOR    the real fruit reads tomato-RED, not sim-orange - and the
                  robustness campaign proved the policy keys on "saturated
                  orange blob". This is aimed at its one known trigger feature.
2. SCENE SURFACES dark wood-grain table vs sim kitchen counter; patterned
                  paper plate vs sim ceramic plate; sockets/cables/pole around.
3. CAMERA POSE    real mount close-but-not-identical; sim says 2 cm free,
                  5 cm degrades - real mount + different lens could exceed it.
```

This battery re-creates each ingredient in sim, one at a time and then all at
once, and measures what each one costs N1.6 in its own renderer.

## 1. What this CAN and CANNOT prove — read before results exist

```text
CAN   name which CONTENT ingredient hurts (color? table? camera?), sized in
      oranges-placed at n>=3; derisk the post-fine-tune hardware test by
      fixing cheap physical factors (fruit choice, mount, table covering).
CANNOT prove transfer would have worked. Sim-rendered "tomato red" is still
      renderer pixels. Passing EVERYTHING here does not clear the real
      camera's sensor statistics - the fine-tune on real data proceeds
      REGARDLESS of this battery's outcome. Diagnostic, not a gate.
```

## 2. The battery — 5 conditions x 3 seeds = 15 runs, ~6-7 h

All via `scripts/sim_policy_eval_instrumented.py`, policy `gr00t-n16` on
:5556, 3,000 steps, seeds 1001/1002/1003, scoring = placements + lifts +
DROPS (standing rule). Every flag below already exists and is committed;
prim names verified (`Orange001..003`, `Plate`, `Robot`,
`counter_main_main_group`).

```text
condition   flags                                              mimics
tomatoRed   --tint="Orange001:0.75,0.15,0.10;Orange002:0.75,   the real fruit's
              0.15,0.10;Orange003:0.75,0.15,0.10"              tomato-red color
woodTable   --tint="counter_main_main_group:0.35,0.22,0.12"    dark wood-grain
                                                               desk
paperPlate  --tint="Plate:0.92,0.90,0.88"                      white paper plate
camOff      --jitter-camera=0.05,0.02,-0.03 --rotate-camera=5  imperfect real
                                                               mount + tilt
REALMIMIC   all four of the above combined                     the closest sim
                                                               can get to the
                                                               run-2 photo
```

Color values were eyeballed from the run-2 evidence frames; they need to be
*in the direction of* the real rig, not exact — the test is whether the
policy's features survive the shift, not colorimetry.

## 3. Decision rules — agreed BEFORE results, so we don't rationalize

```text
tomatoRed craters (<50% vs 94% baseline)
    -> color IS a contributor. Hardware action: use a truly orange fruit or
       an orange ball probe in the post-fine-tune test, so "can't see red
       fruit" and "can't see real pixels" are separated by design.
woodTable / paperPlate crater
    -> surface content matters; consider a lighter table covering for the rig.
camOff craters
    -> re-mount and re-measure the real camera before the next hardware run.
REALMIMIC ~fine (>=70%) while real arm was 0%
    -> content is NOT the blocker; the gap is renderer-vs-sensor statistics.
       Only real training pixels fix that. Fine-tune justified, scene fine.
ALL conditions ~fine
    -> same conclusion as above, stated with n>=3 evidence instead of belief.
```

Per the campaign's lesson: **no verdict at n=1**; dramatic single-run results
flip at n>=3.

## 4. Execution order (tonight)

```text
1. Pi0.5 corrected eval finishes (seeds truncate ~step 1500 by recorder OOM
   while the 18.4 GB Pi0.5 server is resident - partials are scorable).
2. Score + record Pi0.5 partial table in pi05_active_work_tracker.md.
3. STOP the Pi0.5 policy server (frees 18.4 GB; also removes the OOM cause).
4. START N1.6 server: N16_REBUILD_RUNBOOK.md section 3 (port 5556).
5. Regression gate: ONE canonical run first (seed 1001, no flags). Expect
   ~3/3 with <=3 drops. If not, fix serving before burning 15 runs.
6. Launch scripts/n16_realmimic_battery.sh (to be written from the table
   above, same pattern as n16_robustness_battery3_appearance.sh).
7. Morning: score, fill section 5 below, update REALARM_RESULT_20260808.md
   ("why" section) and PLAN_real_arm_via_gr00t_20260806.md.
8. Proceed to the N1.6 real-data fine-tune EITHER WAY (section 1).
```

GPU note: N1.6 server (8.2 GB) + Isaac Sim eval coexist fine — that's the
configuration every prior battery ran in. The OOM only appeared with the
Pi0.5 server resident.

## 5. RESULTS (fill after runs; verdicts only at n>=3)

```text
condition   runs            total    verdict
canonical   _/3             baseline gate: expect ~94% reference
tomatoRed   _/3 _/3 _/3     _/9
woodTable   _/3 _/3 _/3     _/9
paperPlate  _/3 _/3 _/3     _/9
camOff      _/3 _/3 _/3     _/9
REALMIMIC   _/3 _/3 _/3     _/9
```
