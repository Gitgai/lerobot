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
FOV              ~40 deg  (focal 28.7 mm)         ~60-70 deg (typical webcam)
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
                focal_length=28.7 mm, aperture 20.955 mm

REAL EQUIVALENT
  mount to      the robot BASE, not the table and not a tripod at table level.
                It must move with the robot, because that is what the policy
                learned - the view is base-relative, not world-relative.
  height        ~0.60 m above the base plane
  offset        ~0.50 m horizontally from the base
  aim           steeply DOWN at the workspace, roughly 60-70 deg below horizontal
  lens          ~40 deg horizontal FOV. A stock laptop webcam is ~60-70 deg and
                WILL include the room. Either use a narrower lens or crop the
                centre and rescale to 640x480.
  framing test  the table should fill the frame edge to edge. If a wall, a
                socket or a floor is visible, the camera is in the wrong place.
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
