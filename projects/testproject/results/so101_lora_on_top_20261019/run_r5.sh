#!/usr/bin/env bash
# R5 LoRA on top — launcher. Usage:
#   run_r5.sh smoke     # 60 steps, save every 30, resume test: proves loader + LoRA + checkpoint + resume on GPU 1
#   run_r5.sh train     # the real row-1 run (25k steps) as a transient systemd user unit (survives session teardown)
#   run_r5.sh resume    # resume the real run from its last checkpoint
# Standing rules: TMPDIR on /home (tmp quota), HF_HOME on data4tb, systemd-run --user (never setsid/nohup),
# GPU 1 only (GPU 0 holds the operator's LoRA server and the bench wrapper).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
VENV=/home/kiran/sim/vlash-venv
OUT=/mnt/data4tb/so101-lora-on-top-20261021
CFG=$HERE/row1_author_lora.yaml
ENV=(--setenv=CUDA_VISIBLE_DEVICES=1 --setenv=HF_HOME=/mnt/data4tb/huggingface-cache --setenv=TMPDIR=/home/kiran/tmp
     --setenv=HOME=/home/kiran --setenv=PYTHONUNBUFFERED=1 --setenv=TOKENIZERS_PARALLELISM=false)
mkdir -p "$OUT"
case "${1:-}" in
  smoke)
    rm -rf "$OUT/smoke"   # smoke outputs are disposable (ledger §4); never the real run
    systemd-run --user --unit=r5-smoke --collect "${ENV[@]}" --working-directory=/home/kiran/sim/vlash \
      "$VENV/bin/vlash" train "$CFG" --output_dir="$OUT/smoke" --job_name=r5_smoke --steps=60 --save_freq=30 --log_freq=10 --num_workers=2
    echo "unit r5-smoke started; log: journalctl --user -u r5-smoke -f" ;;
  smoke-resume)
    # VLASH auto-resumes when output_dir/checkpoints/last exists (vlash/train.py:256-305): same output dir, more steps
    systemd-run --user --unit=r5-smoke-resume --collect "${ENV[@]}" --working-directory=/home/kiran/sim/vlash \
      "$VENV/bin/vlash" train "$CFG" --output_dir="$OUT/smoke" --job_name=r5_smoke --steps=90 --save_freq=30 --log_freq=10 --num_workers=2
    echo "unit r5-smoke-resume started (expect: resume from step 60, run to 90)" ;;
  train|resume)
    # the same command both starts and resumes: VLASH picks up output_dir/checkpoints/last automatically
    systemd-run --user --unit=r5-row1 --collect "${ENV[@]}" --working-directory=/home/kiran/sim/vlash \
      "$VENV/bin/vlash" train "$CFG"
    echo "unit r5-row1 started/resumed; log: journalctl --user -u r5-row1 -f" ;;
  train2|resume2)
    # row 2 (conservative recipe, 2026-10-22): row2_conservative_lora.yaml, unit r5-row2
    systemd-run --user --unit=r5-row2 --collect "${ENV[@]}" --working-directory=/home/kiran/sim/vlash \
      "$VENV/bin/vlash" train "$HERE/row2_conservative_lora.yaml"
    echo "unit r5-row2 started/resumed; log: journalctl --user -u r5-row2 -f" ;;
  train3|resume3)
    # row 3 (2026-10-24): conservative recipe on all 169 real episodes (both camera placements), unit r5-row3
    systemd-run --user --unit=r5-row3 --collect "${ENV[@]}" --working-directory=/home/kiran/sim/vlash \
      "$VENV/bin/vlash" train "$HERE/row3_all169_conservative.yaml"
    echo "unit r5-row3 started/resumed; log: journalctl --user -u r5-row3 -f" ;;
  *) echo "usage: $0 smoke|smoke-resume|train|resume|train2|resume2|train3|resume3"; exit 2 ;;
esac
