#!/usr/bin/env bash
set -euo pipefail

# Small RunPod training smoke test.
# Purpose: prove that the cleaned dataset, Pi05 dependency stack, and checkpoint
# saving path work before spending money on a long GPU run.

LERO_ROOT="${LERO_ROOT:-/workspace/lerobot}"
DATASET_ROOT="${DATASET_ROOT:-/workspace/lerobot_datasets/so101_pick_orange_move_action_start_view}"
DATASET_REPO_ID="${DATASET_REPO_ID:-local/so101_pick_orange_move_action_start_view}"
BASE_POLICY="${BASE_POLICY:-zz4321/so101_pi05}"
OUTPUT_DIR="${OUTPUT_DIR:-/workspace/outputs/pi05_so101_orange_move_action_start_view_smoke}"
JOB_NAME="${JOB_NAME:-pi05_so101_orange_move_action_start_view_smoke}"
POLICY_REPO_ID="${POLICY_REPO_ID:-local/pi05_so101_orange_move_action_start_view_smoke}"
STEPS="${STEPS:-200}"
BATCH_SIZE="${BATCH_SIZE:-1}"

if [ ! -d "$LERO_ROOT" ]; then
  echo "LeRobot directory not found: $LERO_ROOT" >&2
  exit 1
fi

if [ ! -d "$DATASET_ROOT" ]; then
  echo "Dataset directory not found: $DATASET_ROOT" >&2
  echo "Expected cleaned dataset extracted at this path." >&2
  exit 1
fi

if [ -n "${CONDA_PREFIX:-}" ]; then
  export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
  export LD_PRELOAD="$CONDA_PREFIX/lib/libstdc++.so.6${LD_PRELOAD:+:$LD_PRELOAD}"
fi

cd "$LERO_ROOT"

echo "PI05 CLEANED DATASET SMOKE TRAIN"
echo "  base policy:  $BASE_POLICY"
echo "  dataset root: $DATASET_ROOT"
echo "  output dir:   $OUTPUT_DIR"
echo "  steps:        $STEPS"
echo "  batch size:   $BATCH_SIZE"

lerobot-train \
  --dataset.repo_id="$DATASET_REPO_ID" \
  --dataset.root="$DATASET_ROOT" \
  --policy.type=pi05 \
  --policy.pretrained_path="$BASE_POLICY" \
  --output_dir="$OUTPUT_DIR" \
  --job_name="$JOB_NAME" \
  --policy.repo_id="$POLICY_REPO_ID" \
  --policy.push_to_hub=false \
  --wandb.enable=false \
  --policy.device=cuda \
  --policy.dtype=bfloat16 \
  --policy.gradient_checkpointing=true \
  --policy.compile_model=false \
  --policy.train_expert_only=true \
  --steps="$STEPS" \
  --batch_size="$BATCH_SIZE"

echo "SMOKE_TRAIN_OK"
find "$OUTPUT_DIR/checkpoints" -maxdepth 3 -type d | sort | tail -20 || true
