#!/usr/bin/env bash
# L3 — the 30k-step openpi LoRA run on LIBERO (pi05_libero_low_mem_finetune).
# Plan: docs/pi05_libero_openpi_vs_ours_plan_20261010.md (L3). Requires l3_prep.sh PASS.
# Training is DETACHED (setsid nohup) so it survives the launcher/session; this
# script only starts it, records the launch, and then serves the results dir.
set -u
OPENPI=/home/kiran/sim/openpi
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_low_mem_finetune
EXP=${L3_EXP:-lora_libero_20261010}
export TMPDIR=/home/kiran/tmp TMP=/home/kiran/tmp TEMP=/home/kiran/tmp
export XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.92
export TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1
mkdir -p "$TMPDIR"
LOG=$RES/l3_train_launch.log
exec > >(tee -a "$LOG") 2>&1
step() { echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
cd "$OPENPI"

step "L3 launch facts"
BS=${L3_BATCH:-$(cat "$RES/l3_batch_that_fits.txt" 2>/dev/null || echo "")}
[ -n "$BS" ] || { echo "no batch size: run l3_prep.sh first or set L3_BATCH"; exit 2; }
test -f "$OPENPI/assets/$CFG/physical-intelligence/libero/norm_stats.json" || { echo "norm stats missing"; exit 2; }
if [ -d "$OPENPI/checkpoints/$CFG/$EXP" ]; then echo "checkpoint dir exists: $OPENPI/checkpoints/$CFG/$EXP — refusing to overwrite; set L3_EXP"; exit 2; fi
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
df -h /home | tail -1
echo "config $CFG  exp $EXP  batch $BS  steps 30000  save every 10000  EMA off  wandb off"
echo "TMPDIR=$TMPDIR XLA_PYTHON_CLIENT_PREALLOCATE=$XLA_PYTHON_CLIENT_PREALLOCATE"

step "L3 start (detached)"
TRAIN_LOG=$RES/l3_train_${EXP}.log
setsid nohup "$OPENPI/.venv/bin/python" scripts/train.py "$CFG" --exp-name "$EXP" --batch-size "$BS" --log-interval 100 > "$TRAIN_LOG" 2>&1 < /dev/null &
TPID=$!
echo "$TPID" > "$RES/l3_train_${EXP}.pid"
echo "train pid $TPID  log $TRAIN_LOG"
( while kill -0 "$TPID" 2>/dev/null; do echo "$(date -u +%FT%TZ) $(nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits)"; sleep 30; done ) > "$RES/l3_train_${EXP}_gpu.txt" 2>/dev/null &
disown
sleep 90
if kill -0 "$TPID" 2>/dev/null; then echo "still running after 90 s"; else echo "EXITED within 90 s — tail:"; tail -30 "$TRAIN_LOG"; fi
grep -E "Step|loss=|num_|Initialized|Error|OOM" "$TRAIN_LOG" | tail -5

step "serving $RES on :8765 (preview_stop does NOT stop training; kill \$(cat l3_train_${EXP}.pid) does)"
cd "$RES" && exec python3 -m http.server 8765 --bind 127.0.0.1
