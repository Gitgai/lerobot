# Plate round: continuation training, and the wrist-camera decision

Session of 2026-09-01. Two threads: finishing a longer training run against
machine contention, and testing an ESP32 camera as a wrist-camera replacement.

## 1. Why plate_v2 exists

At step 6000, plate_v1's held-out orange error was STILL FALLING:

```text
                    held-out orange error
baseline                    2.41
plate_v1 step 1500          3.24   <- degraded
plate_v1 step 3000          2.92
plate_v1 step 4500          2.72
plate_v1 step 6000          2.50   <- still improving, not flat
```

The question: does it keep improving past 6000, flatten, or turn back up?
That fixes the step budget for every future round.

WHAT THIS RUN CANNOT ANSWER: whether the PLATE skill improved. All 20 plate
demos are in training, so nothing is held back to score them against. Only the
arm can judge that.

>>> ACTION FOR THE NEXT DATASET: hold 5-10 plate demos OUT of training. <<<
Without a held-out set, "should we train longer?" is unanswerable offline and
every future round repeats this same blind spot.

## 2. The machine is shared - and it bit us three times

The GPU box also runs the DYNUS drone flight campaign in Docker. Those
containers take ~10 cores and peak at 24 GB on a 59 GB machine. Training needs
~20 GB. Under combined pressure `systemd-oomd` terminates the largest consumer,
which is the training. It sends SIGTERM, so the signature is EXIT=143 with NO
error in the log and NO entry from the kernel OOM killer.

```text
attempt 1  killed at step 896   no checkpoint yet   16 min lost
attempt 2  killed at step 1558  ckpt-1500 saved     58 steps lost
attempt 3  killed at step 1564  ckpt-1000 saved    564 steps lost
attempt 4  running with the flight queue idle
```

Lessons, in order of value:

1. **EXIT=143 with a clean log means systemd-oomd, not a bug.** Do not go
   looking for a crash. Check `docker stats` and `free -g` first.
2. **Checkpoint often when sharing the machine.** Attempt 1 lost everything
   because its first save was 600 steps away. Saves every 1000 turned "start
   over" into "lose fifteen minutes".
3. **Resume from the checkpoint, do not restart.** The chain
   plate_v1(6000) -> v2/ckpt-1500 -> v2b/ckpt-1000 -> v2c preserved every step
   that survived.
4. **The flights are the priority campaign; the training gives way.** Stopping
   a container would destroy a 1 km forest flight mid-run AND the batch driver
   would immediately start the next one. Training is the cheap thing to lose.
   The right move is to run training in gaps between flight batches.

## 3. ESP32-S3 as wrist camera - MEASURED, works

Context: the Pi's OV5647 ribbon keeps dying under arm vibration. It has frozen
mid-session twice and cost five arm trials (see plate_train_v1_results).

A Seeed XIAO ESP32-S3 Sense was flashed with a camera server exposing the SAME
interface the robot client already speaks, so only `--wrist_url` changes:

```text
GET /frame    640x480 JPEG + X-Frame-Age-Seconds   <- what the robot reads
GET /stream   MJPEG, plays in any browser
GET /health   rssi, ip, uptime
GET /         viewer page
```

Mock test on the arm, 2026-09-01 (no policy, no GPU):

```text
latency      min 35 / median 46 / max 105 ms      (Pi camera: ~45 ms)
liveness     10/10 unique frames
frame age    0.001 s
uptime       3 h continuous on a USB charger, no faults
mounted?     YES - image changes with arm motion, and MORE for bigger moves
             pan -30 vs -10:  9.9      pan -30 vs +30: 35.1
```

Chain comparison:

```text
Pi     camera -> ribbon -> Pi -> rpicam-vid -> proxy -> client   (4 failure modes hit)
ESP32  board -> client                                           (none yet)
```

### The decision, and it is NOT "switch now"

The ESP32's sensor (OV2640) produces visibly different images from the OV5647
the policy learned from - wider view, different colour, different framing. This
policy's tolerance for image change is near zero: four tape markers took it from
90% to 0%. Swapping the camera would very likely require re-recording all 99
demonstrations.

>>> ADOPT THE ESP32 AT THE MOMENT WE RE-RECORD, NOT BEFORE. <<<
Expanding to 60-80 plate demos already requires recording. Doing both at once
costs nothing extra and permanently retires the ribbon failure.

Until then the OV5647 stays, and it needs a REPLACEMENT RIBBON to be trusted.

Firmware and toolchain live on the arm laptop at `~/esp32work/`; the sketch is
mirrored (with WiFi placeholders) at `scripts/esp32_wrist_cam/`.

## 3b. RESULT: more training buys almost nothing

Every checkpoint, same 10 held-out orange episodes, same probe:

```text
baseline                          2.41
plate_v1  step 1500               3.24
          step 3000               2.92
          step 4500               2.72
          step 6000               2.50
plate_v2  global ~9500            3.08   <- restart spike
          global ~10500           2.67
          global ~11500           2.37   <- best of all
          global ~12000           2.46   <- turned back up
```

ANSWER TO THE QUESTION THIS RUN EXISTED FOR: the curve turns around global
~11500. Doubling the training moved the error 2.50 -> 2.37 at best, then it
worsened. 6000 steps was already the right budget.

Two cautions on reading that table:

1. The sawtooth is the WARM RESTARTS, not learning. Each resume re-runs LR
   warmup and knocks the model off its settled point (3.24 at v1's first save,
   3.08 after the v2 restart), then it recovers. Artefact, not property.
2. 2.37 vs 2.41 vs 2.46 is a 0.09 spread over 60 samples. Do not call the
   "best" checkpoint better than baseline. The honest reading: they are
   equivalent, and the orange skill briefly lost early in training came back.

CONSEQUENCE: training longer is not the lever - DATA is. 20 plate demos against
79 orange ones is the limit, and more passes over those 20 do not move it.
plate_v1 (step 6000) stays the model to test on the arm; nothing here justifies
switching to a v2 checkpoint.

AND STILL INVISIBLE: every number above measures ORANGE picking. Whether the
plate skill improved cannot be seen offline at all, because all 20 plate demos
are in training. Hold 5-10 out next time.

## 4. State at the end of this session

```text
models     orange_pick_baseline_v1   FROZEN, 9/10 on the arm
           plate_v1                  1 honest arm trial: grasped 9 s, no carry
           plate_v2 (in progress)    reaching global step ~12000
rig        arm       connected, USB 3-2 (NOT 3-1, which is faulty)
           wrist cam Pi OV5647 unreliable; ESP32 works but changes the images
           esp32     192.168.1.35:8092 (DHCP - may move)
```

## 5. Next

```text
[NJ]    score every plate_v2 checkpoint on the held-out orange episodes;
        report where the curve turns
[bench] replacement OV5647 ribbon -> then plate_v1 gets its real 10-run test
[bench] record 40-60 more plate demos, holding 5-10 OUT of training,
        proportions ~40% familiar band / ~40% operator-right / ~20% left
[both]  switch to the ESP32 AT that recording session, not before
[NJ]    client guard: abort a run the moment wrist frame age exceeds ~1 s
        (five trials have been wasted driving on a frozen camera)
```
