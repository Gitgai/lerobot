# Bench trials — comprehensive table (SO-101, Pune)

Source: `trials.csv` (hand-kept, one row per trial). `trials_full.csv` adds the numbers computed from each trial's log. Regenerate with `python3 scripts/bench_trials_table.py`.
**Frames, browsable:** `results/bench_frames_by_trial/<date>_<day>_row<X>_<model>_<fruit>/trial<N>_<RESULT>/` (front_chunkNNN.jpg + wrist_chunkNNN.jpg + WHAT_HAPPENED.txt; built by `scripts/sort_bench_frames.py`). Raw dump behind it: every policy call's overhead + wrist JPEG, named `<prefix>_call<N>_{front,wrist}.jpg`; fine-tune 3 rows in `results/so101_lora_on_top_20261019/bench_frames_row3_010000/` (prefix per row in the `frames` column, e.g. row I = c08, row H = c07, row E = c05), public-base rows in `results/so101_bench_20261019/frames/`. Trial N of a row covers calls (N-1)*cap+1 … N*cap. Narrative per trial: `bench_runs.md`. VOID = not a trial (camera fault, stop, wrong launch, fruit not re-placed); excluded from every count.

Trials: 84 recorded, 73 valid, 11 void.

### By model / fruit

| model / fruit | valid | SUCCESS | SUCCESS? | FAIL | rate |
|---|---|---|---|---|---|
| base / citrus | 2 | 0 | 0 | 2 | 0/2 |
| base / onion (off-protocol) | 3 | 0 | 0 | 3 | 0/3 |
| base / orange | 11 | 0 | 0 | 11 | 0/11 |
| base / tomato | 5 | 0 | 0 | 5 | 0/5 |
| fine-tune 3 / tomato | 29 | 7 | 0 | 22 | 7/29 |
| fine-tune 3 / orange | 21 | 9 | 0 | 12 | 9/21 |
| fine-tune 3 / 3 oranges (multi-fruit experiment) | 2 | 0 | 0 | 2 | 0/2 |

### By day / model / fruit

| day / model / fruit | valid | SUCCESS | SUCCESS? | FAIL | rate |
|---|---|---|---|---|---|
| 2026-10-19 / base / citrus | 2 | 0 | 0 | 2 | 0/2 |
| 2026-10-20 / base / onion (off-protocol) | 3 | 0 | 0 | 3 | 0/3 |
| 2026-10-20 / base / orange | 11 | 0 | 0 | 11 | 0/11 |
| 2026-10-26 / base / tomato | 5 | 0 | 0 | 5 | 0/5 |
| 2026-10-26 / fine-tune 3 / tomato | 13 | 4 | 0 | 9 | 4/13 |
| 2026-10-26 / fine-tune 3 / orange | 5 | 3 | 0 | 2 | 3/5 |
| 2026-10-28 / fine-tune 3 / orange | 5 | 0 | 0 | 5 | 0/5 |
| 2026-10-28 / fine-tune 3 / tomato | 10 | 1 | 0 | 9 | 1/10 |
| 2026-10-29 / fine-tune 3 / tomato | 6 | 2 | 0 | 4 | 2/6 |
| 2026-10-29 / fine-tune 3 / 3 oranges (multi-fruit experiment) | 2 | 0 | 0 | 2 | 0/2 |
| 2026-10-29 / fine-tune 3 / orange | 11 | 6 | 0 | 5 | 6/11 |

### By model / fruit / cap

| model / fruit / cap | valid | SUCCESS | SUCCESS? | FAIL | rate |
|---|---|---|---|---|---|
| base / citrus / cap 45 | 2 | 0 | 0 | 2 | 0/2 |
| base / onion (off-protocol) / cap 45 | 3 | 0 | 0 | 3 | 0/3 |
| base / orange / cap 45 | 11 | 0 | 0 | 11 | 0/11 |
| base / tomato / cap 45 | 5 | 0 | 0 | 5 | 0/5 |
| fine-tune 3 / tomato / cap 45 | 5 | 1 | 0 | 4 | 1/5 |
| fine-tune 3 / tomato / cap 75 | 24 | 6 | 0 | 18 | 6/24 |
| fine-tune 3 / orange / cap 75 | 21 | 9 | 0 | 12 | 9/21 |
| fine-tune 3 / 3 oranges (multi-fruit experiment) / cap 120 | 2 | 0 | 0 | 2 | 0/2 |

### Failure modes (valid FAIL trials; the FIRST mode when a trial shows two in sequence)

| failure mode | count |
|---|---|
| close-beside | 18 |
| close-above | 7 |
| no-close | 6 |
| close-short | 6 |
| wrong-place | 5 |
| close-beside/above | 3 |
| released outside the rim | 3 |
| close-above + over-reach | 2 |
| close-above/beside | 2 |
| cap-hit | 2 |
| push + close-beside | 1 |
| no-engage | 1 |
| lift | 1 |

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
| 2026-10-29 | J | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090 — the PRO 5000 is missing since the 10-28 reboot) | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | left mid-table (tray left) |
| 2026-10-29 | K | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | left, forward of mid-table |
| 2026-10-29 | K | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | K | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | right of the arm |
| 2026-10-29 | K | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | left mid-table (placed late, not in the start picture) |
| 2026-10-29 | K | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | tomato | pick up the tomato and place it on the plate | 75 | overhead, position 2 | left | right of the arm |
| 2026-10-29 | L | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | 3 oranges (multi-fruit experiment) | Grab oranges and place into plate. | 120 | overhead, position 2 | left | two oranges close to the base (left and right of the gripper), one beside the tray |
| 2026-10-29 | L | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | 3 oranges (multi-fruit experiment) | Grab oranges and place into plate. | 120 | overhead, position 2 | left | same three spots as L1 |
| 2026-10-29 | M | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | in front of the base |
| 2026-10-29 | M | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | M | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | forward of the base, to its right |
| 2026-10-29 | M | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | M | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | forward of the base, to its right |
| 2026-10-29 | M | void | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | N | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | N | 2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | N | 3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | N | 4 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | N | 5 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | N | void1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | orange still inside tray at start |
| 2026-10-29 | N | void2 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | orange still inside tray at start |
| 2026-10-29 | N | void3 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | left mid-table |
| 2026-10-29 | O | 1 | fine-tune 3 | row3_all169_conservative ckpt 010000 (LoRA merged) | AI90 :8081 GPU 0 (RTX 5090) | orange | pick up the orange and place it on the plate | 75 | overhead, position 2 | left | far right of the arm, near the table edge |

### Every trial — outcome

| date | row | # | result | failure mode | what happened | first move | grip min (chunk) | wrist roll max | chunks | wall s | RTT s | adjudication | log / frames |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-19 | base | 1 | **FAIL** | close-beside | reached; 10 grasp attempts beside the fruit; black front frames on calls 1-2 | 4 | 2 (3) | 35 | 45 | 74.1 | 0.917 |  | bench_ep1 ep1; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-19 | base | 2 | **FAIL** | close-above | jaws on the fruit (floor 10-17); no enclosure; no lift | 4 | 10 (20) | 31 | 45 | 72.8 | 0.918 |  | bench_ep2 ep1; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 3 | **FAIL** | close-beside | between the jaws once; closed beside it; one empty lift | 2 | 3 (33) | 39 | 45 | 89.1 | 1.285 |  | bench_ep3_onion ep1; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 4 | **FAIL** | close-beside | seven closes beside it; empty lift at the end | 2 | 3 (23) | 17 | 45 | 95.6 | 1.325 |  | bench_ep4_onion ep1; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 5 | **FAIL** | close-above | aligned then closed above it; pushed out; network stall 7-14 s/call | 2 | 4 (15) | 48 | 45 | 147.5 | 1.618 |  | bench_ep5_onion ep1; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 6 | **FAIL** | close-above + over-reach | aligned then closed above it; over-reached past it (camera had moved) | 3 | 2 (12) | 33 | 45 | 87.6 | 1.135 |  | bench_ep6_orange ep1; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 7 | **FAIL** | close-beside/above | 15 chunks idle; closes beside/above | 4 | 5 (22) | 20 | 45 | 78.1 | 0.975 |  | bench_ep7_10_orange ep1; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 8 | **FAIL** | close-beside/above | 16 chunks idle; side squeeze then above; pushed ~10 cm | 12 | 3 (44) | 25 | 45 | 84.7 | 1.202 |  | bench_ep7_10_orange ep2; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 9 | **FAIL** | close-above/beside | between the jaws repeatedly; closes above/beside | 4 | 3 (28) | 25 | 45 | 87.2 | 1.199 |  | bench_ep7_10_orange ep3; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 10 | **FAIL** | close-above + over-reach | closed above it; over-reached; hovered | 2 | 2 (13) | 38 | 45 | 85.0 | 1.205 |  | bench_ep7_10_orange ep4; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 11 | **FAIL** | close-beside | four closes all beside it | 4 | 2 (13) | 35 | 45 | 84.6 | 0.962 |  | bench_ep11_16_orange ep1; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 12 | **FAIL** | close-beside | side squeeze then shut on air; rose and hovered open | 4 | 2 (29) | 45 | 45 | 110.8 | 1.19 |  | bench_ep11_16_orange ep2; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 13 | **FAIL** | close-beside | 15 chunks idle; closes beside | 4 | 4 (25) | 45 | 45 | 85.0 | 1.19 |  | bench_ep11_16_orange ep3; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 14 | **FAIL** | close-beside/above | 19 chunks idle; closes beside/above at the jaw tip | 17 | 8 (30) | 30 | 45 | 86.3 | 1.175 |  | bench_ep11_16_orange ep4; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 15 | **FAIL** | no-close (partial) | between the jaws; only partial closes (20-21); hovered open | 3 | 20 (15) | 36 | 45 | 84.8 | 1.195 |  | bench_ep11_16_orange ep5; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-20 | base | 16 | **FAIL** | wrong-place (fruit never in view) | orange never in the wrist view; closes on air | 11 | 9 (38) | 35 | 45 | 84.6 | 1.21 |  | bench_ep11_16_orange ep6; results/so101_bench_20261019/frames/ (R3 record; montages/)_call* |
| 2026-10-26 | ctrl | 1 | **FAIL** | close-above/beside | between the jaws; every close on its side or above | 15 | 4 (43) | 35 | 45 | 84.9 | 1.222 |  | bench_ctrl_tomato_20261026 ep1; results/so101_bench_20261019/frames/c01_call* |
| 2026-10-26 | ctrl | 2 | **FAIL** | close-beside | beside; half-closes with the tomato under one jaw | 2 | 7 (15) | 54 | 45 | 89.9 | 1.328 |  | bench_ctrl_tomato_20261026 ep2; results/so101_bench_20261019/frames/c01_call* |
| 2026-10-26 | ctrl | 3 | **FAIL** | close-above | between the jaws; closes above it | 4 | 7 (16) | 28 | 45 | 90.3 | 1.333 |  | bench_ctrl_tomato_20261026 ep3; results/so101_bench_20261019/frames/c01_call* |
| 2026-10-26 | ctrl | 4 | **FAIL** | close-beside | shut on air beside it; then above it | 5 | 6 (17) | 39 | 45 | 87.6 | 1.25 |  | bench_ctrl_tomato_20261026 ep4; results/so101_bench_20261019/frames/c01_call* |
| 2026-10-26 | ctrl | 5 | **FAIL** | close-beside | beside; partial closes only | 8 | 16 (15) | 39 | 45 | 90.0 | 1.303 |  | bench_ctrl_tomato_20261026 ep5; results/so101_bench_20261019/frames/c01_call* |
| 2026-10-26 | A | 1 | **SUCCESS** | — | reach c8; hold 28-30 c14-20; carried over the tray; released c24 INSIDE the tray at its left end; at rest by c31 | 2 | 28 (19) | 27 | 45 | 80.1 | 1.033 | resolved from frames 2026-10-29: inside the tray (left end, against the inner wall) c26-32; taken out by hand c38 | bench_row3_tomato_20261026 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c01_call* (calls 1-48 overwritten 10-28) |
| 2026-10-26 | A | 2 | **FAIL** | push + close-beside | pushed it toward the base; closed to 4 beside it | 4 | 4 (28) | 36 | 45 | 86.1 | 1.261 |  | bench_row3_tomato_20261026 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c01_call* (calls 1-48 overwritten 10-28) |
| 2026-10-26 | A | 3 | **FAIL** | no-engage | small reach then rest with the gripper open; did not engage | 5 | 41 (17) | 12 | 45 | 87.3 | 1.154 |  | bench_row3_tomato_20261026 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c01_call* (calls 1-48 overwritten 10-28) |
| 2026-10-26 | A | 4 | **FAIL** | cap-hit (idle start) | idle 32 chunks; cap hit mid-approach | 6 | 30 (45) | 8 | 45 | 90.4 | 1.307 |  | bench_row3_tomato_20261026 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c01_call* (calls 1-48 overwritten 10-28) |
| 2026-10-26 | A | 5 | **FAIL** | cap-hit (idle start) | idle 26 chunks; cap hit mid-grasp (closing to 17 on it) | 8 | 14 (41) | 9 | 45 | 90.2 | 1.329 |  | bench_row3_tomato_20261026 ep5; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c01_call* (calls 1-48 overwritten 10-28) |
| 2026-10-26 | B | 1 | **SUCCESS** | — | idle 15; grasp (28-32); carried; lowered INTO the tray; released; at rest | 9 | 27 (42) | 21 | 75 | 144.1 | 1.275 |  | bench_row3b_tomato_20261026 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* (calls 1-348 overwritten 10-28) |
| 2026-10-26 | B | 2 | **VOID** | void | tomato not re-placed (stayed in the tray); arm stayed at rest | 5 | 29 (48) | 6 | 75 | 149.5 | 1.334 |  | bench_row3b_tomato_20261026 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* (calls 1-348 overwritten 10-28) |
| 2026-10-26 | B | 3 | **VOID** | void | same as B2 | 6 | 24 (63) | 7 | 75 | 148.7 | 1.311 |  | bench_row3b_tomato_20261026 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* (calls 1-348 overwritten 10-28) |
| 2026-10-26 | B | 4 | **VOID** | void | same as B2 | 2 | 26 (63) | 4 | 75 | 147.9 | 1.313 |  | bench_row3b_tomato_20261026 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* (calls 1-348 overwritten 10-28) |
| 2026-10-26 | B | 5 | **VOID** | void | same as B2 | 9 | 22 (61) | 12 | 75 | 151.5 | 1.347 |  | bench_row3b_tomato_20261026 ep5; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* (calls 1-348 overwritten 10-28) |
| 2026-10-26 | C | 1 | **VOID** | void | tomato still in the tray at the start; moved late; cap hit | 2 | 15 (72) | 17 | 75 | 142.1 | 1.068 |  | bench_row3c_tomato_20261026 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c03_call* (calls 1-65 overwritten 10-28) |
| 2026-10-26 | C | 2 | **FAIL** | close-short, then close-beside | between the jaws c16-18; closed to 10 at c19 just in front of it; three more approaches (20-37); full close to 1 on air beside it c57-64; retreated open | 7 | 1 (63) | 51 | 75 | 149.5 | 1.298 |  | bench_row3c_tomato_20261026 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c03_call* (calls 1-65 overwritten 10-28) |
| 2026-10-26 | C | 3 | **FAIL** | close-beside, then no-close | jaws beside the tomato c22-31; closed to 12 at c32 with the fruit outside the jaws; then around it (19-33) without a hold; wrist rolled 84 | 7 | 12 (32) | 84 | 75 | 149.3 | 1.34 |  | bench_row3c_tomato_20261026 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c03_call* (calls 1-65 overwritten 10-28) |
| 2026-10-26 | C | 4 | **FAIL** | close-above (partial squeeze), then beside; cap-hit | reach c6-13; jaws closed to 13-19 on its upper side c14-16 (no hold); around it c22-38; close to 9 beside it c46; between the jaws closing to 13 at the cap | 4 | 9 (46) | 59 | 75 | 148.6 | 1.331 |  | bench_row3c_tomato_20261026 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c03_call* (calls 1-65 overwritten 10-28) |
| 2026-10-26 | D | 1 | **FAIL** | close-beside, then no-close | reach c10 with a close to 14 beside it; then the tomato sat between the OPEN jaws (35-54) c20-75; never closed again | 2 | 14 (15) | 52 | 75 | 133.2 | 1.103 |  | bench_row3d_tomato_20261026 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c04_call* (calls 1-75 overwritten 10-28) |
| 2026-10-26 | D | 2 | **SUCCESS** | — | three partial closes (17 at c12, 15 at c21-23, 15 at c46) before a hold (29-31) from ~c51; carried; released INTO the tray by c70 | 3 | 15 (22) | 24 | 75 | 138.1 | 1.186 |  | bench_row3d_tomato_20261026 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c04_call* (calls 1-75 overwritten 10-28) |
| 2026-10-26 | D | 3 | **FAIL** | close-above | between the jaws; closes to 12/19 on its top; no hold | 4 | 3 (14) | 60 | 75 | 141.5 | 1.223 |  | bench_row3d_tomato_20261026 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c04_call* (calls 1-75 overwritten 10-28) |
| 2026-10-26 | D | 4 | **SUCCESS** | — | reach c6-12; HOLD 28-31 c13-28; lifted (table far below in the wrist view c22); released over the tray c30; tomato in the tray c38-75; arm idle in front of it | 3 | 28 (15) | 12 | 75 | 140.8 | 1.222 | resolved from the trace + frames 2026-10-29: gripper 28-31 from c13 to c28 with the tomato between the jaws = a real hold | bench_row3d_tomato_20261026 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c04_call* (calls 1-75 overwritten 10-28) |
| 2026-10-26 | D | 5 | **VOID** | void | wrist camera read failed at chunk 23; client exited | 3 | 38 (10) | 11 | 23 |  |  |  | bench_row3d_tomato_20261026 ep5; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c04_call* (calls 1-75 overwritten 10-28) |
| 2026-10-26 | E | 1 | **SUCCESS** | — | reach c10; hold c20 (20); lift; over the tray c50; released; at rest by c60 | 3 | 10 (19) | 47 | 75 | 130.1 | 0.978 |  | bench_row3e_orange_20261026 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c05_call* |
| 2026-10-26 | E | 2 | **FAIL** | no-close | between the jaws c20-75 (25-48); never held | 3 | 18 (39) | 9 | 75 | 137.2 | 1.178 |  | bench_row3e_orange_20261026 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c05_call* |
| 2026-10-26 | E | 3 | **SUCCESS** | — | reach c10; hold c20 (25); in the tray by c30; hovered open | 4 | 23 (26) | 41 | 75 | 138.4 | 1.179 |  | bench_row3e_orange_20261026 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c05_call* |
| 2026-10-26 | E | 4 | **FAIL** | lift, no delivery | hold c30 (26) and lift; set it back down on the table; never carried to the tray | 8 | 17 (24) | 57 | 75 | 139.0 | 1.181 |  | bench_row3e_orange_20261026 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c05_call* |
| 2026-10-26 | E | 5 | **SUCCESS** | — | reach c10; hold c20 (26); carried left; in the tray by c30; at rest | 3 | 14 (71) | 16 | 75 | 140.4 | 1.179 |  | bench_row3e_orange_20261026 ep5; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c05_call* |
| 2026-10-28 | F | 1 | **FAIL** | wrong-place | reach; swept far right (pan +50; wrist roll 97); shut on air | 4 | 1 (75) | 98 | 75 | 143.8 | 1.275 |  | bench_row3f_orange_20261028 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* |
| 2026-10-28 | F | 2 | **FAIL** | wrong-place (hover at base) | hovered in front of the base; no grasp | 4 | 11 (14) | 13 | 75 | 148.9 | 1.304 |  | bench_row3f_orange_20261028 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* |
| 2026-10-28 | F | 3 | **FAIL** | close-beside | pushed down beside it (grip 4); swept right | 6 | 4 (39) | 36 | 75 | 152.3 | 1.355 |  | bench_row3f_orange_20261028 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* |
| 2026-10-28 | F | 4 | **FAIL** | wrong-place (hover at base) | hovered near the base; rose; orange ended hidden under the arm | 4 | 30 (70) | 11 | 75 | 150.8 | 1.335 |  | bench_row3f_orange_20261028 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* |
| 2026-10-28 | F | 5 | **VOID** | void | aborted at chunk 47 on the operator's word | 3 | 16 (45) | 16 | 47 |  |  |  | bench_row3f_orange_20261028 ep5; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c02_call* |
| 2026-10-28 | G | 1 | **FAIL** | close-beside | stretched far forward and low; came down beside it; gripper open throughout | 2 | 16 (13) | 44 | 75 | 134.4 | 1.002 |  | bench_row3g_orange_20261028 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c04_call* |
| 2026-10-28 | H | 1 | **FAIL** | close-short | reach c14; tomato between the jaws c22-29; closed to 12 at c30 just in front of it; partial closes 16-28 c34-55 beside it; pushed left; wrist rolled 137 | 2 | 12 (30) | 137 | 75 | 138.2 | 1.07 |  | bench_row3h_tomato_20261028 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c07_call* |
| 2026-10-28 | H | 2 | **FAIL** | close-short | between the jaws c20-30; closed to 4 in front of it; swept right | 9 | 3 (42) | 93 | 75 | 150.7 | 1.325 |  | bench_row3h_tomato_20261028 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c07_call* |
| 2026-10-28 | H | 3 | **FAIL** | close-short | between the jaws c20; closed to 3 just in front of it c26; swept away | 4 | 3 (30) | 133 | 75 | 164.5 | 1.372 |  | bench_row3h_tomato_20261028 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c07_call* |
| 2026-10-28 | H | 4 | **SUCCESS** | — | grasp c22 (held ~23); carried; released IN the tray by c40; at rest c40-62 | 5 | 23 (30) | 22 | 75 | 148.3 | 1.354 |  | bench_row3h_tomato_20261028 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c07_call* |
| 2026-10-28 | H | 5 | **FAIL** | close-beside (side squeeze) | jaws pressed against the side of the tomato, open, c14-46; three closes to 23-24 on its side c52-53, c61, c73; no lift | 4 | 23 (75) | 70 | 75 | 144.6 | 1.303 |  | bench_row3h_tomato_20261028 ep5; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c07_call* |
| 2026-10-28 | I | 1 | **FAIL** | close-short, then empty trip to the tray | between the jaws c22-26 (26); closed to 7-8 at c27-29 in front of it; swung empty over the tray c29-33; came back and hovered beside it open; closes to 12 and 9 on air c51-52 | 10 | 7 (29) | 61 | 75 | 143.4 | 1.256 |  | bench_row3i_tomato_20261028 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c08_call* |
| 2026-10-28 | I | 2 | **FAIL** | close-beside | tomato between the jaws c17-19; closed to 10-13 at c20-22 beside it (fruit left of the jaws); closed to 5-8 again c29-32 with the fruit wedged against the arm; wrist roll 129 | 4 | 5 (32) | 129 | 75 | 149.7 | 1.358 |  | bench_row3i_tomato_20261028 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c08_call* |
| 2026-10-28 | I | 3 | **FAIL** | released outside the rim | reach c16; HOLD 28-30 c25-47; lifted and carried to the tray; opened at c49 above the rim and the tomato fell just OUTSIDE it; jaws shut on air (14) c50; re-grasped it (26-28) at the cap | 9 | 14 (51) | 18 | 75 | 147.8 | 1.351 |  | bench_row3i_tomato_20261028 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c08_call* |
| 2026-10-28 | I | 4 | **FAIL** | released outside the rim (then operator moved the fruit c40) | reach c14; HOLD 28 c22-28; carried toward the tray; opened to 54 at c29-30 short of the rim, tomato landed outside at the trays near edge; operator moved it c40; partial close 20-22 on it c53-57; open at the cap | 3 | 14 (54) | 23 | 75 | 150.2 | 1.351 |  | bench_row3i_tomato_20261028 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c08_call* |
| 2026-10-28 | I | 5 | **FAIL** | close-above (partial squeeze) | idle 12; came down on it; jaws closed to 24 on its top c30 and to 16-22 c43-47 (no hold); stayed over it to the cap; never lifted | 4 | 16 (49) | 34 | 75 | 152.4 | 1.355 |  | bench_row3i_tomato_20261028 ep5; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c08_call* |
| 2026-10-29 | J | 1 | **SUCCESS** | — | idle 12 chunks; reach c20; HOLD from c28 (gripper ~30); lifted, carried to the tray, released IN the tray c38-40; back at rest by c50 and held to the cap. First trial with start/end pictures. (A first launch with the orange wording on this tomato was stopped at c40 — void.) | 9 | 24 (37) | 24 | 75 | 181.9 | 1.215 |  | bench_row3j_tomato_20261029 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c10_call* |
| 2026-10-29 | K | 1 | **FAIL** | close-beside (side squeeze), then no-close | reach c20; came down beside the tomato; closed to 16 against its side c40 and pushed it; reopened; hovered beside it with the fruit between the open jaws to the cap | 9 | 9 (54) | 35 | 75 | 188.6 | 1.325 |  | bench_row3k_tomato_20261029 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c11_call* |
| 2026-10-29 | K | 2 | **SUCCESS** | — | reach c10; HOLD by c14 (~29); carried over the tray c26; released IN the tray by c32; back at rest by c40 and held to the cap | 4 | 25 (25) | 25 | 75 | 186.0 | 1.306 |  | bench_row3k_tomato_20261029 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c11_call* |
| 2026-10-29 | K | 3 | **FAIL** | close-beside, push off-view | went right fast c10-16; hovered beside the fruit open; closed to 23 on its side c40; pushed it out of the camera view by c56; stretched fully right over the empty table to the cap | 6 | 8 (61) | 30 | 75 | 191.4 | 1.324 |  | bench_row3k_tomato_20261029 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c11_call* |
| 2026-10-29 | K | 4 | **FAIL** | close-short | found it by c25; between the jaws; closed to 13 just in front of it c40 and pushed it right; followed and closed to 3 beside it at the cap | 7 | 3 (75) | 19 | 75 | 186.8 | 1.329 |  | bench_row3k_tomato_20261029 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c11_call* |
| 2026-10-29 | K | 5 | **FAIL** | released outside the rim | idle 20 chunks; reach; HOLD from ~c38 (27); carried over the tray; released c44 at the tray's right edge — tomato landed OUTSIDE the rim, touching it; arm back at rest by c60 | 7 | 24 (38) | 24 | 75 | 187.3 | 1.29 |  | bench_row3k_tomato_20261029 ep5; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c11_call* |
| 2026-10-29 | L | 1 | **FAIL** | close-above (repeated) | slow start; hovered above the two near oranges from c34; closed to 22-26 ABOVE them five times (c58-64, c100), fruit visible below the closed tips; none of the three moved; 0 of 3 in the tray | 17 | 8 (64) | 28 | 120 | 286.4 | 1.316 |  | bench_row3l_3oranges_20261029 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c12_call* |
| 2026-10-29 | L | 2 | **FAIL** | no-close, over-reach | hovered open above the near-right orange c20-62; then stretched out flat across the table (lift 73, elbow -83) toward the orange beside the tray, jaws beside it at the cap; never closed; 0 of 3 in the tray | 2 | 6 (26) | 54 | 120 | 295.5 | 1.255 |  | bench_row3l_3oranges_20261029 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c12_call* |
| 2026-10-29 | M | 1 | **FAIL** | wrong-place (passed it by) | had the orange between the open jaws c20, moved on past it to the right, closed on air over empty table c40, searched right to the cap | 3 | 4 (55) | 13 | 75 | 182.2 | 1.242 |  | bench_row3m_orange_20261029_part1 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c13_call* |
| 2026-10-29 | M | 2 | **SUCCESS** | — | reach c14; HOLD by c26 (~30); over the tray c30; released IN the tray by c34; at rest by c40 and held to the cap | 6 | 22 (54) | 20 | 75 | 194.4 | 1.348 |  | bench_row3m_orange_20261029_part2 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c14_call* |
| 2026-10-29 | M | 3 | **FAIL** | no-close, over-reach | hovered beside the orange with the jaws open c14-40 (fruit outside the left jaw), then stretched flat across the table past it (lift 66, elbow -80) to the cap | 3 | 22 (67) | 31 | 75 | 187.6 | 1.329 |  | bench_row3m_orange_20261029_part2 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c14_call* |
| 2026-10-29 | M | 4 | **FAIL** | close-beside | came down with the orange off-centre; closed to 32 with the fruit against the outside of the left jaw c40 and pushed it right; followed it open to the cap | 2 | 20 (43) | 44 | 75 | 189.3 | 1.31 |  | bench_row3m_orange_20261029_part2 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c14_call* |
| 2026-10-29 | M | 5 | **FAIL** | no-close, over-reach | hovered above the orange open c20-40 (fruit partly under the left jaw), then stretched flat across the table past it to the cap | 6 | 18 (66) | 36 | 75 | 183.3 | 1.308 |  | bench_row3m_orange_20261029_part2 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c14_call* |
| 2026-10-29 | M | void | **VOID** | void | operator hand on the gripper at c12 while the policy was driving; stopped at c20 and homed. Not a trial. | 4 | 29 (29) | 14 | 36 |  |  |  | bench_row3m_orange_20261029_part1 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c13_call* |
| 2026-10-29 | N | 1 | **SUCCESS** | — | reach and grasp by c31; carried over the tray by c40; released IN the tray c48; back at rest by c60 | 3 | 19 (44) | 19 | 75 | 181.3 | 1.263 |  | bench_row3n_orange_20261029 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c15_call* |
| 2026-10-29 | N | 2 | **SUCCESS** | — | grasped by c16; carried to the tray c20-24; released IN the tray c24; back at rest by c30 | 4 | 13 (19) | 26 | 75 | 189.1 | 1.322 |  | bench_row3n_orange_20261029 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c15_call* |
| 2026-10-29 | N | 3 | **FAIL** | no-close, over-reach | partial closes beside/above the orange; no hold or carry; stretched flat across the table (lift 79, elbow -83) to the cap; orange remained on the table | 3 | 22 (70) | 38 | 75 | 180.2 | 1.304 |  | bench_row3n_orange_20261029_part3 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c17_call* |
| 2026-10-29 | N | 4 | **SUCCESS** | — | grasp held through c36; carried across to the tray; released IN the tray c37; back at rest by c45 | 5 | 17 (28) | 28 | 75 | 184.0 | 1.284 |  | bench_row3n_orange_20261029_part3 ep2; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c17_call* |
| 2026-10-29 | N | 5 | **SUCCESS** | — | grasp held c30-36; carried across to the tray; released IN the tray c37; back at rest by c45 | 12 | 20 (31) | 23 | 75 | 186.3 | 1.297 |  | bench_row3n_orange_20261029_part3 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c17_call* |
| 2026-10-29 | N | void1 | **VOID** | void | orange was not replaced after N2; trial began with the task already complete and is not counted | 38 | 18 (74) | 8 | 75 | 191.5 | 1.37 |  | bench_row3n_orange_20261029 ep3; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c15_call* |
| 2026-10-29 | N | void2 | **VOID** | void | orange was not replaced; at c64 all six motors stopped returning status packets and the client exited; not counted | 49 | 30 (62) | 12 | 64 |  |  |  | bench_row3n_orange_20261029 ep4; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c15_call* |
| 2026-10-29 | N | void3 | **VOID** | void | AK wrist camera disconnected and re-enumerated during the reach; stopped after the second stale wrist frame and released torque; not counted | 2 | 15 (23) | 16 | 25 |  |  |  | bench_row3n_orange_20261029_part2 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c16_call* |
| 2026-10-29 | O | 1 | **SUCCESS** | — | reached right c11-22; grasp held from c23 through c39; carried across the table; released IN the tray c40; back at rest by c44; orange remained in the tray to the cap | 5 | 16 (75) | 26 | 75 | 186.2 | 1.291 |  | bench_row3o_orange_20261029 ep1; results/so101_lora_on_top_20261019/bench_frames_row3_010000/c18_call* |
