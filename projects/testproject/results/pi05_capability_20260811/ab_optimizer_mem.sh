#!/usr/bin/env bash
# A/B: identical config, ONLY the optimizer differs. 3 steps, no checkpoint.
# Answers: is the rung-4 OOM caused by the offload optimizer, or by this config?
set -u
P=/home/kiran/sim/pi05-fullft-probe
for MODE in 0 1; do
  if [ "$MODE" = "0" ]; then NAME=adamw_8bit; else NAME=adamw_cpu_offload; fi
  OUT=/home/kiran/lerobot_assets/probes/ab_$NAME
  LOG=/home/kiran/lerobot_assets/probes/ab_$NAME.txt
  rm -rf "$OUT"
  echo "########## $NAME ##########"
  LEROBOT_CPU_OFFLOAD_ADAM=$MODE stdbuf -oL "$P/.venv312/bin/lerobot-train" \
    --policy.path=lerobot/pi05_base --policy.device=cuda --policy.push_to_hub=false \
    --dataset.repo_id=lerobot/libero_spatial_image \
    '--rename_map={"observation.images.image":"observation.images.base_0_rgb","observation.images.wrist_image":"observation.images.left_wrist_0_rgb"}' \
    --batch_size=8 --steps=3 --save_checkpoint=false \
    --output_dir="$OUT" --job_name=ab_$NAME --wandb.enable=false \
    > "$LOG" 2>&1
  echo "  EXIT=$?"
  grep -oE "step:[0-9]+ .*" "$LOG" | tail -2
  grep -o "Of the allocated memory [0-9.]* GiB" "$LOG" | tail -1
  grep -o "Tried to allocate [0-9.]* MiB" "$LOG" | tail -1
  echo
  sleep 12
done
echo "########## A/B DONE ##########"
