#!/usr/bin/env bash
set -euo pipefail

# Upload the Option A dataset and Pi05 grasp-focus training scripts to RunPod.
#
# Usage:
#   RUNPOD_HOST=213.192.x.x RUNPOD_PORT=40113 \
#     SSH_KEY=$HOME/.ssh/runpod_ed25519 \
#     ./scripts/runpod/upload_orange49_plus_grasp_focus_to_runpod.sh

RUNPOD_HOST="${RUNPOD_HOST:?Set RUNPOD_HOST to the RunPod direct TCP SSH host}"
RUNPOD_PORT="${RUNPOD_PORT:?Set RUNPOD_PORT to the RunPod direct TCP SSH port}"
RUNPOD_USER="${RUNPOD_USER:-root}"
if [ -z "${SSH_KEY:-}" ]; then
  if [ -f "$HOME/.ssh/runpod_ed25519" ]; then
    SSH_KEY="$HOME/.ssh/runpod_ed25519"
  else
    SSH_KEY="$HOME/.ssh/id_ed25519"
  fi
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATASET_TAR="${DATASET_TAR:-/data/downloads/so101_orange_49_plus_grasp_pick_move_focus.tar.gz}"
REMOTE_PROJECT="${REMOTE_PROJECT:-/workspace/testproject}"
REMOTE_DATASETS="${REMOTE_DATASETS:-/workspace/lerobot_datasets}"
REMOTE_DATASET_ROOT="$REMOTE_DATASETS/so101_orange_49_plus_grasp_pick_move_focus"
REMOTE_TAR="/workspace/so101_orange_49_plus_grasp_pick_move_focus.tar.gz"

if [ ! -f "$DATASET_TAR" ]; then
  echo "Dataset tarball not found: $DATASET_TAR" >&2
  echo "Create it first with: ./scripts/runpod/package_orange49_plus_grasp_focus_dataset.sh" >&2
  exit 1
fi

SSH_OPTS=(-i "$SSH_KEY" -p "$RUNPOD_PORT" -o StrictHostKeyChecking=accept-new)
REMOTE="$RUNPOD_USER@$RUNPOD_HOST"

echo "RUNPOD ORANGE49 PLUS GRASP-FOCUS UPLOAD"
echo "  remote:       $REMOTE:$RUNPOD_PORT"
echo "  dataset tar:  $DATASET_TAR"
echo "  remote proj:  $REMOTE_PROJECT"
echo "  remote data:  $REMOTE_DATASET_ROOT"

ssh "${SSH_OPTS[@]}" "$REMOTE" "mkdir -p '$REMOTE_PROJECT/scripts/runpod' '$REMOTE_DATASETS' /workspace/outputs"

scp -i "$SSH_KEY" -P "$RUNPOD_PORT" "$DATASET_TAR" "$REMOTE:$REMOTE_TAR"
scp -i "$SSH_KEY" -P "$RUNPOD_PORT" \
  "$PROJECT_ROOT"/scripts/runpod/pi05_orange49_plus_grasp_focus_*_train.sh \
  "$REMOTE:$REMOTE_PROJECT/scripts/runpod/"

ssh "${SSH_OPTS[@]}" "$REMOTE" "
  set -euo pipefail
  rm -rf '$REMOTE_DATASET_ROOT'
  mkdir -p '$REMOTE_DATASETS'
  tar --no-same-owner -xzf '$REMOTE_TAR' -C '$REMOTE_DATASETS'
  chmod +x '$REMOTE_PROJECT'/scripts/runpod/*.sh
  test -f '$REMOTE_DATASET_ROOT/meta/info.json'
  echo 'UPLOAD_ORANGE49_PLUS_GRASP_FOCUS_AND_EXTRACT_OK'
  du -sh '$REMOTE_DATASET_ROOT'
  find '$REMOTE_PROJECT/scripts/runpod' -maxdepth 1 -type f -print | sort
"
