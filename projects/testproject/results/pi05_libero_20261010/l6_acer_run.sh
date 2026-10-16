#!/usr/bin/env bash
# L6: run the 200-episode LIBERO Spatial evaluation on the ACER against the policy served on AI90.
# Usage on the Acer:  bash l6_acer_run.sh [trials-per-task=20] [task-ids] [trials]
# Results land in ~/l6_libero_remote/L6_lora20k_remote_acer_spatial_n200 and are copied back to AI90.
set -u
AI90=192.168.194.220; PORT=8007; BASE=$HOME/l6_libero_remote; cd "$BASE"; . .venv/bin/activate
export PATH=$HOME/.local/bin:$PATH PYTHONPATH=$BASE/openpi-client/src${PYTHONPATH:+:$PYTHONPATH}
export $(cat gl_backend | sed 's/ works//'); export PYOPENGL_PLATFORM=${MUJOCO_GL}; export TOKENIZERS_PARALLELISM=false
TPT=${1:-20}; TASKS=${2:-}; TRIALS=${3:-}
OUT=$BASE/L6_lora20k_remote_acer_spatial_n$((TPT*10)); LOG=$BASE/l6_acer.log; mkdir -p "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "=== $(date -u +%FT%TZ) G1 network: $(ping -c 5 -q $AI90 | tail -1)"
python -c "import socket,sys;s=socket.socket();s.settimeout(5);sys.exit(s.connect_ex(('$AI90',$PORT)))" && echo "policy port $PORT open" || { echo "policy port CLOSED"; exit 1; }
echo "=== $(date -u +%FT%TZ) G3/G4 eval: tasks=${TASKS:-all} trials=${TRIALS:-0..$((TPT-1))}"
python "$BASE/l2_eval_openpi.py" --suite libero_spatial --trials-per-task "$TPT" --host "$AI90" --port "$PORT" --seed 7 --replan-steps 5 \
  --out "$OUT" --row lora20k_remote_acer ${TASKS:+--task-ids "$TASKS"} ${TRIALS:+--trials "$TRIALS"}
echo "eval rc=$?  $(date -u +%FT%TZ) post-run ping: $(ping -c 5 -q $AI90 | tail -1)"
python - "$OUT" <<'PY'
import json,sys,statistics as st
d=json.load(open(sys.argv[1]+"/summary.json")); f=[json.loads(l) for l in open(sys.argv[1]+"/per_episode.jsonl")]
inf=[e["infer_s_mean"] for e in f]; print(f"RESULT {d['k']}/{d['n']} = {100*d['rate']:.1f}%  CI {[round(100*x,1) for x in d['ci95']]}  wall {d['wall_s']:.0f}s")
print(f"per-call latency: median {1000*st.median(inf):.0f} ms  p95 {1000*sorted(inf)[int(0.95*len(inf))-1]:.0f} ms  (local AI90: ~60 ms)")
PY
echo "=== copying results back to AI90"; scp -rq "$OUT" "$LOG" kiran@$AI90:/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010/ && echo "copied"
