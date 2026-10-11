#!/usr/bin/env bash
# L5 — score OUR openpi LoRA checkpoint(s) with the SAME loop that scored theirs (L2).
# Plan: docs/pi05_libero_openpi_vs_ours_plan_20261010.md (L5).
# Usage via launch.json: L5_STEPS="10000 20000 30000" L5_EXP=lora_libero_20261010
set -u
OPENPI=/home/kiran/sim/openpi
PROBE_PY=/home/kiran/sim/pi05-fullft-probe/.venv312/bin/python
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_low_mem_finetune
EXP=${L5_EXP:-lora_libero_20261010}
STEPS=${L5_STEPS:-"10000 20000 30000"}
PORT=8001
LOG=$RES/l5_eval_${EXP}.log
export TMPDIR=/home/kiran/tmp TMP=/home/kiran/tmp TEMP=/home/kiran/tmp
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTHONPATH=$OPENPI/packages/openpi-client/src${PYTHONPATH:+:$PYTHONPATH}
export XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.45
mkdir -p "$TMPDIR"
exec > >(tee -a "$LOG") 2>&1
step() { echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
SRV=""
stop_srv() { if [ -n "$SRV" ] && kill -0 "$SRV" 2>/dev/null; then kill "$SRV"; sleep 3; kill -9 "$SRV" 2>/dev/null; fi; SRV=""; }
trap stop_srv EXIT

for S in $STEPS; do
  CK=$OPENPI/checkpoints/$CFG/$EXP/$S
  OUT=$RES/L5_${EXP}_step${S}_spatial_n200
  step "L5 step $S — checkpoint $CK"
  if [ ! -d "$CK/params" ]; then echo "checkpoint missing — skipping"; continue; fi
  if [ -f "$OUT/summary.json" ] && grep -q '"wall_s"' "$OUT/summary.json"; then echo "already scored — skipping"; continue; fi
  cd "$OPENPI"
  "$OPENPI/.venv/bin/python" scripts/serve_policy.py --port $PORT policy:checkpoint --policy.config "$CFG" --policy.dir "$CK" > "$RES/l5_server_${EXP}_${S}.log" 2>&1 &
  SRV=$!
  for i in $(seq 1 120); do
    if "$PROBE_PY" -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',$PORT))==0 else 1)"; then echo "server up after ${i}x5s"; break; fi
    kill -0 $SRV 2>/dev/null || { echo "server DIED:"; tail -20 "$RES/l5_server_${EXP}_${S}.log"; break; }
    sleep 5
  done
  kill -0 $SRV 2>/dev/null || continue
  "$PROBE_PY" "$RES/l2_eval_openpi.py" --suite libero_spatial --trials-per-task 20 --port $PORT --out "$OUT" --row "openpi_lora_${EXP}_step${S}"
  echo "eval rc=$?"
  stop_srv
done

step "L5 table so far"
"$PROBE_PY" - "$RES" <<'PY'
import json,glob,os,sys
res=sys.argv[1]
rows=[]
for f in sorted(glob.glob(os.path.join(res,"L2_*n200/summary.json"))+glob.glob(os.path.join(res,"L5_*n200/summary.json"))):
    s=json.load(open(f))
    if s.get("rate") is None: continue
    lo,hi=s["ci95"]; rows.append((s["row"],s["k"],s["n"],100*s["rate"],100*lo,100*hi))
print(f"{'row':45s} {'k/n':>8s} {'rate':>6s}  CI95")
for r in rows: print(f"{r[0]:45s} {r[1]:>3d}/{r[2]:<3d} {r[3]:6.1f}  [{r[4]:.1f},{r[5]:.1f}]")
print("reference (their harness): openpi pi05_libero 98.8 on Spatial")
PY
step "serving $RES on :8765"
cd "$RES" && exec python3 -m http.server 8765 --bind 127.0.0.1
