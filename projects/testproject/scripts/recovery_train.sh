#!/usr/bin/env bash
# Fine-tune GR00T N1.6 FROM checkpoint-6000 on the 60-episode set
# (new30_merged 30 + recovery30 30). Path 2 recovery-data run.
#
# Recipe copied verbatim from wait_and_train.sh (the run that produced
# n16_new30_v1) EXCEPT: base is checkpoint-6000 not stock, dataset is the
# 60-ep merged set, 6000 steps not 12000, output n16_recovery_v1.
# Effective batch 32 (global 4 x accum 8) - the only config that fits 32 GB.
# Launch with nohup, NO timeout (a timeout SIGTERM-kills long runs - learned rule).
set -u
V=/home/kiran/sim/Isaac-GR00T-n16/.venv/bin/python
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
BASE=/home/kiran/lerobot_assets/checkpoints/n16_new30_v1/n16_new30_v1/checkpoint-6000
DATA=/home/kiran/lerobot_assets/datasets/new30_plus_recov30
OUT=/home/kiran/lerobot_assets/checkpoints/n16_recovery_v1
LOG=/home/kiran/n16_recovery_v1.log
NEED_MIB=26000

cd /home/kiran/sim/Isaac-GR00T-n16 || exit 1
# wait for the GPU only if a flight is holding it (never touches the flight)
while true; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
  total=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
  free=$((total - used))
  if [ "$free" -ge "$NEED_MIB" ] && ! pgrep -f "[r]un_flight.py" >/dev/null; then
    echo "[$(date '+%F %T')] GPU free ${free} MiB - STARTING" | tee -a "$LOG"; break
  fi
  echo "[$(date '+%F %T')] GPU free ${free} MiB / flight? $(pgrep -f '[r]un_flight.py'>/dev/null && echo yes || echo no) - waiting" >> "$LOG"
  sleep 120
done

N16_OPTIM=adamw_bnb_8bit PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True $V \
  "$PROJ/scripts/gr00t_patches/launch_finetune.py" \
  --base-model-path "$BASE" \
  --dataset-path "$DATA" \
  --embodiment-tag NEW_EMBODIMENT \
  --modality-config-path "$PROJ/configs/leisaac_so101_gr00t_config.py" \
  --output-dir "$OUT" \
  --experiment-name n16_recovery_v1 \
  --max-steps 6000 \
  --save-steps 3000 \
  --save-total-limit 10 \
  --global-batch-size 4 \
  --gradient-accumulation-steps 8 \
  --learning-rate 1e-4 \
  >> "$LOG" 2>&1
echo "[$(date '+%F %T')] training exited rc=$?" | tee -a "$LOG"
