#!/usr/bin/env bash
# After the 2026-10-11 ~16:17Z reboot killed the trainer at 18.8k (only 10k survived):
#   1. score the 10k checkpoint now (GPU idle)        → first LoRA number
#   2. --resume from 10k with saves every 2500 steps   (operator, 2026-10-11)
#   3. when training ends, score every checkpoint, print the table
set -u
OPENPI=/home/kiran/sim/openpi
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_low_mem_finetune
EXP=lora_libero_20261010
CKDIR=$OPENPI/checkpoints/$CFG/$EXP
export TMPDIR=/home/kiran/tmp XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.92
export TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1
mkdir -p "$TMPDIR"
LOG=$RES/l3_restart_2500.log
exec > >(tee -a "$LOG") 2>&1
step() { echo; echo "=== $(date -u +%FT%TZ) $* ==="; }

step "1. score 10k (L5) before resuming"
L5_NO_SERVE=1 L5_STEPS="10000" L5_EXP="$EXP" bash "$RES/l5_eval_lora.sh"
echo "L5(10k) rc=$?"

step "2. resume from $(ls -d "$CKDIR"/[0-9]* | xargs -n1 basename | sort -n | tail -1) with save_interval=2500 keep_period=2500"
cd "$OPENPI"
TRAIN_LOG=$RES/l3_train_${EXP}_resume2500.log
setsid nohup "$OPENPI/.venv/bin/python" scripts/train.py "$CFG" --exp-name "$EXP" --resume --batch-size 32 --save-interval 2500 --keep-period 2500 --log-interval 100 > "$TRAIN_LOG" 2>&1 < /dev/null &
TPID=$!
echo "$TPID" > "$RES/l3_train_${EXP}.pid"
echo "trainer pid $TPID  log $TRAIN_LOG"
( while kill -0 "$TPID" 2>/dev/null; do echo "$(date -u +%FT%TZ) $(nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits)"; sleep 30; done ) >> "$RES/l3_train_${EXP}_gpu.txt" 2>/dev/null &
sleep 240
kill -0 "$TPID" 2>/dev/null && echo "trainer alive after 240 s" || { echo "trainer EXITED early:"; tail -30 "$TRAIN_LOG"; exit 3; }
grep -aE "Resum|restor|Progress on" "$TRAIN_LOG" | tr '\r' '\n' | tail -3

step "3. waiting for training to end"
while kill -0 "$TPID" 2>/dev/null; do sleep 120; done
echo "trainer exited at $(date -u +%FT%TZ); checkpoints: $(ls -d "$CKDIR"/[0-9]* | xargs -n1 basename | sort -n | tr '\n' ' ')"
sleep 20
STEPS=$(ls -d "$CKDIR"/[0-9]* | xargs -n1 basename | sort -n | tr '\n' ' ')
L5_NO_SERVE=1 L5_STEPS="$STEPS" L5_EXP="$EXP" bash "$RES/l5_eval_lora.sh"
echo "L5(all) rc=$?"
echo "=== DONE $(date -u +%FT%TZ) ==="
