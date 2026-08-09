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

---

# REVISION 2026-08-09 — reorder before running. Machine rebuilt; plan unchanged since.

Written on kiran-AI90 after the restore, before any condition ran. §2's battery
is sound but its **priority is backwards against our own evidence**, and it
omits the dimension most likely to explain the real-arm failure. Nothing below
deletes §2 — it re-sequences it and adds two phases in front.

## R1. Why the order changes

`n16_robustness_campaign_20260806.md` already measured what this policy
tolerates, and the answer is the opposite of §2's emphasis:

```text
APPEARANCE BARELY MATTERS   blue plate + green robot + 35% light + warm layout,
                            all at once -> still reliably 2/3
  dimLight  (35% light)     3/3, 0 drops, a PERFECT run
  smallOrng (75% size)      3/3, fine

GEOMETRY HURTS
  decoys                    6/9  = 67%
  scattered                 4/9  = 44%   "geometry hurts"
  moved plate               3/9  = 33%   THE WORST CONDITION of the whole suite
```

§2 spends **4 of 5 conditions on appearance** (`tomatoRed`, `woodTable`,
`paperPlate`, and the combined `REALMIMIC`), and only `camOff` touches
geometry. That is the cheap-to-vary dimension, not the load-bearing one.

**And the real rig was a geometry condition.** `REALARM_RESULT_20260808.md`
records the scene as *"plate LEFT, one orange center-right"* — against a
canonical sim scene of three oranges with the plate elsewhere. That is
simultaneously **moved plate** (33%) and **a parked/relocated orange** (44%):
the two worst conditions in the suite, combined, plus an object count the
policy never saw in training.

The observed behaviour fits. Run 1: *"smooth motion from rest, sweep to the
LEFT — the plate side — never toward the orange."* That is what a policy
following a learned spatial prior does when the layout it expects is absent.

## R2. The real failure was CATEGORICAL, not graded — test that first

Every §2 condition measures **degradation** (94% -> some lower number). The
hardware failure was **total**: zero object-directedness, gripper never closed,
no approach at any point. Ingredients that each cost 20-60% do not obviously
compose into 100% failure. Something single-bit may be different.

Run these two before anything else. **2 runs, ~5 minutes**, and either result
is decisive:

```text
bgrSwap     --img-bgr-swap        Channel-order mismatch between the real client's
                                  camera pipeline and training. A saturated ORANGE
                                  blob becomes BLUE. The policy keys on that blob
                                  (robustness campaign). Predicted symptom if true:
                                  coherent motion, never approaches the object -
                                  i.e. EXACTLY the real-arm observation.
obsDelay    --obs-delay=N         Real pipeline latency (rpicam-vid -> proxy ->
                                  HTTP) vs sim's instantaneous obs. Pick N from
                                  measured wire latency, not a guess.
```

If `bgrSwap` reproduces the real-arm signature in sim, that is a far simpler
and more actionable explanation than a domain-gap composite — and it is a
**pipeline bug, fixable**, not a policy limitation.

## R3. Revised execution order

```text
PHASE 0  categorical      bgrSwap, obsDelay                      2 runs   ~5 min
PHASE 1  geometry         realLayout (plate left + single orange),
                          movedPlate, parkedOrange               9 runs   ~20 min
PHASE 2  appearance (§2)  tomatoRed, woodTable, paperPlate       9 runs   ~20 min
PHASE 3  composite        REALMIMIC + camOff, and the winning
                          ingredient(s) from 0-2                 6 runs   ~15 min
```

Stop early if Phase 0 reproduces the signature — Phases 1-3 then become
confirmation, not diagnosis.

**`realLayout` is the condition §2 lacks and the one that most resembles the
real scene.** Build it with `--move-plate` and `--park-oranges` (both exist)
to place the plate LEFT and leave a single orange center-right.

## R4. Corrections to §2's mechanics, verified on the rebuilt machine

```text
port            §2 says :5556. The runbook §3 command and every run on this
                machine used :5555. Either works - match the server.
runtime         "5 conditions x 3 seeds = 15 runs, ~6-7 h" is far too
                pessimistic. Measured: ~2 min per 3,000-step run. The whole
                revised battery above is ~1 h, not overnight.
Pi0.5 OOM       §4 steps 1-3 assume the 18.4 GB Pi0.5 server is resident. It is
                not on this machine. Skip them.
DROPS           §2 says scoring includes drops as a standing rule.
                `phase0_score_sweep.py` DOES NOT COMPUTE DROPS. Either add it or
                state its absence in the results - the campaign's own lesson was
                that "a success RATE without a struggle metric flattered the
                policy."
baseline        Do NOT compare against the 94% reference. On this machine the
                canonical rate is 76% (n=18, SIM_VALIDATION_20260809.md) and
                that gap is itself unresolved. Run fresh canonical seeds in the
                same session as the battery and compare against those.
exit codes      Check them. Three runs died of Isaac Sim graphics crashes this
                session; a crashed run writes no CSV and must not be scored as
                a policy failure. Bound batteries to ~12 runs and rest the GPU.
horizon         --policy_action_horizon is INERT on the gr00t-n16 path. Do not
                vary it and do not report it as a condition.
```

## R5. What this still cannot prove

§1's limit is unchanged and worth repeating against the temptation of a clean
sweep: this can name which ingredient hurts, sized in oranges-placed at n>=3.
It **cannot** prove transfer would have worked. Sim-rendered tomato-red is
still renderer pixels, and passing everything here does not clear the real rig.

The one exception is Phase 0: if `bgrSwap` reproduces the failure signature,
that is not a domain-gap claim at all — it is a testable hypothesis about the
client, checkable directly against the run-2 evidence frames.

---

## R6. PHASE 0 RESULTS — 2026-08-09, kiran-AI90. Categorical hypothesis is DEAD.

Run on the rebuilt machine, one server, one session, 20 s GPU rest between Kit
startups, all four runs `exit=0`.

```text
condition   seed   placed   lifts (cm)          d_grasp min   gripper range
canonical   4001    1/3      0.6   4.2  17.7      2.5 cm      -0.09 .. +0.92
canonical   4002    2/3     14.0   2.0  13.8      2.2 cm      -0.12 .. +0.94
bgrSwap     4001    1/3     19.0  13.3  19.3      1.2 cm      -0.08 .. +0.96
bgrSwap     4002    3/3     17.6  13.5  11.8      1.8 cm      -0.10 .. +0.98

canonical   3/6 = 50%          bgrSwap   4/6 = 67%
```

**`--img-bgr-swap` does not reproduce the real-arm signature.** It does not even
degrade the policy: one swapped run was a full 3/3, the end-effector closed to
**1.2 cm**, and the gripper commanded **+0.96**. The hardware failure was the
opposite — never approached, gripper never closed (range 45-59 where a close is
single digits). Nothing resembling it appears here.

⇒ **Channel order is ruled out.** R2's hypothesis was wrong, and cheaply so:
four runs, twelve minutes.

### The stronger result is the disconfirmation it carries

The policy places oranges **with the colour channels inverted** — orange renders
blue — and barely notices. That is a harder version of the robustness campaign's
"appearance barely matters," and it makes §2's headline condition `tomatoRed`
very unlikely to be the culprit: if a full BGR inversion costs nothing, a
red-versus-orange fruit almost certainly does not either.

⇒ **Phase 2 (appearance) drops further in expected value. Phase 1 (geometry) is
now the main line**, which is where `n16_robustness_campaign_20260806.md`
pointed before any of this: moved plate 33%, scattered 44%, and a real scene
that was both at once plus a single orange where training had three.

### Honesty about this sample

```text
n=2 per condition. bgrSwap scoring HIGHER than canonical is noise, not an
effect - do not report it as one. What n=2 CAN settle is the categorical
question, because the predicted signature was total failure and we observed
normal grasping twice.

The canonical pair scored 3/6 = 50%, against this machine's 76% at n=18. Within
spread at n=2, but a reminder that every condition here is measured against a
noisy baseline - and that the unresolved 76%-vs-94% gap sits underneath all of
it (SIM_VALIDATION_20260809.md).
```

### obsDelay: deliberately not run

R2 lists it, and it stays unrun on purpose. The plan's own instruction is to
pick N from *measured* wire latency; the real rig is disconnected, so the
Raspberry Pi wrist stream and the two-machine hop cannot be measured. An
invented N proves nothing if it shows no effect and is an artifact of the guess
if it does. **Run it when the hardware is back**, with a measured number.
