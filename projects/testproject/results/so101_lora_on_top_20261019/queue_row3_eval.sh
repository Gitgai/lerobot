#!/usr/bin/env bash
# After row 3 (unit r5-row3) ends: open-loop MAE on GPU 0 for base, row-1 25k, row-2 7k and every row-3 checkpoint
# (the August hold-out probes as before, PLUS the same probe on 5 September overhead episodes — new30_merged eps 0-4 —
# via --dataset/--episodes), then start the row-3 final server on :8081 (GPU 0; GPU 1 is full with the operator's job)
# with the recorder on, ready for the bench. Isaac gate for row 3 waits for a free GPU. 2026-10-25.
set -u
OUT=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_lora_on_top_20261019
R3=/mnt/data4tb/so101-lora-on-top-20261021/row3_all169_conservative
BASE=/mnt/data4tb/huggingface-cache/models--dongyoonkim--so101-pi05-base/snapshots/56325bafcca9ec3155b8bfdf655be7df17e7f09f
R1=/mnt/data4tb/so101-lora-on-top-20261021/row1_author_lora_b8/checkpoints/025000/pretrained_model
R2=/mnt/data4tb/so101-lora-on-top-20261021/row2_conservative_lora/checkpoints/007000/pretrained_model
while systemctl --user is-active r5-row3 >/dev/null 2>&1; do sleep 30; done
CK=""; for s in 002000 004000 006000 008000 010000; do [ -f $R3/checkpoints/$s/pretrained_model/model.safetensors ] && CK="$CK row3_${s}=$R3/checkpoints/$s/pretrained_model"; done
cd $OUT
CUDA_VISIBLE_DEVICES=0 HF_HOME=/mnt/data4tb/huggingface-cache TMPDIR=/home/kiran/tmp /home/kiran/sim/vlash-venv/bin/python openloop_mae.py \
  --ckpts base=$BASE row1_25k=$R1 row2_7k=$R2 $CK --stride 15 --out openloop_mae_row3_aug.json > openloop_mae_row3_aug.log 2>&1
CUDA_VISIBLE_DEVICES=0 HF_HOME=/mnt/data4tb/huggingface-cache TMPDIR=/home/kiran/tmp /home/kiran/sim/vlash-venv/bin/python openloop_mae.py \
  --dataset /home/kiran/lerobot_assets/datasets/new30_merged --episodes 0,1,2,3,4,20,21 --ckpts base=$BASE row1_25k=$R1 row2_7k=$R2 $CK --stride 15 --out openloop_mae_row3_sep.json > openloop_mae_row3_sep.log 2>&1
FINAL=$R3/checkpoints/010000/pretrained_model
systemctl --user stop so101-lora-server 2>/dev/null || true
systemd-run --user --unit=so101-lora-server --collect --setenv=CUDA_VISIBLE_DEVICES=0 --setenv=HF_HOME=/mnt/data4tb/huggingface-cache --setenv=TMPDIR=/home/kiran/tmp \
  --setenv=HOME=/home/kiran --setenv=PYTHONUNBUFFERED=1 --setenv=RECORD_DIR=$OUT/bench_frames_row3_010000 --setenv=RECORD_EVERY=1 \
  /home/kiran/sim/vlash-venv/bin/python /home/kiran/projects/git/nvidia/lerobot/projects/testproject/scripts/so101_base_policy_server.py --host 0.0.0.0 --port 8081 --ckpt $FINAL/
echo "=== ROW3 EVAL QUEUE DONE $(date -u +%FT%TZ); row-3 server on :8081 (GPU 0)" >> $OUT/isaac_gate/summary.txt
