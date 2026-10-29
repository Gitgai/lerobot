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

## Trials 11–16 — 2026-10-20 — COUNTED (orange), six back-to-back — all FAIL
Same client settings as 7–10 (one process, 30 s countdown, return-to-start). Frames c12_call000001–000270
(45 per trial). Overhead camera still in the trial-6 position. Log bench_ep11_16_orange.jsonl.
Placements: the operator put the orange close to the base, left side (≈5–10 cm from the base plate) in all
six — the folded-arm region (shoulder_lift ≈ −15…+20, elbow 25…45 at the object). The "raised" end poses in the
chunk log are that folded reach, NOT lifts: no wrist frame in any of the six shows the orange inside the jaws.
Median RTT 0.96 / 1.19 / 1.19 / 1.18 / 1.20 / 1.21 s; 85 s per trial (trial 12: 111 s, one slow call).
```text
trial  off-rest at  closes (gripper floor)                    wrist camera
11     chunk 5      12–14 (2), 22–23 (5), 30–31 (3), 42–43 (9)   orange right of / behind the right jaw at every close;
                                                              pushed toward the base
12     chunk 6      15–16 (11), 28–31 (2–3)                     c15–16 squeeze on its side (floor 11); c28–31 shut on air
                                                              with the orange out of the wrist view; arm then rose and
                                                              hovered open (c40–45) — a "done" posture with nothing held
13     chunk 15     23–25 (4), 42 (24)                          c23–25 shut beside it (orange visible right of the jaw)
14     chunk 19     29–31 (7–8), 45 (8)                         c29–31 orange at the right jaw tip, close ended at 7–8 =
                                                              beside/above; c45 closed to 7 on air
15     chunk 6      15 (20), 18 (21)                            orange between/right of the jaws c14–18; only partial
                                                              closes (20–21), then hovering open for 25 chunks
16     chunk 12     36–45 (8–21)                                orange never appears in the wrist view (hidden under the
                                                              arm's shoulder from the overhead view too); closes on air
```
Reading: no change in behaviour class across a third placement region (far-front in 6–7, mid in 8–10, close-in in
11–16). The policy reaches the object region reliably from every placement and never completes a grasp.
Composites: montages/ep{11..16}orange_composite.jpg.

## 2026-10-26 — Fine-tune comparison day: CONTROL ROW (public base, tomato, OVERHEAD camera) — 0/5
Object: a tomato (operator's; red, round, fits the jaws). Off-protocol object → these rows compare MODELS, they do
not count toward the 20. Front camera: overhead, where it has been since trial 6 (= the September training view).
Instruction for the base: "Grab oranges and place into plate." (corpus wording, as before). 5 placements, left-front
of the base, 45 chunks each, median RTT 1.05–1.36 s. AI90 had rebooted 2026-10-25; servers recreated.
Frames: c01_call000001–000225 in frames/ (the recorder restarted with the server; the Oct-19 dry-run c01 frames were
overwritten — 16 files, no result depended on them). Log bench_ctrl_tomato_20261026.jsonl.
```text
trial  off-rest  closes (floor)                        wrist camera
1      chunk 17  26–27 (11), 32–33 (6), 43 (4)          tomato between the jaws c26–38; every close on its side or above
2      chunk 9   15–16 (7), 30–34 (21), 45 (12)         c15 beside; c30–33 half-closes with the tomato under the right jaw
3      chunk 6   15–16 (7), 22–24 (21), 32–34 (15)      between the jaws c15–32; closes above it (floor 7 then 15–21)
4      chunk 7   16–17 (5), 33 (23), 41 (8)             c16–17 shut on air beside it; c41 above it
5      chunk 8   15 (16), 34 (21), 40 (22)              beside at c15; only partial closes after
```
Result: 0/5, tomato nudged in 3 trials, never lifted. Identical failure family to the 16 orange/onion trials.
Montages: montages/ctrl_tomato_T1..T5.jpg.

## 2026-10-26 — FINE-TUNE 3 ROW (row3_all169_conservative ckpt 010000, tomato, OVERHEAD camera, :8081 on GPU 1)
Instruction: "pick up the tomato and place it on the plate" (a trained string; 10 tomato demos in the 169). Same 5
placements as the control row, same client settings. Frames: results/so101_lora_on_top_20261019/bench_frames_row3_010000/
(c01_call000001–000225), log bench_row3_tomato_20261026.jsonl, composites bench_row3_tomato_T1..T5.jpg there.
```text
trial  what happened (frames + joint log)                                                              result
1      rest → tomato in 8 chunks; jaws around it c14, gripper stopped at 28–30 = CLOSED ON THE TOMATO;   GRASP + CARRY +
       lifted and swung (pan → −60) over the tray by c20; opened to 48 over the tray at c24 (release);    RELEASE over the
       back at rest by c31 and held there. Front c26–45: tomato at the tray's near edge/rim.              tray — operator
       FIRST GRASP-AND-CARRY ON THIS BENCH (17 base trials: 0).                                           to confirm final
                                                                                                          spot (in/on rim)
2      tomato placed near the base; arm reached c8, PUSHED it toward the base (front c8–14), jaws on      FAIL (push, close
       its side c14–24, full close to 4 at c27–28 beside it, stayed low                                   beside)
3      tomato left-front close in; arm made a small reach and then held at rest with the gripper wide     FAIL (did not
       open (41→60) for the whole episode; wrist camera saw only table                                    engage)
4      tomato left-front; IDLE at rest for 32 chunks, then began the reach at c38; cap at c45 with the    FAIL (cap hit
       jaws just arriving at the tomato                                                                   mid-approach)
5      tomato left; idle ~26 chunks, reach from c32, gripper closing to 17 with the tomato entering the   FAIL (cap hit
       jaws at c30–45; cap hit                                                                            mid-grasp)
```
Row: 1 grasp-carry-release of 5 (vs 0/5 base, same placements, same session). Two of the four failures are the
45-chunk cap (30 s of motion) cutting an in-progress approach after an idle start — the idle start is the same
behaviour the base showed in trials 7–8 and 13–16; our demos are ~25–30 s long so the cap leaves no slack.
NEXT ROW: --max-chunks 75 (50 s) so a late start can finish; 5 more placements; then the base again at 75 for symmetry.

### Fine-tune 3 ROW B (75-chunk cap) — 1 SUCCESS, 4 VOID
Frames c02_call000001–000375 in bench_frames_row3_010000/, log bench_row3b_tomato_20261026.jsonl, composites
bench_row3b_tomato_T1..T5.jpg.
```text
B1  tomato front-left; idle 15 chunks, reach, jaws around the tomato c20–30 (gripper 28–32 = holding it), lift and
    swing (pan −67) c30–45, lowered INTO the tray and released c50, back at rest by c52, held to c75.
    ★ SUCCESS — tomato inside the tray, arm at rest. The clearest completion on this bench.
B2–B5  VOID: the tomato was NOT re-placed between trials (it stayed in the tray from B1). The model saw a completed
    scene and stayed at rest for all 75 chunks each time, gripper drifting 41 → 21. Not failures — an informative
    "task already done → do nothing" — but not trials either. (A yellow fruit sat at the table's top-left edge
    throughout; not part of the task, the model ignored it.)
```
Fine-tune 3 across VALID trials today: 2 grasp-carry-release in 6 (row A T1 at the tray rim, operator to confirm;
row B T1 clearly inside) vs the base 0 in 5. 4 placements still owed for row B.

### Fine-tune 3 ROW C (75-chunk cap, 4 placements) — 0 of 3 valid, 1 void
Frames c03_call000001–000300, log bench_row3c_tomato_20261026.jsonl, composites bench_row3c_tomato_T1..T4.jpg.
```text
C1  VOID — tomato still in the tray at the start (live frame checked at call 57); moved to the table late in the
    episode, the arm began a reach at ~c60 and hit the cap.
C2  reached c10, tomato between the jaws c20 (close to 10 = on its top/side, no hold), three more approaches with
    the tomato large in the wrist view (gripper 22–37), full close to 1 on air at c60, retreated open.   FAIL
C3  reached c10, tomato between the jaws c30–40 (gripper 31 → 18, no hold), pushed it, circled, ended extended
    with the wrist rolled 84° and the gripper open.                                                      FAIL
C4  tomato placed close to the base; around it c20–60 (gripper 25–43), closing to 14 with the tomato between the
    jaws at c75 — cap hit mid-grasp.                                                                      FAIL (cap)
```
DAY TOTAL, valid trials, tomato, overhead camera, same client: fine-tune 3 **2 of 9** grasp-carry-release
(both with the tomato placed front-left of the base at a middle distance); public base **0 of 5**.
### Fine-tune 3 ROW D (75-chunk cap, 5 placements) — 2 in the tray of 4 valid, 1 void (camera fault)
Frames c04_call000001–000323, log bench_row3d_tomato_20261026.jsonl, composites bench_row3d_tomato_T1..T4.jpg.
```text
D1  reached c10 (gripper 14 beside it), then hovered with the tomato between the open jaws (35–54) c20–75,
    never closed on it.                                                                                   FAIL
D2  reached c10, tomato between the jaws c20–50 (gripper 20–44), lifted and carried c50–60 (tomato large in
    the wrist view with the tray edge below, gripper 28), released INTO the tray, back at rest by c75.
    (An operator hand enters the frame at c75, after the release.)                                        SUCCESS
D3  tomato was on the tray at c1 and on the table by c10 (moved during the first chunks); reached, tomato
    between the jaws c20–50, closes to 12 / 19 on its top, open at c60, no hold.                           FAIL
D4  tomato near the base; reached c10–20 (jaws around it, gripper 41), by c30 the arm is over the tray and the
    tomato is IN it; arm then idled in front of the tray, gripper 48–52, to c75. The gripper never read below
    41, so this was a loose carry or a push into the tray, not a firm grasp.                              IN TRAY
                                                                                                           (mechanism
                                                                                                           unclear)
D5  VOID — the wrist camera read failed at chunk 23 and the client exited (arm left at [12,12,28,31,12,44];
    returned to start with --home-to). bench_client.py now retries a failed read and reopens the device once.
```
DAY TOTAL (valid trials, tomato, overhead camera, same client, 45→75-chunk cap): fine-tune 3 **4 of 13 in the
tray** (B1 and D2 clean grasp-carry-release; A1 at the rim and D4 by an unclear mechanism, operator to adjudicate)
vs the public base **0 of 5**. Both models' misses are the same close-too-high/beside; fine-tune 3 re-approaches.

### Fine-tune 3 ROW E — THE ORANGE (protocol fruit), 75-chunk cap, 5 placements — 3 of 5 SUCCESS
Instruction "pick up the orange and place it on the plate" (trained string, 20 August plate demos + 20 September +
30 recovery). Frames c05_call000001–000375, log bench_row3e_orange_20261026.jsonl, composites bench_row3e_orange_T1..T5.jpg.
Scene notes: the operator moved the tray from the arm's right to its LEFT from trial 3 on; in trials 2 and 4 the
orange was in the tray at chunk 1 and on the table by chunk 10 (placed late) — the arm had not engaged yet, so
those trials are valid. Orange ≈ mandarin size: held at gripper 20–26 (tomato: 28–32).
```text
E1  reach c10, jaws on the orange c20 (g20), lift c40, over the tray c50, released, at rest by c60.      SUCCESS
E2  late placement; orange between the jaws c20–75 (g25–48), never held.                                FAIL
E3  reach c10, hold c20 (g25), in the tray by c30, arm hovered near the tray, open, to c75.             SUCCESS (25 chunks)
E4  late placement; hold c30 (g26) and lift, then set it back down on the table to the right and        FAIL (grasp + lift,
    stayed with it in the jaws, open, to c75; never carried to the tray.                                 no delivery)
E5  reach c10, hold c20 (g26), carried left, in the tray by c30, arm back near rest, gripper drifting   SUCCESS
    24 → 13 idle to c75.
```
With the protocol fruit: **3/5**, all three clean grasp-carry-release-return in 25–50 chunks; the two failures
include one grasp+lift. Compare the public base on this bench with the orange: 0/11 (trials 6–16).

Observations for the record: when fine-tune 3 holds the tomato the gripper reads 28–32 (the tomato is near the
jaw limit — a smaller fruit would close further); its misses are the base's miss (too high / to the side) but it
re-approaches instead of retrying in place; it starts late (15–30 chunks idle) in about half the trials.

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

| 11 (orange, counted) | 2026-10-20 | FAIL | 45 | 84.6 | 0.962 | close-in placement; four closes, all beside the orange |
| 12 (orange, counted) | 2026-10-20 | FAIL | 45 | 110.8 | 1.190 | side-squeeze (floor 11) then shut on air; rose and hovered open |
| 13 (orange, counted) | 2026-10-20 | FAIL | 45 | 85.0 | 1.190 | 15 chunks idle; closes beside |
| 14 (orange, counted) | 2026-10-20 | FAIL | 45 | 86.3 | 1.175 | 19 chunks idle; closes beside/above at the jaw tip |
| 15 (orange, counted) | 2026-10-20 | FAIL | 45 | 84.8 | 1.195 | orange between the jaws, only partial closes (20–21), then hovered open |
| 16 (orange, counted) | 2026-10-20 | FAIL | 45 | 84.6 | 1.210 | orange never in the wrist view; closes on air |

Counted toward the 20: trials 1, 2 (pending the object-fit decision), 6–16 → **0/13**. Off-protocol: trials 3–5 (onion).
CAMERA CAVEAT (2026-10-21): all 16 trials ran with the C270 as a straight-down OVERHEAD front camera (two
positions: trials 1–5 and 6–16). Our own real recordings (so101_orange_89_v21, orange79_plus_plate20) used a LOW
FRONT camera at table height looking toward the base. So 0/13 is the zero-shot number "with an overhead front
camera", not on the training view; the control row for R5 is to be taken with the C270 in the low front position.
Pattern over 16: reach 16/16 · object between or touching the jaws at some point 12/16 · a close that held the object 0/16 ·
lift motions 3 (all empty, trials 3, 4, 6) · placement on the tray 0. Close-too-high: 5, 6, 7, 8, 9, 10, 14; close-beside:
1, 3, 4, 8, 9, 10, 11, 12, 13, 14, 16; over-reach past the object: 6, 10; idle-at-rest start ≥ 12 chunks: 7, 8, 13, 14, 16;
"finished" posture (rose and hovered open with nothing held): 12, 15. Three placement regions tried (far-front, mid, close-in).

## Next (2026-10-28): scripted auto-reset between trials — plan docs/so101_bench_auto_reset_plan_20261028.md
The arm itself takes the orange out of the tray and places it on a pre-registered grid slot between trials
(blind joint-space routine with a gripper-reading check and a camera verify; the policy is not used). Needs a
30-min calibration at the bench (tape the tray, record waypoints). Then 20-trial rows per model.

## 2026-10-28 — FINE-TUNE 3, SESSION 2 (row3_all169_conservative ckpt 010000, :8081 on GPU 1, OVERHEAD camera)
Same checkpoint and serving script as 2026-10-26 (checkpoint files unchanged since 10-24; the server process was
restarted 06:44 and 08:49 EDT and again 15:17 EDT for the recorder fix below). Client: bench_client.py with the
2026-10-28 camera hardening (read retries, reopen, reuse of the last good frame — never triggered today), 75-chunk
cap, 30 s auto pause, return-to-start. CAMERA DEVICES: the Acer re-enumerated its USB cameras — C270 (overhead
front) = /dev/video4, AK (wrist) = /dev/video6, the reverse of Sunday; confirmed from /dev/v4l/by-id. Median RTT
1.0–1.4 s (Sunday 1.0–1.2 s). Logs/composites in results/so101_lora_on_top_20261019/.

FRAME-RECORDER INCIDENT: the server's per-connection prefix counter (c01, c02, …) lived only in the process, so
after the morning restarts today's connections were numbered from c01 again and their JPEGs overwrote Sunday's
files of the same name in bench_frames_row3_010000/: c01 calls 1–48 (Sunday tomato row, trial 1), c02 calls 1–348
(Sunday row B), c03 calls 1–65 (row C), c04 calls 1–75 (row D). Sunday's composites, joint logs and calls.csv rows
are intact; the orange row E frames (c05) are intact. Fixed 15:17 EDT: the server now continues from the highest
prefix on disk (scripts/so101_base_policy_server.py); today's tomato row is c07. Logged in DISK_LEDGER §11.

### ROW F — orange, 10 planned, instruction "pick up the orange and place it on the plate" — 0/4, 1 aborted
Attempt 1 died at chunk 48 of trial 1 (AK wrist camera read failure; the arm was homed with --home-to) → VOID,
files kept as *_attempt1_camfault*; frames c01 calls 1–48. Attempt 2: log bench_row3f_orange_20261028.jsonl,
frames c02 calls 1–347, composites bench_row3f_orange_T1..T4.jpg (+T5_aborted).
```text
F1  orange centre, close to the base (px 271,316); reach, then swept far RIGHT (pan +50, wrist_roll 97),      FAIL
    gripper shut on air (1) at c75.
F2  orange not yet on the table at c1 (placed late); arm hovered in front of the base c30–75, gripper 34→26;  FAIL
    no grasp (min 11 at c14, on air).
F3  orange left-mid (the one demo-like spot today; the colour detector misfired on it); arm pushed down beside  FAIL
    it (grip 4 at c39), then swept right (pan +49).
F4  orange left (px 179,206); hovered near the base, rose, gripper 30 at the end; orange hidden under the      FAIL
    arm in the last frame, not moved to the tray.
F5  ABORTED at chunk 47 on the operator's word ("stop trial and send arm to home"); not counted.               —
```
### ROW G — orange, relaunch — 0/1, then stopped
First launch VOID: my error, the client's default instruction "Grab oranges and place into plate." was sent
instead of the trained string; killed during trial 1 (frames c03 calls 1–64, bench_row3g_orange_20261028_void_wrongtask.jsonl).
Relaunch with the right wording: log bench_row3g_orange_20261028.jsonl, frames c04 calls 1–75, composite bench_row3g_orange_T1.jpg.
```text
G1  orange directly under the gripper, close to the base (px 315,329); stretched far forward and low (wrist   FAIL
    flex 103), came down beside the orange on the left, gripper open 40–52 throughout.
```
Operator stopped the row before trial 2.

WHY 0/5 TODAY AFTER 3/5 ON SUNDAY (checked against the frames): same weights, same script, same instruction, same
orange (same stem mark, ~65 px), same camera views and brightness, no stale frames. What differed: PLACEMENT. In
4 of today's 5 orange trials the orange sat directly in front of / under the gripper, close to the arm base. The
60 September demos (the bench camera's training data) never start there — their oranges sit left mid-table, right
of the tray, or in the tray (scatter: scratch sept_orange_scatter.jpg; grid why_sunday_vs_today.jpg sent to the
operator). Sunday's three successes (E1, E3, E5) were in those demo spots. F3, the one demo-like placement today,
also failed, so placement is not the whole story and five trials are few. Secondary: RTT up ~15 %.
→ For the main rows the orange goes on the demonstration-area slots (auto-reset plan, MAIN grid) — this is the
same conclusion the plan already reached, now with a failure mode to show for it.

### ROW H — TOMATO, 5 trials, instruction "pick up the tomato and place it on the plate" — 1/5
Log bench_row3h_tomato_20261028.jsonl, frames c07 calls 1–375, composites bench_row3h_tomato_T1..T5.jpg. One
void launch before it (stopped in the countdown, no motion). The operator moved the tray during the row: right
of the arm for H1–H3, up-centre near the arm for H4, LEFT of the arm for H5. Orange removed from the table after H1.
```text
H1  tomato left mid-table; reach c10, tomato between the open jaws in the wrist view by c20, jaws CLOSED TO    FAIL (near miss)
    12 just short of it (c30), reopened, wrist rolled to 105, tomato pushed left. A yellow orange sat at the
    table's bottom-left edge throughout (removed after this trial).
H2  tomato left mid-table; same: between the jaws c20–30, closed to 4 in FRONT of the fruit, reopened,         FAIL (near miss)
    swept right.
H3  tomato left mid-table; same: squarely between the jaws c20, closed to 3 just in front of it c26, gave up,  FAIL (near miss)
    swept away.
H4  tomato left mid-table, tray moved up-centre; reach, GRASP c22 (held at ~23), carried left, RELEASED IN THE  SUCCESS
    TRAY by c40, arm at rest c40–62. The operator took the tomato out onto the table at ~c65 and the arm
    re-engaged it in the last chunks (same situation as Sunday's late placements; result taken at completion).
H5  tomato placed RIGHT of the arm, tray LEFT; arm went to the tomato's side by c12 and hovered beside it open   FAIL
    (43–50) to c50, nudging it; closed to 23 on it at the cap (c75), no lift.
```
Pattern of the row: reach 5/5, fruit between the jaws 4/5, but the close came 2–4 cm short of the fruit three
times in a row at the same left-mid spot; the one success was the same spot with the tray closer to the arm.
With Sunday's 4/13 this makes fine-tune 3 on tomato 5/18 valid trials; orange 3/10.

### ROW I — TOMATO, 5 more trials, same settings — 0/5 (one grasp-and-carry without delivery)
Log bench_row3i_tomato_20261028.jsonl, frames c08 calls 1–375, composites bench_row3i_tomato_T1..T5.jpg. Tray LEFT
of the arm throughout. Median RTT 1.26–1.36 s.
```text
I1  tomato left mid-table; between the jaws c25, closed to 19 → SLIPPED out, swung empty to the tray and back,   FAIL (slip)
    hovered beside it open c50–75, nudging it.
I2  tomato left mid-table; came down BESIDE it, closed to 5 on air at c30 with the fruit against the outside of  FAIL
    a jaw, then pulled back toward the base with it wedged, wrist_roll to 129 (training max 91).
I3  tomato RIGHT of the arm; reach c16, GRASP c34, lifted and carried to the tray, RELEASED at c48 just          FAIL (grasp +
    outside the rim onto the table; went back, re-grasped it (27) at the cap at the tray's edge. No delivery.    carry, no delivery)
I4  tomato left, close to the arm; between the open jaws c20, swept to the tray WITHOUT closing; operator's      FAIL (operator
    hand moved the tomato at c40 (after engagement — flagged); hovered over it open to c75.                       intervened c40)
I5  tomato directly UNDER the gripper near the base; idle 12 chunks, came down on it, between the jaws c30–75    FAIL
    (24→33), never lifted, pushed it about.
```
Row pattern: reach 5/5, fruit between the jaws 5/5, a close that held it 1/5 (I3), delivery 0/5. Misses are the
old ones — close short / beside, and one slip — plus one placement under the gripper (I5), the spot that beat the
orange earlier today. Fine-tune 3 on tomato is now 5/23 valid trials (Sunday 4/13, today 1/10); orange 3/10.

## Session tally 2026-10-28
| row | fruit | trials counted | in the tray | void / aborted |
|---|---|---|---|---|
| F | orange | 4 | 0 | attempt 1 (camera), F5 aborted |
| G | orange | 1 | 0 | wrong-wording launch |
| H | tomato | 5 | 1 | one countdown stop |
| I | tomato | 5 | 0 | I4 operator moved the fruit at c40 |

Pending (unchanged): the auto-reset calibration (tray_centre/tray_hover recorded; 10 slots not yet), then the
20-trial rows on the demonstration-area slots. Set aside by the operator: tomato adjudications A1/D4.

## Master table (2026-10-29)
Every trial, one row each, in `trials.csv` (source) and `TRIALS.md` (readable; regenerate with
`scripts/bench_trials_table.py`). Add a CSV row per trial from now on; this narrative file stays the detail record.

## 2026-10-29 — FRAME-BY-FRAME RE-READ of all 23 valid fine-tune-3 tomato trials (operator's request)
Method: per trial, 8 overhead + 8 wrist frames across the episode plus 8 wrist frames around the first deep close,
read against the gripper reading per chunk (strips in the session scratchpad; A1, B1, D1 from Sunday's composites
because their raw frames were overwritten on 10-28). Verdict changes:
```text
A1  SUCCESS?  → SUCCESS   the tomato is INSIDE the tray (left end, against the inner wall) at c26 and c32; the hand
                           takes it out at c38. Released c24 after a 28-30 hold. Adjudication closed from the frames.
D4  SUCCESS?  → SUCCESS   the gripper reads 28-31 from c13 to c28 with the tomato between the jaws and the table far
                           below in the wrist view at c22 = a real hold, not a push. The Sunday note "never below 41"
                           was wrong (it described c31 onward). Adjudication closed from the trace.
I4  no-close  → released outside the rim: hold 28 at c22-28, carried, opened at c29-30 short of the rim, the tomato
                           landed outside at the tray's near edge; the operator moved it at c40 (after the release).
I1  slip      → close-short: jaws closed to 7-8 at c27-29 in front of the fruit, then an empty trip to the tray.
I5  no-close  → close-above (partial squeeze 16-24 on its top); H5 no-close → close-beside (side squeeze 23-24).
C2  → close-short first (10 at c19), beside later;  C4 → partial squeeze (13-19) then beside, cap;  D1 → beside
    first (14 at c10) then hovered open;  D2 → three partial closes (17/15/15) before the hold (29-31) at ~c51.
```
Totals after the re-read: fine-tune 3 tomato **5/23** (A1, B1, D2, D4, H4), nothing pending; orange 3/10.
Failure modes over the 18 tomato fails: close-beside 7 · close-short 5 · close-above/partial squeeze 3 · released
outside the rim 2 · cap-hit after an idle start 2 · no-engage 1 (several trials show two modes in sequence; the
first is counted). What this says: the arm reaches and gets the fruit between the jaws in 21 of 23 trials; the
loss is at the moment of closing — the jaws shut a few cm before the fruit, or next to it, or on its top — and
twice at the moment of release, a few cm short of the rim. Both are precision-at-contact errors, not navigation.

## 2026-10-29 — "No rest frames": what the operator noticed, and two findings from it
1. By design the server records only what the client sends it — the two images captured BEFORE each chunk. After
   chunk 75 the client moves the arm home itself without calling the policy, so the trial's final pose and the
   arm back at rest were never on file. FIX: bench_client.py now saves both cameras after the last chunk's motion
   ("after_last_chunk") and after the return to the start pose ("at_rest"), on the Acer under
   ~/bench_client_frames/<log stem>/; scripts/sort_bench_frames.py pulls them into the per-trial folders.
2. The first frame of every trial after the first was STALE: chunk 1 of H4 shows the arm still extended at H3's end,
   chunk 1 of I3 shows I2's end. The camera driver queue filled during the 30 s pause and read() dropped only 3
   frames, one short of the queue depth. The policy therefore planned its first chunk from the previous scene. Its
   first chunk is a near-no-op at rest, so the trials stand, but it is a real defect. FIX: queue depth set to 1 and
   8 frames dropped after any idle gap > 5 s. The true start-of-trial frame is chunk 2 in the existing folders.

## 2026-10-29 — ROW J: one tomato trial after the AI90 restart — SUCCESS (served on the RTX 5090)
AI90 came back at 09:22; the 4 TB drive mounted again, checkpoints intact (sizes unchanged); the RTX PRO 5000 is still
absent, so the fine-tune 3 server runs on GPU 0 (the 5090). First thing: the three final checkpoints mirrored to
/home/kiran/lerobot_assets/ckpt_mirror/ and their lora_adapters/ copied to results/so101_lora_on_top_20261019/adapters/
(135–571 MB each, kept out of git). A first launch sent the ORANGE wording while a tomato was on the table — stopped at
c40, void (bench_row3j_void_tomato_with_orange_wording.jsonl). Relaunch with the tomato wording:
```text
J1  tomato left mid-table, tray left; idle 12 chunks; reach c20; hold from c28 (gripper 24–30); lifted, carried,   SUCCESS
    released IN the tray c38–40; back at rest by c50 and held to the cap. RTT 1.22 s. First trial with the new
    start / after-last-chunk / at-rest pictures (results/bench_frames_by_trial/2026-10-29_wed_rowJ_ft3_tomato/trial1_SUCCESS/).
```
Fine-tune 3 tomato is now 6/24; orange 3/10.

### ROW K — tomato ×5, same settings as J (RTX 5090), tray left — 1/5
Log bench_row3k_tomato_20261029.jsonl, frames c11 calls 1–375, per-trial folders results/bench_frames_by_trial/2026-10-29_wed_rowK_ft3_tomato/
(with start / after-last-chunk / at-rest pictures). RTT 1.29–1.33 s.
```text
K1  left, forward of mid-table; came down BESIDE it, closed to 16 against its side c40 and pushed it; hovered    FAIL
    beside it open to the cap.
K2  left mid-table; reach c10, HOLD by c14 (~29), over the tray c26, released IN the tray by c32, at rest c40.    SUCCESS
K3  right of the arm; went there fast, hovered beside it open, closed to 23 on its side c40, pushed it OUT of    FAIL
    the camera view by c56, then stretched fully right over the empty table (lift 67, elbow −76) to the cap.
K4  left mid-table, placed late (not in the start picture); between the jaws c25, closed to 13 just in front of  FAIL
    it c40, pushed it right, closed to 3 beside it at the cap.
K5  right of the arm; idle 20, HOLD from ~c38 (27), carried over the tray, released c44 at the tray's RIGHT      FAIL (released
    edge — landed outside, touching the rim; at rest by c60.                                                     outside the rim)
```
Day: J1 + K = 2/6. Fine-tune 3 tomato 7/29; orange 3/10. Pattern unchanged: both right-side placements (K3, K5)
went wrong at the close or the release; the two left mid-table placements that were on the table at the start
(K2, J1) both succeeded; K1 (further forward) and K4 (late) failed at the close.

### ROW L — THREE ORANGES at once, corpus wording "Grab oranges and place into plate.", 120-chunk cap — 0 of 3, twice
Separate experiment (the real demos have one fruit; the base corpus and the Isaac gate have three). Fresh, larger
oranges than Sunday's. Log bench_row3l_3oranges_20261029.jsonl, frames c12 calls 1–240, folders
results/bench_frames_by_trial/2026-10-29_wed_rowL_ft3_3/. RTT 1.2–1.4 s.
```text
L1  two oranges close to the base (either side of the gripper), one beside the tray. Slow start; from c34 the    0 of 3
    arm hovered ABOVE the two near oranges and closed to 22–26 on air above them five times; nothing moved.
L2  same spots. Hovered open above the near-right orange to c62, then stretched flat across the table (lift 73,  0 of 3
    elbow −83) toward the orange beside the tray and sat with the jaws beside it, never closing.
```
Reading: with three oranges the policy never committed to one. It parked above the near pair (the close-to-base
spot that fails for single fruit too) and closed on air, or drifted to the far one without closing. The Isaac
multi-orange skill (9/10 at 200 s) did not show on the bench in these two trials; placement was not the
recommended spread (the operator kept the same three spots for both). Not counted in the single-fruit totals.

### ROW M — single ORANGE ×5, our wording, 75-chunk cap, tray left — 1/5 (+1 void)
Fresh, larger orange than Sunday's. Part 1 (c13): M1, then a VOID trial — the operator's hand was on the gripper at
c12 while the policy was driving; stopped at c20, homed, row relaunched as part 2 (c14) for the remaining four.
Logs bench_row3m_orange_20261029_part{1,2}.jsonl; folders results/bench_frames_by_trial/2026-10-29_wed_rowM_ft3_orange/.
```text
M1  in front of the base; orange between the open jaws c20, then passed it by to the right and searched there      FAIL
    (closed on air c40) to the cap.
M2  LEFT MID-TABLE; reach c14, HOLD by c26 (~30), over the tray c30, released IN the tray by c34, at rest by c40.   SUCCESS
M3  forward of the base, right; hovered beside it open c14–40, then stretched flat across the table past it.        FAIL
M4  LEFT MID-TABLE; came down off-centre, closed to 32 with the fruit against the OUTSIDE of the left jaw c40,        FAIL
    pushed it right, followed it open to the cap.
M5  forward of the base, right; hovered above it open c20–40, then stretched flat across the table past it.          FAIL
```
Reading: the three placements in front of / right of the base all failed without a close (pass-by or over-reach);
of the two left-mid-table placements one was a clean 40-chunk success and one a close-beside. Same picture as the
tomato today. Fine-tune 3 orange 4/15 (Sunday 3/5, Tuesday 0/5, Wednesday 1/5); tomato 7/29.
DAY 2026-10-29 TOTAL (RTX 5090): tomato 2/6, orange 1/5, three-orange experiment 0/3 ×2.
