#!/usr/bin/env bash
# Re-record the drawer layout (task 4, trial 37) on 22.5k and 20k with the extended rerun logging
# (full chunk tensor, plan series, 3D ee path + planned chunk). Verification of the new channels.
set -u
OPENPI=/home/kiran/sim/openpi; PROBE_PY=/home/kiran/sim/pi05-fullft-probe/.venv312/bin/python
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_low_mem_finetune; EXP=lora_libero_20261010; PORT=8004
export TMPDIR=/home/kiran/tmp MUJOCO_GL=egl PYOPENGL_PLATFORM=egl HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTHONPATH=$OPENPI/packages/openpi-client/src XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.45
OUT=$RES/viz_pair_task4_trial37; mkdir -p "$OUT"
exec > >(tee -a "$RES/viz_pair.log") 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
SRV=""; stop(){ [ -n "$SRV" ] && kill "$SRV" 2>/dev/null && sleep 3; SRV=""; }; trap stop EXIT
serve(){ cd "$OPENPI"; "$OPENPI/.venv/bin/python" scripts/serve_policy.py --port $PORT policy:checkpoint --policy.config "$CFG" --policy.dir "$1" > "$RES/viz_pair_server.log" 2>&1 & SRV=$!
  for i in $(seq 1 60); do "$PROBE_PY" -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',$PORT)))" && return 0; kill -0 $SRV || { tail -5 "$RES/viz_pair_server.log"; return 1; }; sleep 5; done; return 1; }
for S in 22500 20000; do
  step "step $S task 4 trials 37 (x3 draws: 37 run three times would reuse the layout; run 37,37,37 is not possible -> run 37 once)"
  serve "$OPENPI/checkpoints/$CFG/$EXP/$S" || { echo "server failed"; continue; }
  "$PROBE_PY" "$RES/l2_eval_openpi.py" --task-ids 4 --trials 37 --port $PORT --out "$OUT/step$S" --row "viz_step${S}" --rerun save --rerun-dir "$OUT/step$S/rerun" --video-dir "$OUT/step$S/video"
  echo "step $S rc=$?"; ls -la "$OUT/step$S/rerun" "$OUT/step$S/video"; stop
done
echo "=== VIZ PAIR DONE $(date -u +%FT%TZ) ==="
