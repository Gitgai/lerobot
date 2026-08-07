#!/usr/bin/env bash
# THE CONTROL the variation battery should have had: the SM's own run-to-run
# variance on the CANONICAL scene. tinted (appearance-only, invisible to a
# GT-driven script) scored 1/3 - logically impossible as a variation effect -
# so the battery's n=1-per-condition design is confounded by SM variance.
PROJ=/home/kiran/projects/git/nvidia/lerobot/projects/testproject
PC=$PROJ/scripts/sim_harness_positive_control.py
OUT=$PROJ/logs/sm_variations
for i in 1 2 3; do
  [ -s "$OUT/canonical_v$i.csv" ] && [ "$(wc -l < "$OUT/canonical_v$i.csv")" -gt 2900 ] && continue
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  echo "[smbase] === canonical_v$i ==="
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u "$PC" --max_steps=3000 --out="$OUT/canonical_v$i.csv") > "$OUT/canonical_v$i.log" 2>&1
  grep -q "wrote" "$OUT/canonical_v$i.log" && echo "[smbase] canonical_v$i OK" || echo "[smbase] canonical_v$i FAILED"
done
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo "[smbase] complete"
