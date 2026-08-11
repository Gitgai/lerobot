#!/usr/bin/env bash
# Stage 0b: measure the NJ<->Pune link and read back both cameras' controls.
#
# WHY: every sim condition tested so far assumed a local policy server. The GPU
# is in New Jersey and the arm is in Pune, and in sim the world PAUSES during a
# policy call while on hardware it does not - so sim can never reproduce a
# latency failure. This has to be measured on the arm.
#
# Reference from pi0.5 on this same link (agent_handoff_pi05_20260803.md):
# ~30 steps of latency, ~2 MB/s tunnel, needed RTC + 14.6x JPEG to grasp at all.
# The N1.6 client has none of those mitigations and sends 1.76 MiB uncompressed
# per call.
#
# RUN THIS FROM THE ARM MACHINE (or via ssh, as below). Read-only: no motion, no
# robot connection, nothing written outside ~/link_probe.
set -u
ARM=${ARM:-gaikwad-prakash@192.168.194.228}
SERVER_HOST=${SERVER_HOST:-192.168.194.158}
SERVER_PORT=${SERVER_PORT:-5556}
OUT="$HOME/projects/git/nvidia/lerobot/projects/testproject/logs/link_probe_$(date +%Y%m%d)"
mkdir -p "$OUT"; LOG="$OUT/probe.log"

if ! timeout 15 ssh -o BatchMode=yes -o ConnectTimeout=10 "$ARM" 'echo ok' >/dev/null 2>&1; then
    echo "NO ROUTE to $ARM - Pune machine offline. Nothing measured." | tee "$LOG"; exit 1
fi

{
echo "=== L1: raw ICMP round trip, arm -> policy server ==="
ssh -o BatchMode=yes "$ARM" "ping -c 50 -i 0.2 -q $SERVER_HOST 2>&1 | tail -3"

echo; echo "=== L1b: TCP connect time to the policy port, n=20 ==="
ssh -o BatchMode=yes "$ARM" "
for i in \$(seq 20); do
  /usr/bin/time -f '%e' bash -c 'exec 3<>/dev/tcp/$SERVER_HOST/$SERVER_PORT' 2>&1 || echo REFUSED
done | sort -n | awk '{a[NR]=\$1} END{print \"  min\",a[1],\" median\",a[int(NR/2)],\" max\",a[NR]}'"

echo; echo "=== L2: throughput arm -> server (what a 1.76 MiB payload costs) ==="
ssh -o BatchMode=yes "$ARM" "
dd if=/dev/zero bs=1M count=8 2>/dev/null | timeout 60 ssh -o BatchMode=yes $SERVER_HOST 'cat > /dev/null' 2>&1 \
  && echo '  8 MiB pushed - divide elapsed by 8 for MiB/s, x1.76 for one policy call' \
  || echo '  no ssh arm->server; use the ping figure and the 2 MB/s pi0.5 reference'"

echo; echo "=== S1-S3: camera controls, BOTH devices (this is the Aug 8 unknown) ==="
ssh -o BatchMode=yes "$ARM" '
for d in /dev/video0 /dev/video4; do
  [ -e "$d" ] || continue
  echo "--- $d ---"
  v4l2-ctl -d "$d" --list-ctrls 2>/dev/null | grep -iE "focus|white_balance|exposure|sharpness|gain" \
    || echo "  v4l2-ctl unavailable"
done'
} 2>&1 | tee "$LOG"

echo; echo "wrote $LOG"
