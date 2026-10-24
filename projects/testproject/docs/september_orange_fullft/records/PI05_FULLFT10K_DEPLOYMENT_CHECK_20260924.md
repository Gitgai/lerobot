# π0.5 full-FT 10k: hardware-free deployment check

Date: 2026-09-24. Status: **model/processor/network correctness passed; substantial remote delay remains. No physical trial clearance.**

Only the selected new full-fine-tuned 10k checkpoint was tested. No LoRA inference/comparison, retraining, motor access, live camera capture, homing or motor-setting change occurred. GR00T PID 11632 and its service on port 5555 were left running.

## Result in plain language

The GPU server receives the recorded images and state in the correct form and returns exactly the same predictions as the independently verified offline 10k model. No adapter merge is needed: this full-FT checkpoint loads directly.

The outstanding deployment issue is response time. Ordinary SSH requests took a median 2.743 seconds; losslessly compressed SSH requests took 1.737 seconds. Server prediction processing itself took a median 0.093 seconds. Transport/RPC waiting dominates the gap; this is not evidence that more model training would fix response latency.

This verifies a diagnostic server/transport path, not motor tracking, physical grasp success or readiness to start RTC. The existing live launcher is still pinned to the older model and was not silently repointed.

## Identity and scope

Checkpoint on GPU host:

`/home/kiran/sim/pi05-fullft-orange50-20260922/orange45_fullft_15k_candidate/checkpoints/010000/pretrained_model`

The diagnostic wrapper checks the model SHA-256 and saved processor hashes against the completed checkpoint evaluation. It accepts only that checkpoint, CUDA, the exact camera/state feature mapping, 50 actions and no rename map. Configuration checks require no PEFT, no relative-action mode and no RTC.

A deliberately unapproved checkpoint request was rejected before model loading. The approved setup then loaded successfully in 61.71 seconds. Setup time is separate from request timing. The diagnostic uses fixed seed 0 and BF16 autocast to match the saved offline reference; the fixed seed is not a decision about physical deployment sampling.

The pickle-based official LeRobot gRPC transport was exposed only on GPU loopback `127.0.0.1:8085`, reached through authenticated SSH tunnels on laptop loopback ports 18085 and 18086. It was not exposed as a public inference endpoint.

## Recorded inputs and exact matching

- 16 recorded timestamp inputs spanning all nine held-out episodes; selected early/late views and previously identified high-error windows.
- Every input includes front and wrist RGB images at 640×480, six-joint state and the orange-to-plate task instruction.
- Input state/image/target/mask/task hashes were matched to the prior offline comparison before replay.
- Demonstrated targets and reference predictions remained client-side comparison data; they were not sent as model inputs.
- State order: shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper. Five arm values use degrees; gripper uses normalized position points.
- The server independently compared its raw-observation conversion against the dataset-style preprocessing path. Camera tensors, normalized state, language tokens and attention masks matched **exactly on all 32 requests**.
- Each input was replayed once over ordinary SSH and once over compressed SSH, alternating which path went first: **32 total requests**.
- All 32 replies contained exactly 50 finite six-joint actions with the expected timestep sequence.
- All replies matched the corresponding saved offline prediction with **maximum absolute difference 0**. No prediction difference was introduced by compression.

This is stronger than matching dimensions alone, but it remains a saved-input test. No camera exposure timing or live scene equivalence was measured.

## Timing results

| Measurement                       | Ordinary SSH | Losslessly compressed SSH |
| --------------------------------- | -----------: | ------------------------: |
| Requests                          |           16 |                        16 |
| Median end-to-end                 |      2.743 s |                   1.737 s |
| p95 end-to-end                    |      4.069 s |                   2.187 s |
| Maximum end-to-end                |      5.888 s |                   2.195 s |
| Median upload/acknowledgement     |      1.840 s |                   1.379 s |
| Replies slower than 50/30 seconds |        15/16 |                      9/16 |

Compression reduced the median by approximately **36.7%** in this paired experiment. It did not eliminate the delay or establish a worst-case bound.

The server-side preprocessing/inference/postprocessing path had median **0.0933 s**, p95 **0.0960 s** and maximum **0.3944 s**. The extra tensor-parity assertions run before that server timer, while end-to-end timing includes them. Therefore this is not a precise pure-network/GPU split. Total time includes serialization, upload, RPC waiting, server work, download, decoding and validation; it excludes camera capture and motor execution. CPU scheduling and diagnostic overhead can contribute.

Sixteen paired inputs are a small, scene-selected sample, not an unbiased long-run network benchmark. No separate warm-up exclusion was applied to the headline timing table. Other workloads and network conditions can change the result.

### What this means for operation

Fifty actions at nominal 30 Hz span about **1.67 seconds**. Nine compressed-path replies took longer than that span. This does not establish enough timing margin for continuously replenishing an asynchronous action queue, and it is not an RTC stability test.

In the existing synchronous non-RTC design, capture → inference wait → execute 50 actions → capture again is sequential. A median-sized compressed wait plus 1.67 seconds of action execution would be about 3.40 seconds per cycle, excluding capture/other overhead. The inference wait would appear as a pause, not disappear because each received chunk runs at 30 Hz. This is arithmetic illustrating the schedule, not a measured physical cycle or a safety guarantee.

## Difficult-example inspection

Eight unchanged saved front/wrist pairs were rendered in two contact sheets and actually inspected:

- [Sheet 0](fullft10k_deployment_20260924/inspection_0.png): original episode 2 at 3.37, 6.77, 16.93 and 23.70 seconds.
- [Sheet 1](fullft10k_deployment_20260924/inspection_1.png): episode 2 at 27.10 s; episode 46 at 3.30 s; episode 58 at 16.57 and 26.53 s.

Episode 2 shows the approach/contact region, an orange between the fingers near the plate, and later an orange resting on the plate after withdrawal. Some early front views clip the orange at the frame edge; the wrist view adds contact detail but is partly occupied by the fingers. Episode 58 shows close gripper/object contact and a later orange-on-plate view. These are observations of the recorded demonstration, not outcomes caused by the tested policy. Still frames do not establish secure grasp force or exact release onset.

Previously measured 10k full-sequence errors, averaged over three seeds, remain substantial in selected cases: episode 46 frame 99 is 10.664% of training spans; episode 58 frame 497 is 9.356%; episode 17 frame 231 is 8.899%. These are identifiers for targeted follow-up, not proof that the policy fails every corresponding physical situation.

An additional displacement diagnostic on the 16 seed-0 predictions found maximum first-target versus observed-state differences of 6.44°, 9.90°, 16.62°, 7.48°, 1.89° and 8.25 gripper points, respectively. These are target displacements, not measured speeds or force, and no new safety threshold was imposed. In the largest elbow example (original episode 37, frame 99), observed state was 92.18°, demonstrated first target 80.88°, and predicted first target 75.55°. Part of that gap already exists between demonstration target and measured state; do not attribute the full 16.62° to prediction error. Transport correctness therefore does not certify physically gentle startup or contact behavior.

## Implementation and cleanup

New scoped scripts:

- `prepare_fullft10k_deployment.py`: creates hashed, recorded-input fixtures.
- `fullft10k_diagnostic_server.py`: pinned diagnostic server, load guard, BF16/seed parity and preprocessing checks; 15-minute maximum server lifetime.
- `check_fullft10k_network.py`: owns temporary server/tunnels, paired replay, rejection test and cleanup attempts.
- `inspect_fullft10k_inputs.py`: factual camera-pixel contact sheets, not generated imagery.

An initial local preflight started before all input files finished copying and stopped on a missing manifest **before any server or tunnel was started**. Its empty `network` directory is preserved. Canonical completed evidence is in `network_v2`.

The successful client performed PID-and-command-identity-checked termination of its owned server (PID 969647); cleanup returned code 0. Subsequent checks confirmed that GPU port 8085 and laptop ports 18085/18086 were closed. GR00T PID 11632/port 5555 remained present. No diagnostic inference service was left running. Original checkpoints, installed packages and live launcher were not edited.

## Next decision

1. Keep 10k as the primary offline candidate and 15k as the previously documented alternative; this test did not rank models again.
2. Retain compressed authenticated SSH as the measured better path for further diagnostics, while treating pauses/jitter as unresolved. Do not call this a low-latency or RTC-ready route.
3. Before physical use, prepare a separately pinned 10k live-launcher configuration and exercise its complete control/lifecycle path with fake actuators. The existing older-model launcher is not ready to invoke unchanged. This network diagnostic did not run that integrated fake-actuator test.
4. Independently refresh motor/gripper status, historical overload review, workspace/cutoff readiness and stopping/readback procedure under supervision. No physical gate is cleared here.
5. A physical trial, if subsequently authorized, must explicitly choose the non-RTC execution behavior and accept its observed pauses. Do not silently add speed/acceleration limits, change motor protections, switch to custom RTC or move the robot from this report.

## Evidence

- [Network report](fullft10k_deployment_20260924/network_v2/report.json)
- [Per-request results](fullft10k_deployment_20260924/network_v2/requests.jsonl)
- [Server log](fullft10k_deployment_20260924/network_v2/server.log)
- [Server timings and parity checks](fullft10k_deployment_20260924/server_timings.jsonl)
- [Input identities](fullft10k_deployment_20260924/inputs/manifest.json)
- [Checkpoint comparison](PI05_FULLFT_CHECKPOINT_EVALUATION_20260924.md)
