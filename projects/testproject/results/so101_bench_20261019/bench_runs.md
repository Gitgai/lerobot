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

## Running tally
| trial | utc | result | chunks | wall s | median RTT s | note |
|---|---|---|---|---|---|---|
| 1 | 2026-10-19T19:58:52Z | FAIL | 45 | 74.1 | 0.917 | reached, 10 grasp attempts beside the fruit, black front frames on calls 1–2 |
