# Bench frames, one folder per trial

Hard links into the raw server dump (see scripts/sort_bench_frames.py). Names: `<date>_<day>_row<X>_<model>_<fruit>/trial<N>_<RESULT>/front_chunk<NNN>.jpg` (overhead camera) and `wrist_chunk<NNN>.jpg`. Chunk NNN = the NNN-th policy call of that trial (one call = 20 arm steps at 30 Hz ≈ 0.7 s of motion + the round trip).

| folder | trials | note |
|---|---|---|
| 2026-10-19_20_rowbase_base_citrus_onion_orange | 16 |  |
| 2026-10-29_wed_rowM_ft3_orange | 6 |  |
| 2026-10-29_wed_rowN_ft3_orange | 8 |  |
| 2026-10-29_wed_rowO_ft3_orange | 6 |  |
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
| 2026-10-29_wed_rowJ_ft3_tomato | 1 |  |
| 2026-10-29_wed_rowK_ft3_tomato | 5 |  |
| 2026-10-29_wed_rowL_ft3_3 | 2 |  |

Trials run from 2026-10-29 on also have `front_start.jpg` (the scene as the trial begins), `front_end_after_last_chunk.jpg` (the pose the policy left the arm in) and `front_end_at_rest.jpg` (back at rest), plus the same for the wrist camera. Earlier trials have no such frames (the client never captured them) and their `chunk001` frame is stale — use chunk002 as the true start frame (bench_runs.md 2026-10-29).
