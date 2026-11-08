# Orange grasp corrective collection

This directory holds the collection manifest and review artifacts for the LeRobot dataset stored at
`~/orange_grasp_corrective_ft4_20261108`.

Target: 30 accepted episodes, beginning with a five-episode quality-gated pilot. See
[`../../../docs/orange_grasp_corrective_collection_20261108.md`](../../../docs/orange_grasp_corrective_collection_20261108.md).

The no-motion hardware/camera preflight passed on 2026-11-08. The saved front image records the scene before the
first episode. Episode 0 was rejected because the orange was never released and remained held against the tray rim
at the cap. Episodes 1 and 2 were accepted as the first two pilot demonstrations. Contact sheets and final-frame
sheets are retained locally for review. `episodes.csv` is append-only: rejected attempts receive a row and are not
deleted.
