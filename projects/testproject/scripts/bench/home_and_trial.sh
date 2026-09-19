#!/usr/bin/env bash
set -u
N=$1
V=~/PrakashProjects/lerobot/lerobot/.venv/bin/python
cd ~/PrakashProjects/lerobot/lerobot
eval $($V ~/arm_ports.py 2>/dev/null | grep "^export")
FOLLOWER_PORT=${FOLLOWER_PORT:-} $V ~/clear_overload.py 2>&1 | sed "s/^/  [clear] /"
homed=0
for a in 1 2 3; do
  if $V ~/home_arm.py >~/home_${N}.log 2>&1; then echo "  homed (attempt $a, $(grep -oE "worst joint error [0-9.]+ deg" ~/home_${N}.log | tail -1))"; homed=1; break; fi
  echo "  home attempt $a failed, clearing + retrying..."; FOLLOWER_PORT=${FOLLOWER_PORT:-} $V ~/clear_overload.py >/dev/null 2>&1; sleep 2
done
[ $homed -eq 1 ] || { echo "  HOMING FAILED 3x - aborting (check follower)"; exit 1; }
bash ~/run_trial.sh $N
