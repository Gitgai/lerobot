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
