#!/usr/bin/env bash
# L2 — openpi's published pi05_libero full-FT checkpoint, scored in OUR loop.
# Plan: docs/pi05_libero_openpi_vs_ours_plan_20261010.md
#   server  : openpi venv  (~/sim/openpi/.venv, python 3.11, jax)  — L1 PASS 2026-10-10
#   client  : probe venv   (~/sim/pi05-fullft-probe/.venv312, has the libero package)
#   RTC     : none. Convention: openpi examples/libero/main.py. n = 20/task x 10 = 200.
# GREEN per the plan's autonomy contract: installs only msgpack+websockets into the
# probe venv (openpi-client itself pins numpy<2 and is NOT installed — it is put on
# PYTHONPATH instead, so the probe venv's numpy/torch are untouched).
set -u
OPENPI=/home/kiran/sim/openpi
PROBE_PY=/home/kiran/sim/pi05-fullft-probe/.venv312/bin/python
CKPT=/home/kiran/.cache/openpi/openpi-assets/checkpoints/pi05_libero
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
OUT=$RES/L2_openpi_pi05_libero_spatial_n200
LOG=$RES/l2_run.log
PORT=8000
export TMPDIR=/home/kiran/tmp TMP=/home/kiran/tmp TEMP=/home/kiran/tmp   # /tmp quota is exhausted
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export PYTHONPATH=$OPENPI/packages/openpi-client/src${PYTHONPATH:+:$PYTHONPATH}
export HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
# 2026-10-10 18:19Z: first L2 attempt died with "failed to create cublas handle: the
# resource allocation failed" — JAX preallocates 75% of the 32 GB card at startup
# while a foreign process holds 10 GB, leaving cuBLAS no workspace. Allocate on demand.
export XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.45
mkdir -p "$TMPDIR" "$OUT"
exec > >(tee -a "$LOG") 2>&1
step() { echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
cleanup() { if [ -n "${SRV:-}" ] && kill -0 "$SRV" 2>/dev/null; then echo "stopping server $SRV"; kill "$SRV"; sleep 3; kill -9 "$SRV" 2>/dev/null; fi; }
trap cleanup EXIT

step "L2.0 facts"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader); do ps -o pid=,etime=,user=,args= -p "$p" 2>/dev/null | cut -c1-160; done
echo "XLA_PYTHON_CLIENT_PREALLOCATE=$XLA_PYTHON_CLIENT_PREALLOCATE MEM_FRACTION=$XLA_PYTHON_CLIENT_MEM_FRACTION"
test -d "$CKPT/params" && echo "checkpoint present: $CKPT" || { echo "checkpoint MISSING at $CKPT"; exit 2; }
"$PROBE_PY" -c "import libero, torch, numpy; print('probe venv: libero ok, torch', torch.__version__, 'numpy', numpy.__version__)" || { echo "probe venv broken"; exit 2; }

step "L2.1 client deps into the probe venv (msgpack, websockets only)"
uv pip install --python "$PROBE_PY" "msgpack>=1.0.5" "websockets>=11.0" 2>&1 | tail -3
"$PROBE_PY" -c "import msgpack, websockets, PIL; from openpi_client import websocket_client_policy, image_tools; print('openpi_client importable from PYTHONPATH')" || { echo "client import FAILED"; exit 2; }

step "L2.2 start openpi policy server (pi05_libero) on :$PORT"
cd "$OPENPI"
# tyro: options bind to the preceding subcommand, so --port goes BEFORE policy:checkpoint
"$OPENPI/.venv/bin/python" scripts/serve_policy.py --port $PORT policy:checkpoint --policy.config pi05_libero --policy.dir "$CKPT" > "$RES/l2_server.log" 2>&1 &
SRV=$!
echo "server pid $SRV"
for i in $(seq 1 120); do
  if "$PROBE_PY" -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',$PORT))==0 else 1)"; then echo "server listening after ${i}x5s"; break; fi
  kill -0 $SRV 2>/dev/null || { echo "server DIED during startup — tail of l2_server.log:"; tail -20 "$RES/l2_server.log"; exit 3; }
  sleep 5
done

step "L2.3 smoke: task 0, one trial (also warms the server's JIT)"
"$PROBE_PY" "$RES/l2_eval_openpi.py" --suite libero_spatial --task-ids 0 --trials-per-task 1 --port $PORT --out "$RES/L2_smoke" --row smoke ; rc=$?
echo "smoke rc=$rc"; [ "$rc" = "0" ] || { echo "SMOKE FAILED — see above and l2_server.log"; tail -30 "$RES/l2_server.log"; exit 4; }

step "L2.4 full run: libero_spatial, 20 trials x 10 tasks = 200, env seed 7"
"$PROBE_PY" "$RES/l2_eval_openpi.py" --suite libero_spatial --trials-per-task 20 --port $PORT --out "$OUT" --row openpi_pi05_libero_fullft ; rc=$?
echo "full run rc=$rc"

step "L2 VERDICT"
if [ -f "$OUT/summary.json" ]; then "$PROBE_PY" - "$OUT/summary.json" <<'PY'
import json,sys
s=json.load(open(sys.argv[1]))
if "rate" in s and s["rate"] is not None:
    r=100*s["rate"]; lo,hi=[100*x for x in s["ci95"]]
    print(f"L2 openpi pi05_libero on libero_spatial: {s['k']}/{s['n']} = {r:.1f}%  CI95 [{lo:.1f},{hi:.1f}]  wall {s['wall_s']}s")
    print("their number 98.8 | >=95 harness agrees | 85-95 find the convention mismatch | <85 fix the harness first")
    for tid,t in s["tasks"].items(): print(f"  task {tid:>2}: {t['k']:2d}/{t['n']}  {t['task']}")
else:
    print("summary incomplete:", {k:v for k,v in s.items() if k!='tasks'})
PY
fi
cleanup
step "serving $RES on :8765 (preview_stop to end)"
cd "$RES" && exec python3 -m http.server 8765 --bind 127.0.0.1
