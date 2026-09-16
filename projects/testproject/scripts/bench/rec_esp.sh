#!/usr/bin/env bash
# Record demonstrations through the ESP32 wrist camera.
#
# WHY: the model has only ever seen the OV5647's wrist view, and every arm
# trial since the camera changed has failed. Rather than keep matching the new
# camera to the old pictures, teach the model what the new camera looks like.
#
#   $1 = number of episodes    $2 = dataset name    $3 = instruction
#
# Two datasets this session:
#   esp_orange   20 eps  "pick up the orange and place it on the plate"
#   esp_apple    10 eps  "pick up the apple and place it on the plate"
#
# NOTE on the apple set (operator's choice, 2026-09-10): the apple is recorded
# ALONE, not alongside the orange. This teaches the apple as an object but will
# NOT teach the model to read the instruction - with only one fruit in view the
# picture already says which to pick, so the words stay redundant. That is the
# same mechanism measured on 2026-08-26 (wrong-sentence penalty -0.04). A
# language-grounding set needs BOTH fruits present with the command choosing.
set -u
V=~/PrakashProjects/lerobot/lerobot/.venv/bin/python
N=${1:?episodes}; NAME=${2:?dataset}; TASK=${3:?instruction}
ROOT=$HOME/$NAME
# cameras BY NAME - the device numbers move between replugs
CAMS=$(python3 ~/camfind.py 2>/dev/null) || { echo "  CAMERA MISSING - refusing to record"; python3 ~/camfind.py; exit 1; }
eval "$CAMS"
echo "  front $FRONT_CAM   wrist $WRIST_CAM"

eval $($V ~/arm_ports.py | grep "^export")
[ -z "${FOLLOWER_PORT:-}" ] && { echo "  FOLLOWER off the bus"; exit 1; }
[ -z "${LEADER_PORT:-}" ]   && { echo "  LEADER off the bus";   exit 1; }

RESUME=""
# resume only if EPISODES exist - a crashed attempt leaves an empty stub
# directory, and --resume on that sends lerobot to HuggingFace (401).
HAVE=$(python3 ~/epcount.py "$ROOT")
if [ "$HAVE" -gt 0 ]; then
  RESUME="--resume=true"
  echo "  $ROOT already holds $HAVE episode(s) - appending"
elif [ -e "$ROOT" ]; then
  # empty stub from a crashed attempt: --resume on it sends lerobot to
  # HuggingFace (401). Safe to clear ONLY because epcount says 0 episodes.
  echo "  clearing empty stub $ROOT"
  rm -rf "$ROOT"
fi
echo "  recording $N episode(s) into $ROOT"
echo "  task: \"$TASK\""

HF_HUB_OFFLINE=1 $V ~/record_wrapper.py \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=my_so101_follower \
  --robot.cameras="{front: {type: opencv, index_or_path: $FRONT_CAM, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: $WRIST_CAM, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader --teleop.port=$LEADER_PORT --teleop.id=my_so101_leader \
  --dataset.repo_id=local/$NAME --dataset.root=$ROOT \
  --dataset.single_task="$TASK" \
  --dataset.num_episodes=$N --dataset.episode_time_s=30 --dataset.reset_time_s=12 \
  --dataset.vcodec=h264 --dataset.push_to_hub=false --display_data=false $RESUME
echo "  --- $NAME now holds $(python3 ~/epcount.py "$ROOT") episodes ---"
