#!/usr/bin/env bash
# Third measurement of the four high-variance conditions -> n=3 each,
# per the project rule that contact-rich sim needs n>=3 to be quotable.
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
EVAL=$PROJ/scripts/sim_policy_eval_instrumented.py
OUT=$PROJ/logs/robustness
run() {
  name=$1; seed=$2; shift 2
  [ -s "$OUT/r3_$name.csv" ] && [ "$(wc -l < "$OUT/r3_$name.csv")" -gt 2900 ] && { echo "[r3] $name done"; return 0; }
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[r3] === NOW SHOWING: $name ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$EVAL" --policy_type=gr00t-n16 --policy_port=5556 \
   --max_steps=3000 --seed=$seed "$@" --out="$OUT/r3_$name.csv") > "$OUT/r3_$name.log" 2>&1
  grep -q "wrote" "$OUT/r3_$name.log" && echo "[r3] $name OK" || echo "[r3] $name FAILED"
}
run decoys  7001 --add-decoys=2
run moved   7002 --move-oranges=0.08,0.06,0
run scatter 7003 --scatter-oranges=0.08,-0.05,-0.06,0.07,0.03,0.10
run plate10 7004 --move-plate=0.10,0.05,0
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[r3] complete"
