# Bench trials — one row per trial (SO-101, Pune, overhead front camera)

Source of truth: `trials.csv` in this folder (add a row per trial, then run `scripts/bench_trials_table.py`).
Full narrative per trial: `bench_runs.md`. VOID rows are not trials (camera fault, aborted, wrong launch, fruit not re-placed) and are left out of every count.

Trials recorded: 61 (54 valid, 7 void).

### model / fruit

| model / fruit | valid trials | SUCCESS | SUCCESS? | FAIL | success rate |
|---|---|---|---|---|---|
| base / citrus | 2 | 0 | 0 | 2 | 0/2 |
| base / onion (off-protocol) | 3 | 0 | 0 | 3 | 0/3 |
| base / orange | 11 | 0 | 0 | 11 | 0/11 |
| base / tomato | 5 | 0 | 0 | 5 | 0/5 |
| fine-tune 3 / tomato | 23 | 3 | 2 | 18 | 3/23 (up to 5/23 if SUCCESS? count) |
| fine-tune 3 / orange | 10 | 3 | 0 | 7 | 3/10 |

### day / model / fruit

| day / model / fruit | valid trials | SUCCESS | SUCCESS? | FAIL | success rate |
|---|---|---|---|---|---|
| 2026-10-19 / base / citrus | 2 | 0 | 0 | 2 | 0/2 |
| 2026-10-20 / base / onion (off-protocol) | 3 | 0 | 0 | 3 | 0/3 |
| 2026-10-20 / base / orange | 11 | 0 | 0 | 11 | 0/11 |
| 2026-10-26 / base / tomato | 5 | 0 | 0 | 5 | 0/5 |
| 2026-10-26 / fine-tune 3 / tomato | 13 | 2 | 2 | 9 | 2/13 (up to 4/13 if SUCCESS? count) |
| 2026-10-26 / fine-tune 3 / orange | 5 | 3 | 0 | 2 | 3/5 |
| 2026-10-28 / fine-tune 3 / orange | 5 | 0 | 0 | 5 | 0/5 |
| 2026-10-28 / fine-tune 3 / tomato | 10 | 1 | 0 | 9 | 1/10 |

### Every trial

| date | row | # | model | fruit | cap | placement | result | what happened |
|---|---|---|---|---|---|---|---|---|
| 2026-10-19 | base | 1 | base | citrus | 45 | — | **FAIL** | reached; 10 grasp attempts beside the fruit; black front frames on calls 1-2 |
| 2026-10-19 | base | 2 | base | citrus | 45 | — | **FAIL** | jaws on the fruit (floor 10-17); no enclosure; no lift |
| 2026-10-20 | base | 3 | base | onion (off-protocol) | 45 | — | **FAIL** | between the jaws once; closed beside it; one empty lift |
| 2026-10-20 | base | 4 | base | onion (off-protocol) | 45 | — | **FAIL** | seven closes beside it; empty lift at the end |
| 2026-10-20 | base | 5 | base | onion (off-protocol) | 45 | — | **FAIL** | aligned then closed above it; pushed out; network stall 7-14 s/call |
| 2026-10-20 | base | 6 | base | orange | 45 | far-front | **FAIL** | aligned then closed above it; over-reached past it (camera had moved) |
| 2026-10-20 | base | 7 | base | orange | 45 | far-front | **FAIL** | 15 chunks idle; closes beside/above |
| 2026-10-20 | base | 8 | base | orange | 45 | mid | **FAIL** | 16 chunks idle; side squeeze then above; pushed ~10 cm |
| 2026-10-20 | base | 9 | base | orange | 45 | mid | **FAIL** | between the jaws repeatedly; closes above/beside |
| 2026-10-20 | base | 10 | base | orange | 45 | mid | **FAIL** | closed above it; over-reached; hovered |
| 2026-10-20 | base | 11 | base | orange | 45 | close-in | **FAIL** | four closes all beside it |
| 2026-10-20 | base | 12 | base | orange | 45 | close-in | **FAIL** | side squeeze then shut on air; rose and hovered open |
| 2026-10-20 | base | 13 | base | orange | 45 | close-in | **FAIL** | 15 chunks idle; closes beside |
| 2026-10-20 | base | 14 | base | orange | 45 | close-in | **FAIL** | 19 chunks idle; closes beside/above at the jaw tip |
| 2026-10-20 | base | 15 | base | orange | 45 | close-in | **FAIL** | between the jaws; only partial closes (20-21); hovered open |
| 2026-10-20 | base | 16 | base | orange | 45 | close-in | **FAIL** | orange never in the wrist view; closes on air |
| 2026-10-26 | ctrl | 1 | base | tomato | 45 | left-front of base | **FAIL** | between the jaws; every close on its side or above |
| 2026-10-26 | ctrl | 2 | base | tomato | 45 | left-front of base | **FAIL** | beside; half-closes with the tomato under one jaw |
| 2026-10-26 | ctrl | 3 | base | tomato | 45 | left-front of base | **FAIL** | between the jaws; closes above it |
| 2026-10-26 | ctrl | 4 | base | tomato | 45 | left-front of base | **FAIL** | shut on air beside it; then above it |
| 2026-10-26 | ctrl | 5 | base | tomato | 45 | left-front of base | **FAIL** | beside; partial closes only |
| 2026-10-26 | A | 1 | fine-tune 3 | tomato | 45 | left-front mid | **SUCCESS?** | grasp (28-30) + carry + release at the tray's near edge/rim; operator to adjudicate in/on rim |
| 2026-10-26 | A | 2 | fine-tune 3 | tomato | 45 | near base | **FAIL** | pushed it toward the base; closed to 4 beside it |
| 2026-10-26 | A | 3 | fine-tune 3 | tomato | 45 | left-front close | **FAIL** | small reach then rest with the gripper open; did not engage |
| 2026-10-26 | A | 4 | fine-tune 3 | tomato | 45 | left-front | **FAIL** | idle 32 chunks; cap hit mid-approach |
| 2026-10-26 | A | 5 | fine-tune 3 | tomato | 45 | left | **FAIL** | idle 26 chunks; cap hit mid-grasp (closing to 17 on it) |
| 2026-10-26 | B | 1 | fine-tune 3 | tomato | 75 | front-left | **SUCCESS** | idle 15; grasp (28-32); carried; lowered INTO the tray; released; at rest |
| 2026-10-26 | B | 2 | fine-tune 3 | tomato | 75 | — | **VOID** | tomato not re-placed (stayed in the tray); arm stayed at rest |
| 2026-10-26 | B | 3 | fine-tune 3 | tomato | 75 | — | **VOID** | same as B2 |
| 2026-10-26 | B | 4 | fine-tune 3 | tomato | 75 | — | **VOID** | same as B2 |
| 2026-10-26 | B | 5 | fine-tune 3 | tomato | 75 | — | **VOID** | same as B2 |
| 2026-10-26 | C | 1 | fine-tune 3 | tomato | 75 | — | **VOID** | tomato still in the tray at the start; moved late; cap hit |
| 2026-10-26 | C | 2 | fine-tune 3 | tomato | 75 | — | **FAIL** | between the jaws; closes on its top/side; full close on air at c60 |
| 2026-10-26 | C | 3 | fine-tune 3 | tomato | 75 | — | **FAIL** | between the jaws (31→18 no hold); pushed it; circled; wrist rolled 84 |
| 2026-10-26 | C | 4 | fine-tune 3 | tomato | 75 | close to base | **FAIL** | around it c20-60; closing to 14 on it at the cap |
| 2026-10-26 | D | 1 | fine-tune 3 | tomato | 75 | — | **FAIL** | reached; hovered with the tomato between the open jaws; never closed |
| 2026-10-26 | D | 2 | fine-tune 3 | tomato | 75 | — | **SUCCESS** | grasp; lifted and carried; released INTO the tray; at rest |
| 2026-10-26 | D | 3 | fine-tune 3 | tomato | 75 | moved during c1-10 | **FAIL** | between the jaws; closes to 12/19 on its top; no hold |
| 2026-10-26 | D | 4 | fine-tune 3 | tomato | 75 | near base | **SUCCESS?** | tomato in the tray by c30 but the gripper never read below 41 (loose carry or push); operator to adjudicate |
| 2026-10-26 | D | 5 | fine-tune 3 | tomato | 75 | — | **VOID** | wrist camera read failed at chunk 23; client exited |
| 2026-10-26 | E | 1 | fine-tune 3 | orange | 75 | left mid-table | **SUCCESS** | reach c10; hold c20 (20); lift; over the tray c50; released; at rest by c60 |
| 2026-10-26 | E | 2 | fine-tune 3 | orange | 75 | right near the tray (late placement) | **FAIL** | between the jaws c20-75 (25-48); never held |
| 2026-10-26 | E | 3 | fine-tune 3 | orange | 75 | right of the tray (tray left) | **SUCCESS** | reach c10; hold c20 (25); in the tray by c30; hovered open |
| 2026-10-26 | E | 4 | fine-tune 3 | orange | 75 | upper-left (tray left; late placement) | **FAIL** | hold c30 (26) and lift; set it back down on the table; never carried to the tray |
| 2026-10-26 | E | 5 | fine-tune 3 | orange | 75 | right of the tray (tray left) | **SUCCESS** | reach c10; hold c20 (26); carried left; in the tray by c30; at rest |
| 2026-10-28 | F | 1 | fine-tune 3 | orange | 75 | centre close to the base | **FAIL** | reach; swept far right (pan +50; wrist roll 97); shut on air |
| 2026-10-28 | F | 2 | fine-tune 3 | orange | 75 | late placement | **FAIL** | hovered in front of the base; no grasp |
| 2026-10-28 | F | 3 | fine-tune 3 | orange | 75 | left mid-table | **FAIL** | pushed down beside it (grip 4); swept right |
| 2026-10-28 | F | 4 | fine-tune 3 | orange | 75 | left | **FAIL** | hovered near the base; rose; orange ended hidden under the arm |
| 2026-10-28 | F | 5 | fine-tune 3 | orange | 75 | — | **VOID** | aborted at chunk 47 on the operator's word |
| 2026-10-28 | G | 1 | fine-tune 3 | orange | 75 | under the gripper near the base | **FAIL** | stretched far forward and low; came down beside it; gripper open throughout |
| 2026-10-28 | H | 1 | fine-tune 3 | tomato | 75 | left mid-table | **FAIL** | between the jaws c20; closed to 12 just short of it; pushed it left (orange still on the table edge) |
| 2026-10-28 | H | 2 | fine-tune 3 | tomato | 75 | left mid-table | **FAIL** | between the jaws c20-30; closed to 4 in front of it; swept right |
| 2026-10-28 | H | 3 | fine-tune 3 | tomato | 75 | left mid-table | **FAIL** | between the jaws c20; closed to 3 just in front of it c26; swept away |
| 2026-10-28 | H | 4 | fine-tune 3 | tomato | 75 | left mid-table (tray moved up-centre) | **SUCCESS** | grasp c22 (held ~23); carried; released IN the tray by c40; at rest c40-62 |
| 2026-10-28 | H | 5 | fine-tune 3 | tomato | 75 | right of the arm (tray left) | **FAIL** | hovered beside it open c12-50; nudged; closed to 23 on it at the cap; no lift |
| 2026-10-28 | I | 1 | fine-tune 3 | tomato | 75 | left mid-table (tray left) | **FAIL** | closed to 19 on it c25 and it SLIPPED; empty trip to the tray; hovered beside it |
| 2026-10-28 | I | 2 | fine-tune 3 | tomato | 75 | left mid-table (tray left) | **FAIL** | closed beside it on air; pulled back with it wedged; wrist roll 129 |
| 2026-10-28 | I | 3 | fine-tune 3 | tomato | 75 | right of the arm (tray left) | **FAIL** | grasp c34; carried; released just OUTSIDE the rim c48; re-grasped at the cap |
| 2026-10-28 | I | 4 | fine-tune 3 | tomato | 75 | left close to the arm (tray left) | **FAIL** | between the open jaws c20; swept to the tray without closing; operator moved the fruit at c40 |
| 2026-10-28 | I | 5 | fine-tune 3 | tomato | 75 | under the gripper near the base | **FAIL** | idle 12; came down on it; between the jaws to the cap; never lifted |
