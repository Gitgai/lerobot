#!/usr/bin/env bash
# L5b — second 200 layouts (trials 20-39) on the 15k, 20k, 22.5k LoRA checkpoints, with rerun traces.
# Smoke first: one episode with --rerun save, assert the .rrd exists and is non-trivial.
set -u
OPENPI=/home/kiran/sim/openpi; PROBE_PY=/home/kiran/sim/pi05-fullft-probe/.venv312/bin/python
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_low_mem_finetune; EXP=lora_libero_20261010; PORT=8003
export TMPDIR=/home/kiran/tmp MUJOCO_GL=egl PYOPENGL_PLATFORM=egl HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTHONPATH=$OPENPI/packages/openpi-client/src XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.45
exec > >(tee -a "$RES/l5b_second_layouts.log") 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
SRV=""; stop(){ [ -n "$SRV" ] && kill "$SRV" 2>/dev/null && sleep 3; SRV=""; }; trap stop EXIT
serve(){ cd "$OPENPI"; "$OPENPI/.venv/bin/python" scripts/serve_policy.py --port $PORT policy:checkpoint --policy.config "$CFG" --policy.dir "$1" > "$RES/l5b_server.log" 2>&1 & SRV=$!
  for i in $(seq 1 60); do "$PROBE_PY" -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',$PORT)))" && return 0; kill -0 $SRV || { tail -5 "$RES/l5b_server.log"; return 1; }; sleep 5; done; return 1; }
T20_39=$(seq -s, 20 39)
first=1
for S in 15000 20000 22500; do
  OUT=$RES/L5b_${EXP}_step${S}_spatial_layouts20-39
  step "step $S — trials 20-39 on all 10 tasks, rerun save"
  serve "$OPENPI/checkpoints/$CFG/$EXP/$S" || { echo "server failed"; continue; }
  if [ $first = 1 ]; then
    step "smoke: one episode with rerun"
    "$PROBE_PY" "$RES/l2_eval_openpi.py" --task-ids 0 --trials 20 --port $PORT --out "$RES/L5b_smoke" --row smoke_rerun --rerun save
    f=$(ls "$RES/L5b_smoke/rerun/"*.rrd 2>/dev/null | head -1); sz=$(stat -c%s "$f" 2>/dev/null || echo 0)
    echo "smoke rrd: $f  $sz bytes"; [ "${sz:-0}" -gt 100000 ] || { echo "SMOKE FAILED: rrd missing/tiny"; exit 2; }
    first=0
  fi
  "$PROBE_PY" "$RES/l2_eval_openpi.py" --trials "$T20_39" --trials-per-task 20 --port $PORT --out "$OUT" --row "lora_step${S}_layouts20-39" --rerun save --rerun-dir "$OUT/rerun"
  echo "step $S rc=$?"; du -sh "$OUT/rerun"; stop
done
step "combined table: layouts 0-19 (L5) + 20-39 (L5b)"
"$PROBE_PY" - "$RES" <<'PY'
import json,glob,os,sys,math
res=sys.argv[1]
def wilson(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return 100*(c-h),100*(c+h)
for S in (15000,20000,22500):
    a=json.load(open(glob.glob(f"{res}/L5_*step{S}_spatial_n200/summary.json")[0]))
    b=json.load(open(f"{res}/L5b_lora_libero_20261010_step{S}_spatial_layouts20-39/summary.json"))
    k=a["k"]+b["k"]; n=a["n"]+b["n"]; lo,hi=wilson(k,n)
    print(f"step {S}: layouts 0-19 {a['k']}/{a['n']}  | 20-39 {b['k']}/{b['n']}  | pooled {k}/{n} = {100*k/n:.1f}%  CI95 [{lo:.1f},{hi:.1f}]")
    t4a=a['tasks']['4']['k']; t4b=b['tasks']['4']['k']; print(f"          drawer task: {t4a}/20 | {t4b}/20")
PY
echo "=== L5B DONE $(date -u +%FT%TZ) ==="
