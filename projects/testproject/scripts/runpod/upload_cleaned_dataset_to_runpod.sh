#!/usr/bin/env bash
set -euo pipefail

# Upload the cleaned SO-101 orange-move dataset and RunPod training scripts.
#
# Usage:
#   RUNPOD_HOST=194.68.xxx.xxx RUNPOD_PORT=22147 ./scripts/runpod/upload_cleaned_dataset_to_runpod.sh

RUNPOD_HOST="${RUNPOD_HOST:?Set RUNPOD_HOST to the RunPod direct TCP SSH host}"
RUNPOD_PORT="${RUNPOD_PORT:?Set RUNPOD_PORT to the RunPod direct TCP SSH port}"
RUNPOD_USER="${RUNPOD_USER:-root}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATASET_TAR="${DATASET_TAR:-/data/downloads/so101_pick_orange_move_action_start_view.tar.gz}"
REMOTE_PROJECT="${REMOTE_PROJECT:-/workspace/testproject}"
REMOTE_DATASETS="${REMOTE_DATASETS:-/workspace/lerobot_datasets}"
REMOTE_DATASET_ROOT="$REMOTE_DATASETS/so101_pick_orange_move_action_start_view"

if [ ! -f "$DATASET_TAR" ]; then
  echo "Dataset tarball not found: $DATASET_TAR" >&2
  echo "Create it first with: ./scripts/runpod/package_cleaned_dataset.sh" >&2
  exit 1
fi

SSH_OPTS=(-i "$SSH_KEY" -p "$RUNPOD_PORT" -o StrictHostKeyChecking=accept-new)
REMOTE="$RUNPOD_USER@$RUNPOD_HOST"

echo "RUNPOD CLEANED DATASET UPLOAD"
echo "  remote:       $REMOTE:$RUNPOD_PORT"
echo "  dataset tar:  $DATASET_TAR"
echo "  remote proj:  $REMOTE_PROJECT"
echo "  remote data:  $REMOTE_DATASET_ROOT"

ssh "${SSH_OPTS[@]}" "$REMOTE" "mkdir -p '$REMOTE_PROJECT/scripts/runpod' '$REMOTE_DATASETS' /workspace/outputs"

scp -i "$SSH_KEY" -P "$RUNPOD_PORT" "$DATASET_TAR" "$REMOTE:/workspace/so101_pick_orange_move_action_start_view.tar.gz"
scp -i "$SSH_KEY" -P "$RUNPOD_PORT" "$PROJECT_ROOT"/scripts/runpod/pi05_cleaned_*_train.sh "$REMOTE:$REMOTE_PROJECT/scripts/runpod/"

ssh "${SSH_OPTS[@]}" "$REMOTE" "
  set -euo pipefail
  rm -rf '$REMOTE_DATASET_ROOT'
  mkdir -p '$REMOTE_DATASETS'
  tar --no-same-owner -xzf /workspace/so101_pick_orange_move_action_start_view.tar.gz -C '$REMOTE_DATASETS'
  chmod +x '$REMOTE_PROJECT'/scripts/runpod/*.sh
  echo 'UPLOAD_AND_EXTRACT_OK'
  du -sh '$REMOTE_DATASET_ROOT'
  find '$REMOTE_PROJECT/scripts/runpod' -maxdepth 1 -type f -print
"
