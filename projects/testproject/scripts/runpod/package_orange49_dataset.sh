#!/usr/bin/env bash
set -euo pipefail

# Package the 49-episode SO-101 orange dataset for RunPod training.

DATASET_ROOT="${DATASET_ROOT:-/data/lerobot_datasets/so101_orange_49}"
OUT="${OUT:-/data/downloads/so101_orange_49.tar.gz}"

if [ ! -d "$DATASET_ROOT" ]; then
  echo "Dataset not found: $DATASET_ROOT" >&2
  exit 1
fi

if [ ! -f "$DATASET_ROOT/meta/info.json" ]; then
  echo "Dataset metadata not found: $DATASET_ROOT/meta/info.json" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")"

echo "Packaging SO-101 orange49 dataset:"
echo "  source: $DATASET_ROOT"
echo "  output: $OUT"

# Dereference symlinks so the RunPod tarball contains real media files.
tar -h -C "$(dirname "$DATASET_ROOT")" -czf "$OUT" "$(basename "$DATASET_ROOT")"

echo "PACKAGE_ORANGE49_OK"
ls -lh "$OUT"
