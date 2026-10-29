# Bench trials — comprehensive table (SO-101, Pune)

Source: `trials.csv` (hand-kept, one row per trial). `trials_full.csv` adds the numbers computed from each trial's log. Regenerate with `python3 scripts/bench_trials_table.py`.
Narrative per trial: `bench_runs.md`. VOID = not a trial (camera fault, stop, wrong launch, fruit not re-placed); excluded from every count.

Trials: 61 recorded, 54 valid, 7 void.

### By model / fruit

| model / fruit | valid | SUCCESS | SUCCESS? | FAIL | rate |
|---|---|---|---|---|---|
| base / citrus | 2 | 0 | 0 | 2 | 0/2 |
| base / onion (off-protocol) | 3 | 0 | 0 | 3 | 0/3 |
| base / orange | 11 | 0 | 0 | 11 | 0/11 |
| base / tomato | 5 | 0 | 0 | 5 | 0/5 |
| fine-tune 3 / tomato | 23 | 3 | 2 | 18 | 3/23 (up to 5/23) |
| fine-tune 3 / orange | 10 | 3 | 0 | 7 | 3/10 |

### By day / model / fruit

| day / model / fruit | valid | SUCCESS | SUCCESS? | FAIL | rate |
|---|---|---|---|---|---|
| 2026-10-19 / base / citrus | 2 | 0 | 0 | 2 | 0/2 |
| 2026-10-20 / base / onion (off-protocol) | 3 | 0 | 0 | 3 | 0/3 |
| 2026-10-20 / base / orange | 11 | 0 | 0 | 11 | 0/11 |
| 2026-10-26 / base / tomato | 5 | 0 | 0 | 5 | 0/5 |
| 2026-10-26 / fine-tune 3 / tomato | 13 | 2 | 2 | 9 | 2/13 (up to 4/13) |
| 2026-10-26 / fine-tune 3 / orange | 5 | 3 | 0 | 2 | 3/5 |
| 2026-10-28 / fine-tune 3 / orange | 5 | 0 | 0 | 5 | 0/5 |
| 2026-10-28 / fine-tune 3 / tomato | 10 | 1 | 0 | 9 | 1/10 |

### By model / fruit / cap

| model / fruit / cap | valid | SUCCESS | SUCCESS? | FAIL | rate |
|---|---|---|---|---|---|
| base / citrus / cap 45 | 2 | 0 | 0 | 2 | 0/2 |
| base / onion (off-protocol) / cap 45 | 3 | 0 | 0 | 3 | 0/3 |
| base / orange / cap 45 | 11 | 0 | 0 | 11 | 0/11 |
| base / tomato / cap 45 | 5 | 0 | 0 | 5 | 0/5 |
| fine-tune 3 / tomato / cap 45 | 5 | 0 | 1 | 4 | 0/5 (up to 1/5) |
| fine-tune 3 / tomato / cap 75 | 18 | 3 | 1 | 14 | 3/18 (up to 4/18) |
| fine-tune 3 / orange / cap 75 | 10 | 3 | 0 | 7 | 3/10 |

### Failure modes (valid FAIL trials)

| failure mode | count |
|---|---|
| close-beside | 12 |
| close-above | 5 |
| no-close | 5 |
| close-beside/above | 3 |
| close-short | 3 |
| close-above + over-reach | 2 |
| close-above/beside | 2 |
| cap-hit (idle start) | 2 |
| wrong-place (hover at base) | 2 |
| no-close (partial) | 1 |
| wrong-place (fruit never in view) | 1 |
| push + close-beside | 1 |
| no-engage | 1 |
| cap-hit | 1 |
| lift, no delivery | 1 |
| wrong-place | 1 |
| slip | 1 |
| released outside the rim | 1 |
| no-close (operator moved fruit c40) | 1 |

### Every trial — conditions

| date | row | # | model | checkpoint | server | fruit | instruction | cap | front camera | tray | placement |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-19 | base | 1 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | citrus | Grab oranges and place into plate. | 45 | overhead, position 1 | — | — |
| 2026-10-19 | base | 2 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | citrus | Grab oranges and place into plate. | 45 | overhead, position 1 | — | — |
| 2026-10-20 | base | 3 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | onion (off-protocol) | Grab oranges and place into plate. | 45 | overhead, position 1 | — | — |
| 2026-10-20 | base | 4 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | onion (off-protocol) | Grab oranges and place into plate. | 45 | overhead, position 1 | — | — |
| 2026-10-20 | base | 5 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | onion (off-protocol) | Grab oranges and place into plate. | 45 | overhead, position 1 | — | — |
| 2026-10-20 | base | 6 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | far-front |
| 2026-10-20 | base | 7 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | far-front |
| 2026-10-20 | base | 8 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | mid |
| 2026-10-20 | base | 9 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | mid |
| 2026-10-20 | base | 10 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | mid |
| 2026-10-20 | base | 11 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | close-in |
| 2026-10-20 | base | 12 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | close-in |
| 2026-10-20 | base | 13 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | close-in |
| 2026-10-20 | base | 14 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | close-in |
| 2026-10-20 | base | 15 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | close-in |
| 2026-10-20 | base | 16 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | orange | Grab oranges and place into plate. | 45 | overhead, position 2 | — | close-in |
| 2026-10-26 | ctrl | 1 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | tomato | Grab oranges and place into plate. | 45 | overhead, position 2 | — | left-front of base |
| 2026-10-26 | ctrl | 2 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | tomato | Grab oranges and place into plate. | 45 | overhead, position 2 | — | left-front of base |
| 2026-10-26 | ctrl | 3 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | tomato | Grab oranges and place into plate. | 45 | overhead, position 2 | — | left-front of base |
| 2026-10-26 | ctrl | 4 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | tomato | Grab oranges and place into plate. | 45 | overhead, position 2 | — | left-front of base |
| 2026-10-26 | ctrl | 5 | base | dongyoonkim/so101-pi05-base (public) | AI90 :8080 GPU 0 | tomato | Grab oranges and place into plate. | 45 | overhead, position 2 | — | left-front of base |
| 2026-10-26 | A | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 45 | overhead, position 2 | — | left-front mid |
| 2026-10-26 | A | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 45 | overhead, position 2 | — | near base |
| 2026-10-26 | A | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 45 | overhead, position 2 | — | left-front close |
| 2026-10-26 | A | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 45 | overhead, position 2 | — | left-front |
| 2026-10-26 | A | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 45 | overhead, position 2 | — | left |
| 2026-10-26 | B | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | front-left |
| 2026-10-26 | B | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | B | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | B | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | B | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | C | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | C | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | C | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | C | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | close to base |
| 2026-10-26 | D | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | D | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | D | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | moved during c1-10 |
| 2026-10-26 | D | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | near base |
| 2026-10-26 | D | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | — | — |
| 2026-10-26 | E | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | right | left mid-table |
| 2026-10-26 | E | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | right | right near the tray (late placement) |
| 2026-10-26 | E | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | right of the tray (tray left) |
| 2026-10-26 | E | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | upper-left (tray left; late placement) |
| 2026-10-26 | E | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | right of the tray (tray left) |
| 2026-10-28 | F | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | right | centre close to the base |
| 2026-10-28 | F | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | right | late placement |
| 2026-10-28 | F | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | right | left mid-table |
| 2026-10-28 | F | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | right | left |
| 2026-10-28 | F | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | right | — |
| 2026-10-28 | G | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | right | under the gripper near the base |
| 2026-10-28 | H | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | right | left mid-table |
| 2026-10-28 | H | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | right | left mid-table |
| 2026-10-28 | H | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | right | left mid-table |
| 2026-10-28 | H | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | up-centre (near arm) | left mid-table (tray moved up-centre) |
| 2026-10-28 | H | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | right of the arm (tray left) |
| 2026-10-28 | I | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | left mid-table (tray left) |
| 2026-10-28 | I | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | left mid-table (tray left) |
| 2026-10-28 | I | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | right of the arm (tray left) |
| 2026-10-28 | I | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | left close to the arm (tray left) |
| 2026-10-28 | I | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 1 | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | under the gripper near the base |

### Every trial — outcome

| date | row | # | result | failure mode | what happened | first move | grip min (chunk) | wrist roll max | chunks | wall s | RTT s | adjudication | log / frames |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-19 | base | 1 | **FAIL** | close-beside | reached; 10 grasp attempts beside the fruit; black front frames on calls 1-2 | 4 | 2 (3) | 35 | 45 | 74.1 | 0.917 |  | bench_ep1 ep1; frames/ (R3 record; montages/) |
| 2026-10-19 | base | 2 | **FAIL** | close-above | jaws on the fruit (floor 10-17); no enclosure; no lift | 4 | 10 (20) | 31 | 45 | 72.8 | 0.918 |  | bench_ep2 ep1; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 3 | **FAIL** | close-beside | between the jaws once; closed beside it; one empty lift | 2 | 3 (33) | 39 | 45 | 89.1 | 1.285 |  | bench_ep3_onion ep1; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 4 | **FAIL** | close-beside | seven closes beside it; empty lift at the end | 2 | 3 (23) | 17 | 45 | 95.6 | 1.325 |  | bench_ep4_onion ep1; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 5 | **FAIL** | close-above | aligned then closed above it; pushed out; network stall 7-14 s/call | 2 | 4 (15) | 48 | 45 | 147.5 | 1.618 |  | bench_ep5_onion ep1; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 6 | **FAIL** | close-above + over-reach | aligned then closed above it; over-reached past it (camera had moved) | 3 | 2 (12) | 33 | 45 | 87.6 | 1.135 |  | bench_ep6_orange ep1; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 7 | **FAIL** | close-beside/above | 15 chunks idle; closes beside/above | 4 | 5 (22) | 20 | 45 | 78.1 | 0.975 |  | bench_ep7_10_orange ep1; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 8 | **FAIL** | close-beside/above | 16 chunks idle; side squeeze then above; pushed ~10 cm | 12 | 3 (44) | 25 | 45 | 84.7 | 1.202 |  | bench_ep7_10_orange ep2; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 9 | **FAIL** | close-above/beside | between the jaws repeatedly; closes above/beside | 4 | 3 (28) | 25 | 45 | 87.2 | 1.199 |  | bench_ep7_10_orange ep3; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 10 | **FAIL** | close-above + over-reach | closed above it; over-reached; hovered | 2 | 2 (13) | 38 | 45 | 85.0 | 1.205 |  | bench_ep7_10_orange ep4; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 11 | **FAIL** | close-beside | four closes all beside it | 4 | 2 (13) | 35 | 45 | 84.6 | 0.962 |  | bench_ep11_16_orange ep1; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 12 | **FAIL** | close-beside | side squeeze then shut on air; rose and hovered open | 4 | 2 (29) | 45 | 45 | 110.8 | 1.19 |  | bench_ep11_16_orange ep2; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 13 | **FAIL** | close-beside | 15 chunks idle; closes beside | 4 | 4 (25) | 45 | 45 | 85.0 | 1.19 |  | bench_ep11_16_orange ep3; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 14 | **FAIL** | close-beside/above | 19 chunks idle; closes beside/above at the jaw tip | 17 | 8 (30) | 30 | 45 | 86.3 | 1.175 |  | bench_ep11_16_orange ep4; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 15 | **FAIL** | no-close (partial) | between the jaws; only partial closes (20-21); hovered open | 3 | 20 (15) | 36 | 45 | 84.8 | 1.195 |  | bench_ep11_16_orange ep5; frames/ (R3 record; montages/) |
| 2026-10-20 | base | 16 | **FAIL** | wrong-place (fruit never in view) | orange never in the wrist view; closes on air | 11 | 9 (38) | 35 | 45 | 84.6 | 1.21 |  | bench_ep11_16_orange ep6; frames/ (R3 record; montages/) |
| 2026-10-26 | ctrl | 1 | **FAIL** | close-above/beside | between the jaws; every close on its side or above | 15 | 4 (43) | 35 | 45 | 84.9 | 1.222 |  | bench_ctrl_tomato_20261026 ep1; frames/c01 |
| 2026-10-26 | ctrl | 2 | **FAIL** | close-beside | beside; half-closes with the tomato under one jaw | 2 | 7 (15) | 54 | 45 | 89.9 | 1.328 |  | bench_ctrl_tomato_20261026 ep2; frames/c01 |
| 2026-10-26 | ctrl | 3 | **FAIL** | close-above | between the jaws; closes above it | 4 | 7 (16) | 28 | 45 | 90.3 | 1.333 |  | bench_ctrl_tomato_20261026 ep3; frames/c01 |
| 2026-10-26 | ctrl | 4 | **FAIL** | close-beside | shut on air beside it; then above it | 5 | 6 (17) | 39 | 45 | 87.6 | 1.25 |  | bench_ctrl_tomato_20261026 ep4; frames/c01 |
| 2026-10-26 | ctrl | 5 | **FAIL** | close-beside | beside; partial closes only | 8 | 16 (15) | 39 | 45 | 90.0 | 1.303 |  | bench_ctrl_tomato_20261026 ep5; frames/c01 |
| 2026-10-26 | A | 1 | **SUCCESS?** | — | grasp (28-30) + carry + release at the tray's near edge/rim; operator to adjudicate in/on rim | 2 | 28 (19) | 27 | 45 | 80.1 | 1.033 | rim or inside? (set aside by operator) | bench_row3_tomato_20261026 ep1; row3 c01 (calls 1-48 overwritten 10-28) |
| 2026-10-26 | A | 2 | **FAIL** | push + close-beside | pushed it toward the base; closed to 4 beside it | 4 | 4 (28) | 36 | 45 | 86.1 | 1.261 |  | bench_row3_tomato_20261026 ep2; row3 c01 (calls 1-48 overwritten 10-28) |
| 2026-10-26 | A | 3 | **FAIL** | no-engage | small reach then rest with the gripper open; did not engage | 5 | 41 (17) | 12 | 45 | 87.3 | 1.154 |  | bench_row3_tomato_20261026 ep3; row3 c01 (calls 1-48 overwritten 10-28) |
| 2026-10-26 | A | 4 | **FAIL** | cap-hit (idle start) | idle 32 chunks; cap hit mid-approach | 6 | 30 (45) | 8 | 45 | 90.4 | 1.307 |  | bench_row3_tomato_20261026 ep4; row3 c01 (calls 1-48 overwritten 10-28) |
| 2026-10-26 | A | 5 | **FAIL** | cap-hit (idle start) | idle 26 chunks; cap hit mid-grasp (closing to 17 on it) | 8 | 14 (41) | 9 | 45 | 90.2 | 1.329 |  | bench_row3_tomato_20261026 ep5; row3 c01 (calls 1-48 overwritten 10-28) |
| 2026-10-26 | B | 1 | **SUCCESS** | — | idle 15; grasp (28-32); carried; lowered INTO the tray; released; at rest | 9 | 27 (42) | 21 | 75 | 144.1 | 1.275 |  | bench_row3b_tomato_20261026 ep1; row3 c02 (calls 1-348 overwritten 10-28) |
| 2026-10-26 | B | 2 | **VOID** | void | tomato not re-placed (stayed in the tray); arm stayed at rest | 5 | 29 (48) | 6 | 75 | 149.5 | 1.334 |  | bench_row3b_tomato_20261026 ep2; row3 c02 (calls 1-348 overwritten 10-28) |
| 2026-10-26 | B | 3 | **VOID** | void | same as B2 | 6 | 24 (63) | 7 | 75 | 148.7 | 1.311 |  | bench_row3b_tomato_20261026 ep3; row3 c02 (calls 1-348 overwritten 10-28) |
| 2026-10-26 | B | 4 | **VOID** | void | same as B2 | 2 | 26 (63) | 4 | 75 | 147.9 | 1.313 |  | bench_row3b_tomato_20261026 ep4; row3 c02 (calls 1-348 overwritten 10-28) |
| 2026-10-26 | B | 5 | **VOID** | void | same as B2 | 9 | 22 (61) | 12 | 75 | 151.5 | 1.347 |  | bench_row3b_tomato_20261026 ep5; row3 c02 (calls 1-348 overwritten 10-28) |
| 2026-10-26 | C | 1 | **VOID** | void | tomato still in the tray at the start; moved late; cap hit | 2 | 15 (72) | 17 | 75 | 142.1 | 1.068 |  | bench_row3c_tomato_20261026 ep1; row3 c03 (calls 1-65 overwritten 10-28) |
| 2026-10-26 | C | 2 | **FAIL** | close-above | between the jaws; closes on its top/side; full close on air at c60 | 7 | 1 (63) | 51 | 75 | 149.5 | 1.298 |  | bench_row3c_tomato_20261026 ep2; row3 c03 (calls 1-65 overwritten 10-28) |
| 2026-10-26 | C | 3 | **FAIL** | no-close | between the jaws (31→18 no hold); pushed it; circled; wrist rolled 84 | 7 | 12 (32) | 84 | 75 | 149.3 | 1.34 |  | bench_row3c_tomato_20261026 ep3; row3 c03 (calls 1-65 overwritten 10-28) |
| 2026-10-26 | C | 4 | **FAIL** | cap-hit | around it c20-60; closing to 14 on it at the cap | 4 | 9 (46) | 59 | 75 | 148.6 | 1.331 |  | bench_row3c_tomato_20261026 ep4; row3 c03 (calls 1-65 overwritten 10-28) |
| 2026-10-26 | D | 1 | **FAIL** | no-close | reached; hovered with the tomato between the open jaws; never closed | 2 | 14 (15) | 52 | 75 | 133.2 | 1.103 |  | bench_row3d_tomato_20261026 ep1; row3 c04 (calls 1-75 overwritten 10-28) |
| 2026-10-26 | D | 2 | **SUCCESS** | — | grasp; lifted and carried; released INTO the tray; at rest | 3 | 15 (22) | 24 | 75 | 138.1 | 1.186 |  | bench_row3d_tomato_20261026 ep2; row3 c04 (calls 1-75 overwritten 10-28) |
| 2026-10-26 | D | 3 | **FAIL** | close-above | between the jaws; closes to 12/19 on its top; no hold | 4 | 3 (14) | 60 | 75 | 141.5 | 1.223 |  | bench_row3d_tomato_20261026 ep3; row3 c04 (calls 1-75 overwritten 10-28) |
| 2026-10-26 | D | 4 | **SUCCESS?** | — | tomato in the tray by c30 but the gripper never read below 41 (loose carry or push); operator to adjudicate | 3 | 28 (15) | 12 | 75 | 140.8 | 1.222 | grasp or push? (set aside by operator) | bench_row3d_tomato_20261026 ep4; row3 c04 (calls 1-75 overwritten 10-28) |
| 2026-10-26 | D | 5 | **VOID** | void | wrist camera read failed at chunk 23; client exited | 3 | 38 (10) | 11 | 23 |  |  |  | bench_row3d_tomato_20261026 ep5; row3 c04 (calls 1-75 overwritten 10-28) |
| 2026-10-26 | E | 1 | **SUCCESS** | — | reach c10; hold c20 (20); lift; over the tray c50; released; at rest by c60 | 3 | 10 (19) | 47 | 75 | 130.1 | 0.978 |  | bench_row3e_orange_20261026 ep1; row3 c05 |
| 2026-10-26 | E | 2 | **FAIL** | no-close | between the jaws c20-75 (25-48); never held | 3 | 18 (39) | 9 | 75 | 137.2 | 1.178 |  | bench_row3e_orange_20261026 ep2; row3 c05 |
| 2026-10-26 | E | 3 | **SUCCESS** | — | reach c10; hold c20 (25); in the tray by c30; hovered open | 4 | 23 (26) | 41 | 75 | 138.4 | 1.179 |  | bench_row3e_orange_20261026 ep3; row3 c05 |
| 2026-10-26 | E | 4 | **FAIL** | lift, no delivery | hold c30 (26) and lift; set it back down on the table; never carried to the tray | 8 | 17 (24) | 57 | 75 | 139.0 | 1.181 |  | bench_row3e_orange_20261026 ep4; row3 c05 |
| 2026-10-26 | E | 5 | **SUCCESS** | — | reach c10; hold c20 (26); carried left; in the tray by c30; at rest | 3 | 14 (71) | 16 | 75 | 140.4 | 1.179 |  | bench_row3e_orange_20261026 ep5; row3 c05 |
| 2026-10-28 | F | 1 | **FAIL** | wrong-place | reach; swept far right (pan +50; wrist roll 97); shut on air | 4 | 1 (75) | 98 | 75 | 143.8 | 1.275 |  | bench_row3f_orange_20261028 ep1; row3 c02 |
| 2026-10-28 | F | 2 | **FAIL** | wrong-place (hover at base) | hovered in front of the base; no grasp | 4 | 11 (14) | 13 | 75 | 148.9 | 1.304 |  | bench_row3f_orange_20261028 ep2; row3 c02 |
| 2026-10-28 | F | 3 | **FAIL** | close-beside | pushed down beside it (grip 4); swept right | 6 | 4 (39) | 36 | 75 | 152.3 | 1.355 |  | bench_row3f_orange_20261028 ep3; row3 c02 |
| 2026-10-28 | F | 4 | **FAIL** | wrong-place (hover at base) | hovered near the base; rose; orange ended hidden under the arm | 4 | 30 (70) | 11 | 75 | 150.8 | 1.335 |  | bench_row3f_orange_20261028 ep4; row3 c02 |
| 2026-10-28 | F | 5 | **VOID** | void | aborted at chunk 47 on the operator's word | 3 | 16 (45) | 16 | 47 |  |  |  | bench_row3f_orange_20261028 ep5; row3 c02 |
| 2026-10-28 | G | 1 | **FAIL** | close-beside | stretched far forward and low; came down beside it; gripper open throughout | 2 | 16 (13) | 44 | 75 | 134.4 | 1.002 |  | bench_row3g_orange_20261028 ep1; row3 c04 |
| 2026-10-28 | H | 1 | **FAIL** | close-short | between the jaws c20; closed to 12 just short of it; pushed it left (orange still on the table edge) | 2 | 12 (30) | 137 | 75 | 138.2 | 1.07 |  | bench_row3h_tomato_20261028 ep1; row3 c07 |
| 2026-10-28 | H | 2 | **FAIL** | close-short | between the jaws c20-30; closed to 4 in front of it; swept right | 9 | 3 (42) | 93 | 75 | 150.7 | 1.325 |  | bench_row3h_tomato_20261028 ep2; row3 c07 |
| 2026-10-28 | H | 3 | **FAIL** | close-short | between the jaws c20; closed to 3 just in front of it c26; swept away | 4 | 3 (30) | 133 | 75 | 164.5 | 1.372 |  | bench_row3h_tomato_20261028 ep3; row3 c07 |
| 2026-10-28 | H | 4 | **SUCCESS** | — | grasp c22 (held ~23); carried; released IN the tray by c40; at rest c40-62 | 5 | 23 (30) | 22 | 75 | 148.3 | 1.354 |  | bench_row3h_tomato_20261028 ep4; row3 c07 |
| 2026-10-28 | H | 5 | **FAIL** | no-close | hovered beside it open c12-50; nudged; closed to 23 on it at the cap; no lift | 4 | 23 (75) | 70 | 75 | 144.6 | 1.303 |  | bench_row3h_tomato_20261028 ep5; row3 c07 |
| 2026-10-28 | I | 1 | **FAIL** | slip | closed to 19 on it c25 and it SLIPPED; empty trip to the tray; hovered beside it | 10 | 7 (29) | 61 | 75 | 143.4 | 1.256 |  | bench_row3i_tomato_20261028 ep1; row3 c08 |
| 2026-10-28 | I | 2 | **FAIL** | close-beside | closed beside it on air; pulled back with it wedged; wrist roll 129 | 4 | 5 (32) | 129 | 75 | 149.7 | 1.358 |  | bench_row3i_tomato_20261028 ep2; row3 c08 |
| 2026-10-28 | I | 3 | **FAIL** | released outside the rim | grasp c34; carried; released just OUTSIDE the rim c48; re-grasped at the cap | 9 | 14 (51) | 18 | 75 | 147.8 | 1.351 |  | bench_row3i_tomato_20261028 ep3; row3 c08 |
| 2026-10-28 | I | 4 | **FAIL** | no-close (operator moved fruit c40) | between the open jaws c20; swept to the tray without closing; operator moved the fruit at c40 | 3 | 14 (54) | 23 | 75 | 150.2 | 1.351 |  | bench_row3i_tomato_20261028 ep4; row3 c08 |
| 2026-10-28 | I | 5 | **FAIL** | no-close | idle 12; came down on it; between the jaws to the cap; never lifted | 4 | 16 (49) | 34 | 75 | 152.4 | 1.355 |  | bench_row3i_tomato_20261028 ep5; row3 c08 |
