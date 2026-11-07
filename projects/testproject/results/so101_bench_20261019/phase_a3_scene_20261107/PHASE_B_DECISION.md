# Phase B controlled-reproduction decision

Date: 2026-11-07  
Checkpoint: fine-tune 3 `row3_all169_conservative_010000`  
Result: **1/3 acquisition; 1/3 end-to-end**

All three trials used the same accepted tray position, orange position, U1 start pose, camera geometry, wording,
JPEG quality 85, no RTC, 20 executed actions per request and 75-chunk cap.

| Trial | Result | Acquisition behaviour |
|---|---|---|
| B1 | fail | idled through chunk 28; two close sequences did not lift the orange |
| B2 | success | reached immediately; lifted by chunk 46; released inside the tray by chunk 56 |
| B3 | fail | reached by chunk 5; three closes left the orange outside the left finger |

The unchanged setup produced substantially different reach timing and alignment. This rejects the hypothesis that
restoring the start state and scene alone makes acquisition repeatable. B1 and B3 also show different failure
geometry: B1 brought the fruit into the wrist corridor but did not secure it, while B3 repeatedly stayed to its
right with the fruit outside the left finger.

The prewritten Decision B rule assigns 0/3 or 1/3 acquisition to the “restored geometry is insufficient” branch.
No more blind repetitions should be run with this checkpoint. The next evidence-bearing step is to run the existing
read-only lateral-and-depth diagnostic on these held-out traces, label its close windows, then collect centred and
corrective/recovery demonstrations for a new checkpoint.
