#!/usr/bin/env bash
# After row 2 (unit r5-row2) finishes: (1) open-loop MAE for every row-2 checkpoint + base + row-1 25k (fast, GPU 1);
# (2) Isaac gate corpusA, 5 episodes each (the diagnostic size used on row 1), for 007000 then 003000, frames on.
# 2026-10-22. Results under results/so101_lora_on_top_20261019/{openloop_mae_row2.json, isaac_gate/}.
set -u
OUT=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_lora_on_top_20261019
R2=/mnt/data4tb/so101-lora-on-top-20261021/row2_conservative_lora
BASE=/mnt/data4tb/huggingface-cache/models--dongyoonkim--so101-pi05-base/snapshots/56325bafcca9ec3155b8bfdf655be7df17e7f09f
R1=/mnt/data4tb/so101-lora-on-top-20261021/row1_author_lora_b8/checkpoints/025000/pretrained_model
while systemctl --user is-active r5-row2 >/dev/null 2>&1; do sleep 30; done
CK=""; for s in 001000 002000 003000 004000 005000 006000 007000; do [ -f $R2/checkpoints/$s/pretrained_model/model.safetensors ] && CK="$CK row2_${s}=$R2/checkpoints/$s/pretrained_model"; done
cd $OUT && CUDA_VISIBLE_DEVICES=1 HF_HOME=/mnt/data4tb/huggingface-cache TMPDIR=/home/kiran/tmp \
  /home/kiran/sim/vlash-venv/bin/python openloop_mae.py --ckpts base=$BASE row1_25k=$R1 $CK --stride 15 --out openloop_mae_row2.json > openloop_mae_row2.log 2>&1
for STEP in 007000 003000; do
  [ -f $R2/checkpoints/$STEP/pretrained_model/model.safetensors ] || continue
  export RUN=$R2 ROWS=corpusA EPISODES=5 RECORD_DIR=$OUT/isaac_gate/frames_row2_$STEP RECORD_EVERY=25
  bash $OUT/run_isaac_gate.sh $STEP row2_$STEP
done
echo "=== ROW2 QUEUE DONE $(date -u +%FT%TZ)" >> $OUT/isaac_gate/summary.txt
