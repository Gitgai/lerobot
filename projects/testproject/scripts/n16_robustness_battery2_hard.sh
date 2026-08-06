#!/usr/bin/env bash
# Waits for battery 1, then runs the HARD scene variations.
until grep -q "\[battery\] complete" /home/kiran/sim/n16_battery.log 2>/dev/null; do sleep 60; done
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
EVAL=$PROJ/scripts/sim_policy_eval_instrumented.py
OUT=$PROJ/logs/robustness
run() {
  name=$1; seed=$2; shift 2
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[battery2] === $name (seed $seed) $* ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$EVAL" --policy_type=gr00t-n16 --policy_port=5556 \
   --max_steps=3000 --seed=$seed "$@" --out="$OUT/$name.csv") > "$OUT/$name.log" 2>&1
  grep -q "wrote" "$OUT/$name.log" && echo "[battery2] $name OK" || echo "[battery2] $name FAILED"
}
run plate10   3001 --move-plate=0.10,0.05,0
run scatter   3002 --scatter-oranges=0.08,-0.05,-0.06,0.07,0.03,0.10
run cam2cm    3003 --jitter-camera=0.02,0,0
run cam5cm    3004 --jitter-camera=0.05,0,-0.03
run combo     3005 --move-oranges=0.07,0.05,0 --move-plate=-0.08,0.06,0
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[battery2] complete"
