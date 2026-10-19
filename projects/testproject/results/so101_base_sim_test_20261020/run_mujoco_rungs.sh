#!/usr/bin/env bash
# R2b rungs 4-5: MuJoCo EnvHub environments, 50 episodes each, against wrapper B (:8081). Sequential (one client per server).
R=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_base_sim_test_20261020
. /home/kiran/sim/mujoco-envhub-venv312/bin/activate
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl CUDA_VISIBLE_DEVICES=0 TMPDIR=/home/kiran/tmp HF_HOME=/mnt/data4tb/huggingface-cache PYTHONUNBUFFERED=1
cd $R; LOG=$R/sim_mujoco.log; exec >> "$LOG" 2>&1
run(){ echo "=== $(date -u +%FT%TZ) $*"; python mujoco_envhub_eval.py "$@" 2>&1 | grep -aE "^\[dbg\]|^\[RESULT\]|^\[FINAL\]|^Traceback|Error: " ; }
run --env namenu --episodes 50 --port 8081 --seed 500 --out $R/results_mj_pickplace_200.jsonl
run --env namenu --episodes 50 --port 8081 --seed 500 --max-steps 600 --out $R/results_mj_pickplace_600.jsonl
for T in MuJoCoPickLift-v1 MuJoCoPickAndPlace-v1 MuJoCoStackCube-v1 MuJoCoTouch-v1; do
  run --env nexus:$T --episodes 50 --port 8081 --seed 500 --out $R/results_nexus_${T%-v1}.jsonl
done
echo "=== MUJOCO RUNGS DONE $(date -u +%FT%TZ)"
