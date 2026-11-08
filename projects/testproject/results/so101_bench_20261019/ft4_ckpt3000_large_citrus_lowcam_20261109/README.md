# FT4 checkpoint 3,000: large-citrus low-camera exploratory row

Date: 2026-11-09  
Policy: fine-tune 4 checkpoint 3,000  
Task string: `pick up the orange and place it on the plate`  
Execution: 20 actions per request, 30 Hz, 75-request cap, return to recorded start  
Scene: large citrus, tray fixed on the left, shifted low/side front-camera view

## Result

**1/5 valid end-to-end successes (20%)**

| Trial | Acquisition | Delivery | Result | Evidence |
|---|---|---|---|---|
| 1 | No | No | Fail | Close landed beside the citrus and pushed it left; no retained lift |
| 2 | No | No | Fail | Citrus rotated during contact; repeated closes remained along its side |
| 3 | No | No | Fail | Hovered beside the citrus, then closed over empty table |
| 4 | Yes, after recovery | Yes | **Success** | Later attempt secured the citrus at chunk 49 and released it in the tray by chunk 52 |
| 5 | Yes | No | Fail | Stable lift by chunk 48, but released on the table immediately in front of the tray by chunk 58 |

Two extra launches are void and excluded: the citrus was already in the tray at their start. Both were interrupted
before meaningful pickup motion. The valid fifth trial was then rerun from the table in a fresh trace.

The first four valid trials are in
`/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_large_citrus_lowcam_20261109_five`; the valid replacement fifth trial
is in `/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_large_citrus_lowcam_20261109_replacement5b`.

## Interpretation

This is an exploratory object-and-camera condition, not a controlled checkpoint comparison. It does not change the
checkpoint 3,000 controlled small-orange result of **1/3 (33.3%)**. Four of five exploratory trials obtained no
end-to-end delivery: three never secured the citrus, while one secured and transported it but released short of the
tray. The result supports the existing plan to restore reference camera geometry and validate acquisition and release
checks before collecting more blind trials.

## Latency

The valid episodes used 75 requests each. Mean request latency was 1,255 ms, 1,243 ms, 1,400 ms, 1,243 ms and
1,156 ms respectively. Trial 3 contained an isolated 3,577 ms maximum; the other valid-trial maxima were 1,659 ms,
1,869 ms, 1,842 ms and 1,435 ms.
