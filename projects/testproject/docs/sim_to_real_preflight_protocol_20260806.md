# SIM-TO-REAL PREFLIGHT — the standing protocol before ANY policy touches hardware

Date: 2026-08-06. Status: **STANDING POLICY** (user's decision). Every policy
headed for the real arm — the as-is N1.6, our future fine-tunes, openpi,
anything — runs this preflight in sim FIRST. No exceptions without an explicit
user override.

Why it exists: the robustness campaign (`n16_robustness_campaign_20260806.md`)
varied the SCENE. The hardware step changes something different — the
OBSERVATION PIPELINE (client code, camera artifacts, timing). Those failures
are silent, they mimic "the policy is bad", and on hardware they are confounded
with everything else. In sim each one can be isolated for the cost of one run.

The principle: **convert hardware debugging (expensive, confounded, risks the
arm) into sim debugging (cheap, isolated, repeatable).** And build a LIBRARY OF
FAILURE SIGNATURES — if the real arm misbehaves, we compare against these runs
and say "that looks like the BGR run" instead of guessing.

---

## Stage A — CLIENT EQUIVALENCE (the Era-1 check; MANDATORY, no hardware)

The hardware client is DIFFERENT CODE from the sim client that produced every
validated result. Era 1's lesson: right checkpoint + wrong wire handling =
silently wrong numbers.

```text
A1. FIELD-BY-FIELD DESK CHECK - real client vs the VALIDATED sim client
    For N1.6 that is: gr00t/eval/real_robot/SO100/eval_so100.py
                  vs  leisaac Gr00t16ServicePolicyClient (validated, 15/15)
    Compare, for every field:
      video    keys (front/wrist), resolution (640x480), dtype (uint8),
               CHANNEL ORDER (RGB vs BGR!), layout (B,T,H,W,C)
      state    keys (single_arm/gripper), dtype (float32), UNITS
               (LeRobot motor units - the real arm is native, the sim needed
               conversion; verify the real client does NOT convert again)
      language key ("annotation.human.task_description"), nesting ([[str]])
      actions  what the client does with the reply (composition? clipping?
               NOTHING should be composed - the server already did;
               probe the wire if in doubt, never trust the config)
    Output: a table in this doc with each row marked VERIFIED or MISMATCH.

    *** COMPLETED 2026-08-06 for the N1.6 as-is test ***

    field            real client (eval_so100.py + lerobot 0.4.4)     status
    --------------   ---------------------------------------------   --------
    video keys       hardcoded ["front","wrist"] - the robot config  VERIFIED
                     MUST name its cameras exactly front / wrist
    resolution       config duty: OpenCVCameraConfig width=640
                     height=480 (set it; not automatic)              CONFIG
    channel order    lerobot 0.4.4 OpenCVCamera DEFAULTS TO RGB and
                     converts BGR2RGB (camera_opencv.py:421)         VERIFIED
    video layout     two recursive_add_extra_dim -> (1,1,H,W,C)
                     uint8 - same shape the sim client produced      VERIFIED
    state order      shoulder_pan, shoulder_lift, elbow_flex,
                     wrist_flex, wrist_roll, gripper - matches the
                     training dataset's names exactly                VERIFIED
    state units      robot-native LeRobot motor units, NO conversion
                     applied (and none needed - unlike sim)          VERIFIED
    language         {"annotation.human.task_description": [[str]]}  VERIFIED
    action handling  decode_action_chunk concatenates and returns -
                     NO composition, NO clipping (server already
                     composed; matches the probe-the-wire finding)   VERIFIED
    wire protocol    PolicyClient from the same repo as the server;
                     LIVE HANDSHAKE PASSED: synthetic obs -> 16
                     action steps in motor-unit scale                VERIFIED

    NOTES
    - lerobot 0.6.1 needs Python >=3.12; this venv is 3.11, so 0.4.4 is the
      newest installable. GOOD NEWS: our calibration dir is literally named
      so_follower/ - the 0.4.x module layout - so 0.4.4 matches the rig's own
      era. lerobot[feetech] extra required for the motor bus.
    - upstream imports so100_follower/so101_follower, which do not exist in
      0.4.4; patched to so_follower (backup: eval_so100.py.orig). The
      "so101_follower" CONFIG NAME is registered by that module, so the CLI
      is unchanged.
    - A2 smoke test PASSED: with no arm attached it fails exactly at
      "Could not connect on port /dev/ttyACM0" - imports, draccus config,
      robot construction and calibration lookup all upstream-verified.
    - torch 2.7.1+cu128 / sm_120 CONFIRMED intact after every install.

A2. NO-ROBOT SMOKE TEST
    Run the real client against the live server with no arm attached. It must
    get as far as hardware discovery and fail THERE - proving imports, config,
    server protocol, and reply handling all work.

GATE: any MISMATCH in A1 is fixed and re-checked BEFORE power ever reaches the
arm. This stage is the single highest-value hour of the whole protocol.
```

## Stage B — FAILURE-SIGNATURE RUNS (one sim run each)

Each run deliberately injects ONE hardware-class defect, so we learn its
signature while everything else is known-good.

```text
B1. BGR SWAP           --img-bgr-swap
    OpenCV cameras deliver BGR; sim frames are RGB. The classic silent bug.
    For THIS policy it should be catastrophic in a RECOGNISABLE way (oranges
    become blue blobs, and the decoy test proved it keys on orange blobs).
    THE POINT: if the real arm ever behaves like this run, check channel
    order before blaming the model.

B2. SENSOR NOISE       --img-noise 8        (gaussian, uint8 sigma)
B3. BLUR               --img-blur 3         (box kernel px)
B4. COMPRESSION        --img-jpeg 40        (encode/decode at quality 40)
B5. WHITE BALANCE      --img-gamma 1.35     (per-channel gain/gamma shift)
    B2-B5 are the REAL appearance gap, in image space - artifacts the renderer
    never produces. The scene campaign's tint/light runs went THROUGH the
    renderer; these do not.

B6. STALE OBSERVATIONS --obs-delay 2        (policy sees frames k steps old)
    In sim the world waits for inference; on hardware it moves ~100-200 ms
    while the policy thinks. Measures the cost of staleness in isolation.

B7. CAMERA ROTATION    --rotate-camera 5    (degrees pitch; position was
    tested in the campaign, ANGLE was not, and degrees move the image more
    than centimetres at this distance)
B8. WRIST CAM JITTER   --jitter-wrist-camera 0.02,0,0
    The wrist camera was never perturbed at all.
```

## Stage C — EXACT-SCENE MATCH (one run)

```text
Run the sim with the scene the user will PHYSICALLY build - same object count,
same approximate layout. The policy has only ever been scored with 3 oranges;
if the real table will have 1, sim must show what it does with 1 BEFORE
hardware does. (Implementation: --park-oranges "2,3" moves the others to a
parking spot far outside the workspace; score only orange001.)
```

## STAGE B/C RESULTS (2026-08-06, battery 4 — one run each, 3,000 steps)

```text
run        injected defect         placed  lifts               verdict
bgrSwap    RGB->BGR channel swap    3/3    [.14,.15,.14]  INVISIBLE (see below)
noise8     gaussian sensor noise    3/3    [.17,.14,.19]  free
blur3      3px box blur             2/3    [.14,.13,.15]  mild (~baseline var.)
jpeg40     JPEG quality 40          2/3    [.14,.13,.16]  mild
gamma135   gamma/white-balance      0/3    [.04,.11,.18]  *** CRATERED ***
stale2     obs 2 steps old          3/3    [.16,.12,.13]  free - latency NOT
                                                          a first-class worry
rot5       front cam pitched 5 deg  2/3    [.15,.15,.19]  mild
wristJit   wrist cam +2 cm          3/3    [.18,.17,.16]  free
oneOrange  single orange (C)        1/1*   [.16, -, - ]   PASS - the one
                                                          available orange was
                                                          picked AND placed
```

### The two findings that rewrite expectations

```text
1. BGR SWAP IS BEHAVIORALLY INVISIBLE (3/3, clean). The predicted "failure
   signature" does not exist - the policy is so hue-invariant that a
   channel-order bug in a real client would produce NO visible symptom.
   => Stage A's SOURCE-LEVEL verification is the ONLY guard against this bug
      class. Behavior-watching cannot catch it. (Verified: lerobot 0.4.4
      converts BGR2RGB explicitly.)

2. WHITE BALANCE IS THE ONE HARDWARE-GAP KILLER. gamma 1.35 - a mild washing-
   out - produced the worst run of the ENTIRE preflight: 0/3 placed. It still
   half-grasps (lifts to 0.18) but never completes. Contrast with bgrSwap:
   a hue PERMUTATION is free, but a CONTRAST/SATURATION compression is fatal.
   The policy appears to key on saturated-blob structure, not hue.

   => RIG REQUIREMENT (new, hard): LOCK the real cameras' auto-white-balance
      and auto-exposure. Webcams re-balance continuously by default; a drifting
      white balance is this policy's one proven kill switch. Verify with
      cv2 CAP_PROP_AUTO_WB=0 / v4l2-ctl before the first episode.
```

Minor: blur/jpeg/5-degree rotation each cost about one orange (baseline
variance is 2/3-3/3 anyway); staleness and wrist jitter are free; the
single-orange scene works, so the physical table may use 1 or 3 oranges.

## Decision rules (agreed now, before any results)

```text
A1 mismatch            -> fix, re-verify, only then hardware
B1 craters (expected)  -> real client's channel order becomes a VERIFIED item
                          in A1, not an assumption
B2-B5 mild degradation -> proceed; note the margin
B2-B5 crater           -> the appearance gap is bigger than the scene campaign
                          suggested; lower as-is expectations further, consider
                          fine-tuning with matched augmentation later
B6 craters at k=2      -> inference latency is a first-class constraint;
                          measure the real loop's latency BEFORE the test and
                          keep it under the measured tolerance
B7/B8 crater           -> camera ANGLES join the rig spec with a tolerance
C   differs wildly     -> build the 3-orange scene on the real table instead
```

## Cost and standing scope

```text
Stage A: ~1 hour of reading + one smoke run. Stage B: 8 runs x ~11 min.
Stage C: 1 run. TOTAL ~2.5 h of mostly unattended sim time.

GOING FORWARD this protocol is run:
  - before the as-is N1.6 hardware test        (first instantiation, now)
  - before the fine-tuned model's hardware run (plan step 5) - Stage A repeats
    ONLY if the client changed; Stages B/C repeat because the POLICY changed
  - before any new architecture's first hardware run (openpi etc.): all stages

KEEP IT LEAN. The protocol earns its place by being ~2.5 cheap hours. If it
bloats into a day of ritual, prune it - Stage A is the part that must never
be skipped.

HONEST LIMIT: passing preflight does NOT guarantee transfer. It removes the
KNOWN silent failure modes so that, when the arm moves, whatever we see is the
POLICY meeting reality - not a channel swap, a unit bug, or a stale frame.
```

## Implementation status

```text
EXISTING flags (campaign): --move-oranges --scatter-oranges --move-plate
                           --jitter-camera --tint --light-scale --light-color
                           --add-decoys --scale-oranges  (--add-plate BROKEN)
TO BUILD (this protocol):  --img-bgr-swap --img-noise --img-blur --img-jpeg
                           --img-gamma --obs-delay --rotate-camera
                           --jitter-wrist-camera --park-oranges
Where: image/delay mods wrap the observation dict in the eval loop (policy-side,
mimicking camera artifacts AFTER rendering); camera-pose mods are env-cfg-side.
Driver: scripts/n16_preflight_battery4.sh once flags exist.
```

---

# STAGE 0 — OBSERVATION EQUIVALENCE. Added 2026-08-09. **Run this FIRST.**

## Why this stage exists: the 2026-08-08 hardware failure fell straight through

Stages A-C are sound and were followed. The rig still failed with zero
object-directedness. Comparing the run-2 evidence frames against sim renders
afterwards showed why:

```text
                 SIM (trained on)                 REAL (given)
front mount      Robot/base/front_camera          laptop webcam ON THE TABLE
front position   (0.0, -0.5, 0.6) m from base     ~table level
front pitch      161 deg about X, steeply DOWN    near-horizontal
front FOV        ~40 deg (focal 28.7 mm)          ~60-70 deg (webcam)
what fills it    the table, edge to edge          wall, socket, pole, speaker
wrist view       plate fills the frame            2/3 robot's own white body
```

**The protocol tested camera ROBUSTNESS, never camera EQUIVALENCE.** B7 pitched
the front camera **5 degrees** (verdict: mild). B8 jittered the wrist **2 cm**
(verdict: free). Both passed, and cameras were treated as settled. The real gap
was ~0.6 m of height, ~70 deg of pitch and 25 deg of FOV — one to two orders of
magnitude beyond anything tested.

Those are different questions:

```text
ROBUSTNESS   perturb the SIM camera, measure degradation
             -> answers "how much slop does this policy tolerate?"
EQUIVALENCE  compare the REAL rig's geometry against the sim config
             -> answers "are we even inside that tolerance?"
```

B7/B8 answered the first. Everyone read them as answering the second. **A
tolerance is meaningless until you have measured the deviation.**

### The second miss, from this protocol's own rules

Stage B found `gamma135` = **0/3 placed**, the worst run of the entire
preflight, and wrote a hard rig requirement: *"LOCK the real cameras'
auto-white-balance AND auto-exposure ... a drifting white balance is this
policy's one proven kill switch."*

`REALARM_RESULT_20260808.md` records the rig as *"WB locked, **exposure
auto**"*. Half-complied. And the run-2 frames measure at mean brightness
**100/255** — a dim, low-contrast image, which is the direction `gamma135`
proved fatal. This is a live second hypothesis, independent of geometry.

## Stage 0 checks — MANDATORY before any hardware run

```text
0A. CAMERA EXTRINSICS      For each camera, write down the REAL mount point,
                           height, offset and angle. Compare against the sim
                           cfg (single_arm_env_cfg.py). Record the DELTA.
                           A delta you have not measured is not a tolerance.

0B. CAMERA INTRINSICS      Real horizontal FOV vs sim (front ~40 deg,
                           wrist ~32 deg). A stock webcam is 60-70 deg and
                           will include the room. Crop+rescale or use a lens.

0C. FRAMING PASS/FAIL      Put a real photo beside a sim render of the same
                           task. FRONT: the table must fill the frame - if a
                           wall, socket or floor is visible, the camera is
                           wrong. WRIST: the robot's own body must be MINOR,
                           not dominant.

0D. EXPOSURE + WB LOCKED   Both, verified with v4l2-ctl / CAP_PROP_AUTO_WB=0
                           and CAP_PROP_AUTO_EXPOSURE. Stage B proved contrast
                           compression is this policy's kill switch.

0E. STREAM INTEGRITY       Log N frames and check for black/duplicate frames
                           BEFORE the policy runs. Run 2's wrist stream was
                           ~13% dead or stale: c0059/c0060 fully black
                           (mean 1.0, sd 0.0) and 19/142 consecutive pairs
                           identical. The front stream was clean.

0F. TOLERANCE CURVE        Run the sim camera sweep (height, pitch, FOV) to
                           find where THIS policy breaks. Then 0A's delta can
                           be judged against a number instead of a guess.
                           See sim_to_real_camera_alignment_20260809.md.
```

**Stage 0 gates Stages A-C.** If 0A-0E fail, a hardware run measures the rig,
not the policy.

---

# THE TRAINING-TRIGGER FRAMEWORK — standing guidance

## The problem this solves

A hardware failure has two very different explanations, and they demand
opposite responses:

```text
H1  OBSERVATION MISMATCH   the policy is fine; the input was out of
                           distribution. Fix the rig. Training is NOT justified.
H2  TRANSFER FAILS         real pixels/dynamics break it even with matched
                           observations. Training (domain randomisation, real
                           fine-tune) IS justified.
```

Without discriminating them, every failure looks like "needs more training" —
and if that is the default response, **the simulator has no value**: you end up
training only on real data and testing only on real hardware, which is the
expensive path sim was built to avoid.

## The 2026-08-08 result does NOT establish H2

`REALARM_RESULT_20260808.md` concludes "THE AS-IS TRANSFER FAILS". The failure
is real and well-measured. The *attribution* is not yet supported.

A transfer test asks: *given the kind of observation it trained on, does the
policy act correctly in the real world?* What was run was: *given an observation
from a viewpoint it has never seen, does the policy act correctly?* The second
question answers itself and says nothing about the first.

⇒ Treat "as-is transfer fails" as **provisional** until Stage 0 passes and the
test is repeated.

## The decision tree — do not train without landing on a branch

```text
STEP 1  Recreate the real camera geometry IN SIM (snapshot-matched).
        Cost: GPU time only. No hardware.

  FAILS in sim  -> H1 supported. The input was OOD.
                   ACTION: fix the mount to match sim, retest hardware.
                   DO NOT TRAIN YET - transfer has still never been tested.

  WORKS in sim  -> H1 refuted. Geometry alone is not sufficient.
                   ACTION: H2 is live. Training IS justified now, and the
                   sweep tells you what to randomise over.

STEP 2  (only if H1 supported) Retest hardware with the rig matched.

  WORKS         -> sim-to-real transfer CONFIRMED. The simulator has value and
                   the pipeline is real.

  FAILS         -> NOW you have a clean transfer failure with the largest
                   confound removed. THAT is the trigger for domain
                   randomisation or real-data fine-tuning - and you know what
                   to randomise, because Stage 0 measured the residual deltas.
```

## The standing rule

```text
No training run is justified by a hardware failure until Stage 0 passes and the
failure has been reproduced with a matched observation channel.

"Add more data" is not a diagnosis. If the observation channel is not
calibrated, sim and real are not measuring the same quantity, and NO transfer
result - positive or negative - carries information.
```

## What "a sim-real relation" concretely means

Not an abstraction. A **calibrated observation channel**:

```text
extrinsics matched   mount point, height, offset, angle
intrinsics matched   FOV, resolution
pipeline matched     channel order, normalisation, latency, exposure/WB locked
VERIFIED             a sim render and a real photo of the same scene look like
                     the same picture
```

Until that holds, transfer cannot be measured. Once it holds, a negative result
is genuinely informative — and *then* training is aimed at a diagnosed problem
instead of a suspected one.

## Honest downside

If the channel is matched and transfer still fails, the "train in sim, deploy on
real" path is closed for this rig. Sim's remaining value is narrower — varied
data generation, eval harnesses, algorithm development. Worth knowing early, and
another reason to establish the correspondence before spending GPU-months.
