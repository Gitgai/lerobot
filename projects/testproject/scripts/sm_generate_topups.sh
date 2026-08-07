#!/usr/bin/env bash
# Top up the two under-represented looks from round 1 (b4 blue plate 1 ep,
# b8 moved geometry 1 ep). New seeds, new files; round-1 data untouched.
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
GEN=$PROJ/scripts/sm_generate_varied.py
OUT=$HOME/sim/leisaac-src/datasets/varied
run() {
  name=$1; seed=$2; shift 2
  [ -s "$OUT/$name.hdf5" ] && { echo "[topup] $name exists, skipping"; return 0; }
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[topup] === $name (seed $seed) ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$GEN" --dataset_file "$OUT/$name.hdf5" \
   --num_demos 5 --max_attempts 25 --seed "$seed" --export all "$@") > "$HOME/sim/gen_$name.log" 2>&1
  grep -E "\[gen\] DONE" "$HOME/sim/gen_$name.log" | tail -1
}
run b4_plate_topup    204 --tint="Plate:0.15,0.25,0.85;counter_main_main_group:0.75,0.75,0.70"
run b8_geometry_topup 208 --move-oranges=0.06,0.05,0 --move-plate=-0.08,0.06,0 --tint="counter_main_main_group:0.25,0.45,0.55"
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[topup] ALL DONE"
