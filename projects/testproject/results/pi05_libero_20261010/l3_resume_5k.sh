#!/usr/bin/env bash
# L3 — wait for the 10k checkpoint, stop the trainer cleanly, resume with 5k saves.
# Operator decision 2026-10-11: 10k checkpoints are too far apart (a crash loses 10 h).
# openpi --resume reloads the last checkpoint with the step counter intact, so the
# cosine schedule continues unchanged. keep_period=5000 keeps every checkpoint for L5.
set -u
OPENPI=/home/kiran/sim/openpi
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_low_mem_finetune
EXP=lora_libero_20261010
CKDIR=$OPENPI/checkpoints/$CFG/$EXP
PIDFILE=$RES/l3_train_${EXP}.pid
WAIT_STEP=${L3_WAIT_STEP:-20000}   # armed 2026-10-11 ~08:40Z for the NEXT checkpoint (10k had passed)
export TMPDIR=/home/kiran/tmp TMP=/home/kiran/tmp TEMP=/home/kiran/tmp
export XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.92
export TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1
LOG=$RES/l3_resume_5k.log
exec > >(tee -a "$LOG") 2>&1
step() { echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
cd "$OPENPI"

step "waiting for checkpoint $WAIT_STEP to be COMMITTED in $CKDIR"
TPID=$(cat "$PIDFILE")
echo "trainer pid $TPID"
while true; do
  # orbax writes to a tmp dir and renames on commit; a committed step dir has params/ and no *.orbax-checkpoint-tmp-* sibling for it
  if [ -d "$CKDIR/$WAIT_STEP/params" ] && [ -d "$CKDIR/$WAIT_STEP/train_state" ] && ! ls -d "$CKDIR"/*orbax-checkpoint-tmp* >/dev/null 2>&1; then
    sleep 60   # let any trailing metadata writes finish
    if ! ls -d "$CKDIR"/*orbax-checkpoint-tmp* >/dev/null 2>&1; then break; fi
  fi
  kill -0 "$TPID" 2>/dev/null || { echo "trainer $TPID is GONE before $WAIT_STEP — not resuming automatically; inspect l3_train_${EXP}.log"; exit 3; }
  sleep 30
done
echo "checkpoint $WAIT_STEP committed:"; ls -la "$CKDIR/$WAIT_STEP"; du -sh "$CKDIR/$WAIT_STEP"

step "stopping trainer $TPID (SIGTERM, then SIGKILL after 60 s)"
kill "$TPID"
for i in $(seq 1 60); do kill -0 "$TPID" 2>/dev/null || break; sleep 1; done
kill -0 "$TPID" 2>/dev/null && { kill -9 "$TPID"; sleep 5; }
echo "trainer stopped"; nvidia-smi --query-gpu=memory.used --format=csv,noheader

step "GPU is free: score every committed checkpoint with the L2 loop (L5) before resuming"
L5_NO_SERVE=1 L5_STEPS="10000 $WAIT_STEP" L5_EXP="$EXP" bash "$RES/l5_eval_lora.sh"
echo "L5 interim rc=$?"

step "resuming from $WAIT_STEP with save_interval=5000 keep_period=5000"
TRAIN_LOG=$RES/l3_train_${EXP}_resume.log
setsid nohup "$OPENPI/.venv/bin/python" scripts/train.py "$CFG" --exp-name "$EXP" --resume --batch-size 32 --save-interval 5000 --keep-period 5000 --log-interval 100 > "$TRAIN_LOG" 2>&1 < /dev/null &
NPID=$!
echo "$NPID" > "$PIDFILE"
echo "new trainer pid $NPID  log $TRAIN_LOG"
( while kill -0 "$NPID" 2>/dev/null; do echo "$(date -u +%FT%TZ) $(nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits)"; sleep 30; done ) >> "$RES/l3_train_${EXP}_gpu.txt" 2>/dev/null &
disown
sleep 180
if kill -0 "$NPID" 2>/dev/null; then echo "resumed trainer alive after 180 s"; else echo "resumed trainer EXITED — tail:"; tail -40 "$TRAIN_LOG"; fi
grep -E "Resuming|restor|Progress on|Error|Traceback" "$TRAIN_LOG" | tail -5

step "serving $RES on :8765"
cd "$RES" && exec python3 -m http.server 8765 --bind 127.0.0.1
