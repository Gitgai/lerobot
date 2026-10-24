# SO101 LeRobot Project Handover

> Historical handover, preserved on October 24. Claims and paths below describe the earlier session and may be obsolete; in particular, USB-reset signatures did not conclusively rule out software or power problems. This is not current training/trial authority. Start from the project README.

Date: 2026-09-15

Recipient: Claude

Purpose: This document records the verified setup, physical-arm investigation, camera configuration, recordings, data quality, and unresolved training decisions for the SO101 LeRobot project.

## Current conclusion

Thirty usable episodes have been recorded. There are twenty orange episodes and ten tomato episodes. Both the Logitech C270 front camera and the wrist camera were recorded in the latest clean datasets.

The recordings are ready for training preparation, but the policy model has not been selected. Do not assume ACT is the chosen model. ACT was only investigated as one possible LeRobot policy. The handoff plan refers to a checkpoint called `orange_pick_baseline_v1`, but that checkpoint and its policy configuration have not been found locally.

## Project locations

- LeRobot source: `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot`
- Project: `/home/gaikwad-prakash/lerobot/lerobot/projects/testproject`
- Virtual environment: `/home/gaikwad-prakash/lerobot/lerobot/projects/testproject/.venv`
- Project configuration: `/home/gaikwad-prakash/lerobot/lerobot/projects/testproject/config/so101.json`
- Project runner: `/home/gaikwad-prakash/lerobot/lerobot/projects/testproject/scripts/so101_runner.py`

The original project launcher had stale virtual-environment paths and stale console-script shebangs. Until that is repaired everywhere, use the project virtual environment directly:

```bash
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/.venv/bin/python
```

The shell also prints an unrelated `.profile` warning about a missing VS Code `env` path. It does not affect LeRobot.

## Robot and USB investigation

The leader and follower are SO101 arms using identical CH340 USB boards.

The follower initially dropped from USB on `/dev/ttyACM3-2` and then again on `/dev/ttyACM3-1`. The leader did not drop. The follower dropped both with torque enabled and with torque disabled. The servo supply remained approximately 5.9 V during one failure. Kernel logs showed clean disconnect and reconnect events without signal-integrity errors.

The investigation therefore pointed to the follower's own USB path: cable, connector, board socket, or board reset. The first failures were not explained by the teleoperation script, laptop USB port, or the gripper alignment.

Later recording sessions completed successfully, including the latest ten-episode tomato session. The follower torque-cleanup script reported every follower joint torque off after recording.

Stable serial paths now used by the project are:

```text
Leader:   /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14029688-if00
Follower: /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00
```

The runner resolves devices by serial identity instead of trusting changing `/dev/ttyACM*` numbers.

## Alignment and safety notes

During the earlier investigation, five joints tracked within roughly half a degree. The gripper had a large initial difference, but this was not the joint that repeatedly caused the first USB failures. The arms did track one another before the crashes.

A temporary first-step safety restriction was tested earlier. It was not a LeRobot default and must not be treated as the final configuration. The current project configuration sets:

```json
"default_max_relative_target": null
```

That means the project does not add a custom 5-degree movement clamp; it leaves the relative-target behavior at LeRobot's default.

## Camera setup

The current recording configuration uses two cameras:

```text
Front camera: Logitech C270
Path: /dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0

Wrist camera: SunplusIT AK-Camera
Path: /dev/v4l/by-id/usb-SunplusIT_Inc_AK-Camera_JV-video-index0
```

Both are recorded at 640x480 and 30 FPS using MJPG input. The final LeRobot videos are AV1 MP4 files.

The built-in Acer webcam was previously used by an incorrect recorder configuration. It is not the intended front camera for the current clean datasets.

The two camera images at one timestamp are two views of one training sample. One sample contains the front image, wrist image, robot state, and action. The model receives both images together only when the selected policy is configured to use both image features.

## Recorded datasets

The following three datasets are the clean training candidates. The older test datasets, failed stubs, and partial retries are not included in the total of thirty and should remain untouched.

| Dataset                                                            | Episodes | Frames | Task                                       |
| ------------------------------------------------------------------ | -------: | -----: | ------------------------------------------ |
| `/data/lerobot_datasets/so101_pick_test_c270_wrist_10eps_final`    |       10 | 17,951 | Pick up the orange and put it on the plate |
| `/data/lerobot_datasets/so101_pick_test_c270_wrist_10eps_adjusted` |       10 | 17,950 | Pick up the orange and put it on the plate |
| `/data/lerobot_datasets/so101_pick_test_c270_wrist_tomato_10eps`   |       10 |  8,980 | Pick up the tomato and put it on the plate |
| Total                                                              |       30 | 44,881 | Two related tasks                          |

The first ten orange episodes used the earlier wrist-camera position. The second ten orange episodes were recorded after moving the wrist camera slightly farther back. The tomato episodes used the corrected setup and approximately 30 seconds per episode.

Each dataset is LeRobot v3.0 with:

- `action`: six joint positions
- `observation.state`: six joint positions
- `observation.images.front`
- `observation.images.wrist`
- timestamps and episode/frame indices
- no audio

The twenty orange episodes use the exact task text `pick up the orange and put it on the plate`. The ten tomato episodes use `pick up the tomato and put it on the plate`. The earlier handoff plan mentioned apple episodes, but the actual new recordings are tomato episodes; no apple episodes are part of this thirty-episode total.

## Data quality findings

The final tomato dataset was checked at the metadata, data, video, and sample-loading levels:

- 10 episodes and 8,980 frames
- 898 frames per episode, approximately 29.93 seconds each
- indices are contiguous from 0 through 8,979
- actions and states contain no non-finite values
- both front and wrist videos contain 8,980 frames
- both videos decode successfully with FFmpeg
- random and edge samples load correctly through `LeRobotDataset`
- the latest recording log has no traceback, timeout, or corrupt-JPEG warning

Visual checks showed the tomato outside the plate at the beginning and on the plate at the end of the sampled episodes. The adjusted orange dataset also showed the orange being placed on the plate in its start/end checks.

The wrist camera is useful, especially for close-up grasping, but it is weaker than the front camera. The gripper jaws occupy a substantial part of many wrist images, and some motion-blurred frames exist.

Measured one-frame-per-second quality checks found:

- Tomato wrist camera: 19 of 299 samples, about 6.4%, had very low sharpness.
- Adjusted orange wrist camera: 27 of 599 samples, about 4.5%, had very low sharpness.
- The corresponding front-camera samples had no frames below the same low-sharpness threshold.

These are quality indicators, not proof that those frames must be deleted. The wrist data remains usable as a secondary view.

The earlier log messages such as `Corrupt JPEG data` were warnings from decoding incoming MJPG camera packets. They can indicate a small number of damaged source frames, but they do not by themselves prove that the final MP4 is corrupt. The saved datasets were checked by decoding the output videos.

## What the action and state data mean

At each timestamp, the dataset pairs the current visual observation and follower state with the leader-derived action. Conceptually:

```text
front image + wrist image + current joint state -> desired robot action
```

There are 44,881 synchronized time samples, not 89,762 independent samples. There are 44,881 front images and 44,881 wrist images, but each pair belongs to the same timestamp and predicts one action.

The data is behavior-cloning data. It does not contain an independent success or reward label. The demonstrations themselves are the supervision. Held-out real-arm trials are still needed to measure whether the trained policy really grasps and places the object.

## Training decision that is still open

No policy architecture has been chosen. The supplied handoff plan says:

1. Record 20 orange-plate episodes and 10 additional object episodes.
2. Hold five of the twenty orange episodes out of training.
3. Train from `orange_pick_baseline_v1` for 6,000 steps.
4. Evaluate held-out demonstrations offline, then evaluate on the arm while scoring grasp and place separately.

The name `orange_pick_baseline_v1` was not found in the local source tree, Downloads folder, or dataset directories. It may be a remote checkpoint or may exist on another machine. Its `config.json` or `train_config.json` is needed to identify the policy type and input format.

ACT must not be described as the selected model. If ACT is eventually selected, its local implementation uses images, robot state, and action chunks; it does not tokenize the natural-language task string. The orange/tomato difference would then have to be inferred visually. A language-conditioned policy such as SmolVLA would use the task text, but it requires additional dependencies and normally a GPU.

## Current training environment

The project virtual environment contains LeRobot 0.5.2, PyTorch 2.10.0, torchvision, datasets, torchcodec, and PyAV. It currently does not contain `accelerate` or `transformers`. CUDA is not available and no NVIDIA GPU was detected.

For an ACT-style training experiment only, the missing general training dependency can be installed with:

```bash
/home/gaikwad-prakash/.local/bin/uv pip install \
  --python /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/.venv/bin/python \
  -e '.[training]'
```

Do not install policy-specific dependencies or start training until the intended policy has been confirmed.

## Safe dataset preparation options

The original datasets should not be overwritten. If the first baseline is an orange-only policy, merge the two orange datasets into a new output directory. If the goal is one policy for both objects, merge all three datasets into a new output directory.

Example all-thirty merge:

```bash
cd /home/gaikwad-prakash/PrakashProjects/lerobot

./projects/testproject/.venv/bin/lerobot-edit-dataset \
  --new_repo_id local/so101_orange_tomato_30eps \
  --new_root /data/lerobot_datasets/so101_orange_tomato_30eps \
  --operation.type merge \
  --operation.repo_ids "['local/so101_pick_test_c270_wrist_10eps_final','local/so101_pick_test_c270_wrist_10eps_adjusted','local/so101_pick_test_c270_wrist_tomato_10eps']" \
  --operation.roots "['/data/lerobot_datasets/so101_pick_test_c270_wrist_10eps_final','/data/lerobot_datasets/so101_pick_test_c270_wrist_10eps_adjusted','/data/lerobot_datasets/so101_pick_test_c270_wrist_tomato_10eps']"
```

This LeRobot version does not currently support passing a list of datasets directly to the standard training pipeline, so merging is the safe way to create one training dataset.

Recommended order:

1. Locate `orange_pick_baseline_v1` and identify its policy type.
2. Build an orange-only baseline from the twenty orange episodes, holding out five complete episodes.
3. Train using the baseline's documented 6,000-step budget if its configuration confirms that plan.
4. Evaluate held-out orange episodes offline.
5. Test the trained policy on the physical arm with low-risk, torque-safe procedures.
6. Train tomato separately or create a combined orange/tomato policy only after deciding whether language conditioning is required.

## Files and logs of interest

- Configuration: `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/config/so101.json`
- Runner: `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/scripts/so101_runner.py`
- Latest tomato recording log: `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/logs/so101/20260915_201125_record.log`
- Latest follower torque cleanup: `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/scripts/disable_follower_torque.py`

The latest recording process has stopped and the follower torque cleanup reported all follower joints off.

## Handover cautions

- Do not delete or overwrite any of the three clean datasets.
- Do not include the old test episode, front-only ten-episode dataset, empty stub, or partial retry in the clean thirty-episode count without reviewing them first.
- Do not call ACT the selected model until the baseline checkpoint is located.
- Do not assume task text is used by every policy.
- Do not train from random frames while claiming a held-out evaluation; hold out complete episodes to avoid temporal leakage.
- Before any physical rollout, confirm the follower USB connection, power supply, camera paths, and torque-release behavior.
