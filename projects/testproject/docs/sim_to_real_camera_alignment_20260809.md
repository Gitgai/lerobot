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

---

# THE LINK — 2026-08-11. The investigation had the topology wrong.

**The GPU is in New Jersey. The arm is in Pune. Every policy call crosses
~12,000 km.** I read `192.168.194.x` as a LAN; it is a ZeroTier overlay. Every
sim condition in this document was designed against an assumed local link.

This reframes the whole investigation, and it explains the thing that has been
unexplained for three days: *why all 13 sim conditions failed to reproduce the
hardware signature.*

## Why sim CANNOT reproduce a latency failure, by construction

```text
SIM   the client steps the environment. When the policy call takes 1 s, the
      world does not advance - physics, objects and cameras all pause with it.
      Serving latency is INVISIBLE. It costs wall clock, never task time.

REAL  the world keeps running. The arm sits frozen mid-reach for the whole
      round trip while gravity, the object and the cameras carry on.
```

No `--obs-delay` value fixes this. That flag makes observations *stale*; it
cannot make the arm *stop*. The two are different failures, and the one the
hardware has is the one sim structurally cannot show.

Stage B's `--obs-delay=2` was 67 ms at 30 Hz. Against a round trip of ~1 s that
is **15x too small** — which is why it came back "free".

## What the code actually does — verified, not inferred

```python
model_obs["video"] = {k: obs[k] for k in self.camera_keys}   # raw uint8 arrays
np.save(output, obj, allow_pickle=False)                     # NO compression
...
action_horizon: int = 8
for action_dict in actions[: cfg.action_horizon]:            # 8 of 16 executed
    robot.send_action(action_dict)
    time.sleep(1.0 / 30 - (toc - tic))                       # 30 Hz
```

* **1.76 MiB per policy call**, uncompressed, NJ↔Pune, every call.
* **8 actions execute = 267 ms of motion**, then the loop blocks on the next call.
* **Half of every chunk is discarded.** The policy plans 16 steps; 8 run.

Duty cycle as a function of round trip:

```text
    RTT     moving    frozen
   0.1 s     72.7%     27.3%
   0.3 s     47.1%     52.9%
   1.0 s     21.1%     78.9%      <- the pi0.5-measured regime
   2.0 s     11.8%     88.2%
```

## This rig has failed this exact way before, and it was solved

`agent_handoff_pi05_20260803.md`, ERA 3 (Jul 29–Aug 1), on **this same link**:

> "The arm moved too fast: latency ate ~60% of each 50-action chunk, so the
> client fast-forwarded through the remainder... RTC_ENABLE=1 with
> RTC_EXEC_HORIZON=35 (default 10 is too small — horizon must exceed the
> ~30-step latency) produced the first grasp -> lift -> CARRY."

and earlier:

> "JPEG-compressed observations (2.77 MB -> ~190 KB, 14.6x; the bottleneck was
> gRPC over the SSH tunnel, ~2 MB/s, NOT the uplink)"

**~30 steps of latency and a ~2 MB/s tunnel were MEASURED on this rig.** At
2 MB/s, N1.6's 1.76 MiB payload is ~0.92 s of upload alone.

Does the N1.6 client carry any of the mitigations that made π0.5 work?

```text
  RTC                    ABSENT
  chunk_size_threshold   ABSENT
  JPEG / compression     ABSENT
  async / decoupled obs  ABSENT
```

**None of them.** The N1.6 real-arm client was written as if the server were
local. π0.5 needed all four to grasp anything over this link.

⇒ A policy stopping every 267 ms for ~1 s, acting on truncated chunks, would
produce *coherent motion that never converges on the object* — the Aug 8
signature — and would do it regardless of camera geometry.

## NOT MEASURED — do this first, it is one command

The round trip has **never been measured**. Everything above is anchored on the
π0.5 numbers, not on N1.6's own. Pune was unreachable on 2026-08-11 (100% loss,
"No route to host"), so it could not be taken then.

```text
T0  measure RTT + payload time from the ARM machine, n=50 calls.
    Gates everything else. Until this exists the duty-cycle row is an estimate.
T1  JPEG the observations (14.6x on pi0.5). ~10 lines.
T2  action_horizon 8 -> 16, or RTC. Stop discarding half of every chunk.
T3  re-run the arm with T1+T2. If it engages, the link was the cause.
```

## Camera blur / autofocus / exposure — the other thing sim cannot render

Sim renders a pinhole camera: perfectly sharp, noise-free, fixed focus, fixed
exposure, no rolling shutter, no compression. **Every condition in this document
compared geometry between a pristine render and a real sensor**, and never
compared image *quality* at all.

The client's own docstring already lists this as rig spec priority (2):

> "(2) LOCK white balance+exposure (v4l2-ctl)"

**Whether that was done on Aug 8 is not recorded anywhere.** And autofocus is
not mentioned in any document — the wrist camera is a Raspberry Pi module on a
*moving arm*; if AF is enabled it hunts on every move.

There is a nasty interaction with the duty cycle above: the client captures its
observation **immediately after the 8-step motion burst** — i.e. at the moment
of maximum motion blur and maximum AF hunt, then freezes for the round trip.

```text
T4  read back the actual v4l2 controls on both cameras: focus_auto,
    white_balance_temperature_auto, exposure_auto, exposure_absolute.
    Free, no robot motion needed. Records what Aug 8 could not tell us.
T5  sharpness on the captured frames: variance-of-Laplacian per frame across a
    run. Blurred frames are measurable after the fact from evidence JPEGs the
    client already writes (c%04d_{front,wrist}.jpg).
T6  sim degradation battery: gaussian blur / exposure shift / JPEG artifacts on
    the render before it reaches the policy. This is the FIRST condition class
    that could plausibly cause a PERCEPTION failure rather than a completion one.
```

## Revised priority

```text
1. T0 measure the round trip          gates everything, one command
2. T4 read back v4l2 controls         free, answers a 3-day-old unknown
3. T1+T2 JPEG + full chunk            ~10 lines, mirrors the pi0.5 fix
4. T5 sharpness on existing frames    free, uses evidence already on disk
5. realInstr (language string)        one flag, still untested
6. T6 sim degradation battery         new code
7. background clutter                 USD assets, expensive
```

Camera geometry remains a real measured effect (89%→44%). It is no longer the
leading explanation for Aug 8.

---

# B9-B12 — recreating the artifacts, 2026-08-11

Correction to the previous section: image quality was **not** untested. B2 noise,
B3 blur, B4 JPEG and B5 gamma already existed, and noise/gamma/bgrSwap were run.
What is missing is not the axis, it is the **shape**: B2-B5 are static and
per-run constant, and every real artifact on this rig is motion-coupled.

The mount asymmetry that makes `--img-blur` wrong twice over:

```text
wrist_camera  prim_path .../Robot/gripper   MOVES with the arm
front_camera  prim_path .../Robot/base      STATIC
```

`--img-blur 3` is isotropic, whole-frame, both cameras, constant. So it blurs the
static camera's static table (never happens) and fails to blur the wrist camera
harder when the arm moves fast (always happens).

```text
B9   --img-motion-blur MS       EXPOSURE TIME. Smear length computed from the
                                camera's MEASURED per-step motion, directional,
                                zero for a camera that did not move.
B10  --img-af-hunt t,max,decay  defocus RAMPS on motion, decays when settled.
B11  --img-ae-lag ALPHA         first-order exposure lag; gamma is a fixed shift.
B12  --policy-stall K           the world advances K steps with NO fresh action.
```

Verified smear for the wrist camera (f_px = 640·36.5/36.83 = 634, from the cfg's
own aperture — never the 20.955 default, that assumption already burned us once):

```text
   exposure     fast reach    slow approach   settled
    1/250 s        6.6 px          1.8 px      0.0 px
    1/60  s       27.5 px          7.4 px      0.0 px
    1/30  s       54.9 px         14.8 px      0.0 px
```

**At 1/30 s the smear is wider than the orange.** And the real client captures
its observation *immediately after* the 8-step motion burst — peak smear, peak
AF hunt. B3's 3 px box blur is not the same experiment.

## B12 is the important one

It is the only flag here that addresses the leading candidate, and it exists
because of a structural fact:

> In sim the client steps the world, so a slow policy call pauses physics too and
> latency is FREE. On hardware the world keeps running while the arm sits frozen.

B12 pays the round trip in **task time** instead of wall clock, by prepending K
hold-actions to each chunk — so every stalled step still writes a full
ground-truth row and the freeze is visible in the CSV. `K = RTT_seconds × 30`.

Pair it with `--obs-delay K`: staleness and stall are two halves of the same
latency and B6 only ever modelled one of them.

**B12's K is not known yet** — the round trip has never been measured (T0). Until
it is, run a sweep (K = 3, 10, 30, 60) and find where success collapses; if it
collapses below the K implied by any plausible RTT, the link is the cause.

---

# 2026-08-11 — THE AUG 8 RUN WAS NOT A PERCEPTION FAILURE. Premise corrected.

The 143 evidence frames from run 2 were sitting in `logs/realarm_frames_run2_20260808/`
the whole time. Nothing had ever looked at them. Measured, not inferred:

## The object MOVED. The policy made contact.

Tracked the target by colour in the STATIC front view — the real-arm twin of
sim's object-displacement column:

```text
  detected in 143/143 front frames
  chunk  0-24    0.0 ->  4.5 px      approach
  chunk 24-36    4.5 -> 21.1 px      CONTACT - object displaced
  chunk 36-142  21.1 -> 20.7 px      stable at the NEW position, never touched again
```

Confirmed visually (`docs/evidence_aug8/aug8_orange_moved.jpg`): the gripper closes in at c0024,
is on the object at c0030, and the object has visibly shifted off the start marker
by c0036. Then the gripper withdraws and never comes back.

**This is a FAILED GRASP followed by non-re-engagement — not an absence of
object-directedness.** The policy found the target, reached it, touched it,
failed to close on it, and then did not try again for 106 more chunks.

⇒ **The founding premise of this document was wrong.** "Coherent motion, zero
object-directedness" is not what the data shows. And the consequence is large:
the 13 sim conditions that produced *completion* failures were reproducing the
**correct class** all along. The three-day puzzle of "why can't sim reproduce
this" dissolves — sim was never failing to reproduce it.

## Why it never re-engaged: the wrist camera lost the workspace

```text
                  front (static, base)      wrist (Pi, on the gripper)
  median sharp          183.0                      27.0
  CV of sharpness        0.10  steady              0.68  VARYING
  frames >= 100          143/143                     1/143
  totally flat frames        0                         2
```

The front camera was healthy for the entire run. The wrist camera was not, and
`docs/evidence_aug8/aug8_wrist_sweep.jpg` shows why it is worse than a sharpness number:

```text
  c0000-c0022   looks DOWN at the table - plate and surface visible. Correct.
  c0033-c0066   looks at the WALL and skirting board.
  c0077-c0142   looks at the FLOOR. No table, no plate, no target. ~46% of the run.
```

The camera drifts off the workspace at roughly the same time the failed grasp
happens, and never recovers. From a floor-only wrist view the policy has one
useful camera instead of two, which is a plausible mechanism for why it never
re-engaged an object the front camera could still see perfectly.

**This is testable in sim and was never tested.** `--rotate-wrist-camera` exists
but the campaign only ever tried 5°; this is the camera ending up somewhere
between 45° and 90° off task. The geometry axis that measured 89%→44% was tested
far too gently.

## Also: the target is not an orange

`docs/evidence_aug8/aug8_orange_moved.jpg` — the object is smooth, glossy and slightly
flattened, with a stem indent. It reads as a **tomato** (or persimmon), not an
orange. Sim oranges are spherical with pebbled skin. Worth confirming with the
user; if the real runs used a tomato, that is a domain gap nobody recorded, and
it bears directly on a grasp that closed and slipped.

## Corrections this forces

```text
1. "zero object-directedness"     WRONG - contact at chunk 24-36, 21 px displaced
2. "perception failure"           WRONG - it is a grasp failure + camera drift
3. "sim cannot reproduce it"      DISSOLVED - sim's completion failures were right
4. wrist camera "13% stale"       UNDERSTATED - 142/143 frames below sharp threshold
```

The latency finding earlier today stands on its own (the client genuinely has no
compression, no RTC, and executes 8 of 16 actions) but it is no longer needed to
explain a perception failure that did not happen. It remains a real defect and a
plausible contributor to the failed grasp.

---

# WRIST CAMERA — diagnosed and partly fixed, 2026-08-12

## Fixed: the proxy was pointed at a dead address and failed SILENTLY

`pi_wrist_proxy.py` was launched Aug 8 13:00 with `--pi-host raspi@192.168.1.18`.
The Pi now lives at **192.168.1.12** (hostname `raspberryw`, also on ZeroTier at
192.168.194.203). ARP for .18 was INCOMPLETE — nothing there.

**The proxy kept returning HTTP 200 with a valid, decodable JPEG.** Three pulls
3 s apart were byte-identical, and identical to a capture hours earlier: one
frozen BLACK frame. A client cannot tell this from a working feed.

⇒ Restarted against .12; verified serving live frames (3 pulls, 3 distinct MD5s).
⇒ **The proxy must fail loudly.** Serving a stale frame with 200 is the worst
   possible behaviour and would silently poison any run.

Note the Aug 8 wrist frames DID change content, so the feed was live then. This
freeze is a LATER fault, not the Aug 8 cause.

## The real problem is LIGHT, and it explains the Aug 8 blur exactly

Sensor is **OV5647 = Camera Module v1: FIXED FOCUS, no AF motor.** So the earlier
autofocus-hunting hypothesis is dead — B10 does not model this rig.

Live measurements, arm parked:

```text
  config                      brightness   sharpness
  current (no flags)               17.9        103
  --ev 2.0                         19.5        118
  --ev 2.0 --gain 8                16.7        153
  --shutter 40ms --gain 12         30.3        333
  front camera, for reference     102.0        183
```

`--ev` barely moves brightness because **auto-exposure is already maxed out.**
Only an explicit long shutter helps, and even at 40 ms the frame is still **3x
darker than the front camera.** The room is simply too dark.

And that is the whole Aug 8 mechanism:

```text
  dark room -> AE lengthens the shutter -> motion blur during the reach
```

Smear during a reach at the shutter speeds darkness forces (f_px=634):

```text
     1/125 s     13 px
     1/60  s     28 px
     1/30  s     54 px
     40 ms       66 px      <- what the test above needed
```

**The orange is only 40-80 px across in the wrist view.** At 1/30 s the smear is
wider than the object. Aug 8 measured median sharpness 27 with CV 0.68 — low AND
varying with motion, which is exactly this and NOT fixed misfocus.

## Actions

```text
1. ADD LIGHT to the workspace.        <- dominant. No setting substitutes for photons.
   Then the shutter can be short and frames stay sharp DURING motion.
2. Lock shutter/gain/AWB explicitly in the proxy's rpicam-vid command. It
   currently passes NO exposure flags at all - rig spec priority (2), never done.
3. Check the OV5647 lens focus for ~15-25 cm working distance. It is a manual
   twist-thread lens; nobody has recorded ever setting it.
4. Make the proxy fail loudly instead of serving a frozen frame with HTTP 200.
```

## Measured in passing: the link

**RTT NJ -> Pune over ZeroTier: min 249 ms, mean 331 ms, max 568 ms (n=4).**
This is T0, previously unmeasured. At 30 Hz that is ~10 env-steps of dead time
per policy call, before the 1.76 MiB uncompressed payload transfer is counted.

---

# TOP CAMERA (Logitech C270) — 2026-08-12. It works, and it is the right camera.

## CORRECTION: "the C270 returns pure black" was WRONG

That conclusion came from captures that never gave the sensor time to wake up.
Raw YUYV straight off the device settles it:

```text
  frame  0: luma min=16 max=16  mean=16.00   std=0.00   distinct=1     <- uniform black
  frame 19: luma min=16 max=235 mean=169.19  std=33.16  distinct=206   <- real image
```

**The C270 needs ~20-60 warm-up frames.** Every earlier capture used
`ffmpeg -frames:v 12` and kept a frame from inside the blank window. The camera
was never faulty.

⇒ **This is a trap for the client too.** Anything that opens the C270 and starts
immediately gets black frames. Whatever consumes it must discard warm-up frames.

With a proper 60-frame warm-up: **sharpness 304.9, brightness 73.2, std 49.3** —
sharper than the Aug 8 front camera (median 183) and well exposed.

## It is the geometry match for sim's `front`

`docs/evidence_aug8/topcam_warm.jpg` is a steep overhead view: table filling the
frame, arm seen from above. That is sim's `front` camera (0.60 m up, 71 deg
depression), NOT the laptop webcam's low side-on view that fed the channel on
Aug 8.

⇒ Route the C270 into the policy's `front` channel. This is the 89%-vs-44% lever
and it is a config change, not a hardware move.

## Its controls are all wrong — the Stage 0b readback, finally taken

```text
  white_balance_automatic       1  AUTO      <- rig spec (2) says LOCK. never done.
  auto_exposure                 3  AUTO      <- Aperture Priority. never locked.
  exposure_dynamic_framerate    1  ON        <- camera SILENTLY DROPS FPS in low light
  power_line_frequency         60 Hz         <- INDIA IS 50 Hz -> flicker banding
  white_balance_temperature     inactive     (masked by auto WB)
  exposure_time_absolute        inactive     (masked by auto exposure)
```

Two of these are worse than cosmetic:

**`exposure_dynamic_framerate`** — the stream was measured at **12.36 fps, not
30**. The camera silently more than halves its rate in dim light. Every staleness
assumption in this investigation used 30 Hz. At 12.36 fps each frame is 81 ms
old, not 33 ms.

**`power_line_frequency=60`** in a 50 Hz country produces rolling brightness
bands under artificial lighting. It is a one-line fix and nobody has ever set it.

## Actions

```text
1. power_line_frequency = 1 (50 Hz)      one line, removes flicker banding
2. auto_exposure = 1 + exposure_time_absolute = fixed
3. white_balance_automatic = 0 + white_balance_temperature = fixed
4. exposure_dynamic_framerate = 0        stop the silent 30 -> 12 fps collapse
5. discard >=30 warm-up frames on open   or the first frames are black
6. route C270 -> the policy's `front` channel
```

Same caveat as the wrist: locking exposure only works once the room has enough
light. Set these AFTER the lighting is fixed, not before.

---

# WRIST-OFF-TASK BATTERY — RESULT, 2026-08-12. 83% -> 0%. Decisive.

24 runs, four arms interleaved, same session, n=6 each.

```text
condition     n   closest approach   placed/18   rate   vs canonical
canonical     6        0.015 m          15/18     83%   -
wrist45       6        0.033 m           0/18      0%   p = 2.9e-07
wrist70       6        0.101 m           0/18      0%   p = 2.9e-07
wrist90       6        0.090 m           0/18      0%   p = 2.9e-07
```

**Misaiming the wrist camera alone takes the task from 83% to zero.** Nothing
else was changed - same scene, same lighting, same policy, same session. The
front camera stayed perfect throughout.

## The battery tested the real defect, not just "an angle"

`docs/evidence_aug8/wrist_angles_rendered.jpg` — the rendered wrist view at each
setting:

```text
  canonical  plate, gripper and table clearly in frame
  45 / 70 / 90 deg   BARE TABLE ONLY. no plate, no gripper, no target.
```

That is the c0077+ regime from the Aug 8 run, where the real wrist camera showed
nothing but floor. The script carried an explicit instruction to check this
before believing the numbers; it passes.

## It reproduces the Aug 8 SHAPE, not just the score

```text
  AUG 8 REAL   approached, contacted (target displaced 21 px), failed the
               grasp, never re-engaged for 106 more chunks
  wrist45 SIM  approaches to 0.033 m, grasp predicate fires 4 times, places
               ZERO, does not recover
```

Same signature: reach, touch, fail, never come back. wrist70/90 do not even
approach (0.09-0.10 m vs canonical's 0.015 m) — consistent with the later half
of the Aug 8 run after the camera had fully drifted.

## What this settles

**The wrist camera drifting off the workspace is SUFFICIENT, on its own, to
cause total task failure.** It is not a contributing factor to be weighed
against latency or instruction strings — it is a complete explanation for a 0%
run.

The campaign's earlier B8 test (`--rotate-wrist-camera=5`, "passed") was
testing 5 degrees against a real offset of 45-90. That is why the axis looked
harmless for three days.

⇒ FIX THE WRIST CAMERA MOUNT. This now outranks every other open item,
  including the 331 ms link and the instruction string.

## What it does NOT settle

```text
- whether the mount DRIFTED during the run or was wrong from the start.
  The Aug 8 frames show the view changing over time (table -> wall -> floor),
  which suggests drift, i.e. a mechanical looseness rather than a bad setup.
- whether fixing it is SUFFICIENT for the real arm. Sufficient-to-break is not
  the same as sufficient-to-fix. The link latency and the front-camera pose are
  still real and still unmeasured on hardware.
```

---

## Evidence for the "c0077+ shows no workspace" claim (challenged 2026-08-12)

The claim was originally an EYEBALL judgement off a 12-frame sample. Challenged,
so here is what actually supports it — including a metric that failed.

**A metric that FAILED.** "Fraction of white-ish pixels" (plate and gripper are
white, wood is not) gives 46.8% early and 70.2% LATE — the opposite of the claim.
It fails because the washed-out pale wall and overexposed floor in the late
frames read as low-saturation-high-value, i.e. as "white". It measures
exposure, not workspace. Recorded so nobody re-derives it.

**A metric that WORKS.** The plate carries a distinctive BLUE radial pattern.
Wood floor, wood table and a pale green wall contain no blue.

```text
                    mean blue    frames with the plate in view
  c0000-c0024         0.72%                 12%
  c0025-c0054         0.21%                  0%
  c0055-c0076         0.29%                  9%
  c0077-c0142         0.37%                  0%     <- never, across 66 frames
```

**The direct evidence.** `docs/evidence_aug8/aug8_late_wrist.jpg` — 12 frames
spread across c0077-c0132. Every one shows blurred wood floor filling most of the
frame, a pale wall along the top edge, a skirting board and a cable. No plate,
no gripper, no table, no target in any of them.

**Calibration.** "Nothing but floor" was loose — there is floor, wall, skirting
board and cable. The defensible claim is narrower and is what the sim battery
tested: **from c0077 the workspace is not in the wrist view at all**, for the
final 66 of 143 chunks (46% of the run). The plate measurement gives 0/66.

---

# T0 MEASURED — from the Aug 8 frames' own timestamps, 2026-08-12

Asked whether more images existed from the failed run. They do not: the arm
machine holds exactly one set, `~/run_frames`, 286 frames, checksum-identical to
the local copy. c0000..c0142, nothing else on the host.

But the file mtimes are a record of the loop, and nobody had read them.

```text
  143 chunks, first -> last = 143 s
  mean per chunk           = 1.007 s
  gap histogram: 0s x4   1s x133   2s x5      <- metronomic
```

Combined with the client executing `actions[:8]` at 30 Hz:

```text
  per chunk              1007 ms
  arm actually moving     267 ms    (8 actions @ 30 Hz)
  blocked on the policy   740 ms
  DUTY CYCLE              26.5% moving, 73.5% FROZEN
```

**The arm spent 73.5% of the Aug 8 run motionless, waiting for New Jersey.**

This is T0. It was called unmeasured on 2026-08-11 and treated as blocking; it
was in the file timestamps the whole time. The earlier estimate (21% moving at a
1.0 s round trip) was close — the real figure is 26.5%.

## Where the 740 ms goes

```text
  ping RTT to Pune, measured today       331 ms
  remainder                              409 ms   <- payload transfer
```

409 ms for 1.76 MiB uncompressed ≈ 4.3 MiB/s. Consistent with the π0.5 finding
that the tunnel, not the uplink, was the bottleneck — and with the fact that the
N1.6 client sends raw `np.save` arrays with no compression.

⇒ **JPEG would remove most of the 409 ms.** π0.5 measured 14.6x on this link.
⇒ B12 is now exactly parameterised: 740 ms at 30 Hz = **`--policy-stall 22`**.
  No longer a guess.

## Standing against the wrist result

The wrist battery proved a misaimed wrist camera is SUFFICIENT to take the task
from 83% to 0%. This does not displace that. It does mean the Aug 8 run had two
independent, individually-serious defects running at once:

```text
  wrist camera off the workspace for 46% of the run   -> sufficient alone (measured)
  arm frozen 73.5% of the run                         -> untested in sim (B12 exists)
```

Fixing the mount without fixing the link would leave the second one intact.

---

# CORRECTION — 2026-08-12. The Aug 8 front camera was RIGHT. My advice was wrong.

Asked whether N1.6 was fine-tuned on the 89 real episodes. Answer: **no** — and
checking exposed a bad recommendation.

## What the checkpoint actually trained on

`experiment_cfg/conf.yaml` of the served checkpoint:

```text
  dataset_paths:   dataset/so101_pick_orange_v2.1
  dataset_type:    physical_embodiment          <- REAL arm data
  embodiment_tag:  new_embodiment
  max_steps: 10000   global_batch_size: 32   episode_sampling_rate: 0.1
```

Two things follow:

1. **The directory name `gr00t_n16_leisaac_orange` is MISLEADING.** "leisaac" is
   the simulator; the checkpoint was fine-tuned on REAL SO-101 data.
2. **`so101_pick_orange_v2.1` is not on this machine at all.** The 89-episode set
   that IS here (`so101_orange_49_plus_grasp_pick_move_focus`, 89 eps / 40,712
   frames / 3 cameras) has **never been used to fine-tune N1.6**.

## The recommendation that was wrong

The 89-episode dataset carries THREE cameras — `front`, `top`, `wrist` — while
the policy consumes only two. Extracting frames:

```text
  observation.images.front   LOW, SIDE-ON  - arm from the side, table edge-on, wall behind
  observation.images.top     overhead
  observation.images.wrist   on the gripper
```

`docs/evidence_aug8/front_channel_truth.jpg` puts the training `front` next to
the Aug 8 client `front`: **same low side-on geometry, same room, same wall, same
stand.** The laptop webcam was feeding the `front` channel a view that matches
the training distribution.

⇒ **My advice to route the C270 into `front` was WRONG.** It would have replaced
  an in-distribution view with an out-of-distribution overhead one. The overhead
  view belongs in `top`, a channel this policy does not consume.

⇒ The Aug 8 front camera was **not** a defect. Remove it from the fix list.

## What this does to the 89% -> 44% result

That number measured sensitivity to moving the SIM camera. But sim's `front` is
overhead while the TRAINING `front` is side-on — so sim's canonical view was
already out of distribution, and the realCam condition moved it TOWARD the real
geometry, not away. The 45-point drop therefore does not mean "the real rig's
camera pose is wrong". It means the sim scene is easier from overhead.

**The whole "front camera geometry" thread rested on assuming sim's camera pose
was the training pose. It was not.** The C270 pose battery is accordingly
withdrawn as the wrong question.

## What SURVIVES this correction

```text
STANDS   wrist off-workspace: 83% -> 0%, p=2.9e-07. The wrist camera is on the
         gripper in BOTH sim and training data, so its geometry IS comparable.
STANDS   arm frozen 73.5% of the Aug 8 run (measured from frame mtimes).
STANDS   wrist blur / dark room / dead proxy - all real, all measured.
FALLS    "the front camera was the wrong one" - it was the right one.
FALLS    the 44%->89% lever as a claim about hardware.
```

---

# WRIST MOUNT — what to actually fix, 2026-08-13

## The aim is already close. The problem is rigidity.

`docs/evidence_aug8/wrist_aim_target.jpg` puts three TRAINING wrist frames above
three live frames from the rig. Both show the gripper fingers entering from the
upper left with the table below, at a similar perspective. **The current aim is
approximately right.**

That matters because it narrows the fix. On Aug 8 the view was correct for the
first ~22 chunks and then drifted to wall and floor. A camera that starts right
and ends wrong is not mis-aimed — **it moved during the run.**

## What the mount photo shows

`docs/evidence_aug8/wrist_mount_closeup.jpg`, from the overhead camera:

```text
- the green PCB appears to REST against the assembly rather than be fastened
- the orange CSI ribbon is long, unsupported, and arcs out under its own
  stiffness. It is the stiffest thing attached to the camera.
- the camera module sits on a small black bracket at roughly 30-45 deg
```

**The ribbon cable is the prime suspect.** A CSI ribbon is springy; every wrist
roll and flex feeds force straight into the camera board. Over a 143-chunk run
that is hundreds of tugs in the same direction — exactly the slow one-way drift
the Aug 8 frames show (table -> wall -> floor, never back).

## The tolerance it has to hold

From the 168-image sweep: the task survives to ~20 deg and is dead by 30 deg.
So the mount must hold the camera to **well inside 20 deg for a whole run**, not
merely be pointed correctly at the start.

## Fix, in order of likely payoff

```text
1. STRAIN-RELIEF THE RIBBON. Tie or tape it to the arm link a few cm back from
   the camera, so cable motion is absorbed by the link and never reaches the
   board. Leave a service loop. This alone may be the whole fix.
2. FASTEN THE BOARD. It should not be possible to move the camera by hand
   without loosening a fastener. Screws or a printed clamp, not friction.
3. RE-CHECK AIM against wrist_aim_target.jpg once it is rigid - aim last, since
   fastening will shift it.
```

## Verification, and it must be a MOVING test

Aiming it once and photographing it proves nothing — Aug 8 passed that test.

```text
  capture a wrist frame
  run the arm through its full range (or a full episode)
  capture again
  the two frames must show the same view
```

If they differ, the mount is still moving. That is the test Aug 8 would have
failed, and no static check would have caught it.

---

# UNRESOLVED: did the camera move, or did the ARM? 2026-08-13

Told that the ribbon is already secured, which removes the leading mechanical
suspect. That raises an alternative never tested:

```text
  A. the camera MOVED on its mount           -> mechanical fix
  B. the camera is RIGID and the ARM drove to poses where it correctly
     points at the floor                     -> not a mount problem at all
```

These need completely different responses, so it matters.

## Two attempts to settle it from the Aug 8 data. Both failed.

**Attempt 1** — match early/late chunks by whole-frame front-camera similarity,
then compare wrist views. Reported a 5.03x ratio and "the camera MOVED".
**Wrong.** The static background (table, wall, plate) dominates the pixel
difference, so a large arm movement barely registers. The "matched" pairs
(c0011 vs c0139) are an upright compact arm against a fully extended one.

**Attempt 2** — isolate the arm by differencing against a per-pixel median
background, match on silhouette. Gave a clean-looking control (late-vs-late
wrist diff 5.6, early-vs-late 34.6). **Also unusable.** The best match found,
c0013 vs c0135, is again visibly two different poses.

**Why both failed, and the actual finding:** *the arm never returns to its early
pose.* In the second half of the run it occupies a different region of the
workspace entirely. With no matched-pose pair anywhere in the 143 chunks, this
question is **not answerable from this dataset**, by any descriptor.

⇒ No claim either way. "The camera moved on its mount" is UNSUPPORTED.

## What still stands regardless of cause

The wrist view carried no workspace content for the final 66 chunks (plate
visible in 0/66), and the sim battery shows that condition alone takes the task
from 83% to 0%. **That holds under both A and B.** Only the FIX differs.

## The physical test that does settle it

Needs the arm returned to the SAME pose - the exact thing the data lacks:

```text
  1. capture a wrist frame, note the arm pose
  2. run the arm through its full range of motion
  3. RETURN IT TO THE SAME POSE   <- the step that makes this a test
  4. capture again
  same pose + different view  -> A, the mount moved
  same pose + same view       -> B, the mount is fine, the policy drove off-task
```

"Before" frames captured 2026-08-13 into `logs/mount_test_20260813/`. The
"after" capture is pending the arm being moved and returned.

If it comes out B, the mount needs nothing and the real problem is that the
policy walks itself into poses where its own wrist camera is useless - which is
a training/behaviour issue, not a screwdriver one.

---

# STALL BATTERY — RESULT, 2026-08-13. It is the STALENESS, not the freezing.

24 runs, four arms interleaved, same session, n=6 each. K=22 from the Aug 8
frame mtimes (740 ms blocked at 30 Hz).

```text
condition     n   closest   placed    rate    vs control
canonical     6   0.019 m   16/18      89%    -
stall22       6   0.015 m   11/18      61%    p = 0.121   NOT significant
delay22       6   0.016 m    4/18      22%    p < 0.001
both22        6   0.016 m    2/18      11%    p < 0.001
```

## The finding

**The arm being motionless is survivable. The policy acting on a stale image is
not.**

- `stall22` — world advances, arm holds, no fresh command: **61%, p=0.121.**
  Costs performance but does not reliably break the task.
- `delay22` — policy sees a 740 ms old observation: **22%, p<0.001.** Destroys it.

These were treated as two halves of one problem for three days. They are not
equal halves: staleness does nearly all the damage.

⇒ **The fix is to reduce observation AGE, not to smooth out the freezing.**

## And it reproduces the Aug 8 signature exactly

Closest approach is 0.015-0.019 m in EVERY arm, including the ones scoring 11%.
The policy still reaches the object; it fails to complete.

```text
  AUG 8 REAL   reached, contacted (target displaced 21 px), failed the grasp
  delay22 SIM  reaches to 0.016 m, places 4/18
```

That is a *completion* failure, and it is a different signature from the wrist
result, where the policy never approached at all (0.09-0.10 m).

## The two causes explain DIFFERENT HALVES of Aug 8

```text
  observed on Aug 8                          reproduced by
  reached, touched, failed the grasp    ->   delay22   (22%, approaches but cannot finish)
  never re-engaged for 106 chunks       ->   wrist off-task (0%, never approaches)
```

Neither alone accounts for the whole run. Together they do, and the timeline
fits: the grasp failed early (chunk 24-36, staleness), and the wrist camera had
left the workspace by c0077, removing any chance of recovery.

## What to do about it

409 ms of the measured 740 ms is payload transfer — 1.76 MiB sent uncompressed
via `np.save` per call. π0.5 measured 14.6x from JPEG on this same link.

```text
  JPEG the observations   -> removes most of 409 ms   ~10 lines, highest payoff
  execute 16 of 16        -> currently 8; halves the calls needed
  RTC                     -> the pi0.5 fix, heavier
```

**Do NOT read `stall22` p=0.121 as "latency is harmless".** The stall is also
softer than K=22 implies (smoke test: a 22-step hold yields ~6 fully-still steps,
because the arm keeps converging toward the held target). What the battery shows
is that of the two latency effects, staleness is the one that matters.

---

# WRIST CAMERA — STATUS, 2026-08-13

## The proxy's hard-coded IP has now broken the feed TWICE in five days

```text
  Aug 8   proxy configured for raspi@192.168.1.18
  Aug 12  Pi had moved to .12  -> feed dead. Proxy served a frozen BLACK frame
          at HTTP 200 for days. Nothing noticed.
  Aug 13  local wifi path to .12 broken -> frozen again, same silent failure,
          within 24 h of the previous fix.
```

**This is the recurring fault, not a one-off.** A hard-coded DHCP address on a
device whose lease rotates, behind a proxy that reports success while serving
stale bytes.

⇒ Repointed at the Pi's **ZeroTier address, 192.168.194.203**, which is assigned
  per-member and persists. Verified serving live frames (3 pulls, 3 distinct
  MD5s). This survives both DHCP rotation and the current local-wifi breakage.
⇒ The proxy should still be made to FAIL LOUDLY. Serving a stale frame with a
  200 is the worst possible behaviour and is what hid this for four days.

## Image quality: FIXED

```text
              sharpness   brightness
  Aug 8 run        27.0        (varied)     1 of 143 frames above threshold
  Aug 13 dark      36.2          17.8
  Aug 13 now      160.3          94.2       <- above the 100 threshold
  front camera    183.0         102.0       reference
```

Lighting was the cause and lighting was the fix, exactly as the
dark-room -> long-shutter -> motion-blur mechanism predicted.

## Geometry: the tolerance is TIGHT

168-image sweep, 7 angles:

```text
   0 deg  placed 2/3     20 deg  placed 1/3
  10 deg  placed 2/3     30 deg  placed 0/3   <- cliff between 20 and 30
                         45/60/90 deg  0/3
```

n=6 confirmation at the endpoints: 83% at 0 deg, 0% at 45/70/90 (p=2.9e-07).

**The mount must hold well inside 20 deg for a whole run.**

## UNRESOLVED: why the view drifted on Aug 8

Two candidates needing opposite fixes:

```text
  A  the camera MOVED on its mount        -> mechanical
  B  the camera is RIGID and the ARM drove to poses where it correctly
     sees the floor                       -> behavioural, mount needs nothing
```

Two attempts to settle this from the Aug 8 data both failed: the arm never
returns to its early pose, so no matched-pose pair exists in the 143 chunks.
**Still open.** Blocked on the physical test (capture, move, RETURN TO THE SAME
POSE, capture).

## Still not done

```text
  - Pi exposure/WB: the proxy launches rpicam-vid with NO flags at all. The ACER
    measurement showed auto can be the right answer (gain, not shutter), so this
    needs measuring on the Pi before locking anything.
  - lens focus: OV5647 is a manual twist lens, currently 160 vs the front's 183.
    Never recorded as having been set.
  - the mount test itself.
```

---

# RESOLVED — 2026-08-13. The camera did NOT move. The ARM drove off-task.

The question that had been open since the correction: did the wrist camera move
on its mount, or did the arm drive to poses where a rigid camera correctly sees
the floor? Two earlier attempts failed because the arm never returns to its early
pose, so no matched-pose pair exists in the data.

## The test that works, and why the earlier ones could not

**The gripper fingers are bolted to the same body as the camera.** So their
position in the wrist frame depends ONLY on the camera's pose relative to the
gripper — never on where the arm is in the room. It does not need a matched pose,
which is exactly what the data lacks.

## Result on the Aug 8 run

```text
  gripper detected in 140 / 143 wrist frames
  centroid EARLY (c0000-c0030, n=31)   (250.7, 162.3)
  centroid LATE  (c0090-c0142, n=53)   (266.5, 172.3)
  SHIFT = 18.6 px  =  ~1.6 deg
  tolerance before the task dies       ~240 px = 20 deg
```

**1.6 degrees over the whole run.** The mount held.

Confirmed independently on the bench today: after the arm was moved by hand and
returned, the gripper silhouette overlapped at IoU 65.4% with a centroid shift of
34 px (~3 deg).

## What this means

```text
  A  the camera MOVED on its mount     -> RULED OUT
  B  the camera is RIGID and the ARM drove to poses where it correctly
     points at the floor                -> CONFIRMED
```

⇒ **The mount needs nothing.** Strain-relief, fasteners, re-aiming — all off the
  list. The earlier advice to fix the mount was aimed at a fault that does not
  exist.

⇒ The real fault is **behavioural**: the policy walked itself into poses where its
  own wrist camera could not see the workspace, and then could not recover
  because it had lost the camera it needed to recover with.

This fits the staleness result. Acting on 740 ms old observations, the policy
failed the grasp at chunks 24-36, then drifted into a pose with no workspace in
the wrist view, and from there had one useful camera instead of two for the
remaining 106 chunks.

## What is still worth doing about the wrist camera

```text
  - NOT the mount.
  - The Pi's rpicam-vid still runs with no exposure flags; needs measuring.
  - The proxy must fail loudly instead of serving stale frames at HTTP 200.
  - Lens focus (160 vs the front camera's 183) has never been set.
```

---

# RETRACTION — 2026-08-13. "The policy reached and touched the orange" was WRONG.

The operator, who watched the Aug 8 run, states: **the arm did not try to reach
toward the orange, and never picked one.** That contradicts the 2026-08-12 claim
in this document that the run was "a failed grasp, not a perception failure".

## The claim, and why it does not hold

It rested on ONE measurement: colour-tracking the orange in the static front view
showed a 21 px centroid shift between chunks 24 and 36, read as contact.

Problems, found on re-examination:

```text
1. The camera was on AUTO exposure and AUTO white balance that day. The whole
   image's brightness and colour drifted during the run, which moves a
   colour-threshold centroid without anything physically moving.
2. The detected orange AREA changed ~20% (2095 -> 2536 px) over the same
   period. A rigid object at constant distance does not change size; the
   threshold was catching a different extent of it.
3. The gripper carries YELLOW parts. A yellow end effector arriving next to an
   orange target can contaminate an orange-hue mask directly.
4. 21 px is 3% of frame width, against a target ~51 px across.
```

An attempt to check it by also tracking the gripper failed too: the white-pixel
mask locked onto the arm's white UPPER BODY, not the end effector, so the
resulting "gripper never got within 230 px" figure measures nothing useful.

## What the frames DO support

`docs/evidence_aug8/table_closeup.jpg` — full-resolution crops, no detection
overlay:

```text
  c0000  orange alone, arm not in frame
  c0024  end effector enters at the top, above and right of the orange
  c0030  end effector beside the orange, approaching from the right
  c0036  still beside it, to the right
  c0060  moved away, right and down
  c0120  far away, up and right
```

The gripper was **adjacent** to the orange for roughly ten chunks, then left and
never came back. **Whether that was an attempt to grasp or incidental passage
through that space is not determinable from these images.**

## Status

```text
  "the arm reached, contacted and failed the grasp"   RETRACTED
  "the arm did not meaningfully engage the orange"    stands - operator observation
```

⇒ The ORIGINAL characterisation of the run was right, and the 2026-08-12
  "premise correction" in this document was itself the error.

## Method note

Three automated analyses of these frames have now failed:

```text
  whole-frame descriptor matching   background dominates, matched unlike poses
  silhouette matching               same failure, arm never returns to a pose
  orange colour tracking            auto-exposure drift, area change, yellow gripper
```

Only the gripper-in-WRIST-frame measurement survived scrutiny, because the
gripper and camera are rigidly coupled so nothing else can explain a shift.

**These 286 JPEGs, from an auto-exposure camera with no telemetry, do not support
fine-grained inference about intent.** Stop trying to extract it. The instrumented
client now records joint state per chunk, which answers such questions directly.

---

# LIVE RUN, 2026-08-14 — the failure captured with instrumentation

First run with the instrumented client. 187 chunks, ~3 min, bounded by `timeout`.
Workspace correct: plate left, three targets clustered right, lights on.

## It reproduced the operator's description exactly

`docs/evidence_aug8/live_run_frames.jpg`: the arm starts upright, swings steadily
up and to the RIGHT, away from the fruit, which sits untouched throughout. The
wrist view has lost the workspace by chunk 60.

**"Moves but does not try to reach" — reproduced, and now measured.**

## What the trace shows

```text
  ROUND TRIP    median 615 ms   min 586   max 2078
                (Aug 8, inferred from file mtimes: 740 ms - close)
  WRIST SHARP   median 58, below threshold in 56% of chunks
                (Aug 8: median 27. Better, still marginal.)
```

The mechanism, which no amount of image analysis could have shown:

```text
  joint              start      end      min      max    range
  shoulder_pan.pos   -11.7   -116.4   -116.4    -11.7    104.7
```

**The policy commands a monotonic leftward pan of ~1 deg per chunk, from chunk 0,
and never corrects.**

```text
  chunk    measured   commanded   delta
      0       -11.7       -12.7    -1.0
     60       -67.9       -68.9    -1.0
    120      -116.2      -117.8    -1.6
    186      -116.4      -117.1    -0.7
```

It walks 105 degrees across the run, hits a limit at -116, and sits there for the
final ~65 chunks still commanding "further left". It leaves the policy's own
training range (-66.9 .. 55.0) at **chunk 59** and spends **68% of the run
outside it**.

## Ruled out by this run

**The starting pose is correct.** Measured against 25 training episodes:

```text
  joint            training start (mean+/-sd)    live run start
  shoulder_pan          -8.3 +/- 5.1                 -11.7   ok
  shoulder_lift       -103.3 +/- 2.4                -104.7   ok
  elbow_flex            96.8 +/- 0.2                  96.8   ok
  wrist_flex            78.7 +/- 1.5                  79.7   ok
  wrist_roll            -2.4 +/- 8.7                   7.6   ok
  gripper               38.2 +/- 12.3                 50.0   ok
```

Every joint inside one standard deviation. **NOTE:** an earlier reading of this
run claimed shoulder_lift started out of distribution. That used the checkpoint's
`statistics.json`, which describes a DIFFERENT dataset
(`so101_pick_orange_v2.1`). Against the actual task's own episodes the start pose
is right. Retracted.

## What this does NOT yet explain

**Why** the policy commands a constant leftward pan from the very first chunk. A
steady ~1 deg/chunk bias for 120 consecutive chunks is not a decision — it is a
systematic offset. Candidates, none tested:

```text
  - the policy does not recognise the scene and is emitting a prior/default
  - the targets are TOMATOES; the training data used oranges
  - the scene is 67% of training brightness, the fruit 49%
  - a sign or frame convention error on shoulder_pan specifically
```

The last is worth checking first because it is the only one that would produce a
*monotonic* drift rather than degraded reaching, and it is checkable in code.

---

# ROOT CAUSE CANDIDATE, 2026-08-14: a compounding pan bias

Chasing why the live run's pan drifted monotonically, via pure inference probes
against the running server. No robot motion.

## What the probes established

**1. The output is dominated by STATE, not vision.**

```text
  vary the IMAGES (real / black / white / grey / swapped)   pan spread  1.2 deg
  vary the STATE  (-40, -11.7, 0, 30)                       pan spread 69.7 deg
```

**2. But vision is NOT ignored** — measuring the whole 16-step chunk rather than
`action[0]`, swapping front/wrist shifts the trajectory by 4.0 deg and black
images by 2.5 deg. An earlier reading of probe 1 concluded "the policy ignores
vision"; that used `action[0]` at the REST pose, where the opening motion is
stereotyped. **Retracted.** It also contradicted the documented sim result that
moving the oranges 0.150 m moves the reach 0.095-0.117 m.

**3. The policy carries a systematic leftward pan bias, on its OWN training data.**
Fed a training state with its matching training images, and compared against what
the demonstrator actually did next:

```text
  frame 150   PREDICTED  2.9 2.8 2.4 2.3 1.8 1.6 1.7 0.9    drifting down
              ACTUAL     3.5 3.5 3.5 3.5 3.5 3.5 3.5 3.5    flat
  frame 300   PREDICTED -11.5 -11.7 -11.6 -12.0 -12.1 ...    drifting down
              ACTUAL    -11.6 -11.5 -11.4 -11.4 -11.4 ...    flat/rising
```

Mean pan error 0.6-2.6 deg per chunk, and **the sign is consistently negative.**

## The mechanism this suggests

On training data a 1 deg error is small. But the real loop is CLOSED - each
chunk's result becomes the next chunk's input - so a constant-sign bias
integrates:

```text
  chunk 1     pan -1
  chunk 2     from there, pan -1 again
  ...
  chunk 120   -105 deg, at the joint stop
```

Which is exactly what the live run measured (-11.7 -> -116.4, 68% of the run
outside the training range).

**Why sim does not run away:** in sim the visual signal is strong and
in-distribution, and the vision term corrects the bias each cycle. On the rig the
visual signal is weaker - tomatoes rather than the training oranges, scene
brightness 67% and fruit 49% of training, wrist sharpness median 58 with 56% of
chunks below threshold. If vision is too weak to correct the bias, the bias wins.

⇒ **Hypothesis: a small pan bias that vision normally cancels, running away when
  the visual signal is degraded.** It fits every observation - the sim/real
  split, "moves but does not reach", the monotonic direction, and the joint stop.

## NOT yet established

```text
  - that the bias CAUSES the runaway rather than accompanying it
  - why the bias exists (checkpoint quality? the corpus units bug? training?)
  - whether strengthening the visual signal (real oranges, more light) stops it
```

The cheapest discriminating test: **put real oranges on the table under good
light and re-run.** If the drift stops, the hypothesis holds and the fix is the
scene, not the code. If it drifts identically, the bias is unconditional and the
checkpoint itself is the problem.

---

# RUN 2, 2026-08-16 — real orange, correct aim, JPEG on. Still fails.

The discriminating test: if the pan bias is conditional on a weak visual signal,
a real orange under a correctly-aimed camera should stop the drift.

Scene verified before starting: plate left, **real orange** centre (hue 14.0
against training's 11.0; the Aug-14 tomatoes were 20.5), front camera restored to
the low side-on training geometry.

## Result: the task failed identically. The numbers did not.

```text
                        RUN 1 (tomatoes, raw)   RUN 2 (orange, JPEG)
  round trip                 615 ms                  564 ms
  wrist sharpness             58                      37
  oranges placed               0                       0

  COMMAND BIAS (action[0] - state)
  shoulder_pan          -0.83   99% neg          -0.24   77% neg   <- REDUCED
  elbow_flex            -2.46   99% neg          -2.38   99% neg   <- UNCHANGED
  gripper               -0.00   50% neg          +0.06   45% neg   (the control)

  MOTION RANGE
  shoulder_pan           104.7                    71.9
  shoulder_lift           51.6                   114.9
  elbow_flex              19.7                    64.5
```

## What this settles, and what it does not

**The pan bias IS partly conditional on the visual signal.** A real, correctly
framed orange cut it from 99% one-signed to 77%, and the pan drift from 105 deg
to 72 deg. That is a real effect and it means vision does reach the pan channel.

**The elbow_flex bias is NOT conditional. It is identical across both runs**
(-2.46/99% vs -2.38/99%), across two different scenes, two different targets, two
camera configurations and two transports. Whatever produces it does not depend on
what the policy sees.

**And the task still failed completely.** `docs/evidence_aug8/run2_frames.jpg`:
the arm rises up and to the right, the orange sits untouched in centre frame, and
the wrist view loses the workspace by c60 and is near-black by c90. The failure
mode shifted - this time driven by shoulder_lift (114.9 deg) and elbow (64.5 deg)
rather than pan alone - but the outcome did not.

⇒ **Improving the scene is not sufficient.** The fork posed on 2026-08-14 resolves
  toward the checkpoint: a bias that survives a corrected scene, on a joint whose
  bias does not move at all, is a property of the model rather than the rig.

## Caveats, stated because several variables moved at once

```text
  - run 2 changed the target, the camera aim AND the transport together.
    The pan improvement cannot be attributed to any one of them.
  - wrist sharpness got WORSE (58 -> 37), so the visual signal was not
    uniformly better. Part of why pan improved and elbow did not may be that.
  - n=1 each. These are traces, not a battery.
```

## Where this points

The checkpoint was fine-tuned on `so101_pick_orange_v2.1`, a dataset **not on
this machine**. The 89-episode set that IS here has never been used for
fine-tuning. If the bias is in the checkpoint, the next move is a training
question - retrain on the available data, or recover the dataset that produced
this one - and not another rig adjustment.

---

# BIAS MEASURED AT SCALE, OFFLINE — 2026-08-16

320 samples across 8 training episodes, 5,120 predicted actions, replayed against
ground-truth demonstrator actions. **No feedback loop**, so anything here is a
property of the model rather than closed-loop dynamics — the distinction the live
runs could not make.

```text
  joint             mean err   median   % neg     95% CI of the mean
  shoulder_pan        -1.040   -0.805     69%   [-1.480, -0.600]   BIASED
  shoulder_lift       +1.495   +1.879     26%   [+0.520, +2.469]   BIASED
  elbow_flex          +5.084   +2.947     25%   [+4.096, +6.072]   BIASED
  wrist_flex          +0.045   -0.536     54%   [-0.704, +0.794]   no
  wrist_roll          +0.801   +0.882     21%   [+0.499, +1.102]   BIASED
  gripper             +0.385   +0.161     48%   [-0.288, +1.058]   no
```

**The gripper is the control and it comes out unbiased**, which validates the
method — the signed errors elsewhere are not an artefact of the measurement.

## The confirmation

**`shoulder_pan` carries a systematic NEGATIVE bias of about -1.0 deg per chunk,
and the confidence interval excludes zero.** It matches the live runs in both
sign and magnitude (-0.83 and -0.24 measured on the arm). This is a model
property, present with no feedback loop, on the policy's own training data.

In closed loop that integrates: -1 deg per chunk over 120 chunks is the 105 deg
runaway that walked the arm into its joint stop in run 1.

## The complication — stated because it matters

**`elbow_flex` is +5.08 offline but was -2.46 LIVE. Opposite signs.**

So the live elbow behaviour is NOT explained by a model bias. Something about the
closed loop, or about the out-of-distribution states the arm reached, reverses
it. The earlier note calling the elbow bias "unconditional" was wrong: it is
unconditional *across live runs*, but it does not agree with the offline
measurement at all.

## The mechanism this supports

```text
  1. the model has a real -1.0 deg/chunk bias on shoulder_pan   (measured, n=320)
  2. closed loop integrates it - each chunk anchors to the new position
  3. the arm leaves the training distribution (run 1: at chunk 59, 68% of the run)
  4. outside it, all joints behave arbitrarily - which is where the elbow sign
     flip and run 2's shoulder_lift excursion come from
```

The pan bias is the *initiator*. The rest is what happens after the arm is
somewhere the policy has never seen.

## Caveat

Measured on TRAINING data, i.e. in-distribution. It says what the model does
where it is well-defined. It says nothing about behaviour outside that, which is
exactly where the live runs spend most of their time.

---

# 2026-08-16 — THE CHECKPOINT IS DOWNLOADED AND SIM-TRAINED. Major correction.

Searched both machines for `so101_pick_orange_v2.1`. **It is on neither.** But
the search found what the checkpoint actually is.

## It was downloaded, not trained here

`~/lerobot_assets/checkpoints/gr00t_n16_leisaac_orange/` carries an HF download
cache (`.cache/huggingface/download/*.metadata`), a README, `.gitattributes` and
a `scripts/` directory — the signature of `hf download` on someone else's model
repo, pulled 2026-08-05.

## Its own README and eval script say SIMULATOR

```text
  README.md          "Finetuned GR00T N1.6 on Leisaac pick orange dataset"
  scripts/finetune.sh --dataset_path dataset/so101_pick_orange_v2.1
  scripts/leisaac_client.sh
                     --task=LeIsaac-SO101-PickOrange-v0      <- the SIM task
                     --policy_language_instruction="Pick up the orange and
                                                     place it on the plate"
```

**LeIsaac is the simulator.** The author's own evaluation recipe runs it against
the Isaac Sim task, not hardware.

### Retracting the "trained on real arm data" claim

On 2026-08-12 this document concluded the checkpoint was fine-tuned on REAL data,
from `dataset_type: physical_embodiment` in its config. **That is the DEFAULT
value of the field** (`gr00t/configs/data/data_config.py:28`), not a statement
about sim versus hardware. The conclusion was drawn from an unset default.

## What this does to the bias finding

The offline bias measurement (320 samples, `shoulder_pan` -1.04, CI excluding
zero) was made against **`so101_orange_49_plus_grasp_pick_move_focus` — the 89
REAL episodes.** If the checkpoint is sim-trained, that is not its training
distribution at all.

⇒ **What I measured is the model's error on data it was never trained on.** That
  is out-of-distribution error, not a defect. Calling it "a bias in the
  checkpoint" over-claimed considerably.

The measurement stands as a fact; the interpretation does not.

## What this reframes

```text
  86% in sim            its NATIVE domain - the task it was fine-tuned on
  0% on the real arm    a straightforward sim-to-real gap
  systematic error on   expected - the model has never seen this distribution
    the 89 real episodes
```

**The model has never been trained on real-arm data.** Every real-arm run has
been out of distribution from the first frame. That is a simpler and more likely
explanation than a defective checkpoint, and it fits every observation.

## Also found: a different instruction

```text
  the author's eval    "Pick up the orange and place it on the plate"
  our client + sim     "Grab orange and place into plate"
```

Different sentences. The 2026-08-14 note "the instruction is ruled out" was based
on our sim eval and our client agreeing with each other — they do, but **neither
matches the string the checkpoint's author used.** Not necessarily wrong, but not
ruled out either. Cheap to test.

## What follows

The 89 real episodes (40,712 frames, 3 cameras) are here and **have never been
used for fine-tuning**. If the diagnosis is a sim-to-real gap, that dataset is
the fix, and the pi0.5 run already proved this GPU can do a full fine-tune.

---

# 2026-08-16 CONFIRMED: sim-trained. And the camera geometry question reopens.

`docs/evidence_aug8/../logs/leisaac_vs_real.jpg` — the LeIsaac dataset's front
camera is unmistakably a RENDER (flat shading, a yellow simulated gripper,
perfect spheres). The 89-episode dataset is a photograph.

```text
  leisaac_pick_orange   60 eps    SIMULATOR   <- what the checkpoint trained on
  so101_orange_49_plus  89 eps    REAL        <- never used for fine-tuning
```

The checkpoint's README says "Finetuned GR00T N1.6 on **Leisaac** pick orange
dataset". Confirmed visually. **The model has never seen real-arm data.**

## This reopens the front-camera question I closed on 2026-08-12

That retraction reasoned: the training `front` is a low side-on view, therefore
the laptop webcam is correct and the overhead C270 would be wrong. **It used the
89-episode REAL dataset as "the training data".** The checkpoint was never
trained on that.

The dataset it WAS trained on has a front camera that is steep and overhead-ish,
with the table filling the frame — the sim geometry (0.60 m up, 71 deg
depression) this document measured back on 2026-08-11.

```text
  what the checkpoint trained on   steep, overhead-ish, table fills the frame
  what the rig sends               low, side-on, wall and room behind
```

⇒ **The original 2026-08-11 advice — route the overhead camera into `front` — may
  have been right, and the retraction wrong.** Both were reasoned from a dataset;
  the first from sim, the second from the 89 real episodes. Only the sim one is
  this checkpoint's training distribution.

⇒ And the 89% -> 44% camera-geometry measurement becomes relevant again. It
  measured exactly this axis, in the checkpoint's own domain.

## Status of the diagnosis

```text
  CONFIRMED   the checkpoint is sim-trained; the real arm is out of distribution
              from the first frame
  LIKELY      the front camera geometry is also mismatched against its actual
              training distribution
  RETRACTED   "the front camera was right all along" (2026-08-12) - reasoned
              from the wrong dataset
```

## Two paths, and they are different work

```text
  A  make the rig look like the SIM      re-aim the front camera overhead.
     Cheap, testable today, and the 89%->44% figure is a real measurement of
     what this axis is worth in the checkpoint's own domain.
  B  make the MODEL know the real world  fine-tune on the 89 real episodes.
     The durable answer, and that data has never been used.
```

A is one afternoon. B is a training run this GPU has already been shown to
handle.

---

# RUN 3, 2026-08-16 — overhead C270 as `front`. FIRST GRIPPER CLOSURE on hardware.

First real-arm run with the front channel fed by the overhead C270 (the training
geometry) instead of the side-on laptop webcam. Same real orange, JPEG on.

## The trend across the three instrumented runs

```text
              run 1              run 2              run 3
front camera  webcam, side-on    webcam, side-on    C270, OVERHEAD
target        tomatoes           real orange        real orange
pan bias      -0.83, 99% neg     -0.24, 77% neg     still drifts, -13 -> -101
gripper       50-58, never       47-58, never       CLOSED to 14.6,
              closed             closed             chunks 189-199
oranges       0                  0                  0
```

**Each step toward the training distribution produces more task-shaped
behaviour.** Run 3's front view (see run3_frames.jpg) now closely resembles the
training renders - overhead, table filling the frame, both oranges and the plate
visible.

## What actually happened in run 3

The pan still walked out of distribution (-13 -> -101 by mid-run). But then:
shoulder_lift ROSE from -104 to -2, wrist_roll became active for the first time
(range 19 deg vs 2-7 in earlier runs), and at chunks 189-199 the gripper closed
into the grasp range for the first time in any hardware run. The wrist view at
those chunks shows the camera nearly touching something WHITE - consistent with
the arm being at the plate.

Zero oranges picked. The closure happened at the wrong place. But this is the
first object-directed-looking sequence the real arm has ever produced.

## Reading

Supports the out-of-distribution diagnosis from both directions: behaviour
degrades gracefully as inputs leave the training distribution, and RECOVERS
incrementally as they approach it. The camera change alone took the policy from
"never actuates the gripper" to "closes it near the plate".

Still not success, and the pan runaway persists - the remaining gap (real
photographs vs renders, plate on the wrong side, wrist sharpness 47) is still
wide. The fine-tune case stands; this adds evidence that scene alignment ALSO
pays, and the two are complementary rather than competing.

---

# RUN 4, 2026-08-16 — closes the gripper ON AIR. The choreography without the object.

Same configuration as run 3 (overhead C270 as front, real orange, JPEG). One
false start: all six motors silent - the arm's power supply was off; operator
restored it.

```text
  200 chunks   rtt median 558 ms   wrist sharpness median 24
  gripper closed at chunk 43, width ~14, and STAYED closed for 157 chunks
  pan walked -10 -> -117 (the runaway again)
  all THREE oranges: pixel-identical positions from c35 to c150. NOTHING moved.
```

Gripper width ~14 is fingers-nearly-touching; an orange holds at ~28-33 (the
pi0.5 measurements). **It closed on air**, near the fruit region, then rose and
"carried" nothing while panning away.

## The emerging picture, two runs in a row

With the overhead camera, the policy now reliably produces the SHAPE of the task
- approach-ish, close, lift, move - but with no grounding on the actual objects.
Run 3 closed near the plate; run 4 closed on air near the fruit. The choreography
fires; the object perception does not. That is precisely what a policy trained
on renders should do when shown photographs: the motion priors transfer, the
visual grounding does not.

## A real regression this run

Wrist sharpness median 24 - BELOW Aug 8's 27. Half the model's vision was mush
this run. The late-run frames are bright (150) and featureless: the camera
staring at the arm's own white parts. The wrist camera remains an unfixed
liability even after the lighting work.

## Standing summary of the four instrumented runs

```text
         front camera      target    gripper            oranges
  run 1  webcam side-on    tomato    never closed       0
  run 2  webcam side-on    orange    never closed       0
  run 3  C270 overhead     orange    closed @ c189      0
  run 4  C270 overhead     orange    closed @ c43, air  0
```

Monotonically more task-shaped as inputs approach the training distribution;
never object-grounded. The fine-tune on real data remains the indicated fix.

## Wrist "blur" resolved by calibration, not repair (2026-08-18)

The pre-A/B checklist said "fix the wrist camera: sharpness 24, needs 60+".
Measured today, live rig, before touching anything:

```text
  live proxy frame          42.3
  rpicam-still 640x480      44.1
  full-res 2592x1944        46.6 whole-frame, uniform near-to-far
  supersample test          1296x972 downscaled -> 38.0 (WORSE than native)
```

Then the reference that should have been measured first - the wrist channel of
the 89 TRAINING recordings themselves:

```text
  median 27.6    p10 14.7    p90 56.6
  78% of training frames are SOFTER than today's 42.3
```

The camera is sharper today than most of what the model trained on. The "60+"
gate was an uncalibrated guess in the client (comment said "below ~100 is
blurred"); run 4's alarming "median 24" sits almost exactly ON the training
median of 27.6 - moving-arm frames carry motion blur, in training and in
serving alike. The OV5647 is fixed-focus; its uniform ~45 on this scene is what
this lens does at this distance, and it is what the dataset looks like.

Actions: client warning recalibrated 60 -> 15 (training p10). No physical
intervention. Do NOT clean/refocus the lens toward "sharp": the model has never
seen a sharp wrist frame; matching training beats improving on it.

Retraction: "fix the wrist camera before the A/B" is withdrawn as a
precondition. The A/B needs only the arm plugged in.

## First real-arm evaluation of the real-data fine-tune - ten scored attempts (2026-08-18)

Model: n16_real79_top checkpoint-10000 ("Brain B", overhead C270 in the front
channel), served from NJ, arm in Pune. Protocol: replay-verified rig first,
then ten policy attempts, arm reset to the training rest pose between attempts,
orange repositioned by the operator, every run traced (rtt, state, action,
wrist health) with every model input frame saved.

### Rig verification (before any policy attempt)
Joint replay of recording 56 grasped, carried and released its orange once the
orange was placed at the recorded spot (gripper gap +3.4 sustained 7 s).
Two placement misses first - the gap collapse pinpointed both. The rig can
still do the task; the recordings are reproducible on today's hardware.

### The ten attempts

| # | grasped | carried | end of carry | stage/6 |
|---|---------|---------|--------------|---------|
| 1 | + (+11 peak) | + | timer cut mid-place (100s limit, mine) | 5 |
| 2 | - | - | hover stall 3 cm short, never closed | 1 |
| 3 | + (+7.6) | + | slip during swing | 5- |
| 4 | - | - | overreached, pecked past the orange | 2 |
| 5 | - | - | overreached, hovered open | 2 |
| 6 | + (+4.3) | + | DELIBERATE release at pan +50 | 5.5 |
| 7 | + (+6.0) | + | slip at pan +64 | 5- |
| 8 | + (+6.2) | + | DELIBERATE release at pan +64 | 5.5 |
| 9 | + (+3.1) | - | froze holding the orange on the table | 3.5 |
| 10 | + (+3.5) | + | slip at pan +50 | 5- |

Grasped 7/10. Carried 6/10. Deliberate correctly-angled releases 2.
Orange on the table at the end: 0 - see geometry below.

### The two systematic findings

1. GEOMETRY, not policy: training releases span pan -28..+72 (median +42,
   p90 +63, n=62). Tonight's carry endings (+50, +64, +64, +50) are INSIDE
   that range. But the wrist camera at those poses shows the table edge and
   the wall socket where July's recordings show wood under the orange
   (train_release_ep27 vs place_check). The base-to-table relation changed
   when the arm was moved weeks ago; the trained release sector now overhangs
   air. A base rotation of ~15-20 deg CCW (or a 10-15 cm slide) restores it -
   attempted once by the operator, verified unchanged, deferred to next
   session with the park-at-release-pose photo check as the acceptance test.

2. Slips correlate with shallow grasps: the three mid-swing slips had grip
   gaps +3.1-3.5; the runs that held to a deliberate release had +4.3-6.2
   (operator demos: +6.0). Grasp depth, not the swing itself, decides
   whether the carry survives.

### Constants across all ten
round trip median 564 ms (p95 610, n=~2300 cycles), duty cycle 31% moving,
wrist frame age ~45 ms, wrist sharpness in training range. Three connect-time
bus faults (voltage error id6, no-status id4, bad-status id5/id6) - all at
connect, never mid-run; motor PSU suspected, watch it.

### What this settles
The sim-trained checkpoint never moved the arm toward an orange. The
real-data fine-tune, first time on hardware: 7/10 grasps at operator-level
grip strength, 6 carries, 2 deliberate releases. Every remaining failure is
either understood rig geometry or a known imitation-learning mode (stall,
shallow grasp) that more/better demonstrations address. The "train on real
photographs" diagnosis is confirmed end to end.

### Next
- Fix base geometry (photo acceptance test ready: place_pose.npy park + wrist view shows wood)
- Brain A (side camera) ten-attempt set for the A/B - needs the side camera re-aimed
- Grasp-depth improvement: more demos with deep grasps, or a grasp-retry behaviour
- RTC to lift the 31% duty cycle

## RETRACTION: "the base moved" (2026-08-19)

The operator challenged the moved-base conclusion: the wrist at the parked
release pose is tilted diagonally, so the camera sees the wall socket
regardless of what is under the fingers. Verified - they are right:

```text
wrist_flex at release:   July ep27 +46.2   ep31 +57.1
                         run 8     -82.4   run 6 -61.6     (~130 deg apart)
```

The July-vs-tonight wrist-camera comparison compared two different camera
attitudes, not two different tables. The park-and-photograph acceptance test
tested camera direction, not drop position. "Base moved" is WITHDRAWN; the
operator confirms nothing in the rig has moved. The base adjustments requested
on 2026-08-18/19 were based on this error.

## The real finding: policy-commanded wrist drift in long carries

Training carries hold wrist_flex +35..+103 (median +85; below -50 in only
0.3% of 14,601 carry frames). Tonight every hold STARTED in that range
(+41..+89) and then drifted; runs 6/7/8 ended at -62..-87. Commanded-vs-actual
lag is under 6 deg throughout - the policy commanded the drift, the servo
obeyed. The failure is compounding off-distribution drift during carries that
run 10-30x slower than the demonstrations (31% duty, 60-90 s to reach the
release zone vs 2-3 s in demos). The longer the rollout lingers in states no
demo contains, the further the wrist walks out of distribution; slips and
badly-aimed releases follow.

Consequence for priorities: RTC / longer execution horizon moves UP - making
rollouts temporally resemble demonstrations directly attacks this mechanism.
The base stays where it is.

## Re-score after the retraction (2026-08-19)

Operator confirms: the oranges in runs 6 and 8 landed ON THE TABLE. With the
off-table-release claim withdrawn, those runs read: approached, grasped,
lifted, carried, deliberately released, orange at a new spot on the table.
That is the task, complete.

FINAL BRAIN B SCORE: 2/10 full completions, 7/10 grasps, 6/10 carries.
First fully autonomous real-arm completions for N1.6 on this rig - ever.
The wrist-drift finding stands (awkward release attitude, slips in 3 runs),
as does the sim benchmark context (86%).

## The A/B completed: Brain A ten attempts (2026-08-19)

Brain A = n16_real79_side checkpoint-10000, front channel = the laptop's
built-in webcam (the July recording camera, confirmed in docs and never moved).
Same protocol, client, latency regime as Brain B's ten. Room at brightness
~100 vs training 173 (operator's call to proceed; camera settings audited,
two off-default controls reset, sensor physically cannot reach 173 at 30 fps
in this light).

| attempt | result |
|---|---|
| 1-3 | COMPLETE: grasp ~20s, carry to +49..+52, release, return to rest |
| 4 | grasped, released instantly - orange had been placed AT the drop zone |
| 5-8, 10 | over-carry: strong hold, sailed past the zone, pinned at pan +116.5 (joint limit), cut |
| 9 | over-carry, half-opened (cmd 32) at the limit, orange stayed wedged |

A: 10/10 grasps (grip +4.6..+7.0), 3/10 complete, ZERO slips/stalls/overreaches.
B:  7/10 grasps, 2/10 complete, failures split stall/overreach/slip.

Statistics, honestly: completions 3 vs 2 (no difference), grasps 10/10 vs 7/10
(Fisher p~0.2, suggestive not significant). The qualitative gap is failure
STRUCTURE: A has exactly one failure mode (does not stop the carry); B has
three. One fix on A (release timing) addresses 6/7 of its failures.

Unexplained: A's completions were runs 1-2-3 consecutively. Tested and
refuted: lighting drift (99-105 all runs), orange placement (clustered, no
separation), wrist-mount shift (a10 matches a1). Untested candidate: servo
temperature across the 90-min session. Recorded as open.

Bus faults at connect reached six for the campaign (ids 3,4,5,6 various);
never mid-run. Motor PSU remains the suspect component.

### Verdict
Brain A (side camera) is the base going forward: it grasps every time, never
drops, and fails in exactly one way. Next fixes target that one way:
RTC (carry duration is the drift window), release-focused demos (the plate
as an explicit place target), and optionally a software release guard.

## Visual audit of all 20 runs; a4 rescored (2026-08-19)

Storyboards built for every run (9 sampled moments, front + wrist) and checked
against the trace-based scores. One correction found: run a4 was a COMPLETION.
The policy carried with the gripper commanded ~31.5 - above the audit's <30
"shut" threshold - fingers blocked at 36 (gap +4.7), swing to +50, wide-open
release, return to rest. The threshold-free re-audit (sustained gap>2) confirms
holds in all 10 A runs and 7 B runs; no other stage scores changed.

FINAL: Brain A 4/10 complete, 10/10 grasps. Brain B 2/10 complete, 7/10 grasps.

Full visual record published (all 20 storyboards, request/response anatomy,
corrections log): claude.ai artifact "N1.6 real-arm A/B - the full visual record".
