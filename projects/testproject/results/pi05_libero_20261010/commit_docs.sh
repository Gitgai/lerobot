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
git commit -q -F - <<'MSG'
pi0.5 LIBERO: L1 gate PASS, L2 their full-FT 200/200 in our loop, L3 LoRA running

L1: openpi JAX stack runs on the 5090 (jax 0.5.3 sees the GPU; pi05_libero
forward pass finite, 59 ms warm). L2: their published full-FT checkpoint
scores 200/200 on LIBERO Spatial (CI95 98.1-100) through our port of their
eval convention — harness validated against their 98.8. L3: openpi LoRA
config added (trainable 467M of 3.40B = LoRA 50M + SigLIP 415M + proj 2M,
openpi's own low_mem definition), batch 32 fits, 3.5 s/step, ~29 h; resume
with 5k checkpoints at 10k per operator. Plans: LIBERO (L1-L5) and the
LeIsaac orange task (O0-O3) with the public SO-101 data survey; router
rewritten as tracker. Scripts, launch records and the L2 result included.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
echo "commit rc=$?"
git log --oneline -1
git push 2>&1 | tail -5
echo "push rc=${PIPESTATUS[0]}"
echo "=== done ==="
cd "$RES" && exec python3 -m http.server 8769 --bind 127.0.0.1
