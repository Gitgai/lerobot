# Official GR00T N1.6 baseline: read-only audit

Date: 2026-10-04. No hardware access, motor commands, package installs, service restarts or execution-setting changes were performed. This audit reads source/configuration and checks Python imports only.

## Conclusion

The official N1.6 SO100/SO101 reference is synchronous, with raw image transport, an execution horizon of8 actions and a nominal30Hz pacing loop. It does not implement the project's RTC workers, latency-based skip or three-tick blending. Therefore disabling custom RTC alone is insufficient to describe the entire existing client as unmodified official code.

The reference cannot currently run unchanged in Acer's existing venv: the `gr00t` package is absent and the official example's `so100_follower`/`so101_follower` imports are incompatible with the installed LeRobot layout. Use a separate version-matched environment rather than upgrading the working one in place. Preserve the official action-generation/execution logic, and explicitly identify any safety/logging lifecycle integration; do not call such a wrapper completely unmodified official software.

## Source identity

- AI90 checkout: `/home/kiran/sim/Isaac-GR00T-n16`
- Origin: `https://github.com/NVIDIA/Isaac-GR00T`
- HEAD: `ead52833afbbf4243f8cd5e7664f48a94de03b19`, described as `n1.6-release`.
- `gr00t/eval/real_robot/SO100/eval_so100.py` and its `pyproject.toml` have no working-tree diff against that HEAD.
- Working tree is NOT entirely clean: `gr00t/policy/server_client.py` has an added JPEG decoder; `gr00t/experiment/launch_finetune.py` also has changes. Backup files exist. Do not reset or discard them.
- This verifies the locally checked-out release and clean reference files, not a fresh independent verification of all upstream objects or all loaded model tensors.
- Pinned source reference: https://github.com/NVIDIA/Isaac-GR00T/blob/ead52833afbbf4243f8cd5e7664f48a94de03b19/gr00t/eval/real_robot/SO100/eval_so100.py

## Execution comparison

| Aspect               | Official reference at this commit                                                       | Existing project path                                             | Baseline decision                                                                           |
| -------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Request timing       | Blocking get_action, then execute, then next observation                                | RTC overlaps requests and execution                               | Use official synchronous sequence                                                           |
| Execute per response | `action_horizon=8` by default                                                           | RTC walks/skips a16-step reply; sequential path defaults8         | Use8 for initial baseline, without claiming16 predicted means16 executed                    |
| Pacing               | Sleep remainder of1/30s after each send                                                 | 30Hz plus project diagnostics/scheduling                          | Keep official pacing; document logging overhead                                             |
| RTC                  | No RTC option/loop in this reference                                                    | Custom workers, age-based entry index,3-tick blend                | Exclude custom RTC                                                                          |
| Images               | Raw NumPy arrays via msgpack/NPY                                                        | JPEG92 extension in recent trials                                 | Raw official wire format for strict baseline                                                |
| Adapter              | front/wrist; five arm joints plus gripper; B=1,T=1; server reply mapped directly        | Same observed ordering/shape logic; optional JPEG                 | Reuse official adapter; do not add current joint state twice                                |
| Timeout              | Config includes `timeout=60`, but inspected eval loop never uses it and is `while True` | Current numbered launcher has no trial timer                      | Do not mistake unused60 for enforced runtime limit                                          |
| Request timeout      | Constructor accepts15000ms but official socket initialization does not set RCVTIMEO     | Project client explicitly sets RCVTIMEO                           | Document behavioral difference and stop implications; do not silently claim equivalence     |
| Lifecycle            | robot.connect, infinite eval loop; no explicit try/finally disconnect in this file      | Project signal/cleanup/Status monitoring                          | Preserve safe stop integration explicitly; do not drop cleanup just to match a minimal demo |
| Evidence             | Prints actions; no equivalent full two-camera trial journal                             | Images, motor telemetry, target/stop logs and automatic reporting | Integrate evidence without modifying targets; verify new client coverage                    |

Raw transport changes bandwidth relative to prior JPEG trials. Do not interpret any timing change as RTC-only causation. A remote connection may introduce longer gaps between chunks; official does not imply continuous motion over this network.

## Environment compatibility

Official example dependencies pin LeRobot to `c75455a6de5c818fa1bb69fb2d92423e86c70475` and instruct a no-dependencies editable GR00T install. These are source instructions, not commands executed in this audit.

Acer existing venv: `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv`.

- Installed LeRobot reports0.5.2 from local source checkout HEAD `ad10219fea3a6b52f93cde9b0d293ad8d48c064a`.
- `gr00t`: not installed.
- numpy-related transport dependencies msgpack/zmq and torch are discoverable.
- Read-only import `from lerobot.robots import so100_follower, so101_follower` fails with ImportError.

Thus `python official_eval.py` in the current venv is not a ready launch command. The existing script's vendor/adaptation approach avoided these dependencies, but is not an untouched upstream client.

## Server/checkpoint and action mapping

Recovery checkpoint6000 is the intended unchanged model. Checkpoint metadata/index hashes read from disk:

```text
model.safetensors.index.json e990f96cb8663eba1fa901b4491fe70e2003d847f49f62a6a6e825a58ea2e0e2
config.json cd265fe9f1c037188a09d317155d3a4c28d1db1a5d8f0bb129934b5e170fdd27
```

These are NOT hashes of the actual weight shards and do not alone establish live loaded-weight identity.

The project modality config registers NEW_EMBODIMENT, front/wrist images, single_arm/gripper state,16 predicted action steps, RELATIVE arm and ABSOLUTE gripper representation. Both inspected adapters map server outputs directly to the same six joint names. Config comments state relative-to-absolute composition occurs server-side; inspect the actual processor conversion and checkpoint artifacts before declaring full end-to-end equivalence. Keep calibrated arm degrees and normalized gripper positions consistent with training.

The server decoder diff only adds JPEG handling; its raw array branch remains unchanged. A raw client can avoid that JPEG branch, but a server with an inactive custom patch is still not a byte-for-byte clean installation. For a strictly clean baseline, prepare an isolated clean server path or explicitly document the retained inactive extension; do not mutate the existing shared server.

## Next preparation steps

1. Prepare a separate pinned official client environment; validate dependencies/imports without replacing the existing venv. Check the pinned LeRobot driver's startup/register defaults against existing protections before any connection.
2. Complete actual processor/output-unit and full checkpoint provenance verification; check clean official server feasibility without disrupting the current service.
3. Choose the minimum explicit stop/recording integration that leaves official requests, returned actions and execution unchanged. If additional policy/device adaptation beyond lifecycle/recording is required, report it before implementation.
4. Record an exact baseline command only after compatibility is established. Use the tomato label, correct ports and camera IDs,8 executed actions, raw transport and no custom RTC. Do not invent an executable command before the environment is ready.
5. Only after fresh rig readiness, run the separately numbered three-trial set under the parent plan. Fault recurrence stops progression to the next trial; no clearing/retrying or increased limits.

Not performed: environment creation, complete dependency resolution, weight-shard hashing, running server audit of loaded tensors, hardware readiness, inference requests, or physical trials. No mandatory fake-actuator gate is added.
