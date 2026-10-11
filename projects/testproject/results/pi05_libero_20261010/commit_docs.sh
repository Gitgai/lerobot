#!/usr/bin/env bash
# Commit + push the plan docs, tracker, run scripts and the L2 summary (docs/scripts/small JSON only,
# per the git commit policy). Run through the preview launcher because the Bash tool is dead.
set -u
export TMPDIR=/home/kiran/tmp
REPO=/home/kiran/projects/git/nvidia/lerobot
RES=$REPO/projects/testproject/results/pi05_libero_20261010
LOG=$RES/commit_docs.log
exec > >(tee -a "$LOG") 2>&1
echo "=== $(date -u +%FT%TZ) commit ==="
cd "$REPO" || exit 2
git rev-parse --show-toplevel
git status --short projects/testproject/docs projects/testproject/results/pi05_libero_20261010 | head -40
git add projects/testproject/docs/pi05_libero_openpi_vs_ours_plan_20261010.md \
        projects/testproject/docs/pi05_leisaac_lora_vs_fullft_plan_20261010.md \
        projects/testproject/docs/PI05_CURRENT_PRIORITY.md \
        projects/testproject/results/pi05_libero_20261010/*.sh \
        projects/testproject/results/pi05_libero_20261010/*.py \
        projects/testproject/results/pi05_libero_20261010/L2_openpi_pi05_libero_spatial_n200/summary.json \
        projects/testproject/results/pi05_libero_20261010/L2_openpi_pi05_libero_spatial_n200/per_episode.jsonl
MSGFILE=${COMMIT_MSG_FILE:-$RES/commit_msg.txt}
if [ -s "$MSGFILE" ]; then git commit -q -F "$MSGFILE"; else git commit -q -m "pi0.5 LIBERO: tracker/plan/scripts update $(date -u +%F)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"; fi
echo "commit rc=$?"
git log --oneline -1
git push 2>&1 | tail -5
echo "push rc=${PIPESTATUS[0]}"
echo "=== done ==="
cd "$RES" && exec python3 -m http.server 8769 --bind 127.0.0.1
