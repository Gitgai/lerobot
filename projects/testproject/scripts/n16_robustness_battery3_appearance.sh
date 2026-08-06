#!/usr/bin/env bash
# Battery 3: APPEARANCE variations - colors, lighting, decoys, extra plate,
# object scale. Waits for battery 2 to finish first.
until grep -q "\[battery2\] complete" /home/kiran/sim/n16_battery2.log 2>/dev/null; do sleep 60; done
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
EVAL=$PROJ/scripts/sim_policy_eval_instrumented.py
OUT=$PROJ/logs/robustness
run() {
  name=$1; seed=$2; shift 2
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[battery3] === $name (seed $seed) $* ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$EVAL" --policy_type=gr00t-n16 --policy_port=5556 \
   --max_steps=3000 --seed=$seed "$@" --out="$OUT/$name.csv") > "$OUT/$name.log" 2>&1
  grep -q "wrote" "$OUT/$name.log" && echo "[battery3] $name OK" || echo "[battery3] $name FAILED"
}
run bluePlate  4001 --tint="Plate:0.15,0.25,0.85"
run greenArm   4002 --tint="Robot:0.15,0.65,0.25"
run decoys     4003 --add-decoys=2
run twoPlates  4004 --add-plate=0.15,-0.12
run dimLight   4005 --light-scale=0.35
run warmLight  4006 --light-color=1.0,0.62,0.35
run smallOrng  4007 --scale-oranges=0.75
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[battery3] complete"
