> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/SAVED_4K_SERVING_CHECK_20261020.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# Saved 4k checkpoint and serving check — 20 October 2026

## Scope and result

User explicitly requested offline checks only, **no physical trial**.

Passed: official OpenPI fresh checkpoint loading, prediction on 33 recorded validation observations, and two loopback WebSocket requests using the official server handler. The temporary loopback listener closed and the diagnostic process exited successfully. No robot connection, live camera access, movement, motor settings, package installation or installed-source changes.

This verifies an OpenPI serving path, **not drop-in compatibility with the previous LeRobot robot/RTC client**.

## Evidence

- [Serving report](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/saved_4k_serving_report.json).
- [33-observation reload evaluation](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/saved_4k_reload_evaluation.json).
- [Diagnostic script](/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/check_saved_fruit_serving.py).
- Remote evidence directory: `/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX/saved_4k_serving_check`.
- Checkpoint: `/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX/checkpoints/pi05_fruit55_lora_vision/fruit55_lora_vision_5k/4000`.
- Interpreter: `/home/kiran/sim/openpi/.venv/bin/python`.
- Source revision: `0a0b19f2896856bb8e4cb3904ebf3b508c20a4f6`; remote `git status --short` returned empty.
- GPU: RTX PRO 5000, UUID `GPU-9245300a-3a82-0401-5417-dbeb319e5858`. Other GPU workloads left untouched.

`create_trained_policy` loaded saved parameters as bfloat16 and normalization from the checkpoint assets. This was not inference from the training process's in-memory state.

## Recorded-data check

Selected start, midpoint and end from each of 11 validation episodes: 27 orange observations and 6 tomato observations. Every prediction was finite with shape `(30, 6)`; the evaluator validated targets and padding counts and saved repeated same-process predictions.

These 33 observations are an integration check, not a replacement for the full 10,307-observation comparison. Their MAE must not be compared directly with full-manifest MAE as evidence of improvement. A full repeated checkpoint ranking and exact equality to training-time validation were not established here.

Inputs: six joint-state values, front image, wrist image, fruit-specific instruction. Outputs: 30 actions, each containing five joint targets in degrees plus gripper position in normalized points. The existing fruit adapter preserves the training mapping; missing right-wrist input is masked.

## Transport check

The official `WebsocketPolicyServer._handler` ran on an ephemeral **127.0.0.1-only** listener on AI90. The diagnostic sent MessagePack requests and checked metadata, finite `(30,6)` replies and server timings. No listener was exposed to Acer or the robot.

| Saved observation | Round trip | Server inference |
| ----------------- | ---------: | ---------------: |
| Orange episode 2  |    4.549 s |          4.544 s |
| Tomato episode 47 |    0.084 s |          0.080 s |

First-call compilation/warmup may contribute to the large first request; its components were not separately profiled. Two calls are not a latency benchmark or a network-delay estimate.

Requests used the recorded loader's float32 CHW images: **7,373,085 bytes per request**. This is a diagnostic representation, not an approved deployment format. No JPEG was used. Do not confuse it with the approximately 1.84 MB pair of uint8 RGB images from earlier deployments.

## Compatibility gap

The inspected pinned OpenPI `Pi0.sample_actions` signature accepts observation, denoising-step count and optional noise. It does **not** expose the remaining-action-prefix/inference-delay inputs of the earlier LeRobot guided-RTC path. Its attention “prefix” refers to observation tokens, not evidence of RTC.

The official OpenPI server invokes `policy.infer(obs)` over WebSocket. The earlier LeRobot/remote-draft robot path and checkpoint loaders are different. A passed loopback request does not validate JPEG decoding, RTC, queue scheduling, cross-machine transport, Rerun tracing or physical behavior.

No custom RTC implementation, weight conversion, client replacement or silent RTC-off deployment was introduced.

## Next offline work

1. Identify an officially supported serving route that can consume this exact OpenPI LoRA-plus-vision checkpoint while satisfying the intended RTC requirements.
2. Document any necessary conversion or bridge and verify all learned components and normalization survive it; do not assume a LoRA-only export captures the learned vision weights.
3. Only after choosing that route, test recorded-data requests between Acer and AI90, image encoding, action ordering and tracing without robot imports or connections.
4. Preserve current environments/checkpoints. The diagnostic leaves only its isolated script and reports; no rollback of installed code is needed.

**Physical trials remain excluded by the user's current instruction.**
