# Orange grasp corrective collection

This directory holds the collection manifest and review artifacts for the LeRobot dataset stored at
`~/orange_grasp_corrective_ft4_20261108`.

Target: 30 accepted episodes, beginning with a five-episode quality-gated pilot. See
[`../../../docs/orange_grasp_corrective_collection_20261108.md`](../../../docs/orange_grasp_corrective_collection_20261108.md).

The no-motion hardware/camera preflight passed on 2026-11-08. The saved front image records the scene before the
first episode. Episode 0 was rejected because the orange was never released and remained held against the tray rim
at the cap. Episodes 1-5 passed the quality pilot. Episodes 6-10 were then recorded back-to-back and also passed all
visual checks. The collection currently has 10 accepted direct centred-grasp demonstrations and one rejected
recording. Episodes 11-15 completed the planned direct-grasp quota, giving 15 accepted direct demonstrations total.
Contact sheets and final-frame sheets are retained for review. `dataset_manifest.json` records
accepted/rejected indices and file hashes. `episodes.csv` is append-only: rejected attempts receive a row and are
not deleted.
