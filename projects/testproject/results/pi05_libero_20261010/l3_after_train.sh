#!/usr/bin/env bash
# L5 auto — when the L3 trainer has finished (30k checkpoint committed, or the
# trainer is gone after the resume), score every checkpoint not yet scored with
# the L2 loop and print the table. Armed 2026-10-11.
set -u
OPENPI=/home/kiran/sim/openpi
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_low_mem_finetune
EXP=lora_libero_20261010
CKDIR=$OPENPI/checkpoints/$CFG/$EXP
LOG=$RES/l3_after_train.log
export TMPDIR=/home/kiran/tmp
exec > >(tee -a "$LOG") 2>&1
step() { echo; echo "=== $(date -u +%FT%TZ) $* ==="; }

step "waiting for the resume to have happened, then for training to END"
until grep -q "resumed trainer alive" "$RES/l3_resume_5k.log" 2>/dev/null; do sleep 60; done
echo "resume observed at $(date -u +%FT%TZ)"
while true; do
  if [ -d "$CKDIR/30000/params" ] && ! ls -d "$CKDIR"/*orbax-checkpoint-tmp* >/dev/null 2>&1; then echo "30000 committed"; break; fi
  if ! pgrep -f "[s]cripts/train.py $CFG --exp-name $EXP" >/dev/null; then echo "trainer process gone (no 30000 yet) — scoring what exists"; break; fi
  sleep 60
done
# give the trainer a moment to exit and release the GPU
for i in $(seq 1 30); do pgrep -f "[s]cripts/train.py $CFG --exp-name $EXP" >/dev/null || break; sleep 10; done
nvidia-smi --query-gpu=memory.used --format=csv,noheader
ls -d "$CKDIR"/[0-9]* 2>/dev/null

step "L5: score every committed checkpoint not yet scored"
STEPS=$(ls -d "$CKDIR"/[0-9]* 2>/dev/null | xargs -n1 basename | sort -n | tr '\n' ' ')
L5_NO_SERVE=1 L5_STEPS="$STEPS" L5_EXP="$EXP" bash "$RES/l5_eval_lora.sh"
echo "L5 rc=$?"
step "serving $RES on :8770"
cd "$RES" && exec python3 -m http.server 8770 --bind 127.0.0.1
