#!/usr/bin/env bash
# Q (operator 2026-10-20): why replan every 5 of 10? What if the client executes the WHOLE chunk and only then
# asks again (stop-and-wait)? Frozen protocol (sim waits, no staleness) → isolates the "fewer corrections" cost.
set -u
R=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
PY=/home/kiran/sim/pi05-fullft-probe/.venv312/bin/python
export TMPDIR=/home/kiran/tmp MUJOCO_GL=egl PYOPENGL_PLATFORM=egl PYTHONPATH=/home/kiran/sim/openpi/packages/openpi-client/src HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
exec >> "$R/l6b_replan_full_chunk.log" 2>&1
until "$PY" -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',8007)))"; do sleep 5; done
for RP in 10; do
  OUT=$R/L6b_replan${RP}_lora20k_spatial_n200; rm -rf "$OUT"
  echo "=== $(date -u +%FT%TZ) frozen protocol, replan every $RP of 10 (execute the whole chunk, then ask)"
  "$PY" "$R/l2_eval_openpi.py" --suite libero_spatial --trials-per-task 20 --host 127.0.0.1 --port 8007 --seed 7 --replan-steps $RP --out "$OUT" --row "lora20k_replan${RP}" | grep -E "RESULT|=== task"
done
echo "reference: replan 5 (standard) = 199/200 (L5) / 198/200 (L6 D=0)"
echo "=== L6B DONE $(date -u +%FT%TZ)"
