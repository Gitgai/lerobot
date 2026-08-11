# Camera alignment: why N1.6 failed on hardware, and how to set the rig up

Date: 2026-08-09, kiran-AI90. Written after comparing the run-2 evidence frames
against sim renders side by side.

Supersedes the appearance-first emphasis of
`n16_realmimic_sim_battery_20260808.md`. That plan asked "which content
ingredient hurts?" This one asks a sharper question the photos forced:
**were the two cameras even pointing at the same thing?**

---

## 0. The finding

The sim and real "front" cameras share a *name* and nothing else.

```text
                 SIM  (what N1.6 trained on)      REAL (what it was given)
mount            Robot/base/front_camera          laptop webcam on the table
position         (0.0, -0.5, 0.6) m from base     ~table level
                 i.e. 0.6 m ABOVE the base
orientation      161 deg about X - steeply DOWN   near-horizontal, across the table
FOV              ~67 deg (focal 28.7 mm,          ~60-70 deg (typical webcam)
                 aperture 38.11 mm)                => NOT a difference. See the
                                                      correction in the execution
                                                      log; an earlier draft said
                                                      40 deg by assuming the
                                                      IsaacLab DEFAULT aperture.
what fills it    the table, edge to edge          wall, power outlet, pole, speaker
```

The wrist pair diverges the same way: sim looks straight down onto the plate,
which fills the frame; the real view is dominated by the robot's own white body
with the plate reduced to a corner patch.

**Why this is worse than a domain gap.** The channel names matched, so nothing
errored anywhere in the stack — the client sent `front`, the policy consumed
`front`. But the policy's `front` input was trained on an elevated downward view
and was handed a table-level horizontal one. Same key, different meaning.

It also explains the *shape* of the hardware failure. `REALARM_RESULT_20260808.md`
records coherent motion with **zero object-directedness** — intact motion priors,
absent visual grounding. That is what a policy does when its observation comes
from a viewpoint its training distribution never contained. And the robustness
campaign already noted the policy is sensitive at **5 cm** of camera
displacement; the real rig differs by tens of centimetres and tens of degrees.

Every condition tested so far came back null (`bgrSwap` 67%, `movedPlate` 67%,
`parkedOrange` 67%, `realLayout` 50%, against canonical 74%) — because all of
them perturb *within* the trained viewpoint. None of them move the camera.

---

## 1. How the real rig SHOULD be set up

Derived from `leisaac/tasks/template/single_arm_env_cfg.py`. **Verify signs by
snapshot rather than trusting this table** — the conventions are `ros` for both
cameras and easy to mirror.

### Front camera

```text
sim config      pos=(0.0, -0.5, 0.6)  rot=(0.165, -0.986, 0, 0)  convention=ros
                focal_length=28.7 mm, horizontal_aperture=38.11 mm  -> ~67 deg

REAL EQUIVALENT
  mount to      the robot BASE, not the table and not a tripod at table level.
                It must move with the robot, because that is what the policy
                learned - the view is base-relative, not world-relative.
                *** This is a separate requirement from pose. A static tripod
                that happens to match the initial framing is still a different
                observation model the moment the robot moves. ***
  height        ~0.60 m above the base plane
  offset        ~0.50 m horizontally from the base
  aim           steeply DOWN at the workspace, roughly 60-70 deg below horizontal
  lens          ~67 deg horizontal FOV. A STOCK LAPTOP WEBCAM IS FINE - it is
                already 60-70 deg. (An earlier draft of this file said to fit a
                ~40 deg lens; that was wrong, and following it would have made
                the mismatch worse.)
  framing test  the table should fill the frame edge to edge. If a wall, a
                socket or a floor is visible, the camera is in the wrong PLACE -
                and at this FOV that means pose, not lens.
```

### Wrist camera

```text
sim config      pos=(-0.001, 0.1, -0.04) on Robot/gripper   focal 36.5 mm (~32 deg)

REAL EQUIVALENT
  mount to      the gripper
  offset        ~0.10 m forward along the gripper axis, ~0.04 m below it
  aim           at the grasp point, so the plate/object dominates the frame
  framing test  the robot's own body should be a MINOR part of the frame. In the
                current rig it fills roughly two thirds - that is the mismatch.
```

### Stream integrity — fix regardless of geometry

Measured over the 143 run-2 wrist frames:

```text
c0059, c0060     mean 1.0, sd 0.0, 5.3 KB   completely BLACK
c0061            mean 40.0                   very dark
19/142           consecutive pairs ~identical -> frozen/duplicate frames
=> ~13% of the wrist stream was dead or stale
```

The front stream was clean by comparison: 0 identical pairs, 68-77 KB
throughout. **A policy fed stale frames is being lied to**, whatever else is
wrong. Fix the `rpicam-vid -> pi_wrist_proxy -> :8092` path before the next
hardware attempt.

### Verification before any policy runs

Photograph the rig from both cameras and compare against a sim render of the
same task. If the two do not look like the same scene from the same viewpoint,
the policy will not transfer, and no amount of fine-tuning fixes a camera mount.

---

## 2. The sim experiment — prove it before touching the robot

**Hypothesis.** If the real camera geometry is recreated in sim, a policy that
places 74% of oranges will fail there too — with the same signature (coherent
motion, no object-directedness).

**Why this is worth doing.** It converts "the domain gap is large" into a
measured, attributable cause, using only GPU time. If sim-with-real-camera fails
while sim-with-sim-camera works, camera placement is established as *sufficient*
to cause the failure.

### Method: match by snapshot, not by arithmetic

Camera extrinsics cannot be derived from a photograph without calibration. So:

```text
1. port --snapshot-dir / --snapshot-at from sim_harness_positive_control.py
   into sim_policy_eval_instrumented.py   (it exists only in the former)
2. iterate --jitter-camera / --rotate-camera / --camera-fov until the sim
   render resembles logs/realarm_frames_run2_20260808/c0000_front.jpg
3. do the same for the wrist against c0000_wrist.jpg
4. freeze those values as the condition `realCam`
```

Both flags apply as **unclamped additive offsets**, so any magnitude works
today:

```python
cam.offset.pos = (old[0]+dx, old[1]+dy, old[2]+dz)   # no limit
q_new = q_old * q_delta                               # any angle
```

Starting point for the front camera, to be refined visually: bring it down
~0.55 m and rotate toward horizontal — `--jitter-camera=0,0,-0.55
--rotate-camera=<70..90>`.

### The variation ladder

Run each at n=3 as a screen; follow up anything that moves at n=12. Canonical on
this machine is **74% (n=22, 2.23 oranges/run, sd 0.97)** — that is the
comparator, not G485's 94%, which is out of scope.

```text
level  condition      change                                   expectation
0      canonical      none                                     ~74%  (control)
1      camHeight      front camera lowered in 4 steps:         find the cliff
                      -0.15 / -0.30 / -0.45 / -0.55 m
2      camPitch       front rotated 15 / 30 / 45 / 70 deg      find the cliff
3      camFOV         40 -> 50 -> 65 deg                       webcam framing
4      wristPose      wrist translated AND rotated toward
                      the real framing                          never tested before
5      realCam        front + wrist together, snapshot-matched  THE prediction
6      realCam+drop   plus 13% frame staleness                  adds the stream bug
7      realFull       realCam + single fruit + measured tints   closest analogue
                      + dimming + jpeg
```

Levels 1-3 are the valuable ones: they produce a **tolerance curve** — how far
the camera can move before this policy breaks. That number is directly useful
when mounting the real camera, and nobody has it.

### Code needed — small, mirroring what exists

```text
--rotate-wrist-camera   ~10 lines, copy of --rotate-camera   (wrist can only
                        be translated today; the real difference is angular)
--camera-fov            ~2 lines, set cam.spawn.focal_length
--frame-drop            ~15 lines, hold the previous obs for a fraction of steps
--snapshot-dir          port from the positive control
```

Not reachable by any flag: **background clutter** (wall, socket, pole). That is
scene geometry, not a camera parameter, and needs USD assets added to
`kitchen_with_orange`. Given the wide real FOV, a large share of the policy's
input *was* background — so this may matter, and it is the one item that cannot
be screened cheaply.

---

## 3. What this can and cannot establish

```text
CAN   show camera geometry is SUFFICIENT to destroy performance in sim, and
      quantify how much displacement this policy tolerates.
CAN   give the rig a concrete mounting spec with a pass/fail framing test.

CANNOT prove geometry was the ONLY cause on hardware. Other real-world factors
      (real pixels, dynamics, the stale wrist stream) remain uncontrolled.
CANNOT prove that fixing the camera makes N1.6 work on the arm. Matching the
      viewpoint removes one specific, large, measured discrepancy; sim-rendered
      pixels are still not real pixels - the caveat from
      n16_realmimic_sim_battery_20260808.md section 1 stands unchanged.
```

**The honest framing of the user's hypothesis** — *"with the correct hardware
setup like in sim, N1.6 may work on hardware"* — is that it is a **reasonable
and now testable prediction**, promoted from speculation by the evidence above,
but not yet a conclusion. The sim experiment can make it much more or much less
likely before any hardware time is spent, which is precisely why it should run
first.

---

## 4. Status of the earlier battery

Stopped mid-run on 2026-08-09 in favour of this line. Banked and resumable:

```text
realLayout 12 · movedPlate 12 · parkedOrange 12 · camOff 12 · woodTable 12
scattered 10 · tomatoRed 11 · paperPlate 5 · REALMIMIC 0
```

Those results stand and should be scored — but note every one of them perturbs
*within* the trained viewpoint, which is why they were all null. `camOff` is the
closest to this line and moved the camera by only 5 cm and 5 deg.

---

# EXECUTION LOG — 2026-08-09/10, kiran-AI90

## CORRECTION: FOV was never a mismatch. Position and pitch are.

§0 of this document claimed sim's front camera is ~40 deg against a webcam's
~65 deg. **That was wrong.** It assumed IsaacLab's *default* 20.955 mm aperture.
`single_arm_env_cfg.py` sets it explicitly:

```python
front:  focal_length=28.7,  horizontal_aperture=38.11   # comment: "For a 78 deg FOV"
wrist:  focal_length=36.5,  horizontal_aperture=36.83   # comment: "For a 75 deg FOV"
```

⇒ sim front is **~67 deg** (78 deg on the square-image basis the comment uses),
squarely in laptop-webcam range. **Strike FOV from the list of differences.**

What survives, and it is the large part:

```text
position   sim (0.0, -0.5, 0.6) m from the robot base   vs   webcam at table level
pitch      161 deg about X, steeply DOWN                vs   near-horizontal
mount      moves WITH the robot base                    vs   static on the table
```

The mount point matters independently of pose: the policy learned a
**base-relative** view. A tripod that does not move with the robot is a
different observation model even if the initial framing matches.

## Flags implemented in `sim_policy_eval_instrumented.py`

```text
--rotate-wrist-camera N   pitch the WRIST about its local X. It could previously
                          only be TRANSLATED; the real wrist differs in ANGLE.
                          Mirrors the existing --rotate-camera quaternion compose.
--camera-fov D            front FOV in degrees -> focal_length, computed against
--wrist-fov  D            the cfg's OWN horizontal_aperture (do NOT hardcode
                          20.955 - that is the bug that produced the wrong 40 deg)
--snapshot-dir / --snapshot-at
                          ported verbatim from sim_harness_positive_control.py.
                          This is the only way to match a sim view to a photo:
                          extrinsics cannot be derived from an image without
                          calibration, so you iterate and look.
```

NOT implemented: `--frame-drop` (for the ~13% stale wrist stream). It touches
the observation path rather than config, and the staleness hypothesis is
independent of geometry — keep the two changes separable.

## The snapshot sweep — what each configuration looks like

Six 120-step runs, snapshot at step 60, saved to `logs/camshots/`. Pictures were
the goal, not scores.

```text
A_baseline    (unmodified)                                    what N1.6 trained on
B_fov65       --camera-fov=65                                 ~no visible change
C_low         --jitter-camera=0,0,-0.45                       lowered, still pitched down
D_low_pitch   --jitter-camera=0,0,-0.45 --rotate-camera=45    *** CLOSEST MATCH ***
E_realcam     --jitter-camera=0,0,-0.55 --rotate-camera=70    overshoots - too low,
                                                              objects loom
F_realboth    E + --rotate-wrist-camera=-35 --wrist-fov=55    front overshoots as E
```

**The `realCam` condition, for reuse:**

```bash
--jitter-camera=0,0,-0.45 --rotate-camera=45
```

Judged against `logs/realarm_frames_run2_20260808/c0000_front.jpg`: both show the
table receding, objects at natural scale, the robot standing behind, plate left,
and background above the table edge. The baseline shows none of that.

## Limits of this match — read before quoting any result from it

```text
VISUAL, NOT CALIBRATED   D means "looks like the photo", not "is the photo". No
                         measurement of the real mount exists. When the rig is
                         reconnected, MEASURE the mount and redo this properly.
NO BACKGROUND            sim has no wall, socket, pole or speaker. In the real
                         frame those occupy a large share of a ~67 deg view.
                         Not reachable by any flag - it is scene geometry.
WRIST NOT MATCHED YET    F pitched the wrist -35 deg but the front overshot in
                         the same run, so the wrist match is unvalidated.
```

## Status and the next measurement

```text
DONE     flags implemented; sweep captured; realCam flag string identified
NEXT     realCam at n=12 vs canonical 74% (n=22, 2.23 oranges/run, sd 0.97)
         -> this is STEP 1 of the training-trigger decision tree in
            sim_to_real_preflight_protocol_20260806.md
```

Reminder of what that measurement decides, because it is the whole point:

```text
realCam CRATERS  -> H1 supported. The hardware failure was an out-of-distribution
                    observation. Fix the mount; retest hardware. NO training yet.
realCam HOLDS    -> H1 refuted. Geometry alone is not sufficient; H2 is live and
                    training IS justified, with the sweep telling you what to
                    randomise over.
```

---

# STEP 1 RESULT — 2026-08-10. Geometry is a LARGE factor but does NOT explain the hardware failure.

Step 1 of the training-trigger decision tree
(`sim_to_real_preflight_protocol_20260806.md`). Ran on kiran-AI90, one server,
one session. 18 runs, 3,000 steps each, all `exit=0` (one retry after a
SIGKILL).

## Design

**12 realCam + 6 canonical, INTERLEAVED 2:1** — realCam, realCam, canonical,
repeated six times, seeds 7001-7052.

The canonical arm is not redundant with the pooled n=22 baseline. It controls
for *session* effects — GPU state, server instance, thermal drift. Running all
of one arm then all of the other would put any drift entirely on the second
half, where it would masquerade as the effect. Interleaving splits it evenly.

```text
realCam = --jitter-camera=0,0,-0.45 --rotate-camera=45
```

Verified applied, from the run log — flags silently not taking effect is a real
failure mode here (`--policy_action_horizon` is inert on this path and nobody
noticed for two batteries):

```text
[eval] jittered front camera: (0.0, -0.5, 0.6) -> (0.0, -0.5, 0.15)
[eval] front camera pitched 45.0 deg
```

## Result

```text
                 n     placed        mean/run    sd
canonical        6     16/18 = 89%   2.67        0.52
realCam         12     16/36 = 44%   1.33        0.98

drop 1.33 oranges/run   SE 0.35   t = 3.77   ~1.4 within-condition SDs
per-run realCam:  [2,1,2,2,0,2,0,2,1,3,1,0]
per-run canonical:[3,3,2,2,3,3]
```

**Moving the camera to the real rig's viewpoint HALVES performance.** That is a
solid, significant effect, and it confirms viewpoint matters a great deal.

## But the failure SIGNATURE does not match the hardware

```text
                       sim realCam                real arm (REALARM_RESULT_20260808)
approaches the object  YES - d_grasp 0.4-3.8 cm   NO - never approached
gripper closes         YES - up to +1.14          NO - stayed 45-59 (a close is
                                                      single digits)
lifts                  YES - up to 18.1 cm        NO
places                 44% of oranges             ZERO, across two runs
```

Under real-rig geometry the policy still reaches, grasps, lifts and places -
placing on **9 of 12 runs**, including one full 3/3. The arm showed **zero
object-directedness for an entire run, twice**.

⇒ These are **different failure modes, not different severities of the same
one.**

## Verdict — neither branch of the decision tree, which is more useful

```text
H1 PARTIALLY SUPPORTED   viewpoint is a genuine, large contributor. The mounting
                         spec in section 1 stands and is worth acting on.
                         But it is NOT SUFFICIENT to produce what the arm did.

H2 STILL LIVE            something beyond camera geometry is also acting.

=> TRAINING IS STILL NOT JUSTIFIED. Two known, mechanically fixable defects
   remain in the observation channel. Fine-tuning now aims at a channel that is
   still broken in at least two measurable ways.
```

### The remaining candidates, now narrower and rankable

```text
1. STALE WRIST STREAM   ~13% of run-2 wrist frames dead or stale (two fully
                        black, 19/142 consecutive pairs identical). Untested in
                        sim - needs --frame-drop, not yet implemented.
2. EXPOSURE / CONTRAST  the rig ran "WB locked, exposure AUTO" against this
                        protocol's own hard requirement to lock BOTH. Stage B
                        measured gamma 1.35 -> 0/3 placed, the worst run of the
                        entire preflight, and the run-2 frames measure at mean
                        brightness 100/255. THE CLOSEST KNOWN ANALOGUE TO A
                        TOTAL FAILURE.
3. MISSING BACKGROUND   sim has no wall, socket, pole or speaker; they occupy a
                        large share of the real ~67 deg frame. No flag reaches
                        this - it is scene geometry.
4. REAL PIXELS          the irreducible remainder.
```

Candidate 2 deserves priority: it is the only tested condition that ever
produced a **total** failure in sim, and the rig demonstrably half-complied with
the rule written to prevent it.

## Incidental

This session's canonical scored **89%** against the pooled 74% (n=22). Same
server, same session, six runs. That makes the 44% contrast cleaner, and
suggests the pooled figure is dragged down by runs taken under worse GPU
conditions - which is an argument for always pairing a condition with
same-session canonical runs rather than comparing against a stored number.

---

# COMBINATION TEST — 2026-08-11. Both rig defects together STILL do not reproduce the failure.

Step 1 showed camera geometry halves performance but the policy keeps grasping.
`gamma135` (Stage B, G485, n=1) scored 0/3 but also kept grasping. The rig had
**both** defects at once — wrong camera pose AND exposure left on auto. Does the
combination produce the perception failure the arm showed?

24 runs, three arms interleaved so session drift hits all equally. One run hung
(exit 124) and retried clean.

## Result

```text
                 n     placed          mean   sd     vs canonical
canonical        6     16/18 =  89%    2.67   0.52       —
gammaOnly        6     11/18 =  61%    1.83   0.98    -0.83   t=1.84
comboRG         12     17/36 =  47%    1.42   1.00    -1.25   t=3.51
realCam (Step 1) 12    16/36 =  44%    1.33   0.98    -1.34   t=3.77

per-run canonical  [3,3,2,3,3,2]
per-run gammaOnly  [0,3,2,2,2,2]
per-run comboRG    [0,1,1,2,1,3,3,2,2,0,1,1]
```

**The combination is no worse than the camera alone** — 47% vs 44%, well inside
noise. Camera geometry dominates; adding a washed-out image on top adds nothing
measurable. Not the interaction that was hypothesised.

## Answer to the question: NO

```text
                     approach       gripper      lifts    places
comboRG              1.1 cm         +1.14        yes      47%
gammaOnly            0.5 cm         +1.16        yes      61%
realCam              0.4-3.8 cm     +1.14        yes      44%
REAL ARM             never          never        no       0
```

Four sim conditions now degrade performance substantially and **not one
reproduces the hardware signature.** Every simulated failure is a COMPLETION
failure — the policy sees the orange, reaches it, grasps it, and mishandles the
task. The arm's failure was a PERCEPTION failure: it never engaged the object
at all.

⇒ Something about that rig is still not modelled. The two untested candidates
are also the two that are hard to test:

```text
STALE WRIST FEED    ~13% of run-2 frames dead or frozen. Needs --frame-drop,
                    deliberately not implemented (touches the obs path).
BACKGROUND CLUTTER  wall, socket, pole, speaker fill much of the real ~67 deg
                    view. NO FLAG CAN PRODUCE THIS - it is scene geometry and
                    needs USD assets added to kitchen_with_orange.
```

## CORRECTION to a standing rig requirement

`sim_to_real_preflight_protocol_20260806.md` Stage B recorded `gamma135` = 0/3,
called it *"the one hardware-gap killer"*, and wrote a hard rig requirement on
that basis. **That was n=1.**

At n=6 here, gamma scores **61% (mean 1.83)** with one zero run, and does not
clear significance against canonical (t=1.84). The single 0/3 on G485 looks like
an unlucky draw from a wide distribution, not a reliable kill switch.

The requirement to lock auto-exposure and auto-white-balance is still worth
keeping — it costs nothing and the effect is real if not fatal. But it should
not be described as *the* killer, and the exposure-left-on-auto violation on the
2026-08-08 rig is **not** a sufficient explanation for that failure.

## Unresolved: the physics instability

`comboRG` produced a **106 cm "lift"** — an orange displaced further than the
table is tall. Same signature as `gate_seed2004` (56 cm) and
`p1_movedPlate_5001` (157 cm); roughly **6% of runs** across the session.

Those runs are not scoring the policy at all. Cause unknown. Any rate computed
without excluding them is contaminated, and nobody has looked at why it happens.

## Method note worth keeping

One run hung rather than crashed (`exit=124`, the `timeout` firing) and burned
its full 50-minute budget before the retry logic could act. **The harness was
hardened against crashes, which are loud and fast, but not against hangs, which
are silent and slow.** A healthy 3,000-step run takes ~2.5 minutes; the 3000 s
timeout was inherited without thought and is ~20x too generous. Use ~600 s.

---

# STATE OF THE INVESTIGATION — 2026-08-11. Read this first.

## The question

Did the 2026-08-08 hardware failure happen because the RIG was set up wrong, or
because sim-to-real transfer genuinely does not work for this policy? The two
answers demand opposite responses — fix a camera mount, or spend months on new
training — so guessing is expensive in both directions.

## Answer so far: partly the rig, and the rest is not yet explained

**Camera geometry is a real, measured factor.** Recreating the rig's viewpoint
in sim halves performance: canonical 89% -> realCam 44%, t = 3.77. A hardware
mounting spec derived from the sim config is in §1, with a pass/fail framing
test.

**But no sim condition reproduces the hardware failure.** Every condition
tested, scored the same way, against a pooled canonical of 79% (n=34):

```text
condition               n     placed    mean   approach   gripper
canonical (pooled)     34   81/102  79%    2.38     0.6 cm    +1.15
movedPlate             15    32/45  71%    2.13     0.4 cm    +1.08
parkedOrange*          15    10/15  67%    0.67     0.9 cm    +0.97
bgrSwap                 2     4/6   67%    2.00     1.2 cm    +0.98
camOff (5cm/5deg)      12    23/36  64%    1.92     1.1 cm    +1.15
realLayout*            14     9/14  64%    0.64     1.1 cm    +1.11
woodTable              12    22/36  61%    1.83     0.6 cm    +1.10
gammaOnly               6    11/18  61%    1.83     0.5 cm    +1.16
paperPlate              5     9/15  60%    1.80     0.6 cm    +1.06
tomatoRed              11    18/33  55%    1.64     1.0 cm    +1.13
realCam+gamma          12    17/36  47%    1.42     1.1 cm    +1.14
realCam                12    16/36  44%    1.33     0.4 cm    +1.14
scattered              10    12/30  40%    1.20     0.5 cm    +1.10

* parked conditions are scored out of 1 orange, not 3
```

**Look at the last two columns.** In every single condition the policy still
approaches to within ~1 cm and closes the gripper past +0.97. On the arm it
never approached at all and the gripper never left 45-59.

```text
ALL SIM FAILURES     completion failures - sees the orange, mishandles the task
THE HARDWARE FAILURE a perception failure - never engaged the object
```

⇒ The rig defects cost roughly half the success rate and are worth fixing on
their own merits. **They do not explain 2026-08-08.** Something about that setup
is still unmodelled.

## Consequently: NO TRAINING IS JUSTIFIED YET

Written into `sim_to_real_preflight_protocol_20260806.md` as a standing rule,
with Stage 0 (observation *equivalence*, not just robustness) and the decision
tree for when a training run is warranted. Two known, mechanically fixable
defects still sit in the observation channel; training now aims at a channel
that is broken in at least two measurable ways.

## Open — the two remaining candidates both need real work

```text
STALE WRIST FEED     ~13% of run-2 wrist frames dead or frozen (two fully black,
                     19/142 consecutive pairs identical). Needs --frame-drop
                     written - it touches the observation path, not config.
                     EFFORT: ~15 lines + one battery.

BACKGROUND CLUTTER   wall, socket, pole, speaker fill much of the real ~67 deg
                     view; sim has none of it. NO FLAG CAN REACH THIS - it is
                     scene geometry and needs USD assets added to
                     kitchen_with_orange.
                     EFFORT: real asset work. This is the expensive one, and it
                     is also the only untested candidate that could plausibly
                     cause a PERCEPTION failure rather than a completion one.
```

## Open — one unexplained defect that contaminates every rate above

A **physics instability** fires in roughly **6% of runs**, producing impossible
displacements: 106 cm in `cb_comboRG`, 157 cm in `p1_movedPlate_5001`, 56 cm in
`gate_seed2004`, against a task whose real lifts top out near 20 cm. Those runs
are not scoring the policy at all. Cause unknown, nobody has looked. **Any rate
in this document that does not exclude them is contaminated by ~6%.**

## Also open — the project work that never depended on any of this

The **N1.6 fine-tune on the 89 real-arm episodes**. Data restored, and it needs
no simulator. `REALARM_RESULT_20260808.md` called it "the strongest option, armed
for exactly this moment".

⚠ **2026-08-11 correction: "the 32 GB training ceiling already broken with
`adamw_bnb_8bit`" is NOT currently supported.** `bitsandbytes` is absent from
every venv on this machine and from the uv cache, so that result cannot be
reproduced or confirmed — see the note at the head of
`REALARM_RESULT_20260808.md`. **This does not block the N1.6 fine-tune** (N1.6 is
~1.09B against π0.5's 4.14B, a different memory problem), but the ceiling should
be treated as re-openable rather than broken until STEP −1 of
`pi05_full_finetune_on_5090_plan_20260811.md` settles whether 8-bit optimizer
states work on this Blackwell card at all.

Note it also sidesteps the entire question above: training on real data from
this table, this arm, these cameras does not require sim and real to correspond.

---

# NON-CAMERA FACTORS — 2026-08-11. One ruled out by inspection, one still live.

The investigation treated cameras as the frontier because that is where the
measurable effect was. Four non-camera factors had never been examined. Checked
here; results below.

## RULED OUT — state units in the real-arm client

**Hypothesis.** Hours earlier we found a units bug in the sim corpus (actions in
radians, state in motor units, ~57x). The real client passes robot state
straight through with no conversion:

```python
state = np.array([obs[k] for k in self.robot_state_keys], dtype=np.float32)
model_obs["state"] = {"single_arm": state[:5], "gripper": state[5:6]}
```

If the arm's units disagreed with the policy's, its proprioception would be
nonsense — and a policy that cannot locate itself would never reach for
anything while its motion priors kept producing smooth trajectories. That is
the PERCEPTION-failure signature no camera condition reproduced.

**Checked.** The client reads LeRobot `so_follower` keys
(`shoulder_pan.pos` … `gripper.pos`). The checkpoint's own
`statistics.json`, `new_embodiment` entry — the embodiment tag the server is
launched with — expects:

```text
state.single_arm   min [-66.95, -99.35, -100.07, -7.24, -14.35]
                   max [ 54.98,  94.01,   99.92, 100.18,  49.99]
state.gripper      min [1.42]   max [72.83]
```

i.e. roughly **-100..100 for the arm and 0..100 for the gripper** — LeRobot's
normalised motor convention (`RANGE_M100_100` / `RANGE_0_100`), which is exactly
what `.pos` returns. **The ranges agree. No conversion is missing.**

⇒ Not the cause. Recorded so it is not re-chased.

## STILL LIVE — the language instruction was never tested

GR00T is instruction-conditioned; the string goes into the model as
`annotation.human.task_description`.

```text
REAL ARM   "Grab orange and place into plate"
           (n16_realarm_client.py:184, the client default)
SIM        "Pick three oranges and put them into the plate, then reset the arm
           to rest state."   (the env's cfg.task_description)
```

**Every sim condition in this document used the env string. The hardware run
used a different one. That difference has never been tested.**

The two differ in object count (one vs three), verb, and the trailing reset
clause. `sim_policy_eval_instrumented.py` already exposes
`--policy_language_instruction`, and its help text warns to override it only
for a deliberate instruction experiment — which this is.

```text
TEST   realInstr : --policy_language_instruction="Grab orange and place into plate"
       n=12 against same-session canonical. ~45 min, one flag, no code.
```

This is the cheapest untested candidate remaining and the only one that needs
neither new code nor USD assets.

## NOT YET CHECKED

```text
CAMERA->CHANNEL MAP   the client sends camera_keys = ["front","wrist"]. WHICH
                      physical device fed "front" on 2026-08-08 is taken from a
                      doc line, not from the run's own config. The dataset
                      carries THREE cameras (front/top/wrist) against a policy
                      that takes two, so a mapping decision exists somewhere and
                      is not written down.
INITIAL POSE          sim resets to a defined rest pose; the real arm's starting
                      configuration was never compared against it.
RESOLUTION / PREPROC  sim TiledCamera render size vs the client's 640x480, and
                      whatever resize/normalise happens between. Stage A checked
                      channel order and layout; normalisation is not recorded as
                      checked.
CHUNK TIMING          the real loop's execution rate vs sim's. --obs-delay=2 was
                      free in Stage B, but that tested staleness, not rate.
```

## Priority after this

```text
1. realInstr           one flag, 45 min, no code                    <- do first
2. camera->channel map free, read the run's config not the prose
3. --frame-drop        ~15 lines, tests the 13% stale wrist feed
4. background clutter  USD assets; expensive, and still the only candidate that
                       could plausibly cause a PERCEPTION failure
```
