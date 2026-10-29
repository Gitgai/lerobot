# Bench frames, one folder per trial

Hard links into the raw server dump (see scripts/sort_bench_frames.py). Names: `<date>_<day>_row<X>_<model>_<fruit>/trial<N>_<RESULT>/front_chunk<NNN>.jpg` (overhead camera) and `wrist_chunk<NNN>.jpg`. Chunk NNN = the NNN-th policy call of that trial (one call = 20 arm steps at 30 Hz ≈ 0.7 s of motion + the round trip).

| folder | trials | note |
|---|---|---|
| 2026-10-26_sun_rowctrl_base_tomato | 5 |  |
| 2026-10-26_sun_rowA_ft3_tomato | 5 | trial 1 frames lost |
| 2026-10-26_sun_rowB_ft3_tomato | 5 | trial 1 frames lost; trial 2 frames lost; trial 3 frames lost; trial 4 frames lost |
| 2026-10-26_sun_rowC_ft3_tomato | 4 |  |
| 2026-10-26_sun_rowD_ft3_tomato | 5 | trial 1 frames lost |
| 2026-10-26_sun_rowE_ft3_orange | 5 |  |
| 2026-10-28_tue_rowF_ft3_orange | 5 |  |
| 2026-10-28_tue_rowG_ft3_orange | 1 |  |
| 2026-10-28_tue_rowH_ft3_tomato | 5 |  |
| 2026-10-28_tue_rowI_ft3_tomato | 5 |  |
