#!/usr/bin/env bash
# ============================================================================
# C270 POSE BATTERY - what is YOUR overhead camera actually worth?
#
# WHY: it was claimed that wiring the C270 into the policy's `front` channel
# recovers the measured 89% -> 44% camera-geometry penalty. That claim is NOT
# supported. What is measured is sim's OWN front pose (0.60 m up, 0.5 m out,
# 71 deg depression, 67.2 deg FOV) against ONE specific offset (-0.45 m, +45
# deg). The C270's actual pose has never been measured - it was eyeballed from
# a single photo, which is the same error that already produced a wrong 40-deg
# FOV figure earlier in this investigation.
#
# Two things are known to differ:
#   FOV     sim 67.2 deg  vs  C270 49.6 deg (60 deg diagonal spec, 4:3)
#           -> the C270 captures 70% of the width = 48% of the AREA.
#   POSE    unmeasured.
#
# This battery puts the SIM front camera at the C270's REAL pose and reports a
# real number, instead of borrowing one from a different camera position.
#
# ---------------------------------------------------------------------------
# YOU MUST SUPPLY THREE MEASUREMENTS, taken from the ROBOT BASE:
#
#   C270_HEIGHT_M   height of the C270 lens above the robot base plate
#   C270_DIST_M     horizontal distance from the robot base to the lens
#   C270_ANGLE_DEG  how far the lens is tilted DOWN from horizontal
#                   (0 = looking straight out, 90 = straight down)
#
# Sim's own front camera, for reference: 0.60 m up, 0.50 m out, 71 deg down.
#
# Run it like:
#   C270_HEIGHT_M=0.55 C270_DIST_M=0.45 C270_ANGLE_DEG=65 ./n16-c270-pose.sh
# ---------------------------------------------------------------------------
#
# Arms, interleaved (4 x 6 = 24 runs, ~55 min):
#   c270pose   6   measured pose + measured 49.6 deg FOV   <- the question
#   c270fov    6   sim pose, but 49.6 deg FOV only         <- isolates FOV alone
#   webcam     6   the Aug 8 laptop-webcam pose            <- what you HAD
#   canonical  6   control, same session
#
# The webcam arm matters: without it this battery says what the C270 scores but
# not whether it is BETTER than what was already there.
# ============================================================================
set -u
: "${C270_HEIGHT_M:?set C270_HEIGHT_M - height of the C270 lens above the robot base, in metres}"
: "${C270_DIST_M:?set C270_DIST_M - horizontal distance from robot base to lens, in metres}"
: "${C270_ANGLE_DEG:?set C270_ANGLE_DEG - downward tilt from horizontal, in degrees}"

LOGDIR="$HOME/backup_staging/rebuild-logs"
REPO="$HOME/projects/git/nvidia/lerobot"
OUT="$REPO/projects/testproject/logs"
CK="$HOME/lerobot_assets/checkpoints/gr00t_n16_leisaac_orange/ckpt/checkpoint-10000"
MAIN="$LOGDIR/n16-c270-pose.log"
SNAP="$OUT/c270_pose_shots"

# sim's own front camera
SIM_H=0.60; SIM_D=0.50; SIM_A=71.0
C270_FOV=49.6

# deltas the eval flags expect: --jitter-camera is dx,dy,dz in metres from the
# configured mount; --rotate-camera is a pitch DELTA in degrees.
DZ=$(python3 -c "print(f'{$C270_HEIGHT_M - $SIM_H:.4f}')")
DY=$(python3 -c "print(f'{-($C270_DIST_M - $SIM_D):.4f}')")
DA=$(python3 -c "print(f'{$C270_ANGLE_DEG - $SIM_A:.2f}')")
C270POSE="--jitter-camera=0,$DY,$DZ --rotate-camera=$DA --camera-fov=$C270_FOV"
FOVONLY="--camera-fov=$C270_FOV"
WEBCAM="--jitter-camera=0,0,-0.45 --rotate-camera=45"

FREE=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
if [ "${FREE:-0}" -lt 8000 ]; then
    echo "REFUSING TO START: only ${FREE} MiB VRAM free (need ~8000)." | tee "$MAIN"; exit 1
fi

mkdir -p "$SNAP"
{
echo "=== $(date +%T) C270 POSE BATTERY ==="
echo "measured C270: height=${C270_HEIGHT_M} m  dist=${C270_DIST_M} m  tilt=${C270_ANGLE_DEG} deg"
echo "sim front    : height=${SIM_H} m  dist=${SIM_D} m  tilt=${SIM_A} deg  fov=67.2 deg"
echo "-> deltas applied: dy=${DY} dz=${DZ} pitch=${DA} fov=${C270_FOV}"
} > "$MAIN"

start_server () {
    pkill -f 'gr00t.eval.run_gr00t_server' 2>/dev/null; sleep 6
    HF_HUB_OFFLINE=1 "$HOME/sim/Isaac-GR00T-n16/.venv/bin/python" -u -m gr00t.eval.run_gr00t_server \
        --model_path "$CK" --embodiment-tag NEW_EMBODIMENT --host 0.0.0.0 --port 5555 \
        > "$LOGDIR/n16-server-c270.log" 2>&1 &
    SRV=$!
    for i in $(seq 1 90); do
        ss -tln 2>/dev/null | grep -q ':5555' && { echo "--- server READY $(date +%T) ---" >> "$MAIN"; return 0; }
        kill -0 "$SRV" 2>/dev/null || return 1
        sleep 5
    done
    return 1
}
start_server || { echo "SERVER FAILED" >> "$MAIN"; exit 1; }

cd "$HOME/sim/leisaac-src"
one () {
    local label=$1 seed=$2; shift 2
    local snap=""
    case "$seed" in
        7101|7102|7103|7104) snap="--snapshot-dir=$SNAP --snapshot-at=30,60" ;;
    esac
    # -k 30: Isaac Sim BLOCKS SIGTERM during startup, so a plain `timeout` fires
    # and is ignored - one run survived 45 min under `timeout 600` on 2026-08-12.
    LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets \
    ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
      timeout -k 30 600 "$HOME/sim/leisaac-venv/bin/python" -u \
        "$REPO/projects/testproject/scripts/sim_policy_eval_instrumented.py" \
        --policy_type=gr00t-n16 --policy_port=5555 --max_steps=3000 --seed="$seed" \
        "$@" $snap --out="$OUT/c270_${label}_${seed}.csv" \
        > "$LOGDIR/n16-c270-${label}-${seed}.log" 2>&1
    return $?
}
run () {
    local label=$1 seed=$2; shift 2
    [ -s "$OUT/c270_${label}_${seed}.csv" ] && { echo "--- $label $seed SKIP ---" >> "$MAIN"; return; }
    # shellcheck disable=SC2086
    one "$label" "$seed" $*; rc=$?
    if [ $rc -ne 0 ] || [ ! -s "$OUT/c270_${label}_${seed}.csv" ]; then
        echo "--- $label $seed exit=$rc RETRY ---" >> "$MAIN"
        sleep 45; start_server >/dev/null 2>&1
        # shellcheck disable=SC2086
        one "$label" "$seed" $*; rc=$?
        echo "--- $label $seed retry exit=$rc $(date +%T) ---" >> "$MAIN"
    else
        echo "--- $label $seed exit=0 $(date +%T) ---" >> "$MAIN"
    fi
    sleep 20
}

S=7101
for blk in 1 2 3 4 5 6; do
    run c270pose  "$S"        $C270POSE
    run c270fov   "$((S+1))"  $FOVONLY
    run webcam    "$((S+2))"  $WEBCAM
    run canonical "$((S+3))"
    S=$((S+10))
done

kill "$SRV" 2>/dev/null
echo "=== $(date +%T) C270 POSE BATTERY DONE ===" >> "$MAIN"
echo "Snapshots in $SNAP - CHECK THEM. If the c270pose front view does not look" >> "$MAIN"
echo "like what the real C270 actually sees, the measurements were wrong." >> "$MAIN"
