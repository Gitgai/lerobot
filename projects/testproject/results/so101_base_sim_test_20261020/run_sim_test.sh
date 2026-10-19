#!/usr/bin/env bash
# R2 "simulator test": the public SO-101 pi0.5 checkpoint (served by so101-base-server on :8080, GPU 1) drives
# LeIsaac's PickOrange task on GPU 0, headless, N seeded episodes. Usage: run_sim_test.sh <rounds> <tag> "<instruction>" [seed]
set -u
ROUNDS=${1:-2}; TAG=${2:-smoke}; INSTR=${3:-"Grab oranges and place into plate."}; SEED=${4:-7}
R=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_base_sim_test_20261020
LEISAAC=/home/kiran/sim/leisaac-src; IL=$LEISAAC/dependencies/IsaacLab/source
export OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y TMPDIR=/home/kiran/tmp CUDA_VISIBLE_DEVICES=0 PYTHONUNBUFFERED=1
export PYTHONPATH=$IL/isaaclab_tasks:$IL/isaaclab_assets:$IL/isaaclab_mimic:$IL/isaaclab_rl${PYTHONPATH:+:$PYTHONPATH}
LOG=$R/sim_${TAG}.log; exec >> "$LOG" 2>&1
echo "=== $(date -u +%FT%TZ) sim test: rounds=$ROUNDS tag=$TAG seed=$SEED instr='$INSTR'"
until /home/kiran/sim/leisaac-venv/bin/python -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',8080)))" 2>/dev/null; do sleep 10; done
echo "policy server port open $(date -u +%H:%M:%SZ)"
cd $LEISAAC && /home/kiran/sim/leisaac-venv/bin/python scripts/evaluation/policy_inference.py \
  --task=LeIsaac-SO101-PickOrange-v0 --headless --enable_cameras --device cuda:0 --seed "$SEED" \
  --step_hz 30 --episode_length_s 100 --eval_rounds "$ROUNDS" \
  --policy_type=lerobot-pi05 --policy_host=127.0.0.1 --policy_port=8080 --policy_timeout_ms 60000 \
  --policy_action_horizon 20 --policy_language_instruction "$INSTR" \
  --policy_checkpoint_path /mnt/data4tb/huggingface-cache/models--dongyoonkim--so101-pi05-base
echo "=== rc=$? $(date -u +%FT%TZ)"; grep -E "\[Evaluation\] (Episode|Final|now)" "$LOG" | tail -5
echo "=== SIM TEST DONE $TAG"
