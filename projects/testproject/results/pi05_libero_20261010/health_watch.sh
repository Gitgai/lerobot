#!/usr/bin/env bash
# Health watchdog for the L4-noEMA run. Prints ONE line per check only when something crosses a
# threshold, plus a one-line heartbeat every hour. Run under the Monitor tool (tracked), not nohup.
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
PIDF=$RES/l4noema_train_fullft_noema_libero_20261014.pid; LOGF=$RES/l4noema_train_fullft_noema_libero_20261014.log
last_hb=0; last_step=0; last_t=$(date +%s)
while true; do
  now=$(date +%s); ts=$(date -u +%H:%MZ)
  # split on commas ONLY: the flag fields contain spaces ("Not Active")
  IFS=',' read -r t clk hw sw pc fan < <(nvidia-smi -i 1 --query-gpu=temperature.gpu,clocks.sm,clocks_event_reasons.hw_thermal_slowdown,clocks_event_reasons.sw_thermal_slowdown,clocks_event_reasons.sw_power_cap,fan.speed --format=csv,noheader,nounits | tr -d ' ')
  free_gb=$(df -BG --output=avail / | tail -1 | tr -dc 0-9); swap_gb=$(free -g | awk '/Swap/{print $3}'); avail_gb=$(free -g | awk '/Mem/{print $7}'); load=$(cut -d' ' -f1 /proc/loadavg)
  step=$(tr '\r' '\n' < "$LOGF" | grep -a "Progress on: [0-9]" | tail -1 | sed 's/.*Progress on: \([0-9.]*\)kit.*/\1/'); step=${step:-0}
  alive=0; kill -0 "$(cat "$PIDF" 2>/dev/null)" 2>/dev/null && alive=1
  msg=""
  [ "$alive" = 0 ] && msg="$msg TRAINER DEAD;"
  [ "${t:-0}" -ge 90 ] && msg="$msg GPU1 temp ${t}C;"
  [ "$hw" = "Active" ] && msg="$msg HW THERMAL SLOWDOWN;"
  [ "$sw" = "Active" ] && msg="$msg sw thermal slowdown;"
  [ "${free_gb:-0}" -lt 80 ] && msg="$msg root ${free_gb}GB free;"
  [ "${avail_gb:-99}" -lt 8 ] && msg="$msg host RAM ${avail_gb}GB avail;"
  [ "${swap_gb:-0}" -gt 20 ] && msg="$msg swap ${swap_gb}GB;"
  if [ "$alive" = 1 ] && [ $((now-last_t)) -ge 900 ]; then
    ds=$(python3 -c "print(round(($step-$last_step)*1000))" 2>/dev/null || echo 0)
    [ "$ds" -lt 60 ] && msg="$msg STALLED (${ds} steps in 15 min);"
    last_step=$step; last_t=$now
  fi
  [ -n "$msg" ] && echo "$ts ALERT:$msg  [step ${step}k gpu1 ${t}C ${clk}MHz fan ${fan}% powercap=$pc]"
  if [ $((now-last_hb)) -ge 3600 ]; then echo "$ts ok  step ${step}k  gpu1 ${t}C ${clk}MHz fan ${fan}% powercap=$pc  root ${free_gb}GB  ram ${avail_gb}GB avail swap ${swap_gb}GB load $load"; last_hb=$now; fi
  [ "$alive" = 0 ] && exit 0
  sleep 300
done
