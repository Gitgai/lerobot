#!/usr/bin/env bash
set -euo pipefail

# One-episode Pi05 overfit diagnostic.
# Goal: verify that the training/inference path can memorize one clean
# successful SO-101 orange episode before spending time on broader training.

LERO_ROOT="${LERO_ROOT:-/workspace/lerobot}"
LERO_ENV="${LERO_ENV:-/workspace/miniforge3/envs/lerobot-py312}"
DATASET_ROOT="${DATASET_ROOT:-/workspace/lerobot_datasets/so101_pick_orange_episode29_overfit}"
DATASET_REPO_ID="${DATASET_REPO_ID:-local/so101_pick_orange_episode29_overfit}"
BASE_POLICY="${BASE_POLICY:-zz4321/so101_pi05}"
OUTPUT_DIR="${OUTPUT_DIR:-/workspace/outputs/pi05_so101_episode29_overfit}"
JOB_NAME="${JOB_NAME:-pi05_so101_episode29_overfit}"
POLICY_REPO_ID="${POLICY_REPO_ID:-local/pi05_so101_episode29_overfit}"
STEPS="${STEPS:-1000}"
BATCH_SIZE="${BATCH_SIZE:-1}"
SAVE_FREQ="${SAVE_FREQ:-500}"

if [ ! -d "$LERO_ROOT" ]; then
  echo "LeRobot directory not found: $LERO_ROOT" >&2
  exit 1
fi

if [ ! -d "$DATASET_ROOT" ]; then
  echo "Dataset directory not found: $DATASET_ROOT" >&2
  exit 1
fi

if [ -d "$LERO_ENV" ]; then
  export PATH="$LERO_ENV/bin:$PATH"
  export CONDA_PREFIX="$LERO_ENV"
fi

if [ -n "${CONDA_PREFIX:-}" ]; then
  export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
  export LD_PRELOAD="$CONDA_PREFIX/lib/libstdc++.so.6${LD_PRELOAD:+:$LD_PRELOAD}"
fi

export HF_HOME="${HF_HOME:-/workspace/hf_cache}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-/workspace/hf_cache/datasets}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/workspace/hf_cache/transformers}"

cd "$LERO_ROOT"

echo "PI05 EPISODE 29 ONE-EPISODE OVERFIT"
echo "  base policy:  $BASE_POLICY"
echo "  dataset root: $DATASET_ROOT"
echo "  output dir:   $OUTPUT_DIR"
echo "  steps:        $STEPS"
echo "  batch size:   $BATCH_SIZE"
echo "  save freq:    $SAVE_FREQ"

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
  --batch_size="$BATCH_SIZE" \
  --save_freq="$SAVE_FREQ"

echo "EPISODE29_OVERFIT_TRAIN_OK"
find "$OUTPUT_DIR/checkpoints" -maxdepth 3 -type d | sort | tail -30 || true
