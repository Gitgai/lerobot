#!/usr/bin/env bash
# Read-only: is the trainer losing GPU time (graphics contexts, per-process SM share) or CPU time?
set -u
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
LOG=$RES/diag_gpu2.log
exec > "$LOG" 2>&1
echo "=== $(date -u +%FT%TZ) gpu/cpu contention snapshot ==="
echo "--- full nvidia-smi process table (C = compute, G = graphics, C+G = both)"
nvidia-smi | sed -n '/Processes/,$p'
echo "--- per-process SM / memory / encoder utilisation, 5 samples 1 s apart (pmon)"
nvidia-smi pmon -c 5 -s um 2>&1 | head -60
echo "--- device-level utilisation 5 samples"
nvidia-smi --query-gpu=utilization.gpu,utilization.memory,power.draw,clocks.sm --format=csv -l 1 -c 5 2>/dev/null | head -8
TP=$(cat "$RES/l3_train_lora_libero_20261010.pid")
echo "--- trainer $TP and its children: cpu%, state, allowed cpus"
ps -o pid,ppid,stat,pcpu,pmem,nlwp,args --ppid "$TP" -p "$TP" | cut -c1-140
echo "trainer Cpus_allowed_list: $(grep Cpus_allowed_list /proc/$TP/status)"
for c in $(pgrep -P "$TP"); do echo "child $c Cpus_allowed_list: $(grep Cpus_allowed_list /proc/$c/status | cut -f2)  state: $(awk '/^State/{print $2}' /proc/$c/status)"; done
echo "--- flight processes allowed cpus"
for p in $(pgrep -f '[d]ynus_node|[g]zserver'); do echo "pid $p $(grep Cpus_allowed_list /proc/$p/status | cut -f2) $(ps -o pcpu= -p $p)% $(ps -o comm= -p $p)"; done
echo "--- per-core busy % over 3 s (mpstat if present, else /proc/stat delta)"
if command -v mpstat >/dev/null; then mpstat -P ALL 3 1 | tail -40; else
  read -r -a a < <(grep '^cpu ' /proc/stat); sleep 3; read -r -a b < <(grep '^cpu ' /proc/stat)
  idle=$(( b[4]-a[4] )); tot=0; for i in 1 2 3 4 5 6 7 8; do tot=$(( tot + b[i]-a[i] )); done
  echo "all-core busy: $(( 100*(tot-idle)/tot ))%"; fi
echo "--- load / mem / swap"
uptime; free -g | head -2; swapon --show | tail -2
echo "--- recent trainer step rate"
tr '\r' '\n' < "$RES/l3_train_lora_libero_20261010.log" | grep "Progress on" | tail -2
echo "=== done ==="
cd "$RES" && exec python3 -m http.server 8767 --bind 127.0.0.1
