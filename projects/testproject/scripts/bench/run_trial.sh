#!/usr/bin/env bash
# One scored trial. $1 = trial number.
set -u
N=$1
V=~/PrakashProjects/lerobot/lerobot/.venv/bin/python
eval $($V ~/arm_ports.py 2>/dev/null | grep "^export")
eval "$(python3 ~/camfind.py 2>/dev/null)"
rm -rf ~/run_frames && mkdir -p ~/run_frames
cd ~/PrakashProjects/lerobot/lerobot
timeout 300 $V ~/n16_realarm_client.py \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=my_so101_follower \
  --robot.cameras="{front: {type: opencv, index_or_path: $FRONT_CAM, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: $WRIST_CAM, width: 640, height: 480, fps: 30}}" \
  --policy_host=192.168.194.220 --policy_port=5555 \
  --jpeg_quality=92 \
  --lang_instruction="pick up the orange and place it on the plate" \
  > ~/trial_${N}.log 2>&1
echo "  chunks: $(grep -c '^\[real\] chunk' ~/trial_${N}.log)"
grep -oE "rtt=[0-9]+ms" ~/trial_${N}.log | tr -d 'rtms=' | sort -n | awk '{a[NR]=$1} END{print "  median rtt: " a[int(NR/2)] " ms"}'
rm -rf ~/trial_${N}_frames && cp -r ~/run_frames ~/trial_${N}_frames
echo "  frames: $(ls ~/trial_${N}_frames | wc -l)"
