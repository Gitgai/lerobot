#!/usr/bin/env bash
# Waits for the running gate unit to finish, then gates earlier checkpoints on corpusA (20 episodes each, same seeds
# 100–119 as the base), frames recorded every 25th call under isaac_gate/frames_<step>/. 2026-10-22.
set -u
OUT=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_lora_on_top_20261019
while systemctl --user is-active r5-gate >/dev/null 2>&1; do sleep 30; done
for STEP in 012500 005000; do
  export ROWS=corpusA EPISODES=20 RECORD_DIR=$OUT/isaac_gate/frames_$STEP RECORD_EVERY=25
  bash $OUT/run_isaac_gate.sh $STEP lora_$STEP
done
echo "=== QUEUE DONE $(date -u +%FT%TZ)" >> $OUT/isaac_gate/summary.txt
