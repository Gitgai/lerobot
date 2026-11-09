# FT4 checkpoint 3,000: prospective shadow-verifier trial

Date: 2026-11-09  
Result: **0/1; acquisition failure**

This was the first new trial recorded after implementing the read-only three-stage verifier. The policy and dispatch
settings were unchanged: 20 executed actions per request, 30 Hz, 75-request cap and scripted return to start. The
small orange began in the same lower-right controlled cluster used by the restored-camera row.

The arm reached and searched around the orange with the gripper open, but never issued a measured close transition.
There was no grasp, lift, transport or release. The orange became occluded by the extended arm during the search.
At the cap, the verifier independently reported `acquisition_failure`, with zero close attempts, no retained lift
and no tray check. This agrees with the reviewed physical outcome.

The live instrumentation completed all 75 observations and recorded 75 verifier decisions, 75 predictions and 1,500
dispatched actions. Both camera stale counters remained zero. Mean request latency was 1,169.5 ms, median 1,177.1 ms
and maximum 1,213.9 ms. The arm returned to within approximately one degree/point of its recorded start state.

This trial validates prospective integration and the no-close path. It does not validate the retained-lift or release
branches because the policy never closed. Phase D1 therefore stands at **1/10 prospective trials**, with more watched
stage coverage required before any motor gate can be considered.

Raw trace: `/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_shadow_prospective_20261109_t1`  
Chunk log: `/home/gaikwad-prakash/bench_ft4_ckpt3000_shadow_prospective_20261109_t1.jsonl`
