#!/usr/bin/env bash
set -euo pipefail

# Package the Option A dataset for RunPod training:
# original SO-101 orange49 + approved grasp/pick/move focus windows once.

DATASET_ROOT="${DATASET_ROOT:-/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus}"
OUT="${OUT:-/data/downloads/so101_orange_49_plus_grasp_pick_move_focus.tar.gz}"

if [ ! -d "$DATASET_ROOT" ]; then
  echo "Dataset not found: $DATASET_ROOT" >&2
  exit 1
fi

if [ ! -f "$DATASET_ROOT/meta/info.json" ]; then
  echo "Dataset metadata not found: $DATASET_ROOT/meta/info.json" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")"

echo "Packaging SO-101 orange49 plus grasp-focus dataset:"
echo "  source: $DATASET_ROOT"
echo "  output: $OUT"

# Dereference symlinks so the RunPod tarball contains real MP4 files.
tar -h -C "$(dirname "$DATASET_ROOT")" -czf "$OUT" "$(basename "$DATASET_ROOT")"

echo "PACKAGE_ORANGE49_PLUS_GRASP_FOCUS_OK"
ls -lh "$OUT"
