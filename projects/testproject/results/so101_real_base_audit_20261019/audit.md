# Audit of dongyoonkim/so101-pi05-base-dataset (R0) — interim, 2026-10-19

Source of truth: meta/{info,sources,episodes,tasks,episodes_stats} + ATTRIBUTION.md pulled to
/mnt/data4tb/huggingface-cache. Per-source table: sources.csv · task table: tasks.csv (this dir).

## From metadata alone (R0.2, R0.3, part of R0.5)
```text
sources            156 (150 Hub + 6 author-recorded); licences 155 apache-2.0, 1 MIT
episodes           13,969; frames 7,272,752; length min 3 / median 450 / max 2,960 frames
                   8 episodes < 30 frames, 11 < 60 (degenerate candidates); 23 with near-zero motion
largest sources    5hadytru/so101_grasp_2 780 · _3 370 · zacapa chess 274 · TzuShian chess 274 ·
                   y1y2y3/so101_test8 250 · zacapa/SO101_AVE_07 226 · observabot die 217 …
                   (top 15 sources = 3,877 ep = 28%)
task strings       406; dominated by cube/block (230 strings), pen/marker/eraser (48),
                   push/button/lever/box/drawer (41), cup/bowl/plate (27); stack 3; sort 0; cloth 0
                   biggest single task: "Place each object in the plastic bin" 1,360 ep (3 sources)
SIMULATION inside  despite the card's "simulation split" step, ≥4 sources are sim by name:
                   CoRL2026-CSI IsaacLab PullCube 100 · EverNorif isaaclab orange 83 ·
                   aaronsu11 so101_fruit_leisaac 57 · omkarmayekar555 sim_… one_orange 64 = 304 ep
ORANGE             8 sources carry an "orange" string, but:
                     real orange FRUIT on a plate: LightwheelAI/so101-place-orange 61 ep (our rig's naming)
                                                   aaronsu11/so101_fruit 200 ep (mixed fruit, some orange)
                     sim orange:                   EverNorif 83 · aaronsu11 leisaac 57 · omkarmayekar 64
                     "orange" = a colour:          zaringleb cube 60 · geekscape cube 50 · nbirukov lego 130
                   → genuinely real orange-fruit demonstrations: ~61 + a share of 200. Few.
survey overlap     inside the merge already: LightwheelAI/so101-place-orange, LightwheelAI/so101-pick-pen.
                   NOT inside: armnet (2,499), hungho77 (455), wsagi real orange (99), lerobot/svla —
                   these remain additive for Stage 3.
```
## Needs the parquet files (R0.4, R0.5 — pending download)
camera occupancy per source (mask columns) · fps per source (timestamp) — the 450 ten-fps episodes ·
exact duplicates (hash of action stream) · near duplicates across sources (length, mean action) ·
degenerate episodes (motion from the stream, not stats) · then R0.6 verdicts and R0.7 video samples.
