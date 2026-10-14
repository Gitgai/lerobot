#!/usr/bin/env bash
# L4 smoke, both GPUs: fsdp_devices=2 shards the train state across the 5090 (32 GB) and the
# PRO 5000 (72 GB). Recipe as published (fp32, AdamW, EMA on). Batch must divide by 2.
set -u
OPENPI=/home/kiran/sim/openpi; RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero
export TMPDIR=/home/kiran/tmp TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1
export XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.95
unset CUDA_VISIBLE_DEVICES
LOG=$RES/l4_smoke_fsdp2.log; exec > >(tee -a "$LOG") 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
PY=$OPENPI/.venv/bin/python; cd "$OPENPI"
step "fsdp=2 smoke: 30 steps, batch 16 then 8, both GPUs sampled"
rm -f "$RES/l4_fsdp2_batch_that_fits.txt"
for BS in 16 8; do
  echo "--- batch $BS fsdp_devices 2"
  ( while true; do echo "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr '\n' ' ')"; sleep 1; done ) > "$RES/l4_fsdp2_bs${BS}_vram.txt" 2>/dev/null & SMP=$!
  t0=$(date +%s)
  $PY scripts/train.py "$CFG" --exp-name "smoke_fsdp2_bs${BS}" --overwrite --num-train-steps 30 --batch-size "$BS" --fsdp-devices 2 --save-interval 1000 --log-interval 10 --no-wandb-enabled > "$RES/l4_smoke_fsdp2_bs${BS}.log" 2>&1; rc=$?
  kill $SMP 2>/dev/null
  echo "batch $BS rc=$rc wall $(( $(date +%s)-t0 ))s  peak GPU0 $(awk '{print $1}' "$RES/l4_fsdp2_bs${BS}_vram.txt" | sort -n | tail -1) MiB  peak GPU1 $(awk '{print $2}' "$RES/l4_fsdp2_bs${BS}_vram.txt" | sort -n | tail -1) MiB"
  tr '\r' '\n' < "$RES/l4_smoke_fsdp2_bs${BS}.log" | grep -aE "Progress on: [0-9]|^Step|RESOURCE_EXHAUSTED|Error|sharding" | tail -5
  if [ "$rc" = 0 ]; then echo "FSDP2 SMOKE PASS at batch $BS"; echo "$BS" > "$RES/l4_fsdp2_batch_that_fits.txt"; break; fi
done
rm -rf "$OPENPI/checkpoints/$CFG"/smoke_fsdp2_* 2>/dev/null
step "FSDP2 VERDICT"; [ -f "$RES/l4_fsdp2_batch_that_fits.txt" ] && echo "FITS across both GPUs at batch $(cat "$RES/l4_fsdp2_batch_that_fits.txt")" || echo "does not fit even sharded across 32+72 GB"
echo "=== FSDP2 SMOKE DONE ==="
