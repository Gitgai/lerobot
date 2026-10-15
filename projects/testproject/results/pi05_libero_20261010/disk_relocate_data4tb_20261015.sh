#!/usr/bin/env bash
# Operator 2026-10-15: use the EMPTY 4 TB (/mnt/data4tb), not the DYNUS drive.
#  A. wait for disk_cleanup_20261015.sh to finish, then relocate openpi-checkpoints
#     from /mnt/dynus4tb to /mnt/data4tb and re-point the symlinks under ~/sim/openpi.
#  B. move the three orange training_state dirs (25 GB each) to /mnt/data4tb, symlinks
#     left in place — resumable, nothing deleted (operator: move, not delete; no compression:
#     measured zstd ratio 88.7%, not worth it).
set -u
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
LOG=$RES/disk_relocate_data4tb_20261015.log; exec > >(tee -a "$LOG") 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
until grep -q "CLEANUP DONE" "$RES/disk_cleanup_20261015.log" 2>/dev/null; do sleep 15; done
step "A. relocate LoRA checkpoints dynus4tb -> data4tb"
OLD=/mnt/dynus4tb/openpi-checkpoints/lora_libero_20261010; NEW=/mnt/data4tb/openpi-checkpoints/lora_libero_20261010
SRC=/home/kiran/sim/openpi/checkpoints/pi05_libero_low_mem_finetune/lora_libero_20261010
mkdir -p "$NEW"
for s in $(ls "$OLD"); do
  rsync -a "$OLD/$s/" "$NEW/$s/" && ! rsync -ac --dry-run --itemize-changes "$OLD/$s/" "$NEW/$s/" | grep -q '^>f' || { echo "MISMATCH $s"; continue; }
  [ -L "$SRC/$s" ] && ln -sfn "$NEW/$s" "$SRC/$s"
  rm -rf "$OLD/$s" && echo "relocated $s -> $NEW/$s"
done
rmdir "$OLD" /mnt/dynus4tb/openpi-checkpoints 2>/dev/null; ls -la "$SRC" | grep -E '^l|^d' | awk '{print $9, $10, $11}'

step "B. move orange training_state (x3) -> data4tb, symlink left"
O=/home/kiran/sim/pi05-fullft-orange50-20260922/orange45_fullft_15k_candidate/checkpoints
D=/mnt/data4tb/pi05-fullft-orange50-20260922/orange45_fullft_15k_candidate/checkpoints
for s in 005000 010000 015000; do
  [ -d "$O/$s/training_state" ] && [ ! -L "$O/$s/training_state" ] || { echo "SKIP $s"; continue; }
  mkdir -p "$D/$s"
  rsync -a "$O/$s/training_state/" "$D/$s/training_state/" && ! rsync -ac --dry-run --itemize-changes "$O/$s/training_state/" "$D/$s/training_state/" | grep -q '^>f' || { echo "MISMATCH $s"; continue; }
  rm -rf "$O/$s/training_state" && ln -s "$D/$s/training_state" "$O/$s/training_state" && echo "moved $s/training_state -> $D/$s/ (symlink left; pretrained_model untouched)"
done
du -sh $O/*/pretrained_model
step "after"; df -h / /mnt/data4tb /mnt/dynus4tb | tail -3; echo "=== RELOCATE DONE ==="
