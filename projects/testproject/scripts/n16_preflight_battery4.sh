#!/usr/bin/env bash
# Preflight Stage B (failure signatures) + Stage C (exact scene), one defect
# per run. See sim_to_real_preflight_protocol_20260806.md.
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
EVAL=$PROJ/scripts/sim_policy_eval_instrumented.py
OUT=$PROJ/logs/preflight
mkdir -p "$OUT"
run() {
  name=$1; seed=$2; shift 2
  if [ -s "$OUT/$name.csv" ] && [ "$(wc -l < "$OUT/$name.csv")" -gt 2900 ]; then
    echo "[battery4] $name already complete, skipping"; return 0
  fi
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[battery4] === $name (seed $seed) $* ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$EVAL" --policy_type=gr00t-n16 --policy_port=5556 \
   --max_steps=3000 --seed=$seed "$@" --out="$OUT/$name.csv") > "$OUT/$name.log" 2>&1
  grep -q "wrote" "$OUT/$name.log" && echo "[battery4] $name OK" || echo "[battery4] $name FAILED"
}
run bgrSwap   5001 --img-bgr-swap
run noise8    5002 --img-noise=8
run blur3     5003 --img-blur=3
run jpeg40    5004 --img-jpeg=40
run gamma135  5005 --img-gamma=1.35
run stale2    5006 --obs-delay=2
run rot5      5007 --rotate-camera=5
run wristJit  5008 --jitter-wrist-camera=0.02,0,0
run oneOrange 5009 --park-oranges=2,3
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[battery4] complete"
