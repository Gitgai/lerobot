#!/usr/bin/env bash
set -euo pipefail

# First real expert-only direct fine-tune from lerobot/pi05_base on the
# 49-episode SO-101 orange dataset.

LERO_ROOT="${LERO_ROOT:-/workspace/lerobot}"
DATASET_ROOT="${DATASET_ROOT:-/workspace/lerobot_datasets/so101_orange_49}"
DATASET_REPO_ID="${DATASET_REPO_ID:-local/so101_orange_49}"
BASE_POLICY="${BASE_POLICY:-lerobot/pi05_base}"
OUTPUT_DIR="${OUTPUT_DIR:-/workspace/outputs/pi05_base_to_orange49_expert}"
JOB_NAME="${JOB_NAME:-pi05_base_to_orange49_expert}"
POLICY_REPO_ID="${POLICY_REPO_ID:-local/pi05_base_to_orange49_expert}"
STEPS="${STEPS:-5000}"
BATCH_SIZE="${BATCH_SIZE:-1}"
SAVE_FREQ="${SAVE_FREQ:-1000}"
VIDEO_BACKEND="${VIDEO_BACKEND:-pyav}"

if [ ! -d "$LERO_ROOT" ]; then
  echo "LeRobot directory not found: $LERO_ROOT" >&2
  exit 1
fi

if [ ! -f "$DATASET_ROOT/meta/info.json" ]; then
  echo "Dataset metadata not found: $DATASET_ROOT/meta/info.json" >&2
  exit 1
fi

if [ -n "${CONDA_PREFIX:-}" ]; then
  export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
  export LD_PRELOAD="$CONDA_PREFIX/lib/libstdc++.so.6${LD_PRELOAD:+:$LD_PRELOAD}"
fi

export HF_HOME="${HF_HOME:-/workspace/hf_cache}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-/workspace/hf_cache/datasets}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/workspace/hf_cache/transformers}"

cd "$LERO_ROOT"

echo "PI05 BASE -> ORANGE49 EXPERT-ONLY TRAIN"
echo "  base policy:  $BASE_POLICY"
echo "  dataset root: $DATASET_ROOT"
echo "  output dir:   $OUTPUT_DIR"
echo "  steps:        $STEPS"
echo "  batch size:   $BATCH_SIZE"
echo "  save freq:    $SAVE_FREQ"
echo "  video backend: $VIDEO_BACKEND"

lerobot-train \
  --dataset.repo_id="$DATASET_REPO_ID" \
  --dataset.root="$DATASET_ROOT" \
  --dataset.video_backend="$VIDEO_BACKEND" \
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
  --batch_size="$BATCH_SIZE" \
  --save_freq="$SAVE_FREQ"

echo "PI05_BASE_ORANGE49_EXPERT_TRAIN_OK"
find "$OUTPUT_DIR/checkpoints" -maxdepth 3 -type d | sort | tail -30 || true
