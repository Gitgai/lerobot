#!/usr/bin/env bash
# STEP 2: largest batch that fits. Stops at the first OOM (plan §STEP 2).
S=/tmp/claude-1000/-home-kiran-projects-git/4a4f129c-25d6-4f4f-ba05-204fe5318fad/scratchpad
cd /home/kiran/sim/pi05-fullft-probe
for BS in 16 32; do
  OUT=/home/kiran/lerobot_assets/probes/pi05_sweep_bs${BS}_$(date +%H%M%S)
  GPUDIR=${OUT}_gpu
  ./gpu_monitor.sh start $GPUDIR 2 >/dev/null
  stdbuf -oL -eL .venv312/bin/lerobot-train \
    --dataset.repo_id=lerobot/libero_spatial_image \
    --policy.type=pi05 --policy.pretrained_path=lerobot/pi05_base \
    --policy.device=cuda --policy.dtype=bfloat16 \
    --policy.gradient_checkpointing=true --policy.compile_model=false \
    --policy.freeze_vision_encoder=false --policy.train_expert_only=false \
    --policy.push_to_hub=false \
    --batch_size=$BS --steps=30 --save_checkpoint=false \
    --wandb.enable=false --log_freq=10 \
    --output_dir=$OUT > $S/sweep_bs${BS}.log 2>&1
  EXIT=$?
  ./gpu_monitor.sh stop $GPUDIR >/dev/null
  echo "===== bs=$BS EXIT=$EXIT ====="
  if [ $EXIT -ne 0 ]; then
    if grep -qi "out of memory\|OutOfMemoryError" $S/sweep_bs${BS}.log; then
      echo "  OOM at bs=$BS -> ceiling found, stopping sweep"
    else
      echo "  FAILED for a non-OOM reason:"
      grep -viE "torchcodec|libav|decoder" $S/sweep_bs${BS}.log | grep -iE "error" | tail -2
    fi
    break
  fi
  grep -oE "updt_s:[0-9.]+|mem_gb:[0-9.]+" $S/sweep_bs${BS}.log | tail -2 | tr '\n' ' '; echo
  ./gpu_monitor.sh report $GPUDIR | grep -E "memory.used|per-process|pid" | head -3
done
echo "SWEEP DONE"
