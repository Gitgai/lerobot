#!/usr/bin/env bash
# pi05_sim_varied eval runner (3 seeds, --radian-actions salvage path).
# Prereq: pi05 policy server on :8080. Context: docs/pi05_active_work_tracker.md section 13.
for s in 1001 1002 1003; do
  for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
  sleep 3
  (cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
   ~/sim/leisaac-venv/bin/python -u /home/kiran/projects/git/nvidia/lerobot/projects/testproject/scripts/sim_policy_eval_instrumented.py \
   --policy_type=lerobot-pi05 --policy_port=8080 \
   --policy_checkpoint_path=$HOME/lerobot_assets/checkpoints/pi05_sim_varied/checkpoints/030000/pretrained_model \
   --camera-rename="front:base_0_rgb,wrist:left_wrist_0_rgb" --radian-actions --max_steps=3000 --seed=$s \
   --out=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/logs/pi05svR_run_$s.csv) > /home/kiran/sim/pi05svR_run_$s.log 2>&1
  echo "seed $s done"
done
for p in $(pgrep -f "leisaac-venv/bin/python"); do [ "$(cat /proc/$p/comm 2>/dev/null)" = python ] && kill -9 $p; done
echo ALL-DONE
