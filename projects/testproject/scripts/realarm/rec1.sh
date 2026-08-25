#!/usr/bin/env bash
# Record ONE plate demo. NO automatic retry.
#
# Retrying automatically (removed 2026-08-25) recorded an episode while the
# operator was still resetting - and because the previous crash had left the
# orange IN the gripper, that episode showed the arm 'holding' from frame 0.
# It looked like a good demo to every check except the first-hold test. One
# attempt per go: the operator always knows when the arm is live.
set -u
V=~/PrakashProjects/lerobot/lerobot/.venv/bin/python
eval $($V ~/arm_ports.py)
if [ -z "${FOLLOWER_PORT:-}" ] || [ -z "${LEADER_PORT:-}" ]; then
  echo "  AN ARM IS OFF THE BUS - replug or wait, then try again"; exit 1
fi
timeout 90 $V ~/record_wrapper.py \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=my_so101_follower \
  --robot.cameras="{front: {type: opencv, index_or_path: /dev/video0, width: 640, height: 480, fps: 30}, wrist: {type: http, url: http://127.0.0.1:8092/frame, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader --teleop.port=$LEADER_PORT --teleop.id=my_so101_leader \
  --dataset.repo_id=local/plate_demos --dataset.root=$HOME/plate_demos --resume=true \
  --dataset.single_task="pick up the orange and place it on the plate" \
  --dataset.num_episodes=1 --dataset.episode_time_s=25 --dataset.reset_time_s=3 \
  --dataset.vcodec=h264 --dataset.push_to_hub=false --display_data=false > /tmp/rec.log 2>&1
rc=$?
if [ $rc -eq 0 ]; then
  echo "  recorded cleanly"
else
  echo "  DROPPED ($(grep -oE 'Errno [0-9]+' /tmp/rec.log | head -1)) - the episode may still have saved;"
  echo "  RESET THE SCENE (orange out of the gripper, back on the table) before the next go"
fi
