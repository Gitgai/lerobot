#!/usr/bin/env bash
# Read-only diagnosis of /tmp ("Disk quota exceeded" killed the L1 uv sync and
# plausibly the Bash tool). Deletes nothing. Serves its own log on :8766.
set -u
OUT=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
LOG=$OUT/diag_tmp.log
exec > "$LOG" 2>&1
echo "=== $(date -u +%FT%TZ) /tmp diagnosis ==="
echo "--- df"; df -h /tmp /dev/shm /home / 2>&1
echo "--- df inodes"; df -i /tmp 2>&1
echo "--- mount"; mount | grep -E ' /tmp | /dev/shm ' || echo "(no separate mount line for /tmp)"
echo "--- systemd tmp.mount"; systemctl show tmp.mount -p ActiveState -p What -p Options 2>/dev/null || true
echo "--- quota"; quota -s 2>/dev/null || echo "(quota: n/a)"
echo "--- top-level sizes under /tmp (du -xsh, may take a moment)"
du -xsh /tmp/* /tmp/.[!.]* 2>/dev/null | sort -h | tail -20
echo "--- count"; find /tmp -xdev -type f 2>/dev/null | wc -l
echo "--- claude scratch dirs"; du -xsh /tmp/claude-* 2>/dev/null | sort -h | tail -5
ls -la /tmp | head -40
echo "--- write test"; ( echo x > /tmp/.l1_write_test && echo "write to /tmp OK" && rm -f /tmp/.l1_write_test ) || echo "write to /tmp FAILED"
echo "--- /home/kiran/tmp"; mkdir -p /home/kiran/tmp && echo x > /home/kiran/tmp/.t && rm /home/kiran/tmp/.t && echo "write to /home/kiran/tmp OK"
echo "=== done ==="
cd "$OUT" && exec python3 -m http.server 8766 --bind 127.0.0.1
