# Whole-episode 10-action orange trials

Date: 2026-11-08  
Checkpoint: fine-tune 3 `row3_all169_conservative_010000`  
Instruction: `Grab oranges and place into plate.`

All three trials used exactly 10 executed actions for every policy request. No adaptive or near-action mode was enabled.
The cap was 150 requests, preserving the 1,500-action maximum used by the 75-request, 20-action trials. JPEG quality
was 85 and RTC was disabled.

| Trial | Result | Main observation | Wall time | Median RTT | Clamps |
|---|---|---|---:|---:|---:|
| H10-1 | fail | orange outside left finger on approach; empty closes; fruit displaced slightly | 288.1 s | 1.223 s | 0 |
| H10-2 | fail | new central placement; same outside-left-finger miss; prolonged empty search | 293.3 s | 1.202 s | 0 |
| H10-3 | fail | forward-right placement; outside-left-finger miss by c24; repeated empty closes to cap | 294.5 s | 1.235 s | 2 |

H10-2 reached approximately 116 degrees of measured wrist roll near the cap. The scripted return restored the U1
start, and the post-run read-only check began with torque disabled and passed. No camera frames were stale.

The camera geometry had shifted relative to the fixed Phase B reference, and the orange was moved between H10-1 and
H10-2. H10-3 used the forward-right placement already present when the run began. These trials therefore show that whole-episode 10-action execution did not repair acquisition in the tested
scenes, but they are not a controlled estimate of the effect relative to 20 actions.

The 150-request cap also allowed a long unproductive search and large wrist-roll drift. Future shorter-horizon
experiments require an absolute joint envelope and an early acquisition timeout. The preferred next step remains
corrective demonstration collection rather than additional blind horizon trials.
