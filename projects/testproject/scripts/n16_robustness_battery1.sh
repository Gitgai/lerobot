#!/usr/bin/env bash
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
EVAL=$PROJ/scripts/sim_policy_eval_instrumented.py
OUT=$PROJ/logs/robustness
run() {  # name seed extra...
  name=$1; seed=$2; shift 2
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[battery] === $name (seed $seed) $* ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$EVAL" --policy_type=gr00t-n16 --policy_port=5556 \
   --max_steps=3000 --seed=$seed "$@" --out="$OUT/$name.csv") > "$OUT/$name.log" 2>&1
  grep -q "wrote" "$OUT/$name.log" && echo "[battery] $name OK" || echo "[battery] $name FAILED"
}
run seedA 2001
run seedB 2002
run seedC 2003
run movedA 2004 --move-oranges=0.05,0.05,0
run movedB 2005 --move-oranges=-0.05,0.08,0
run movedC 2006 --move-oranges=0.10,0.0,0
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[battery] complete"
