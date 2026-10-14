#!/usr/bin/env bash
# L4 chain: wait for the smoke verdict → launch the 30k full-FT run on GPU 1 (recipe as published,
# batch from the smoke, saves every 2500) → when it ends, score every checkpoint with the L2 loop
# (policy server on GPU 0) → print the three-row table. Everything detached; log: l4_chain.log
set -u
OPENPI=/home/kiran/sim/openpi; PROBE_PY=/home/kiran/sim/pi05-fullft-probe/.venv312/bin/python
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero; EXP=fullft_libero_20261014; CKDIR=$OPENPI/checkpoints/$CFG/$EXP
export TMPDIR=/home/kiran/tmp TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1
LOG=$RES/l4_chain.log; exec > >(tee -a "$LOG") 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }

step "waiting for the smoke verdict"
until grep -q "L4 SMOKE DONE" "$RES/l4_smoke.log" 2>/dev/null; do sleep 30; done
BS=$(cat "$RES/l4_batch_that_fits.txt" 2>/dev/null || true)
[ -n "$BS" ] || { echo "smoke did not find a fitting batch — NOT launching (rent a bigger box per plan)"; exit 3; }
echo "batch $BS"

step "launch: $CFG as published, batch $BS, 30k steps, save every 2500, GPU 1"
cd "$OPENPI"
[ -d "$CKDIR" ] && { echo "exp dir exists: $CKDIR — refusing"; exit 2; }
TRAIN_LOG=$RES/l4_train_${EXP}.log
CUDA_VISIBLE_DEVICES=1 XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.95 \
  setsid nohup "$OPENPI/.venv/bin/python" scripts/train.py "$CFG" --exp-name "$EXP" --batch-size "$BS" \
  --save-interval 2500 --keep-period 2500 --log-interval 100 --no-wandb-enabled > "$TRAIN_LOG" 2>&1 < /dev/null &
TPID=$!; echo "$TPID" > "$RES/l4_train_${EXP}.pid"; echo "trainer pid $TPID log $TRAIN_LOG"
( while kill -0 "$TPID" 2>/dev/null; do echo "$(date -u +%FT%TZ) $(nvidia-smi -i 1 --query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits)"; sleep 30; done ) > "$RES/l4_train_${EXP}_gpu.txt" 2>/dev/null &
sleep 300
kill -0 "$TPID" 2>/dev/null && echo "trainer alive after 300 s" || { echo "trainer EXITED early:"; tail -30 "$TRAIN_LOG"; exit 4; }
tr '\r' '\n' < "$TRAIN_LOG" | grep -a "Progress on" | tail -1

step "waiting for training to end"
while kill -0 "$TPID" 2>/dev/null; do sleep 300; done
echo "trainer exited $(date -u +%FT%TZ); checkpoints: $(ls -d "$CKDIR"/[0-9]* 2>/dev/null | xargs -n1 basename | sort -n | tr '\n' ' ')"
sleep 30

step "score every checkpoint (server on GPU 0, L2 loop, layouts 0-19, n=200)"
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl PYTHONPATH=$OPENPI/packages/openpi-client/src
PORT=8005
for S in $(ls -d "$CKDIR"/[0-9]* | xargs -n1 basename | sort -n); do
  OUT=$RES/L5_${EXP}_step${S}_spatial_n200
  [ -f "$OUT/summary.json" ] && grep -q '"wall_s"' "$OUT/summary.json" && { echo "step $S already scored"; continue; }
  CUDA_VISIBLE_DEVICES=0 XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.45 \
    "$OPENPI/.venv/bin/python" scripts/serve_policy.py --port $PORT policy:checkpoint --policy.config "$CFG" --policy.dir "$CKDIR/$S" > "$RES/l4_server_${S}.log" 2>&1 & SRV=$!
  for i in $(seq 1 90); do "$PROBE_PY" -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',$PORT)))" && break; kill -0 $SRV 2>/dev/null || { echo "server died for $S"; tail -5 "$RES/l4_server_${S}.log"; break; }; sleep 5; done
  kill -0 $SRV 2>/dev/null || continue
  "$PROBE_PY" "$RES/l2_eval_openpi.py" --suite libero_spatial --trials-per-task 20 --port $PORT --out "$OUT" --row "openpi_fullft_${EXP}_step${S}"
  echo "step $S eval rc=$?"; kill $SRV 2>/dev/null; sleep 3
done

step "THREE-ROW TABLE"
"$PROBE_PY" - "$RES" <<'PY'
import json,glob,os,sys
res=sys.argv[1]
def row(f):
    s=json.load(open(f)); 
    if s.get("rate") is None: return None
    lo,hi=s["ci95"]; return (s["row"],s["k"],s["n"],100*s["rate"],100*lo,100*hi)
print(f"{'row':48s} {'k/n':>8s} {'rate':>6s}  CI95")
for pat in ["L2_*n200","L5_fullft_*n200","L5_lora_*n200","L5b_*layouts20-39"]:
    for f in sorted(glob.glob(os.path.join(res,pat,"summary.json"))):
        r=row(f)
        if r: print(f"{r[0]:48s} {r[1]:>3d}/{r[2]:<3d} {r[3]:6.1f}  [{r[4]:.1f},{r[5]:.1f}]")
print("reference (their harness): 98.8")
PY
echo "=== L4 CHAIN DONE $(date -u +%FT%TZ) ==="
