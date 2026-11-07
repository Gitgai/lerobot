# Fine-tune 3 latency probe — 2026-11-08

Ten no-robot requests were sent from the Acer in Pune to fine-tune 3 on the AI90 RTX 5090 in New Jersey. The client used JPEG quality 85, two 640×480 cameras, ten requested actions, and the existing stop-and-wait gRPC transport. Server-side frame and CSV recording was disabled.

## Measured medians

| Stage | Median | Range |
|---|---:|---:|
| Front JPEG encode | 2.5 ms | 1.5–3.9 ms |
| Wrist JPEG encode | 2.5 ms | 1.4–7.6 ms |
| Observation pickle | <0.1 ms | <0.1 ms |
| Observation upload RPC | 547.4 ms | 267.9–862.7 ms |
| Server JPEG decode | 3.6 ms | 2.8–13.4 ms |
| Server preprocessing | 1.5 ms | 1.2–20.6 ms |
| RTX 5090 inference | 174.9 ms | 166.8–187.2 ms |
| Server postprocessing | 0.1 ms | 0.1–4.9 ms |
| Server recording | 0.0 ms | recording disabled |
| Action RPC, including inference and return transport | 460.4 ms | 442.3–530.1 ms |
| Client action unpickle | 0.8 ms | 0.7–7.5 ms |
| End-to-end | 1,024.1 ms | 718.6–1,358.5 ms |

Median observation payload was 106.7 KiB. A contemporaneous ping was about 260 ms. The action RPC is consistent with one network round trip plus about 175 ms inference. The observation upload RPC is the largest avoidable stage and varies in roughly one-RTT increments, consistent with the client-streaming RPC being opened and closed for every observation over the long-distance link.

## Changes

- Server recording is now opt-in through `--record-dir`; ordinary trials perform no server disk recording.
- The bench client records per-request JPEG, pickle, observation-RPC, action-RPC and unpickle timings.
- The server logs JPEG decode, preprocessing, inference, postprocessing and recording timings.
- The existing LeRobot asynchronous client in `src/lerobot/async_inference/robot_client.py` already decouples observation upload from actuation and uses an action queue. Adapting the bench configuration to that client is the next transport change; a single bidirectional streaming RPC would require a protobuf service change because the current API defines `SendObservations` and `GetActions` separately.
