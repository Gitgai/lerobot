#!/usr/bin/env bash
# Does the SCRIPTED state machine still complete under the scene variations?
# If yes, it can GENERATE demonstration episodes across all of them - the
# diverse-dataset plan for fine-tuning. One run per variation.
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
PC=$PROJ/scripts/sim_harness_positive_control.py
OUT=$PROJ/logs/sm_variations
mkdir -p "$OUT"
run() {
  name=$1; shift
  if [ -s "$OUT/$name.csv" ] && [ "$(wc -l < "$OUT/$name.csv")" -gt 2900 ]; then
    echo "[smvar] $name already complete, skipping"; return 0
  fi
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[smvar] === $name $* ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$PC" --max_steps=3000 "$@" --out="$OUT/$name.csv") > "$OUT/$name.log" 2>&1
  grep -q "wrote" "$OUT/$name.log" && echo "[smvar] $name OK" || echo "[smvar] $name FAILED"
}
run moved     --move-oranges=0.08,0.06,0
run scatter   --scatter-oranges=0.08,-0.05,-0.06,0.07,0.03,0.10
run plate10   --move-plate=0.10,0.05,0
run decoys    --add-decoys=2
run smallOrng --scale-oranges=0.75
run bigOrng   --scale-oranges=1.25
run tinted    --tint="Plate:0.15,0.25,0.85" --light-scale=0.5
run combo     --move-oranges=0.06,0.05,0 --move-plate=-0.08,0.06,0 --add-decoys=2
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[smvar] complete"
