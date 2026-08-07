#!/usr/bin/env bash
# Addendum snapshots the user asked for: ARM color, ROOM (light) color, and a
# properly DIM scene (0.5 was barely visible; use 0.25). Waits for the
# baseline-variance control to finish first.
until grep -q "\[smbase\] complete" /home/kiran/sim/sm_baseline.log 2>/dev/null; do sleep 60; done
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
PC=$PROJ/scripts/sim_harness_positive_control.py
OUT=$PROJ/logs/sm_variations
SNAP=$OUT/snapshots
shot() {
  name=$1; shift
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[snap2] === $name ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$PC" --max_steps=70 --snapshot-dir="$SNAP" --snapshot-at=30,60 \
   "$@" --out="$OUT/snap_$name.csv") > "$OUT/snap_$name.log" 2>&1
  echo "[snap2] $name done"
}
shot greenArm  --tint="Robot:0.15,0.65,0.25"
shot warmRoom  --light-color=1.0,0.55,0.30
shot coolRoom  --light-color=0.55,0.70,1.0
shot dimRoom   --light-scale=0.25
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[snap2] complete"
