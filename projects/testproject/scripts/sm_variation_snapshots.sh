#!/usr/bin/env bash
# Capture 2 reference images (front+wrist) of EVERY scene variation - fast
# 70-step runs, queued behind the main SM variation battery.
until grep -q "\[smvar\] complete" /home/kiran/sim/sm_variations.log 2>/dev/null; do sleep 60; done
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
PC=$PROJ/scripts/sim_harness_positive_control.py
OUT=$PROJ/logs/sm_variations
SNAP=$OUT/snapshots
mkdir -p "$SNAP"
shot() {
  name=$1; shift
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[snap] === $name ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$PC" --max_steps=70 --snapshot-dir="$SNAP" --snapshot-at=30,60 \
   "$@" --out="$OUT/snap_$name.csv") > "$OUT/snap_$name.log" 2>&1
  echo "[snap] $name done"
}
shot canonical
shot moved     --move-oranges=0.08,0.06,0
shot scatter   --scatter-oranges=0.08,-0.05,-0.06,0.07,0.03,0.10
shot plate10   --move-plate=0.10,0.05,0
shot decoys    --add-decoys=2
shot smallOrng --scale-oranges=0.75
shot bigOrng   --scale-oranges=1.25
shot tinted    --tint="Plate:0.15,0.25,0.85" --light-scale=0.5
shot combo     --move-oranges=0.06,0.05,0 --move-plate=-0.08,0.06,0 --add-decoys=2
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[snap] complete"
