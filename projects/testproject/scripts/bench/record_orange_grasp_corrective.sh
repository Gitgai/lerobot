#!/usr/bin/env bash
# Record one reviewed orange grasp-centering demonstration at a time.
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHON=${LEROBOT_PYTHON:-/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python}
NAME=${ORANGE_DEMO_NAME:-orange_grasp_corrective_ft4_20261108}
ROOT=${ORANGE_DEMO_ROOT:-/home/gaikwad-prakash/$NAME}
TASK="pick up the orange and place it on the plate"
ROBOT_CAL=/home/gaikwad-prakash/.cache/huggingface/lerobot/calibration/robots/so_follower/my_so101_follower.json
LEADER_CAL=/home/gaikwad-prakash/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/my_so101_leader.json

usage() {
  echo "Usage: $0 --check | --record"
  echo "  --check   validate devices, calibration, imports and camera frames; no arm motion"
  echo "  --record  run the same check, then record exactly one teleoperated episode"
}

MODE=${1:-}
if [[ "$MODE" != "--check" && "$MODE" != "--record" ]]; then
  usage
  exit 2
fi

[[ -x "$PYTHON" ]] || { echo "ERROR: LeRobot Python is missing: $PYTHON"; exit 1; }
[[ -f "$ROBOT_CAL" ]] || { echo "ERROR: follower calibration is missing: $ROBOT_CAL"; exit 1; }
[[ -f "$LEADER_CAL" ]] || { echo "ERROR: leader calibration is missing: $LEADER_CAL"; exit 1; }

eval "$("$PYTHON" "$SCRIPT_DIR/arm_ports.py" | grep '^export ')"
[[ -n "${FOLLOWER_PORT:-}" ]] || { echo "ERROR: follower controller is not present"; exit 1; }
[[ -n "${LEADER_PORT:-}" ]] || { echo "ERROR: leader controller is not present"; exit 1; }

CAMERA_ASSIGNMENTS=$("$PYTHON" "$SCRIPT_DIR/camfind.py")
eval "$CAMERA_ASSIGNMENTS"
[[ -n "${FRONT_CAM:-}" && -n "${WRIST_CAM:-}" ]] || { echo "ERROR: front or wrist camera is missing"; exit 1; }

"$PYTHON" - "$FRONT_CAM" "$WRIST_CAM" <<'PY'
import sys
import cv2
import numpy as np

for role, path in (("front", sys.argv[1]), ("wrist", sys.argv[2])):
    cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    frames = []
    usable = []
    # The C270 can emit black frames for roughly two seconds while automatic
    # exposure settles. Wait for real images instead of rejecting normal warm-up.
    for _ in range(120):
        ok, frame = cap.read()
        if ok and frame is not None:
            frames.append(frame)
            if float(np.mean(frame)) >= 5.0 and float(np.std(frame)) >= 3.0:
                usable.append(frame)
                if len(usable) >= 3:
                    break
    cap.release()
    if len(usable) < 3:
        raise SystemExit(
            f"ERROR: {role} camera {path} did not produce three usable frames "
            f"after {len(frames)} reads"
        )
    frame = usable[-1]
    if frame.shape[:2] != (480, 640):
        raise SystemExit(f"ERROR: {role} camera is {frame.shape[1]}x{frame.shape[0]}, expected 640x480")
    mean = float(np.mean(frame))
    std = float(np.std(frame))
    if mean < 5.0 or std < 3.0:
        raise SystemExit(f"ERROR: {role} camera frame appears blank (mean={mean:.1f}, std={std:.1f})")
    delta = float(np.mean(np.abs(usable[-1].astype(np.int16) - usable[-2].astype(np.int16))))
    print(f"OK camera {role}: {path}, 640x480, mean={mean:.1f}, std={std:.1f}, frame_delta={delta:.2f}")
PY

"$PYTHON" -c "from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig; from lerobot.scripts.lerobot_record import main; print('OK LeRobot recorder imports')"

BEFORE=$("$PYTHON" "$SCRIPT_DIR/epcount.py" "$ROOT")
if [[ -e "$ROOT" && ! -f "$ROOT/meta/info.json" ]]; then
  echo "ERROR: $ROOT exists but has no readable metadata; refusing to modify or delete it"
  exit 1
fi

echo "OK follower: $FOLLOWER_PORT"
echo "OK leader:   $LEADER_PORT"
echo "OK dataset:  $ROOT ($BEFORE existing episodes)"
echo "OK task:     $TASK"

if [[ "$MODE" == "--check" ]]; then
  echo "PREFLIGHT PASSED: no arm connection or motion was performed"
  exit 0
fi

RESUME_ARGS=()
if (( BEFORE > 0 )); then
  RESUME_ARGS+=(--resume=true)
fi

RERUN_BIN=/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/rerun
RERUN_GRPC_PORT=9882
RERUN_WEB_PORT=9116
if ! ss -ltn | grep -q ":$RERUN_GRPC_PORT "; then
  [[ -x "$RERUN_BIN" ]] || { echo "ERROR: Rerun executable is missing: $RERUN_BIN"; exit 1; }
  nohup "$RERUN_BIN" --serve-web --bind 127.0.0.1 \
    --port "$RERUN_GRPC_PORT" --web-viewer-port "$RERUN_WEB_PORT" \
    --server-memory-limit 1GB >/tmp/orange_grasp_rerun.log 2>&1 &
  echo $! >/tmp/orange_grasp_rerun.pid
  for _ in $(seq 1 40); do
    ss -ltn | grep -q ":$RERUN_GRPC_PORT " && break
    sleep 0.25
  done
fi
ss -ltn | grep -q ":$RERUN_GRPC_PORT " || { echo "ERROR: Rerun server did not start"; exit 1; }
LIVE_URL="http://127.0.0.1:$RERUN_WEB_PORT/?url=rerun%2Bhttp%3A%2F%2F127.0.0.1%3A$RERUN_GRPC_PORT%2Fproxy"
echo "LIVE VIEW: $LIVE_URL"

echo "RECORDING ONE EPISODE. Teleoperate with the leader arm; use Esc to stop the session."
ORANGE_DEMO_LIVE=1 HF_HUB_OFFLINE=1 "$PYTHON" "$SCRIPT_DIR/record_2cam_demos.py" \
  --robot.type=so101_follower --robot.port="$FOLLOWER_PORT" --robot.id=my_so101_follower \
  --robot.cameras="{front: {type: opencv, index_or_path: $FRONT_CAM, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: $WRIST_CAM, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader --teleop.port="$LEADER_PORT" --teleop.id=my_so101_leader \
  --dataset.repo_id="local/$NAME" --dataset.root="$ROOT" \
  --dataset.single_task="$TASK" \
  --dataset.num_episodes=1 --dataset.episode_time_s=35 --dataset.reset_time_s=3 \
  --dataset.vcodec=h264 --dataset.push_to_hub=false \
  --display_data=true --display_ip=127.0.0.1 --display_port="$RERUN_GRPC_PORT" \
  "${RESUME_ARGS[@]}"

AFTER=$("$PYTHON" "$SCRIPT_DIR/epcount.py" "$ROOT")
if (( AFTER != BEFORE + 1 )); then
  echo "ERROR: expected episode count $((BEFORE + 1)), found $AFTER"
  exit 1
fi
echo "RECORDED: $ROOT now contains $AFTER episode(s). Review this episode before accepting it."
