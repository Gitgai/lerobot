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

## The author's own pipeline records (github jinnymo/so101-pi05-base, pipeline/artifacts/, copied to author_artifacts/)
```text
dedup (23_dedup_result)   210 candidate sets → 182 kept, 28 dropped as identical / strict-subset /
                          "leakage" (train+val splits of one recording). Examples dropped: six
                          k1000dai conveyor variants, tshiamor block variants, SGPatil table-cleanup-train,
                          zaringleb cube "with_corrective_actions" (subset of pick_single_cube).
per-episode drops (25)    151 episodes in 16 sources, almost all "video duration != action duration"
                          (101 of them in one 10-fps CoRL2026 source; 13 in EverNorif orange sim); 4 empty.
manifest (27)             211 → 181 kept (then 156 after the licence filter); 8 sources had task strings
                          normalised; tiers: tier1 46 · tier2 115 · tier2b 5 · tier3 39 · 6 author sets.
camera map (21)           211 sources; 68 have a NON-wrist camera in a wrist slot (card says 42 of the
                          final 156); 2 ambiguous; 6 streams dropped.
```
Reading so far: the author did real work — fingerprint dedup across authors, length-mismatch drops,
licence filter — and documented it. What the card UNDER-states: simulation data is inside (≥4 sources,
304 ep) and real orange-fruit demonstrations are ~61 (+ part of 200 mixed-fruit). Our own checks still
to run on the parquet: exact duplicate EPISODES across sources (the author deduped at dataset level),
fps/occupancy from the streams, degenerate episodes.

## From the parquet sample, 3 episodes per source (R0.4, 2026-10-19)
```text
fps per source     151 sources at 30 fps · 5 sources at 10 fps = 450 episodes (the card's number confirmed):
                   CoRL2026-CSI IsaacLab PullCube 100 · CoRL2026-CSI teleop stack RGB block 150 ·
                   anvilbot-patrickhhh 3cams 50 / front_wrist 50 / relocate_cube 100
                   → 2 of the 5 are the CoRL2026 sim/teleop sets; all 5 were EXCLUDED from the author's training run
real cameras       sources: 1 camera 17 · 2 cameras 125 · 3 cameras 14
                   episodes: 1 camera 1,314 (9.4%) · 2 cameras 11,504 (82%) · 3 cameras 1,151
                   slot use: base_0_rgb real in 153 sources · left_wrist_0_rgb in 142 · right_wrist_0_rgb in 14
                   → the dominant layout is exactly OURS (external + wrist, 2 slots); 1,314 single-camera
                     episodes trained with one slot black
orange sources     all 30 fps; 7 of 8 are base+left_wrist (our layout); nbirukov lego has 3 cameras
```

## Visual pass (R0.7, 2026-10-19): 2 episodes × 22 sources (20 largest + all orange) — montages/ (54 PNG, not in git)
Top row of each sheet = base_0_rgb slot, bottom = left_wrist_0_rgb slot, 6 frames across the episode.
```text
SLOTS SWAPPED (wrist view sits in base_0_rgb, external view in the wrist slot):
  5hadytru/so101_grasp_1, _2, _3     1,360 ep   uploader's "front" IS the wrist camera, "overhead" the external;
                                                the author's keyword rule mapped front→base, overhead→wrist
  y1y2y3/so101_test8                   250 ep   "fixed"/"handeye" keys, content is the other way round
  sabinMlminator/so101_pickplace_cubes 200 ep   same symptom
  total                              1,810 ep = 13.0% of the release, 3 of the 15 largest sources
TWO EXTERNAL CAMERAS, NO WRIST VIEW (the card's "non-wrist in a wrist slot" case, seen):
  TzuShian/so101_white_chess           274 ep   overhead green-screen + table-level side view
CORRECT (external top, wrist bottom): LightwheelAI orange · aaronsu11 fruit · zacapa chess + AVE_07 ·
  observabot die · k1000dai conveyor · nbirukov lego · wantobcm box2bowl · SurajChess marker · aiden-li
  picktape + drawers · CoRL2026 teleop stack · hackathon sushi · zaringleb ×2 · geekscape · self/stack_cube
SIM (rendered, obvious): EverNorif orange · aaronsu11 leisaac · omkarmayekar orange — also correct slots
QUALITY NOTES: 5hadytru wrist stream is very dark (black table, underexposed) and partly occluded by a
  person's hand in frame 1 of ep 3196; y1y2y3 and zacapa AVE_07 are dim; sushi set shows a hand in frame.
```
Why it matters: the author's slot semantics ("base = external, left_wrist = wrist") is what the policy
learned on 87% of the data; 13% taught it the opposite pairing. For a policy that reads both views this
is label noise on the camera channel, not fatal, but it is the single largest defect found and it is
invisible in the metadata — only the pictures show it. Fix for a retrain: swap the two slots for these
five sources (a manifest edit, no re-encoding). The 1,314 single-camera episodes and the 274 two-external
episodes are weaker signal, not wrong.

## R0.5 + R4 — duplicates, degenerate episodes, and the cleaned manifest (2026-10-20 02:16Z, all 13,969 parquet files)
```text
exact duplicate episodes   1 (inside one source); cross-source near-duplicates 0  → the author's dataset-level
                           dedup holds at the episode level; the "14k" is real, not repeats
degenerate                 11 shorter than 60 frames, 23 nearly static (10 overlap), 0 NaN
manifest_clean.csv         KEEP 13,292 of 13,969 = 95.2%  (real, 30 fps, not duplicate/degenerate)
  dropped                  sim 304 · 10-fps 350 (the other 100 ten-fps are sim) · static 23 · short 11 · dup 1
  kept but flagged         slot_swap_fix 1,809 (apply the base↔wrist swap) · dark_wrist 1,835 · hand_in_frame 920
                           (whole sources flagged from 2 sampled episodes — a flag, not a drop) · two_external 274
  kept by real cameras     1 cam 1,311 · 2 cams 10,880 · 3 cams 1,101
  real orange-fruit kept   96 (LightwheelAI 61 + aaronsu11 fruit, orange tasks, 35)
  sources kept             148 of 156
```
## Verdict
The corpus is sound as data: no hidden repetition, almost no junk, 95% usable at 30 fps on real arms, and
82% in exactly our two-camera layout. Its two real weaknesses are (1) 13% of episodes with the camera slots
swapped — a labelling error of the merge, fixable by a manifest swap, and the one thing the pictures caught
that no metadata could — and (2) task coverage: cube/block-heavy, 96 real orange-fruit episodes in total.
For our purpose it is a legitimate real-SO-101 base to fine-tune FROM, not a source of orange demonstrations;
our own 89 + 99 real orange episodes remain the task data. The checkpoint trained on it (13,519 of these
episodes) carries the slot noise; whether that matters is what R2 (sim, closed loop) and the replay ladder
(R3a G2, in-corpus vs held-out vs ours, as-shipped vs swapped) will measure.
