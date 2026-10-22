#!/usr/bin/env bash
# R2 "simulator test": the public SO-101 pi0.5 checkpoint (served by so101-base-server on :8080, GPU 1) drives
# LeIsaac's PickOrange task on GPU 0, N episodes. Our logged copy of LeIsaac's evaluation script writes one JSON
# line per episode to results_<tag>.jsonl (Kit's os._exit swallows buffered prints, so never rely on stdout).
# Usage: run_sim_test.sh <rounds> <tag> "<instruction>" [seed]      HEADLESS=0 → Isaac Sim window on the desktop
set -u
ROUNDS=${1:-2}; TAG=${2:-smoke}; INSTR=${3:-"Grab oranges and place into plate."}; SEED=${4:-7}; HEADLESS=${HEADLESS:-1}; TASK=${TASK:-LeIsaac-SO101-PickOrange-v0}
R=${OUTDIR:-/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_base_sim_test_20261020}   # OUTDIR: where results_<tag>.jsonl + logs go
PORT=${PORT:-8080}; SIM_GPU=${SIM_GPU:-0}; CKPT_LABEL=${CKPT_LABEL:-/mnt/data4tb/huggingface-cache/models--dongyoonkim--so101-pi05-base}   # R5 gate: PORT=8081 SIM_GPU=1
LEISAAC=/home/kiran/sim/leisaac-src; IL=$LEISAAC/dependencies/IsaacLab/source
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)   # sim_eval_logged.py lives beside this script, not in OUTDIR
export OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y TMPDIR=/home/kiran/tmp CUDA_VISIBLE_DEVICES=$SIM_GPU PYTHONUNBUFFERED=1
export PYTHONPATH=$IL/isaaclab_tasks:$IL/isaaclab_assets:$IL/isaaclab_mimic:$IL/isaaclab_rl${PYTHONPATH:+:$PYTHONPATH}
LOG=$R/sim_${TAG}.log; exec >> "$LOG" 2>&1
HFLAG="--headless"; [ "$HEADLESS" = "0" ] && HFLAG=""
echo "=== $(date -u +%FT%TZ) sim test: port=$PORT gpu=$SIM_GPU ckpt=$CKPT_LABEL task=$TASK rounds=$ROUNDS tag=$TAG seed=$SEED headless=$HEADLESS instr='$INSTR'"
until /home/kiran/sim/leisaac-venv/bin/python -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',$PORT)))" 2>/dev/null; do sleep 10; done
echo "policy server port open $(date -u +%H:%M:%SZ)"
cd $LEISAAC && /home/kiran/sim/leisaac-venv/bin/python $SCRIPT_DIR/sim_eval_logged.py \
  --task=$TASK $HFLAG --enable_cameras --device cuda:0 --seed "$SEED" --reseed_each_episode \
  --step_hz 30 --episode_length_s "${EP_LEN:-100}" --eval_rounds "$ROUNDS" \
  --policy_type=lerobot-pi05 --policy_host=127.0.0.1 --policy_port=$PORT --policy_timeout_ms 60000 \
  --policy_action_horizon 20 --policy_language_instruction "$INSTR" \
  --policy_checkpoint_path "$CKPT_LABEL" \
  --results_jsonl "$R/results_${TAG}.jsonl"
echo "=== rc=$? $(date -u +%FT%TZ)"; [ -f "$R/results_${TAG}.jsonl" ] && echo "episodes: $(wc -l < $R/results_${TAG}.jsonl)  successes: $(grep -c '"success": true' $R/results_${TAG}.jsonl)"
echo "=== SIM TEST DONE $TAG"
