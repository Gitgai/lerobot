#!/usr/bin/env bash
# L4 — openpi's pi05_libero FULL fine-tune, recipe as published (fp32 weights, fp32 AdamW,
# EMA 0.999, cosine 5e-5, 30k steps), on GPU 1 (RTX PRO 5000 72GB). Only batch size may move.
# Step 1: norm stats for the pi05_libero config (same dataset; openpi keys stats by config name).
# Step 2: 50-step smoke at batch 32 → 16 → 8, VRAM sampled on GPU 1. EMA stays ON.
set -u
OPENPI=/home/kiran/sim/openpi
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_noema
export CUDA_VISIBLE_DEVICES=1 TMPDIR=/home/kiran/tmp TOKENIZERS_PARALLELISM=false
export XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.95
LOG=$RES/l4noema_smoke.log; exec > >(tee -a "$LOG") 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
PY=$OPENPI/.venv/bin/python; cd "$OPENPI"
step "L4.0 facts"; nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader
$PY -c "import jax; print('jax devices', jax.devices())"
step "L4.1 norm stats for $CFG"
if [ -f "assets/$CFG/physical-intelligence/libero/norm_stats.json" ]; then echo present; else
  unset HF_HUB_OFFLINE; $PY scripts/compute_norm_stats.py --config-name "$CFG" 2>&1 | tail -3; fi
ls -la "assets/$CFG/physical-intelligence/libero/" || { echo "NORM STATS MISSING"; exit 2; }
step "L4.2 smoke: 50 steps, recipe as published MINUS EMA (operator-approved 2026-10-14), batch 32 → 16 → 8"
rm -f "$RES/l4noema_batch_that_fits.txt"
for BS in 32 16 8; do
  echo "--- batch $BS"
  ( while true; do nvidia-smi -i 1 --query-gpu=memory.used --format=csv,noheader,nounits; sleep 1; done ) > "$RES/l4noema_smoke_bs${BS}_vram.txt" 2>/dev/null & SMP=$!
  t0=$(date +%s)
  $PY scripts/train.py "$CFG" --exp-name "smoke_bs${BS}" --overwrite --num-train-steps 50 --batch-size "$BS" --save-interval 1000 --log-interval 10 --no-wandb-enabled > "$RES/l4noema_smoke_bs${BS}.log" 2>&1; rc=$?
  kill $SMP 2>/dev/null
  echo "batch $BS rc=$rc wall $(( $(date +%s)-t0 ))s peak VRAM $(sort -n "$RES/l4noema_smoke_bs${BS}_vram.txt" | tail -1) MiB"
  tr '\r' '\n' < "$RES/l4noema_smoke_bs${BS}.log" | grep -aE "Progress on|^Step|RESOURCE_EXHAUSTED|Error" | tail -4
  if [ "$rc" = 0 ]; then echo "SMOKE PASS at batch $BS"; echo "$BS" > "$RES/l4noema_batch_that_fits.txt"; break; fi
done
rm -rf "$OPENPI/checkpoints/$CFG"/smoke_bs* 2>/dev/null
step "L4NOEMA SMOKE VERDICT"
[ -f "$RES/l4noema_batch_that_fits.txt" ] && echo "FITS at batch $(cat "$RES/l4noema_batch_that_fits.txt") with EMA OFF" || echo "DOES NOT FIT at 8/16/32 with EMA OFF → per plan: rent a bigger box; do not bend the recipe"
echo "=== L4NOEMA SMOKE DONE ==="
