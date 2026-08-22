# N1.6 robustness campaign — how much can the scene change before it breaks?

Date: 2026-08-06 (final update 08-07). Status: **COMPLETE at n>=3.**
User's call, and the right one: _more sim testing before hardware; don't rush._

> **READ SECTION 5 (end of file) FIRST** — the final n>=3 table supersedes every
> intermediate verdict in sections 2-4, and several INVERTED at proper n.

---

## 0. Why this exists — the user caught what the summary hid

The Phase 0 headline was "5/5 runs, 15/15 oranges, stdev 0.00". Watching the
policy live, the user said **"it appears to struggle"** — and re-scoring ALL
12 full-length runs for drops proved them right:

```text
12 runs, canonical scene:
  34/36 oranges placed (94%)      <- not 100%: two runs ended 2/3
  13 drops total = 1.1 PER RUN    <- grasps, loses the orange, retries
  last placement anywhere from step 311 to step 2932
```

**Lesson for how we report:** a success RATE without a struggle metric
flattered the policy. Drops/retries are now scored on every run, alongside
placements and lifts. An impression from the GUI caught what five seeded runs
"with stdev 0.00" did not.

---

## 1. The campaign design — three batteries, easy to hard

All runs: 3,000 steps, same checkpoint (`12e21/gr00t_n1d6_leisaac_pick_orange`),
same server (:5556), same scoring (placements + lifts + DROPS). Sequential,
visible on the desktop. Outputs in `logs/robustness/`.

```text
BATTERY 1 - STABILITY + GEOMETRY (DONE, results below)
  seedA/B/C   fresh seeds, canonical scene      is 94% stable?
  movedA/B/C  ALL oranges shifted 5-10 cm       object perception, layout kept

BATTERY 2 - HARD GEOMETRY (running)
  plate10     plate (the GOAL) moved 10 cm      goal perception; training only
                                                ever varied it +/-3 cm
  scatter     EACH orange moved differently     destroys relative layout
  cam2cm      front camera mount off 2 cm       realistic mounting error
  cam5cm      camera off 5 cm + 3 cm down       sloppy mount
  combo       oranges AND plate both moved      nothing where training put it

BATTERY 3 - APPEARANCE (queued; the user's requested variations)
  bluePlate   plate tinted blue                 goal recognition by color?
  greenArm    THE ROBOT tinted green            self-appearance robustness
  decoys      2 orange-colored spheres added    "an orange" vs "anything orange"
  twoPlates   second identical plate            goal ambiguity (GT tracks only
                                                the original)
  dimLight    lights at 35%                     evening
  warmLight   warm-orange lighting              recolors the ENTIRE scene
  smallOrng   oranges at 75% size               visual + grasp-width change
```

**On "mixed fruits":** no other fruit assets exist locally or in the scene
repo, so literal apples/bananas are not available. The DECOY test is the
sharper version of the same question — same color, same size, wrong object.
Real fruit variety = the S4 scene-diversity work (more LeIsaac scenes), later.

### New difficulty knobs (all in `sim_policy_eval_instrumented.py`, committed)

```text
--move-oranges dx,dy,dz          uniform shift (S1)
--scatter-oranges dx1,dy1,...    per-orange offsets
--move-plate dx,dy,dz            move the goal
--jitter-camera dx,dy,dz         perturb the front camera mount
--tint "Name:r,g,b;..."          recolor any scene entity (Plate, Robot, ...)
                                 binds PreviewSurface stronger-than-descendants
                                 so it overrides the asset's textures
--light-scale f / --light-color r,g,b    global lighting
--add-plate dx,dy                second identical plate
--add-decoys N                   orange-colored spheres near the oranges
--scale-oranges f                object size
Drivers: scripts/n16_robustness_battery{1,2_hard,3_appearance}.sh
```

---

## 2. RESULTS

### Battery 1 — DONE

```text
run        placed  drops  lifts
seedA        3/3     3    [0.14, 0.15, 0.17]
seedB        2/3     2    [0.18, 0.15, 0.18]
seedC        3/3     1    [0.18, 0.16, 0.15]
movedA       2/3     2    [0.18, 0.12, 0.14]
movedB       2/3     1    [0.14, 0.03, 0.16]   <- one orange barely lifted
movedC       3/3     2    [0.17, 0.22, 0.09]

canonical: 8/9 oranges (89%)     moved: 7/9 (78%)
```

Read: **the policy is good but not clean.** It fumbles ~1-2 times per run even
at home, and moving the oranges costs about one orange in nine. Perception is
object-directed (it FINDS moved oranges) but precision suffers.

### Battery 2 — hard geometry (DONE)

```text
run        placed  drops  lifts               read
plate10      2/3     2    [0.19, 0.21, 0.18]  goal moved 10 cm: still finds it
scatter      2/3     1    [0.15, 0.16, 0.11]  layout destroyed: still works
cam2cm       3/3     1    [0.17, 0.15, 0.17]  2 cm mount error: NO degradation
cam5cm       2/3     4    [0.13, 0.14, 0.20]  5 cm: works but FUMBLES (4 drops)
combo        2/3     0    [0.18, 0.04, 0.10]  everything moved: 2/3, no drops
```

### Battery 3 — appearance (DONE)

```text
run        placed  drops  lifts               read
bluePlate    3/3     2    [0.17, 0.13, 0.12]  plate color: does not care
greenArm     3/3     1    [0.14, 0.17, 0.16]  own arm recolored: does not care
decoys       1/3     1    [0.16, 0.00, 0.01]  *** CRATERED - see below ***
twoPlates   CRASHED - script bug in --add-plate ("Accessed schema on invalid
            prim": deepcopying a parse_usd-created scene entity cfg is not a
            valid way to clone one). KNOWN BROKEN, needs a proper fix.
dimLight     3/3     0    [0.17, 0.16, 0.18]  35% light: PERFECT run, 0 drops
warmLight    2/3     2    [0.15, 0.19, 0.16]  scene recolored: minor cost
smallOrng    3/3     2    [0.14, 0.14, 0.13]  75% oranges: fine
```

---

## 2b. THE CAMPAIGN'S THREE FINDINGS

```text
1. APPEARANCE BARELY MATTERS. Blue plate, green robot, 35% lighting, warm
   lighting, small oranges - all essentially unaffected. The policy is NOT
   keying on precise colors or brightness. (dimLight was its cleanest run of
   the entire campaign: 3/3, zero drops, done by step 624.)

2. GEOMETRY COSTS ABOUT ONE ORANGE. Move things - the oranges, the plate, the
   layout, everything at once - and it drops from ~89% to reliably 2/3. It
   still FINDS everything (perception is genuinely object-directed, confirming
   S1), but precision suffers. Camera mounting has real slack: 2 cm is free,
   5 cm works with fumbling.

3. *** DECOYS CRATER IT: 1/3, two oranges NEVER TOUCHED (lifts 0.00/0.01). ***
   Two orange-colored spheres reduced the task's best policy to a third of its
   performance - the single largest effect of ANY variation tested, larger
   than moving every object and the goal simultaneously. It keys on "orange
   blob", not "an orange".
```

### What this decides for hardware (per the pre-agreed rules in section 3)

```text
camera mounting   SLACK EXISTS. 2 cm free, 5 cm degraded-but-functional.
                  Mount carefully but do not obsess.
table cleanliness THE HARD REQUIREMENT. Nothing orange-ish anywhere near the
                  workspace - no clutter, period. This is the one variation
                  that broke it.
room lighting     not a controlled variable; it does not care.
expectations      at HOME it is ~85% with 1.1 drops/run and degrades gracefully
                  except for decoys. On out-of-domain real pixels, the as-is
                  test's realistic goal remains "purposeful reach toward the
                  orange", with task completion a pleasant surprise.
```

---

## 3. What this decides (agreed BEFORE the results, so we don't rationalize)

```text
CAMERA RUNS (cam2cm / cam5cm) -> HOW PRECISELY MUST THE REAL CAMERA BE MOUNTED?
  degrades badly at 2 cm  -> sim-spec mounting is CRITICAL; hardware test waits
                             on a careful mount
  shrugs off 5 cm         -> the rig has slack; mounting is not the long pole

DECOYS -> if it grabs a decoy, it keys on "orange blob", not "an orange".
  Real-table clutter will fool it; the hardware scene must be CLEAN.

LIGHTING -> if dim/warm lighting hurts, the real room's lighting is a variable
  to control, not a detail.

OVERALL DEGRADATION CURVE -> sets EXPECTATIONS for the as-is hardware test.
  A policy at ~85% in its own domain with 1.1 drops/run will NOT be better on
  hardware. If the hard batteries crater it, the as-is test's realistic goal is
  "any purposeful reach", not "task completion".
```

**The hardware test stays parked until this campaign is scored and read.**
That ordering is the user's decision and it stands.

---

## 4. Standing rule this campaign added

> **Report struggle, not just success.** Placements alone flattered this
> policy. Every sim evaluation now reports drops/retries and last-placement
> step alongside the success rate — and when a human watching the GUI disagrees
> with the summary statistics, RE-SCORE before defending the summary.

---

## 5. FINAL n>=3 TABLE (2026-08-07, tour + round 3) — supersedes every number above

```text
condition       runs           total   verdict
decoys          1/3, 2/3, 3/3  6/9=67% moderate - "FATAL" was an n=1 artifact
scattered       2/3, 0/3, 2/3  4/9=44% geometry hurts
moved plate     2/3, 1/3, 0/3  3/9=33% THE WORST CONDITION of the whole suite
moved oranges   class 1-3/3    ~33-60% geometry hurts
appearance      all runs       ~100%   confirmed free at n=2 everywhere
canonical       n=12           94%     the baseline

THE INVERSION: the n=1 campaign said "decoys fatal, geometry ~one orange".
n>=3 says the opposite: decoys moderate, MOVED GOAL worst. Every dramatic n=1
verdict this project produced flipped or softened at n>=3.

RIG SPEC UPDATE (supersedes section 2b priorities):
  1. LAYOUT MATCH is now the TOP requirement: plate left, oranges clustered
     10-15 cm right of it, matching the sim's canonical arrangement.
  2. clean table (nothing orange-ish) - stays, demoted to second
  3. locked white balance - stays (preflight finding, n=1 but mechanism-clear)
  4. camera mounting slack unchanged
```
