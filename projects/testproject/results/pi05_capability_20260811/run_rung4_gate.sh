#!/usr/bin/env bash
# P0 — RUNG 4 CHECKPOINT GATE
# Train with CPUOffloadAdamW, INTERRUPT mid-run, RESUME from the checkpoint.
# The gate is the resume, not the step time.
set -u
P=/home/kiran/sim/pi05-fullft-probe
OUT=/home/kiran/lerobot_assets/probes/pi05_rung4_gate
TEL=${OUT}_tel
rm -rf "$OUT" "$TEL"; mkdir -p "$TEL"

# host-memory telemetry: rung 4's distinguishing risk is PINNED (unswappable) RAM
( while true; do
    printf '%s %s %s\n' "$(date +%s)" \
      "$(awk '/MemAvailable/{print $2}' /proc/meminfo)" \
      "$(awk '/^Mlocked/{print $2}' /proc/meminfo)"
    sleep 5
  done ) > "$TEL/host_mem.txt" 2>/dev/null &
MEMPID=$!
trap 'kill $MEMPID 2>/dev/null' EXIT

export LEROBOT_CPU_OFFLOAD_ADAM=1
COMMON=(
  --policy.path=lerobot/pi05_libero_base
  --policy.device=cuda
  --policy.push_to_hub=false
  --dataset.repo_id=lerobot/libero_spatial_image
  '--rename_map={"observation.images.wrist_image":"observation.images.image2"}'
  --batch_size=8
  --steps=180
  --save_checkpoint=true
  --save_freq=60
  --output_dir="$OUT"
  --job_name=rung4_gate
  --wandb.enable=false
)

echo "=== PHASE 1: train, interrupt after the first checkpoint ==="
stdbuf -oL "$P/.venv312/bin/lerobot-train" "${COMMON[@]}" > "$TEL/train.txt" 2>&1 &
TP=$!
echo "train pid $TP"

# wait for checkpoint 000060 to be COMPLETE (optimizer state is the last big write)
for i in $(seq 1 240); do
  kill -0 $TP 2>/dev/null || { echo "train exited early (code unknown)"; break; }
  if [ -f "$OUT/checkpoints/000060/training_state/optimizer_state.safetensors" ]; then
     sz=$(stat -c%s "$OUT/checkpoints/000060/training_state/optimizer_state.safetensors")
     sleep 8
     sz2=$(stat -c%s "$OUT/checkpoints/000060/training_state/optimizer_state.safetensors")
     [ "$sz" = "$sz2" ] && { echo "checkpoint 000060 settled at $((sz2/1000000)) MB"; break; }
  fi
  sleep 10
done

if kill -0 $TP 2>/dev/null; then
  echo ">>> INTERRUPTING training (pid $TP) to simulate an operator stop"
  kill -9 $TP; sleep 12
else
  echo ">>> training already exited"
fi
nvidia-smi --query-gpu=memory.used --format=csv,noheader

echo; echo "=== PHASE 2: RESUME — this is the gate ==="
stdbuf -oL "$P/.venv312/bin/lerobot-train" \
  --config_path="$OUT/checkpoints/last/pretrained_model/train_config.json" \
  --resume=true > "$TEL/resume.txt" 2>&1
echo "RESUME EXIT=$?"
