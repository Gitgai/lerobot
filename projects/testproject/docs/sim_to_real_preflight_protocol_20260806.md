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
