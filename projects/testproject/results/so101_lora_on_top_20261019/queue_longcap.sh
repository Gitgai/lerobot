#!/usr/bin/env bash
# Longer-cap diagnostic (2026-10-22): after the row-2 eval queue finishes, re-run Isaac corpusA with a 200 s cap
# (EP_LEN=200; the gate used 100 s) for row-2 7k and row-1 25k, 5 episodes each, same seeds 100-104, frames on,
# with the eval now logging oranges_on_plate + at_rest per episode. Separates "slower than the base" from "cannot".
set -u
OUT=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_lora_on_top_20261019
while systemctl --user is-active r5-row2-eval >/dev/null 2>&1; do sleep 30; done
export EP_LEN=200 ROWS=corpusA EPISODES=5 RECORD_EVERY=25
RUN=/mnt/data4tb/so101-lora-on-top-20261021/row2_conservative_lora RECORD_DIR=$OUT/isaac_gate/frames_row2_007000_cap200 bash $OUT/run_isaac_gate.sh 007000 row2_007000_cap200
RUN=/mnt/data4tb/so101-lora-on-top-20261021/row1_author_lora_b8  RECORD_DIR=$OUT/isaac_gate/frames_025000_cap200       bash $OUT/run_isaac_gate.sh 025000 lora_025000_cap200
echo "=== LONGCAP QUEUE DONE $(date -u +%FT%TZ)" >> $OUT/isaac_gate/summary.txt
