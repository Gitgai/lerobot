#!/usr/bin/env bash
# REAL-MIMIC battery: recreate the real rig's content inside sim and measure
# what each ingredient costs N1.6. Plan + decision rules (agreed BEFORE
# results): docs/n16_realmimic_sim_battery_20260808.md
#
# PREREQS (manual, in order):
#   1. Pi0.5 policy server STOPPED (18.4 GB freed - it OOMs the recorder)
#   2. N1.6 server on :5556      (N16_REBUILD_RUNBOOK.md section 3)
# Run: nohup bash n16_realmimic_battery.sh > /home/kiran/sim/n16_realmimic.log 2>&1 &
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
EVAL=$PROJ/scripts/sim_policy_eval_instrumented.py
OUT=$PROJ/logs/realmimic
mkdir -p "$OUT"

TOMATO="Orange001:0.75,0.15,0.10;Orange002:0.75,0.15,0.10;Orange003:0.75,0.15,0.10"
WOOD="counter_main_main_group:0.35,0.22,0.12"
PAPER="Plate:0.92,0.90,0.88"

run() {
  name=$1; seed=$2; shift 2
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[realmimic] === $name (seed $seed) $* ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$EVAL" --policy_type=gr00t-n16 --policy_port=5556 \
   --max_steps=3000 --seed=$seed "$@" --out="$OUT/${name}_s${seed}.csv") > "$OUT/${name}_s${seed}.log" 2>&1
  grep -q "wrote" "$OUT/${name}_s${seed}.log" && echo "[realmimic] ${name}_s${seed} OK" || echo "[realmimic] ${name}_s${seed} FAILED"
}

# Regression gate first: one canonical run. If this is not ~3/3 the serving
# stack is broken - fix that before reading ANY variation result.
run canonical 1001

for seed in 1001 1002 1003; do
  run tomatoRed  $seed --tint="$TOMATO"
  run woodTable  $seed --tint="$WOOD"
  run paperPlate $seed --tint="$PAPER"
  run camOff     $seed --jitter-camera=0.05,0.02,-0.03 --rotate-camera=5
  run REALMIMIC  $seed --tint="$TOMATO;$WOOD;$PAPER" --jitter-camera=0.05,0.02,-0.03 --rotate-camera=5
done

for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[realmimic] complete"
