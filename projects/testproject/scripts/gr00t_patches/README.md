# Patches to the vendored Isaac-GR00T-n16 tree

These files live at `~/sim/Isaac-GR00T-n16/` and are NOT part of this repo's
package. Copies are kept here so the changes survive a reinstall of GR00T -
otherwise they are silently lost and the reasons with them.

## launch_finetune.py

Two local changes, both with `.pre-*` backups beside the originals:

1. **Env-gated optimizer** (2026-08-17). `N16_OPTIM=adamw_bnb_8bit` selects
   8-bit Adam. Stock fp32 AdamW needs ~29.8 GB on a 31.3 GB card and OOMs at
   optimizer-state creation regardless of batch size. Default unchanged.

2. **Automatic LINEAGE.json** (2026-08-26). Writes parent / dataset / steps /
   tune-flags / optimizer / commit into the output directory BEFORE training
   starts, so the record survives a crash.

   Why: on 2026-08-26 the operator asked which model that day's fine-tune had
   started from, and nothing recorded it - not the config, not
   training_args.bin, not the logs. It had to be established by comparing
   action-head weights against three candidates (0.0016 to the true parent vs
   0.0032/0.0034 to the others). A checkpoint should carry its own history.

   Verified 2026-08-26 with a 20-step run: file written, parent correctly
   resolved through the `orange_pick_baseline_v1` symlink to
   `n16_real79_side/checkpoint-10000`.
