#!/usr/bin/env bash
# 2026-10-15 16:54Z: the desktop app that hosted the Claude session was killed and took the whole
# process tree with it — trainer (setsid nohup was NOT enough: same cgroup), chain, watchdog —
# at step 14.7k; last checkpoint 12500. This script: --resume from the latest checkpoint as its
# own systemd USER unit (survives session/app kills), same recipe (bs 32, saves every 2500),
# then the unchanged scoring stage + three-row table. Run it under systemd-run too.
set -u
OPENPI=/home/kiran/sim/openpi; PROBE_PY=/home/kiran/sim/pi05-fullft-probe/.venv312/bin/python
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_noema; EXP=fullft_noema_libero_20261014; CKDIR=$OPENPI/checkpoints/$CFG/$EXP
export TMPDIR=/home/kiran/tmp TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1
LOG=$RES/l4noema_chain.log; exec >> "$LOG" 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
TRAIN_LOG=$RES/l4noema_train_${EXP}.log; PIDF=$RES/l4noema_train_${EXP}.pid

step "RESUME from $(ls -d "$CKDIR"/[0-9]* | xargs -n1 basename | sort -n | tail -1): $CFG bs 32, saves every 2500, GPU 1, as unit l4noema-train"
echo "disk: $(df -h / | awk 'NR==2{print $4}') free; need $(( (12 - $(ls -d "$CKDIR"/[0-9]* | wc -l)) * 31 )) GB more"
cd "$OPENPI"
systemctl --user reset-failed l4noema-train.service 2>/dev/null
systemd-run --user --unit l4noema-train --collect --working-directory="$OPENPI" \
  -p StandardOutput=append:"$TRAIN_LOG" -p StandardError=append:"$TRAIN_LOG" \
  -E CUDA_VISIBLE_DEVICES=1 -E XLA_PYTHON_CLIENT_PREALLOCATE=false -E XLA_PYTHON_CLIENT_MEM_FRACTION=0.95 \
  -E TMPDIR=/home/kiran/tmp -E TOKENIZERS_PARALLELISM=false -E HF_HUB_OFFLINE=1 -E HOME=/home/kiran \
  "$OPENPI/.venv/bin/python" scripts/train.py "$CFG" --exp-name "$EXP" --resume --batch-size 32 \
  --save-interval 2500 --keep-period 2500 --log-interval 100 --no-wandb-enabled || { echo "systemd-run failed"; exit 5; }
sleep 3; TPID=$(systemctl --user show -p MainPID --value l4noema-train.service); echo "$TPID" > "$PIDF"; echo "trainer pid $TPID (unit l4noema-train) log $TRAIN_LOG"
( while kill -0 "$TPID" 2>/dev/null; do echo "$(date -u +%FT%TZ) $(nvidia-smi -i 1 --query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits)"; sleep 30; done ) >> "$RES/l4noema_train_${EXP}_gpu.txt" 2>/dev/null &
sleep 420
kill -0 "$TPID" 2>/dev/null && echo "trainer alive after 420 s" || { echo "trainer EXITED early:"; tail -30 "$TRAIN_LOG"; exit 4; }
tr '\r' '\n' < "$TRAIN_LOG" | grep -aE "Resum|restor|Progress on" | tail -3

step "waiting for training to end"
while kill -0 "$TPID" 2>/dev/null; do sleep 300; done
echo "trainer exited $(date -u +%FT%TZ); checkpoints: $(ls -d "$CKDIR"/[0-9]* 2>/dev/null | xargs -n1 basename | sort -n | tr '\n' ' ')"
sleep 30

step "score every checkpoint (server on GPU 0, L2 loop, layouts 0-19, n=200)"
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl PYTHONPATH=$OPENPI/packages/openpi-client/src
PORT=8006
for S in $(ls -d "$CKDIR"/[0-9]* | xargs -n1 basename | sort -n); do
  OUT=$RES/L5_${EXP}_step${S}_spatial_n200
  [ -f "$OUT/summary.json" ] && grep -q '"wall_s"' "$OUT/summary.json" && { echo "step $S already scored"; continue; }
  CUDA_VISIBLE_DEVICES=0 XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.45 \
    "$OPENPI/.venv/bin/python" scripts/serve_policy.py --port $PORT policy:checkpoint --policy.config "$CFG" --policy.dir "$CKDIR/$S" > "$RES/l4noema_server_${S}.log" 2>&1 & SRV=$!
  for i in $(seq 1 90); do "$PROBE_PY" -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',$PORT)))" && break; kill -0 $SRV 2>/dev/null || { echo "server died for $S"; tail -5 "$RES/l4noema_server_${S}.log"; break; }; sleep 5; done
  kill -0 $SRV 2>/dev/null || continue
  "$PROBE_PY" "$RES/l2_eval_openpi.py" --suite libero_spatial --trials-per-task 20 --port $PORT --out "$OUT" --row "openpi_fullft_noema_step${S}"
  echo "step $S eval rc=$?"; kill $SRV 2>/dev/null; sleep 3
done

step "THREE-ROW TABLE"
"$PROBE_PY" - "$RES" <<'PY'
import json,glob,os,sys
res=sys.argv[1]
def row(f):
    s=json.load(open(f))
    if s.get("rate") is None: return None
    lo,hi=s["ci95"]; return (s["row"],s["k"],s["n"],100*s["rate"],100*lo,100*hi)
print(f"{'row':48s} {'k/n':>8s} {'rate':>6s}  CI95")
for pat in ["L2_*n200","L5_fullft_noema_libero_20261014_*n200","L5_lora_*n200","L5b_*layouts20-39"]:
    for f in sorted(glob.glob(os.path.join(res,pat,"summary.json"))):
        r=row(f)
        if r: print(f"{r[0]:48s} {r[1]:>3d}/{r[2]:<3d} {r[3]:6.1f}  [{r[4]:.1f},{r[5]:.1f}]")
print("reference (their harness): 98.8")
PY
echo "=== L4NOEMA CHAIN DONE $(date -u +%FT%TZ) ==="
