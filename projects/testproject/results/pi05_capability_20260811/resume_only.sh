#!/usr/bin/env bash
# Phase 2 only — the checkpoint at 000060 already exists, so re-run just the gate.
set -u
P=/home/kiran/sim/pi05-fullft-probe
OUT=/home/kiran/lerobot_assets/probes/pi05_rung4_gate
export LEROBOT_CPU_OFFLOAD_ADAM=1
echo "=== RESUME (the gate) ==="
stdbuf -oL "$P/.venv312/bin/lerobot-train" \
  --config_path="$OUT/checkpoints/last/pretrained_model/train_config.json" \
  --resume=true > "$OUT""_tel/resume.txt" 2>&1
echo "RESUME EXIT=$?"
