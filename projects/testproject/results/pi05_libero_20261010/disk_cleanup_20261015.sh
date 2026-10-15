#!/usr/bin/env bash
# Operator-approved 2026-10-15: rows 1 and 3 of the cleanup table ONLY.
#  1. delete the four September smoke checkpoints (2-5 step models)       ~132 GB
#  3. move 8 spare LoRA checkpoints to the 4 TB, 20000 stays on root       ~74 GB
# Nothing else is touched. Every path is checked before it is removed. Log: disk_cleanup_20261015.log
set -u
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
LOG=$RES/disk_cleanup_20261015.log; exec > >(tee -a "$LOG") 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
S=/home/kiran/sim/pi05-fullft-orange50-20260922
step "before"; df -h / /mnt/dynus4tb | tail -2

step "1. delete the four September smoke checkpoints"
for d in "$S/smoke_training/checkpoints/000003" "$S/smoke_training/checkpoints/000005" \
         "$S/main_worker_integration_20260923/training/checkpoints/000002" "$S/main_worker_integration_20260923/training/checkpoints/000003"; do
  if [ -d "$d/pretrained_model" ] && [ -d "$d/training_state" ]; then
    sz=$(du -sh "$d" | cut -f1); rm -rf "$d" && echo "removed $sz  $d"
  else echo "SKIP (not the expected checkpoint layout): $d"; fi
done
rm -f "$S/smoke_training/checkpoints/last" "$S/main_worker_integration_20260923/training/checkpoints/last" 2>/dev/null
echo "kept: $(ls $S/orange45_fullft_15k_candidate/checkpoints/)"

step "3. move spare LoRA checkpoints to the 4 TB (rsync + checksum, then remove source, leave symlink)"
SRC=/home/kiran/sim/openpi/checkpoints/pi05_libero_low_mem_finetune/lora_libero_20261010
DST=/mnt/dynus4tb/openpi-checkpoints/lora_libero_20261010; mkdir -p "$DST"
for s in 10000 12500 15000 17500 22500 25000 27500 29999; do
  [ -d "$SRC/$s" ] && [ ! -L "$SRC/$s" ] || { echo "SKIP $s (missing or already a link)"; continue; }
  rsync -a "$SRC/$s/" "$DST/$s/" && rsync -ac --dry-run --itemize-changes "$SRC/$s/" "$DST/$s/" | grep -q '^>f' && { echo "CHECKSUM MISMATCH $s — source kept"; continue; }
  rm -rf "$SRC/$s" && ln -s "$DST/$s" "$SRC/$s" && echo "moved $s -> $DST/$s (symlink left)"
done
echo "on root: $(ls -la $SRC | grep -v '^l' | grep -E '^d' | awk '{print $NF}' | tr '\n' ' ')"
step "after"; df -h / /mnt/dynus4tb | tail -2; echo "=== CLEANUP DONE ==="
