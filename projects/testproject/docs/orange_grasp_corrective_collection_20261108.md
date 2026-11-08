# Orange grasp-centering demonstration plan

Date: 2026-11-08  
Dataset: `orange_grasp_corrective_ft4_20261108`  
Task text: `pick up the orange and place it on the plate`  
Status: no-motion preflight passed; one of five pilot demonstrations accepted

## Why this dataset is needed

Fine-tune 3 completes orange-to-tray in 15 of 57 trials (26.3%). The dominant failure occurs before transport: the
gripper closes beside the orange, usually with the orange outside the left finger, or closes while too shallow to
make contact. The three whole-episode 10-action trials were 0/3, so changing the action horizon did not fix the
spatial error.

The model already trained on 30 off-target recovery demonstrations from `esp_recovery` / `recovery30_v21`. Those
removed the earlier hover/no-descent failure. This collection must teach the narrower behavior that is still weak:
open-centre-close-lift, including a visible correction before a bad close.

## Collection protocol

Record one episode per recorder launch. Use the leader arm to demonstrate the entire task while the follower and
both policy cameras are recorded at 30 Hz.

For every accepted episode:

1. Start with the orange and tray visible, cameras fixed, and hands clear of both camera views.
2. Approach with the gripper visibly open.
3. Pause or slow briefly when the orange is between the fingers; do not close beside it.
4. Close with the orange contacting both inner finger surfaces.
5. Lift 3-5 cm and retain it briefly so the grasp is unambiguous.
6. Carry smoothly to the tray, release inside it, and move clear.
7. End without touching a camera, tray, or follower arm.

For a corrective episode, deliberately begin with a small safe lateral or shallow error while the gripper remains
open. Show the correction in view, then perform the same centred close and lift. Never demonstrate a collision,
hard push, blind close, or large recovery outside the established workspace.

## Balanced 30-episode target

Use five marked orange positions. Collect six accepted episodes at each position:

- three direct centred grasps;
- one correction from the orange appearing outside the left finger;
- one correction from the orange appearing outside the right finger;
- one shallow/depth correction.

The first milestone is five accepted pilot episodes, one per position. We inspect these before recording the other
25. This catches swapped cameras, weak closes, occlusion, timing errors, or an unsuitable placement distribution
before a full session is recorded.

Episode 0 was recorded on 2026-11-08 with 1,347 frames from each camera. It had a centred grasp and secure lift, but
the gripper remained closed over the tray and held the orange against the rim through the end of the 45-second
recording. The recorder then reported motor 6 overload while disconnecting. A direct safety check found torque off
on all six motors, zero load, 6.5-6.6 V and normal 31-33 C temperatures. Episode 0 is preserved but rejected for
`release`; it is not one of the five accepted pilot episodes. Subsequent recordings use 35 seconds, enough for a
20-30-second demonstration plus a move-clear margin without a long loaded hold.

Episode 1 was recorded with 1,048 frames from each camera and passed every acceptance check: centred pre-close,
bilateral contact, secure lift, controlled transport, release inside the tray and a clean move-clear. Disconnect was
normal, and the subsequent safety check found torque off, zero load and 6.6-6.7 V. Pilot progress is 1/5 accepted.

## Acceptance rating

An episode is accepted only when every item below is `yes`:

| Check | Evidence |
|---|---|
| Both cameras valid | Front and wrist streams are fresh, correctly named, synchronized and free of long dropouts |
| Correct scene | One orange, fixed tray, intended marked position, no distractor or hand occlusion |
| Centred pre-close | Both fingers visibly straddle the orange at usable depth before closure |
| Bilateral close | Orange contacts both sides; no outside-jaw close or table push |
| Secure lift | Orange follows the gripper by at least 3 cm and remains held during a short pause |
| Controlled transport | No slip, collision, cable pull, or extreme joint excursion |
| Correct release | Orange is released and remains inside the tray |
| Clean completion | Arm moves clear and the episode ends normally |

Rejected episodes are labelled with one primary reason: `camera`, `scene`, `centering`, `contact`, `lift`,
`transport`, `release`, or `completion`. They are preserved for diagnosis and excluded from the positive imitation
dataset.

## Commands

No-motion preflight:

```bash
projects/testproject/scripts/bench/record_orange_grasp_corrective.sh --check
```

Record exactly one new episode after the scene and leader arm are ready:

```bash
projects/testproject/scripts/bench/record_orange_grasp_corrective.sh --record
```

The script resolves arms by controller serial and cameras by hardware name. It refuses to record when calibration,
either arm, either camera, or an existing empty/corrupt dataset is missing. It never deletes a dataset.

During recording, the same LeRobot process publishes its front and wrist observations, joint/action values, and a
35-second countdown to the local Rerun server on ports 9882/9116. The browser viewer consumes that Rerun stream; it
does not open either camera and therefore does not compete with the recorder.

### Preflight result

The no-motion preflight passed on 2026-11-08. It resolved the follower as `/dev/ttyACM0` and the leader as
`/dev/ttyACM1` by controller serial, the C270 front camera as `/dev/video6`, and the AK wrist camera as
`/dev/video0`. Both cameras delivered nonblank 640×480 frames, both calibration files were present, and the official
LeRobot recorder imports loaded. The C270 produced black warm-up frames while automatic exposure settled; the
preflight now waits for three usable frames instead of treating those warm-up frames as a fault.

## After the five-episode pilot

Generate front/wrist contact sheets and inspect the close and first lift. Add the decision to `episodes.csv`. If all
five are accepted, continue to 30 accepted episodes. Then generate hashes, distribution counts and an episode-level
held-out split before fine-tune 4. Do not start training from an unaudited folder or report training loss as robot
success.
