#!/usr/bin/env bash
# The overnight batch matrix from sm_data_generation_track_20260806.md 6.2.
# Each batch: fresh HDF5, distinct look, N successful episodes (capped by
# max_attempts so no batch can eat the night). Sequential - one sim at a time.
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
GEN=$PROJ/scripts/sm_generate_varied.py
OUT=$HOME/sim/leisaac-src/datasets/varied     # OUTSIDE the git tree - artifacts
DEMOS="${DEMOS:-6}"
CAP="${CAP:-15}"
LOG=$HOME/sim/gen_batches.log
run() {
  name=$1; seed=$2; shift 2
  [ -s "$OUT/$name.hdf5" ] && { echo "[batches] $name exists, skipping"; return 0; }
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[batches] === $name (seed $seed) $* ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$GEN" --dataset_file "$OUT/$name.hdf5" \
   --num_demos "$DEMOS" --max_attempts "$CAP" --seed "$seed" "$@") > "$HOME/sim/gen_$name.log" 2>&1
  grep -E "\[gen\] DONE" "$HOME/sim/gen_$name.log" | tail -1
}
run b1_canonical 101
run b2_counterA  102 --tint="counter_main_main_group:0.20,0.30,0.80;wall_room:0.20,0.70,0.30"
run b3_counterB  103 --tint="counter_main_main_group:0.55,0.35,0.20;cab_main_main_group:0.85,0.20,0.20;cab_1_main_group:0.90,0.75,0.15"
run b4_plate     104 --tint="Plate:0.15,0.25,0.85;counter_main_main_group:0.75,0.75,0.70"
run b5_arm       105 --tint="Robot:0.15,0.65,0.25;counter_main_main_group:0.30,0.30,0.35"
run b6_decoys    106 --add-decoys=2
run b7_scale     107 --scale-oranges=0.8 --tint="counter_main_main_group:0.60,0.55,0.45"
run b8_geometry  108 --move-oranges=0.06,0.05,0 --move-plate=-0.08,0.06,0 --tint="counter_main_main_group:0.25,0.45,0.55"
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[batches] ALL DONE"
du -sh "$OUT"
