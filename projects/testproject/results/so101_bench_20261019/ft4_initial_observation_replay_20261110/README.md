# FT4 checkpoint 3,000: saved-observation initiation replay

Date: 2026-11-10  
Robot access: **none**  
Inputs: saved front/wrist images and measured state from regular-orange row 2  
Checkpoint: FT4 checkpoint 3,000

## Result

The initiation failure is primarily **stochastic policy instability**, with additional sensitivity to the arm pose
and image reached after small start-area movements.

All seven chunk-1 observations from T2, T3, T5, T7, T8, T9 and T10 were replayed ten times. None of the **70**
predictions contained a purposeful shoulder/elbow reach in the first 20 actions. This includes successful T3. The
checkpoint therefore does not normally command an immediate reach from the recorded starting scene.

Exact transition observations produced different outputs on repeated inference:

| Saved observation | Historical action | Reaches in ten exact replays |
|---|---|---:|
| T3 c31, immediately before the successful reach | no reach | **3/10** |
| T3 c32, successful trial's first reach chunk | reach | **5/10** |
| T2 c56, immediately before its late reach | no reach | **0/10** |
| T2 c57, late trial's first reach chunk | reach | **2/10** |
| T10 c65, immediately before its very late reach | no reach | **0/10** |
| T10 c66, very late trial's first reach chunk | reach | **0/10** |

At chunk 32, the four no-engagement scenes from T5, T7, T8 and T9 produced **0 reaches in 40 replays**. By contrast,
the exact T3 c32 input produced five reaches in ten. This shows both effects:

1. The policy is stochastic: an identical T3 input can yield either a reach or continued small movement.
2. The small pose/image changes accumulated before T3 c32 made reaching more likely than in the no-engagement trials.

The model has one observation step and no temporal image history. Repeated small predictions change the current arm
pose and camera view; eventually some trials enter a state where a stochastic sample produces a large reach. T3 got
that sample early enough to finish. T2 and T10 got it late. T5, T7, T8 and T9 never got it before the cap.

This finding rules out motors, camera freshness and network latency as the direct cause of the stationary behavior:
the replay contains no robot, and the variation is already present in the policy output. Latency still reduces later
closed-loop correction opportunities, but it does not create the initial no-reach predictions.

## Consequence

Making inference deterministic is not sufficient: the chunk-1 mode was no-reach in all 70 replays. The next model
revision needs demonstrations that begin at the deployed start pose and immediately execute the reach, with idle or
long settling prefixes removed. Before motor use, the revised checkpoint should pass this same frozen replay gate:

- a high fraction of chunk-1 samples must initiate a reach;
- the successful T3 approach/close observations must remain valid;
- no candidate action may be selected by a motor gate until it has passed saved-trace and read-only shadow testing.

An interim multi-sample action selector could sample several chunks and select a purposeful reach only during task
initiation, but it is a heuristic. It must be tested offline and in shadow mode before it can control the arm.

## Artifacts

- `report.json`: 70 chunk-1 replay results.
- `transition_report.json`: 100 transition/no-engagement replay results.
- `replay.py`: robot-free reproducible replay tool.

The FT4 server was run only for this replay. Qwen was restored afterward and its `/health` endpoint returned HTTP 200.
