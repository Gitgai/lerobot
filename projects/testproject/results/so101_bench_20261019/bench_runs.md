# SO-101 bench runs — public checkpoint dongyoonkim/so101-pi05-base, non-pipelined client

Protocol: R3 in docs/pi05_so101_real_base_audit_plan_20261019.md (20 placements, success = fruit on the plate,
no contact with anything else). Client: bench_client.py (this directory) on the Acer (192.168.194.228), policy
wrapper scripts/so101_base_policy_server.py on AI90 GPU 0, port 8080, over ZeroTier (Pune ↔ NJ).
Rig: front = Logitech C270 overhead (/dev/video6), wrist = AK-Camera (/dev/video4), arm /dev/ttyACM0
(calibration id my_so101_follower). Instruction: "Grab oranges and place into plate." Chunk 20 at 30 Hz,
per-step clamp 8° (15 gripper units). Frames recorded server-side: frames/c05_call*_{front,wrist}.jpg (every call).

## Trial 1 — 2026-10-19 19:57–19:58 UTC — FAIL (reach OK, grasp missed)
Scene as the operator left it ("try as is"): one yellow citrus (not an orange) ~15 cm in front-left of the base,
grey oval tray to its right. Arm started at rest [0, -105, 97, 79, -1, 49] (pan, lift, elbow, wrist_flex,
wrist_roll, gripper; LeRobot units). 45 chunks, 74 s wall, median round trip 917 ms per call (server 142 ms,
the rest is JPEG transport over ZeroTier) → duty ≈ 667 / (667 + 917) = 42%.

What the arm did (frames + joint log, Acer ~/bench_ep1.jsonl):
- calls 1–5: gripper closed from 49 → 2 at rest, wrist_flex dipped; **front frames of calls 1 and 2 were
  fully black** (C270 warm-up after open; wrist camera was fine) — the first two chunks were planned without
  the front view
- calls 6–9: shoulder_lift −100 → +6, elbow 94 → −3: the arm swung out and down to the table, gripper opened
- calls 9–45: the arm hovered at the fruit (pan 16–28, lift 25–39, elbow −8 to −23) and **opened and closed
  the gripper ten times** (49→2, 38→8, 32→11, 40→9, 42→8, 46→7 …). In every wrist frame the fruit is beside or
  behind the jaws, never between them; the fruit never moved; nothing was carried toward the tray
- end pose [25, 17, −30, 97, −33, 7] (extended over the table). After the client disconnected the arm was
  found at [6, 2, 41, 41, −34, 38] (moved by hand or sagged with torque off); returned to the start pose with
  `--home-to` at 20:0x UTC

Reading: same behaviour class as the simulator (competent reacher, fragile grasper): it goes to the object
and executes grasp attempts, but the approach pose is off by a few cm and it retries in place instead of
re-approaching. Not scored against a different object: the fruit is a yellow citrus, larger than the
corpus's oranges (jaw opening vs fruit diameter not measured — measure before trial 2).

Montages: montages/ep1_front_every4.jpg, montages/ep1_wrist_key.jpg.

Fixes made after trial 1 (bench_client.py, copied to the Acer, md5 88d872a8…):
- camera warm-up: read until a frame has signal (≤ 3 s), abort if still black
- `--home-to a,b,c,d,e,f`: slow clamped move to a pose and exit; `--return-start`: after each episode move
  back to the pose it started from
- episode record now carries start_state / end_state

## Trial 2 — 2026-10-19 20:10–20:12 UTC — FAIL (jaws on the fruit, could not close around it, no lift)
Operator re-placed the citrus closer to the base, front-left (tray unchanged). Start pose = rest (returned by
`--home-to`). 45 chunks, 72.8 s, median RTT 0.918 s. Front camera warm-up worked (frame mean 163 on call 1);
the wrist camera's first frame was under-exposed (mean 10, calls 2+ fine) → warm-up now wants two frames > 40.

What the arm did (frames c06_call*, Acer ~/bench_ep2.jsonl):
- calls 1–8: rest → table in 8 chunks, gripper held open (42–43)
- calls 9–45: hovered at the fruit (pan 6–12, lift 38–45, elbow −18 to −33) and cycled the gripper eight
  times. Unlike trial 1 the fruit sits BETWEEN the jaws in the wrist frames from call 13 on, and the gripper
  bottomed at 10–17 on every close (it reached 2 on empty air in trial 1) → the jaws were squeezing the fruit
  but could not enclose it; shoulder_lift never went back up, so no lift attempt; the fruit was nudged a few
  cm toward the tray by the jaw contacts (front frames 17 → 45)
- ended extended at [9, 36, −20, 100, −31, 30]; `--return-start` brought it to [0, −105, 92, 76, −1, 49]
  (elbow/wrist 5° and 3° short of the target — the 20 s move budget or servo stall under gravity; harmless)

Reading: closer than trial 1 — contact and squeeze, no enclosure, no lift. Evidence for the size hypothesis:
the gripper floor of 10–17 units on the fruit vs 2 on air says the jaws stop on the fruit's equator. Whether
a lift would have followed with a graspable orange is not answerable from this trial.

Montages: montages/ep2_front_every4.jpg, montages/ep2_wrist_key.jpg.

## Trial 3 — 2026-10-20 ~04:2x UTC — OFF-PROTOCOL object (onion) — FAIL (reach OK, jaws beside it, one empty lift)
Operator's object: a small brown onion (fits the jaws easily; not an orange, so this is a generalisation probe
and NOT one of the 20). Placed ~12 cm front-left of the base, tray unchanged. Start = rest (wrist_flex 65
instead of 79 — the return move after trial 2 had stopped short; harmless). 45 chunks, 89 s, median RTT
1.285 s (slower network than yesterday's 0.92 s; server compute unchanged). Both cameras warmed up (129 / 176).

What the arm did (frames c07_call*, bench_ep3_onion.jsonl):
- calls 1–7: rest → table in 6 chunks, gripper open (48)
- calls 8–22: hovered over the onion, three partial closes (30, 19, 11), pan drifting 18 → 25
- calls 23–24: onion BETWEEN the jaws in the wrist view, gripper closed to 3–4 — but the close landed on the
  onion's side, not around it; by call 25 the onion is beside the jaw again (nudged)
- calls 32–35: second full close (3) beside the onion
- calls 35–37: **lift with the gripper closed** (shoulder_lift 34 → 14, elbow −35 → −8) — the first lift motion
  seen on the bench — but the jaws were empty (wrist 35/36: onion to the right of the closed jaws); gripper
  opened to 37 at the top (a "release" with nothing in hand)
- calls 38–45: back down, two more closes (6, 18), ended extended at [24, 40, −22, 90, −39, 16]; returned
  to start by the client (reached [1, −104, 97, 65, −2, 48])

Reading: the policy treats the onion as the target (goes to it, no hesitation) — object identity did not
stop it. The failure is the same grasp-placement error as trials 1–2, now on an object that fits, plus one
grasp→lift→release sequence executed on an empty gripper: the model believed it had grasped. That is the
"fragile grasper" of the simulator ladder on real hardware, and the first bench evidence that the gap is
grasp pose/timing, not object size alone.

Montages: montages/ep3onion_front_every4.jpg, ep3onion_front_lift.jpg (calls 22–38), ep3onion_wrist_key.jpg.

## Trial 4 — 2026-10-20 — OFF-PROTOCOL (onion, larger reddish one) — FAIL (jaws beside it, one empty lift)
Operator re-placed a larger red onion (orange-ish colour, fits the jaws) front-left. 45 chunks, 95.6 s, median
RTT 1.325 s. Rest → table in 4 chunks. Seven close cycles; gripper floor 4 (calls 9, 23–24, 32: empty) and
13 (calls 40–42: a glancing squeeze on the onion's side, wrist 41–42). Calls 42–43: lift (shoulder_lift 53 → 36)
with the gripper at 13–17 — empty; onion still on the table in front 43. Onion nudged a few cm. Returned to start.
Frames c08_call*, log bench_ep4_onion.jsonl, montages ep4onion_front_every4 / ep4onion_wrist_key / ep4onion_front_end.

## Trial 5 — 2026-10-20 — OFF-PROTOCOL (same onion, placed closer to the base) — FAIL (aligned, closed ABOVE it)
Onion placed ~8 cm in front of the base, slightly left. 45 chunks, 147.5 s, median RTT 1.618 s with a ZeroTier
stall on calls 24–30 (10.7 s, 6.6 s, 8.2 s, 6.6 s, 9.6 s, 14.0 s per call; server compute stayed 141–145 ms,
so the stall was the network). Non-pipelined client → the arm simply waited; no motion during the stall.
- calls 5–9: arm over the onion, **onion squarely between the jaws in the wrist view (calls 8, 9, 13, 14)** —
  the first correctly aligned approach on the bench — yet the gripper closed to 6 (call 9) and 4 (call 15):
  the fingers shut above the onion (approach not low enough) and the close pushed it out (wrist 15)
- calls 16–45: re-approach with pan −4 to −7, three more closes (17, 11, 18) beside it, then hovering with the
  gripper open through the stall; ended at [−1, 19, 11, 70, −43, 17]; returned to start
Reading: lateral alignment can be right; the miss here is HEIGHT at the close (fingers above the object), which
the wrist camera shows plainly. Same family as trials 1–4: grasp pose, not object identity or size.
Frames c09_call*, log bench_ep5_onion.jsonl, montages ep5onion_front_every4 / ep5onion_wrist_key.

## Trial 6 — 2026-10-20 — COUNTED (orange, fits the jaws) — FAIL (aligned, closed above it, then over-reached)
First counted trial with a real orange (a mandarin-sized orange, fits the open jaws with room). Placed ~15 cm
straight in front of the base. **Rig change noticed in the first frame: the overhead C270's view differs from
trials 1–5** (base now top-centre, tray right, table edge visible top-left — the camera was moved or bumped
between trials 5 and 6; operator asked). 45 chunks, 87.6 s, median RTT 1.135 s; both cameras warmed up.
- calls 1–10: rest → table in 9 chunks (slower start: 3 chunks of small wrist motion first), gripper 40–48
- calls 11–14: **orange between the jaws (wrist 11–13), gripper closed to 2** — fingers shut above the fruit;
  the orange did not move
- calls 15–45: the arm extended PAST the orange (shoulder_lift 44 → 68, elbow −43 → −73: the furthest reach
  of any trial) and worked the gripper there (floors 10, 16, 19–22), orange behind/below the jaws in the
  wrist view the whole time; one short lift at 42 (shoulder 55 → 38) with gripper 22, empty; ended at
  [21, 52, −44, 87, −33, 35]; returned to start
Reading: as trial 5 — correct lateral alignment, close too high — followed by a new failure: an over-reach
beyond the object, consistent with the moved overhead camera (the front view is the policy's main depth cue;
a shifted camera shifts where it thinks the object is). Counted as FAIL; the camera move is a CONFOUND for
this trial and must be fixed (restore the view of trials 1–5 or re-fix the mount and keep it) before trial 7.
Frames c10_call*, log bench_ep6_orange.jsonl, montages ep6orange_front_every4 / ep6orange_wrist_key / ep6orange_front_end.

## Trials 7–10 — 2026-10-20 — COUNTED (orange), four back-to-back — all FAIL
Run as one client process (`--episodes 4 --return-start --pause-between 30`; operator re-placed the orange in the
30 s countdown; one gRPC connection → frames c11_call000001–000180, 45 per trial). Overhead camera in the
trial-6 position throughout (not restored; consistent for 6–10). Log bench_ep7_10_orange.jsonl + .run.log.
Median RTT 0.98 / 1.20 / 1.20 / 1.21 s; 78–87 s per trial. Composites: montages/ep{7,8,9,10}orange_composite.jpg.
```text
trial  placement                 off-rest at  closes (gripper floor)          what the wrist camera shows
7      ~15 cm in front, centre   chunk 15     21–22 (4), 28–30 (24), 41 (7)   c21: shut beside; c40→41: orange between the
                                                                              jaws, close ended at 7 with the fruit still
                                                                              visible between the fingertips → closed above it
8      ~15 cm front-left         chunk 16     22–26 (11–13), 30–31 (3),       c22–26: orange between the jaws, floor 11–13 =
                                              37–38 (4), 42 (21)               squeezing its side, no hold; c30–31 beside;
                                                                              c36–38 above it; orange pushed ~10 cm toward base
9      ~8 cm, close to the base  chunk 7      21 (7), 28 (2), 31–32 (3),      c17–22 between the jaws, closes above (7, 13);
                                              33 (14), 38–39 (16)              c27–28 beside; c30–33 above again; nudged
10     left of the base          chunk 7      12–13 (2), 20 (3), 26–27 (18–20) c11–14 beside; c19–20 orange between the jaws,
                                              33–34 (24)                       shut to 3 above it; then the arm reached far
                                                                              past it (shoulder 68, elbow −74) and hovered
                                                                              with half-closed gripper over nothing
```
New in this batch: two trials (7, 8) sat motionless at rest for 14–15 chunks (≈20 s) before starting the reach —
the policy output "hold" at the start pose; trials 9 and 10 started within 6 chunks. Not seen in trials 1–6.
Reading: identical failure family across all four — the arm finds the orange and gets it between the jaws,
and the close is 1–3 cm too high or to one side; it never re-adjusts downward, it retries the same close.

## Running tally
| trial | utc | result | chunks | wall s | median RTT s | note |
|---|---|---|---|---|---|---|
| 1 | 2026-10-19T19:58:52Z | FAIL | 45 | 74.1 | 0.917 | reached, 10 grasp attempts beside the fruit, black front frames on calls 1–2 |
| 2 | 2026-10-19T20:12:03Z | FAIL | 45 | 72.8 | 0.918 | reached, jaws on the fruit (gripper floor 10–17), no enclosure, no lift, fruit nudged |
| 3 (onion, off-protocol) | 2026-10-20 | FAIL | 45 | 89.1 | 1.285 | reached, onion between the jaws once but closed beside it, one empty-handed lift+release, nudged |
| 4 (onion, off-protocol) | 2026-10-20 | FAIL | 45 | 95.6 | 1.325 | reached, seven closes beside it (floor 4; 13 once = glancing squeeze), empty lift at the end |
| 5 (onion, off-protocol) | 2026-10-20 | FAIL | 45 | 147.5 | 1.618 | aligned between the jaws at calls 8–14 but closed ABOVE it (floor 4–6), pushed out; ZeroTier stall 7–14 s/call on 24–30 |

| 6 (orange, counted) | 2026-10-20 | FAIL | 45 | 87.6 | 1.135 | aligned at calls 11–14 but closed above it (floor 2), then over-reached past the orange; overhead camera had moved (confound) |

| 7 (orange, counted) | 2026-10-20 | FAIL | 45 | 78.1 | 0.975 | 15 chunks idle at rest, then closes beside / above the orange |
| 8 (orange, counted) | 2026-10-20 | FAIL | 45 | 84.7 | 1.202 | 16 chunks idle, side-squeeze (floor 11–13) then above; orange pushed ~10 cm |
| 9 (orange, counted) | 2026-10-20 | FAIL | 45 | 87.2 | 1.199 | prompt start; between the jaws repeatedly, closes above/beside |
| 10 (orange, counted) | 2026-10-20 | FAIL | 45 | 85.0 | 1.205 | closed above it at c20, then over-reached far past it and hovered |

Counted toward the 20: trials 1, 2 (pending the object-fit decision), 6, 7, 8, 9, 10 → **0/7**. Off-protocol: trials 3–5 (onion).
Pattern over 10: reach 10/10 · object between the jaws at some point 8/10 (all but 1, 4) · a close that held the object 0/10 ·
lift motions 3 (all empty, trials 3, 4, 6) · placement on the tray 0. Close-too-high: 5, 6, 7, 8, 9, 10; close-beside: 1, 3, 4, 8, 9, 10;
over-reach past the object: 6, 10 (both with the moved overhead camera); idle-at-rest start ≥ 14 chunks: 7, 8.
