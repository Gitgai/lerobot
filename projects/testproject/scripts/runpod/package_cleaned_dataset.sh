#!/usr/bin/env bash
set -euo pipefail

DATASET_ROOT="${DATASET_ROOT:-/data/lerobot_datasets/so101_pick_orange_move_action_start_view}"
OUT="${OUT:-/data/downloads/so101_pick_orange_move_action_start_view.tar.gz}"

if [ ! -d "$DATASET_ROOT" ]; then
  echo "Dataset not found: $DATASET_ROOT" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")"

echo "Packaging cleaned dataset:"
echo "  source: $DATASET_ROOT"
echo "  output: $OUT"

# The action-start dataset reuses the original videos through symlinks.
# Dereference them so the RunPod tarball contains real video files.
tar -h -C "$(dirname "$DATASET_ROOT")" -czf "$OUT" "$(basename "$DATASET_ROOT")"

echo "PACKAGE_OK"
ls -lh "$OUT"
