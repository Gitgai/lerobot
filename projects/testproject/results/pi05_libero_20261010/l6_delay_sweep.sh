#!/usr/bin/env bash
# L6: success vs injected inference latency, LIBERO Spatial, LoRA 20k served on :8007 (unit l6-remote-server).
# Gate: realtime D=0 must be inside the frozen CI (>=195/200 ~ 97.2%) before the sweep continues.
set -u
R=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
PY=/home/kiran/sim/pi05-fullft-probe/.venv312/bin/python
export TMPDIR=/home/kiran/tmp MUJOCO_GL=egl PYOPENGL_PLATFORM=egl PYTHONPATH=/home/kiran/sim/openpi/packages/openpi-client/src HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
exec >> "$R/l6_delay_sweep.log" 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
run(){ D=$1; OUT=$R/L6_delay${D}ms_lora20k_spatial_n200
  [ -f "$OUT/summary.json" ] && grep -q '"wall_s"' "$OUT/summary.json" && { echo "D=$D already done"; return 0; }
  rm -rf "$OUT"; step "D=${D} ms"
  "$PY" "$R/l2_eval_openpi.py" --suite libero_spatial --trials-per-task 20 --host 127.0.0.1 --port 8007 --seed 7 --replan-steps 5 \
     --latency-mode realtime --inject-delay-ms "$D" --stale-policy skip --out "$OUT" --row "lora20k_delay${D}ms" | grep -E "RESULT|=== task"
  echo "D=$D rc=${PIPESTATUS[0]}"; }
step "G1 gate: realtime D=0 must match frozen (199/200)"
run 0
K=$("$PY" -c "import json;print(json.load(open('$R/L6_delay0ms_lora20k_spatial_n200/summary.json'))['k'])" 2>/dev/null || echo 0)
echo "gate k=$K"; [ "$K" -ge 195 ] || { echo "GATE FAILED (k=$K < 195): mode is not faithful at D=0 — STOP"; echo "=== L6 SWEEP ABORTED"; exit 2; }
for D in 100 250 500 1000; do run $D; done
step "TABLE: success vs injected latency (LoRA 20k, Spatial, n=200, realtime mode, stale=skip)"
"$PY" - "$R" <<'PY'
import json,sys,glob,re,statistics as st
R=sys.argv[1]; print(f"{'delay':>7s} {'steps':>5s} {'k/n':>8s} {'rate':>6s}  CI95          holds/ep  steps/ep(succ)")
for f in sorted(glob.glob(R+"/L6_delay*ms_lora20k_spatial_n200/summary.json"), key=lambda p:int(re.findall(r"delay(\d+)ms",p)[0])):
    s=json.load(open(f)); e=[json.loads(l) for l in open(f.replace("summary.json","per_episode.jsonl"))]
    lo,hi=s["ci95"]; succ=[x["steps"] for x in e if x["success_done"]]
    print(f"{s['inject_delay_ms']:5.0f}ms {s['delay_steps']:5d} {s['k']:3d}/{s['n']:<3d} {100*s['rate']:6.1f}  [{100*lo:.1f},{100*hi:.1f}]  {st.mean(x['n_hold'] for x in e):7.1f}  {st.mean(succ) if succ else float('nan'):8.1f}")
print("frozen protocol reference, same policy/layouts: 199/200 = 99.5%")
PY
echo "=== L6 SWEEP DONE $(date -u +%FT%TZ)"
