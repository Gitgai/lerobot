# N1.6 robustness campaign — how much can the scene change before it breaks?

Date: 2026-08-06. Status: **battery 1 DONE, battery 2 RUNNING, battery 3 QUEUED.**
User's call, and the right one: *more sim testing before hardware; don't rush.*

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

### Battery 2 — pending

### Battery 3 — pending

*(fill in as they complete; each battery ends with "[batteryN] complete" in
/home/kiran/sim/n16_batteryN.log)*

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
