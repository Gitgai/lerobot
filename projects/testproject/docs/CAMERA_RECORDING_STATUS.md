# Camera and Recording Status

> Historical September 15 record, preserved in Git on October 24. This is not a fresh camera check or approval to record. Start from the project README for current task-specific status.

**Verified:** 2026-09-15 on the Ubuntu laptop

## Authoritative physical camera mapping

The cameras currently attached to the machine are:

| Intended name | Physical camera                       | Stable device path                                             |
| ------------- | ------------------------------------- | -------------------------------------------------------------- |
| `front`       | Logitech C270                         | `/dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0` |
| `wrist`       | OV4689, shown by Linux as `AK-Camera` | `/dev/v4l/by-id/usb-SunplusIT_Inc_AK-Camera_JV-video-index0`   |

Linux also exposes the laptop's built-in Acer webcam at `/dev/video0` and related
nodes. It is present, but it is **not** the intended front camera for this rig.
Use the stable `by-id` paths above rather than numeric `/dev/videoN` paths.

## What happened to the 10-episode dataset

The simplified `./bin/so101 record` launcher used the single `camera_name` and
`camera_index` fields in `config/so101.json`. Those fields pointed to the Acer
built-in webcam, and the launcher emitted only one camera configuration.

Therefore `/data/lerobot_datasets/so101_pick_test_new` contains:

- 10 complete episodes
- 17,951 frames at 30 FPS
- `observation.images.front` only
- Acer webcam frames, not C270 frames
- no `observation.images.wrist` feature

The episodes are valid recordings, but they are not the intended C270-plus-wrist
dataset. Missing camera frames cannot be added after recording.

## Legacy configuration warning

Older project scripts used a three-camera naming scheme: built-in laptop camera
as `front`, C270 as `top`, and a Raspberry Pi/HTTP source as `wrist`. That naming
does not match the current physical rig reference. Do not copy that mapping
without checking the target model's camera contract.

## Correct recording setup

The recorder is now configured to emit the current two-camera rig:

```text
front = Logitech C270 (OpenCV, MJPG, with warm-up)
wrist = local OV4689 AK-Camera (OpenCV)
```

The first validation episode was recorded successfully on 2026-09-15 at:

```text
/data/lerobot_datasets/so101_pick_test_c270_wrist
```

It contains one episode, 1,795 frames, and both
`observation.images.front` and `observation.images.wrist` at 30 FPS. The arm
USB connection stayed up and follower torque was verified off afterward.

Run a live frame check for both cameras before additional sessions. Record into
this new dataset or another compatible new directory, and preserve the older
front-only datasets. Do not use `--delete` unless the user explicitly wants
that dataset removed.

## Safety and historical handoff notes

The attached 2026-09-15 handoff described an earlier follower USB-dropout
problem and instructed the next agent not to record until a 30-second test
passed. That was a historical gate, not a permanent prohibition. The follower
later passed the required communication tests, a 60-second default teleoperation
test, and the 10-episode recording run. Torque cleanup is still required after
every arm command.
