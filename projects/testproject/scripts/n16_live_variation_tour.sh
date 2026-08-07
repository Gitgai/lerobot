#!/usr/bin/env bash
# N1.6 live variation tour - the user watches the WORKING POLICY handle every
# scene variation on the desktop before the hardware attempt. Doubles as the
# n=2 second measurement for the robustness campaign's n=1 conditions.
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
EVAL=$PROJ/scripts/sim_policy_eval_instrumented.py
OUT=$PROJ/logs/robustness
run() {
  name=$1; seed=$2; shift 2
  [ -s "$OUT/live_$name.csv" ] && [ "$(wc -l < "$OUT/live_$name.csv")" -gt 2900 ] && { echo "[tour] $name done already"; return 0; }
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[tour] === NOW SHOWING: $name ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$EVAL" --policy_type=gr00t-n16 --policy_port=5556 \
   --max_steps=3000 --seed=$seed "$@" --out="$OUT/live_$name.csv") > "$OUT/live_$name.log" 2>&1
  grep -q "wrote" "$OUT/live_$name.log" && echo "[tour] $name OK" || echo "[tour] $name FAILED"
}
run tinted    6001 --tint="Plate:0.15,0.25,0.85;counter_main_main_group:0.20,0.30,0.80"
run decoys    6002 --add-decoys=2
run greenArm  6003 --tint="Robot:0.15,0.65,0.25"
run smallOrng 6004 --scale-oranges=0.75
run dimLight  6005 --light-scale=0.35
run moved     6006 --move-oranges=0.08,0.06,0
run scatter   6007 --scatter-oranges=0.08,-0.05,-0.06,0.07,0.03,0.10
run plate10   6008 --move-plate=0.10,0.05,0
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[tour] complete"
