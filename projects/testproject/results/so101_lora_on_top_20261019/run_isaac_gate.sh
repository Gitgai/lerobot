#!/usr/bin/env bash
# R5 Isaac gate ("did not break it"): serve a LoRA checkpoint (merged model) with the same wrapper the base used,
# on GPU 1 port 8081, and score it on LeIsaac PickOrange with the R2 harness — same seeds as the base's control run.
#   run_isaac_gate.sh <checkpoint step, e.g. 025000> [tag]
# Rows (pre-registered 2026-10-21, 50 seeded episodes each, non-pipelined, chunk 20, 100 s cap):
#   corpusA  "Grab oranges and place into plate."          seeds 100..149  control: base 38/50 = 76%  → forgetting check
#   plateC   "pick up the orange and place it on the plate" seeds 300..349  our own plate instruction (new row; base not scored)
#   oursB    "pick up the orange and move it to another place" seeds 200..249  control: base 16/50 = 32% (optional, if time)
# Everything on GPU 1 (policy server + Isaac Sim); GPU 0 keeps the operator's server and the bench wrapper.
set -euo pipefail
STEP=${1:?checkpoint step dir name, e.g. 025000}; TAG=${2:-lora_${STEP}}
ROWS=${ROWS:-corpusA,plateC}; EPISODES=${EPISODES:-50}   # 2026-10-22: ROWS/EPISODES overrides for diagnostic rows (timeouts cost 7 min each)
RUN=/mnt/data4tb/so101-lora-on-top-20261021/row1_author_lora_b8
CK=$RUN/checkpoints/$STEP/pretrained_model
OUT=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_lora_on_top_20261019
SIM=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_base_sim_test_20261020
WRAP=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/scripts/so101_base_policy_server.py
[ -f "$CK/model.safetensors" ] || { echo "no checkpoint at $CK"; exit 1; }
mkdir -p "$OUT/isaac_gate"
# 1) policy server for the LoRA checkpoint (no frame recorder), transient unit on GPU 1 :8081
systemctl --user stop so101-lora-server 2>/dev/null || true
systemd-run --user --unit=so101-lora-server --collect \
  --setenv=CUDA_VISIBLE_DEVICES=1 --setenv=HF_HOME=/mnt/data4tb/huggingface-cache --setenv=TMPDIR=/home/kiran/tmp \
  --setenv=HOME=/home/kiran --setenv=PYTHONUNBUFFERED=1 --setenv=RECORD_DIR="${RECORD_DIR:-}" --setenv=RECORD_EVERY="${RECORD_EVERY:-25}" \
  /home/kiran/sim/vlash-venv/bin/python "$WRAP" --host 127.0.0.1 --port 8081 --ckpt "$CK/"
echo "so101-lora-server started on :8081 (GPU 1) with $CK"
# 2) the three rows, Isaac on GPU 1 too; results_<tag>_<row>.jsonl in $OUT/isaac_gate
export OUTDIR=$OUT/isaac_gate PORT=8081 SIM_GPU=1 CKPT_LABEL=$CK HEADLESS=1
case ",$ROWS," in *,corpusA,*) bash $SIM/run_sim_test.sh $EPISODES "${TAG}_corpusA" "Grab oranges and place into plate." 100;; esac
case ",$ROWS," in *,plateC,*)  bash $SIM/run_sim_test.sh $EPISODES "${TAG}_plateC"  "pick up the orange and place it on the plate" 300;; esac
case ",$ROWS," in *,oursB,*)   bash $SIM/run_sim_test.sh $EPISODES "${TAG}_oursB"   "pick up the orange and move it to another place" 200;; esac
systemctl --user stop so101-lora-server
for f in "$OUT"/isaac_gate/results_${TAG}_*.jsonl; do echo "$(basename $f): $(grep -c '"success": true' $f)/$(wc -l < $f)"; done | tee -a "$OUT/isaac_gate/summary.txt"
echo "=== GATE DONE $TAG $(date -u +%FT%TZ)" >> "$OUT/isaac_gate/summary.txt"
