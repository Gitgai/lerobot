#!/usr/bin/env bash
# Operator-approved 2026-10-10: stop the LeRobot policy server from the Oct 7
# pi05-rtc-remote-draft folder (pid 3307624, ~10 GB VRAM, up ~3.5 days) so the
# L3 LoRA run can use batch 32. Kills ONLY a process whose command line matches
# both 'lerobot_policy_server' and 'pi05-rtc-remote-draft'. Nothing else.
set -u
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
LOG=$RES/stop_stale_policy_server.log
exec > >(tee -a "$LOG") 2>&1
echo "=== $(date -u +%FT%TZ) before ==="
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
KILLED=0
for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader); do
  args=$(ps -o args= -p "$p" 2>/dev/null)
  case "$args" in
    *lerobot_policy_server*pi05-rtc-remote-draft*)
      echo "match pid $p: $(ps -o etime= -p "$p") :: ${args:0:200}"
      kill "$p" && echo "SIGTERM sent to $p"
      for i in $(seq 1 10); do kill -0 "$p" 2>/dev/null || break; sleep 1; done
      if kill -0 "$p" 2>/dev/null; then kill -9 "$p" && echo "SIGKILL sent to $p"; sleep 2; fi
      KILLED=$((KILLED+1));;
    *) echo "leave pid $p: ${args:0:120}";;
  esac
done
echo "killed $KILLED process(es)"
sleep 3
echo "=== $(date -u +%FT%TZ) after ==="
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
echo "=== done ==="
cd "$RES" && exec python3 -m http.server 8767 --bind 127.0.0.1
