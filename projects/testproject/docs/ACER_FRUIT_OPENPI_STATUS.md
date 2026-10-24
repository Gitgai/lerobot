# Acer fruit OpenPI track — current navigation

Updated 24 October 2026 for repository consolidation. This is not a fresh hardware check or the status of all AI90 experiments.

## Code

Repository candidate: [fruit OpenPI integration](../scripts/inference/fruit_openpi/README.md). Nine source files migrated with recorded SHA-256 provenance. Fourteen pure tests pass; CLI help, network-worker import and syntax checks pass without opening devices or connections. Active launch locations have not switched. Full client/server and physical execution from the new location remain unverified.

## Last established outcome

The fruit LoRA-plus-vision 4k checkpoint was the provisional deployment candidate after the 5k-update training run. The October 22 orange trial used RTC off and network JPEG off. It did not demonstrate placement. A roughly 56-second camera/control pause correlated with NVMe read/write timeouts and a controller reset; an earlier reset was found on October 8. Last trial cleanup verified all six motor torques off, but this document is not a current motor-state readback.

The stale-plan timing check was added and tested without movement. It cannot release motors while the whole host is stalled. Physical retries remain paused pending the separate host-storage investigation. Migration is not a fix for that issue or a reason to retrain.

## Documentation snapshots and original evidence

Eleven selected [training, trial and recovery documents](fruit_openpi_history/README.md) are now preserved inside this repository. They are dated snapshots; raw data and some linked reports remain external. Later storage/backup activity appears in the copied recovery documents and has not been independently checked by this migration task.

On Acer, base path `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/`:

| Subject                                 | Relative location under that base                                         |
| --------------------------------------- | ------------------------------------------------------------------------- |
| Training plan and history               | `PI05_ORANGE_TOMATO_LORA_PLAN_20261017.md`                                |
| Training/data/checkpoint reviews        | `fruit_review_20261017/`                                                  |
| Last physical trial review              | `fruit_openpi_client/orange_trial_01_20261022/REVIEW.md`                  |
| Storage investigation and backup limits | `fruit_openpi_client/storage_investigation_20261022/RECOVERY_PROGRESS.md` |
| Original client and operational history | `fruit_openpi_client/README.md`                                           |

The existing directories are retained to preserve evidence and relative links. They are not all committed or backed up merely because this index is in the repository. Large frames/videos/checkpoints must not be bulk-added to Git.

## Next migration steps

Audit remaining document/code dependencies and duplicates; migrate selected documentation with valid links and provenance; review the precise Git diff and exclusions; perform applicable pre-commit checks before committing/pushing. Keep existing user changes separate. Follow the [consolidation plan](REPOSITORY_CONSOLIDATION_PLAN_20261024.md).
