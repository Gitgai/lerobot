#!/usr/bin/env bash
# Read-only: ages and sizes of the big /tmp entries. Deletes nothing.
set -u
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
LOG=$RES/tmp_ages.log
exec > "$LOG" 2>&1
echo "=== $(date -u +%FT%TZ) now ==="
echo "--- top-level /tmp entries over 100 MB: size, last-modified (dir), newest file inside, owner"
for d in /tmp/* /tmp/.[!.]*; do
  [ -d "$d" ] || continue
  sz=$(du -xsm "$d" 2>/dev/null | cut -f1)
  [ "${sz:-0}" -ge 100 ] || continue
  newest=$(find "$d" -xdev -type f -printf '%TY-%Tm-%Td %TH:%TM\n' 2>/dev/null | sort | tail -1)
  printf '%6s MB  dir-mtime %s  newest-file %s  %s  %s\n' "$sz" "$(stat -c %y "$d" | cut -c1-16)" "${newest:-?}" "$(stat -c %U "$d")" "$d"
done | sort -k1 -n
echo "--- any process with an open file under those dirs? (lsof may be absent)"
command -v lsof >/dev/null && lsof +D /tmp 2>/dev/null | awk 'NR>1{print $1, $2, $9}' | grep -E "dynus|tmp\.|codex|seed" | head -20 || echo "(lsof not available)"
echo "--- dynus processes"
pgrep -fa '[d]ynus' | cut -c1-160 || echo "(none)"
echo "=== done ==="
cd "$RES" && exec python3 -m http.server 8767 --bind 127.0.0.1
