#!/usr/bin/env bash
# L3 prep — openpi LoRA on LIBERO: config check, dataset + norm stats, memory smoke.
# Plan: docs/pi05_libero_openpi_vs_ours_plan_20261010.md (L3). Does NOT start the 30k run.
set -u
OPENPI=/home/kiran/sim/openpi
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
LOG=$RES/l3_prep.log
CFG=pi05_libero_low_mem_finetune
export TMPDIR=/home/kiran/tmp TMP=/home/kiran/tmp TEMP=/home/kiran/tmp
# 2026-10-10 20:08Z: with MEM_FRACTION=0.6 the batch-32 smoke OOM'd at a peak of
# 18.9 GB total used — the CAP, not the card (30 GB free after the stale server was
# stopped). The GPU is ours now: let JAX use 92%.
export XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.92
export TOKENIZERS_PARALLELISM=false
unset HF_HUB_OFFLINE
mkdir -p "$TMPDIR" "$RES"
exec > >(tee -a "$LOG") 2>&1
step() { echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
PY=$OPENPI/.venv/bin/python
cd "$OPENPI"

step "L3.0 facts"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
df -h /home | tail -1
git -C "$OPENPI" status --short src/openpi/training/config.py
git -C "$OPENPI" diff --stat

step "L3.1 the config builds, and the trainable set is ONLY lora params"
"$PY" - <<'PY'; rc=$?
import jax, flax.nnx as nnx
from openpi.training import config as _config
import openpi.shared.nnx_utils as nnx_utils
cfg = _config.get_config("pi05_libero_low_mem_finetune")
print("model:", cfg.model)
print("batch", cfg.batch_size, "steps", cfg.num_train_steps, "ema", cfg.ema_decay, "lr", cfg.lr_schedule)
# shape-only init on CPU to count params without touching the GPU
with jax.default_device(jax.devices("cpu")[0]):
    model = cfg.model.create(jax.random.key(0))
params = nnx.state(model, nnx.Param)
flat = dict(jax.tree_util.tree_flatten_with_path(params.to_pure_dict())[0]) if False else None
import jax.tree_util as jtu
leaves = jtu.tree_leaves_with_path(params.to_pure_dict())
total = sum(int(v.size) for _, v in leaves)
train_state = nnx.state(model, cfg.trainable_filter)
tleaves = jtu.tree_leaves_with_path(train_state.to_pure_dict())
trainable = sum(int(v.size) for _, v in tleaves)
sized = [(jtu.keystr(p), int(v.size)) for p, v in tleaves]
def bucket(n):
    if "lora" in n: return "lora adapters (gemma attn+ffn)"
    if "['PaliGemma']['img']" in n: return "SigLIP vision encoder (openpi leaves it trainable)"
    if "['PaliGemma']['llm']" in n: return "GEMMA NON-LORA (must be empty)"
    return "projections / time MLP (openpi leaves them trainable)"
from collections import defaultdict
agg = defaultdict(lambda: [0, 0])
for n, s in sized:
    agg[bucket(n)][0] += 1; agg[bucket(n)][1] += s
print(f"total params {total/1e9:.3f}B  trainable {trainable/1e6:.1f}M  ({100*trainable/total:.2f}%)  trainable tensors {len(sized)}")
for k, (c, s) in sorted(agg.items()):
    print(f"  {s/1e6:8.1f}M in {c:3d} tensors  {k}")
gemma_non_lora = [n for n, _ in sized if bucket(n).startswith("GEMMA")]
assert not gemma_non_lora, f"Gemma weights outside LoRA are trainable: {gemma_non_lora[:3]}"
assert any("lora" in n for n, _ in sized), "no LoRA tensors trainable at all"
print("G-L GATE PASS: Gemma trains only through LoRA adapters; vision encoder + projections train fully,")
print("               which is openpi's OWN low_mem_finetune definition (get_freeze_filter freezes '.*llm.*' only).")
PY
echo "L3.1 rc=$rc"; [ "$rc" = "0" ] || { echo "CONFIG/GATE FAILED"; exit 2; }

step "L3.2 dataset download + norm stats for $CFG (physical-intelligence/libero, 273k frames)"
if [ -f "$OPENPI/assets/$CFG/physical-intelligence/libero/norm_stats.json" ]; then
  echo "norm stats already present"
else
  "$PY" scripts/compute_norm_stats.py --config-name "$CFG" 2>&1 | grep -v -E "^\s*$" | tail -15
  echo "compute_norm_stats rc=${PIPESTATUS[0]}"
fi
ls -la "$OPENPI/assets/$CFG/physical-intelligence/libero/" 2>/dev/null || { echo "NORM STATS MISSING"; exit 3; }
du -sh "${HF_LEROBOT_HOME:-$HOME/.cache/huggingface/lerobot}/physical-intelligence/libero" 2>/dev/null || true

step "L3.3 memory smoke: 30 steps at batch 32, then 16 if that OOMs (VRAM sampled at 1 Hz)"
# a previous prep launch may have left ITS smoke running (preview_stop may not reach the child)
for p in $(pgrep -f "[s]cripts/train.py $CFG --exp-name smoke_"); do echo "killing leftover smoke pid $p"; kill "$p"; sleep 5; kill -9 "$p" 2>/dev/null; done
rm -f "$RES/l3_batch_that_fits.txt"
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
for BS in 32 16; do
  echo "--- smoke batch $BS"
  ( while true; do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits; sleep 1; done ) > "$RES/l3_smoke_bs${BS}_vram.txt" 2>/dev/null &
  SMP=$!
  t0=$(date +%s)
  "$PY" scripts/train.py "$CFG" --exp-name "smoke_bs${BS}" --overwrite --num-train-steps 30 --batch-size "$BS" --save-interval 1000 --log-interval 10 > "$RES/l3_smoke_bs${BS}.log" 2>&1
  rc=$?
  kill $SMP 2>/dev/null
  echo "batch $BS rc=$rc wall $(( $(date +%s) - t0 ))s  peak VRAM(total used) $(sort -n "$RES/l3_smoke_bs${BS}_vram.txt" | tail -1) MiB"
  grep -E "Step|loss=|num_learnable|Initialized train state|OOM|RESOURCE_EXHAUSTED|Error|it/s|s/it" "$RES/l3_smoke_bs${BS}.log" | tail -8
  echo "step timings (tqdm tail):"; tr '\r' '\n' < "$RES/l3_smoke_bs${BS}.log" | grep -E "^\s*[0-9]+%|it/s|s/it" | tail -3
  if [ "$rc" = "0" ]; then echo "SMOKE PASS at batch $BS"; echo "$BS" > "$RES/l3_batch_that_fits.txt"; break; fi
done
rm -rf "$OPENPI/checkpoints/$CFG/smoke_bs32" "$OPENPI/checkpoints/$CFG/smoke_bs16" 2>/dev/null

step "L3 PREP VERDICT"
if [ -f "$RES/l3_batch_that_fits.txt" ]; then
  echo "L3 PREP PASS — batch that fits: $(cat "$RES/l3_batch_that_fits.txt"). Launch the 30k run with l3_train.sh."
else
  echo "L3 PREP FAIL — neither batch 32 nor 16 ran 30 steps. See l3_smoke_bs*.log"
fi
step "serving $RES on :8765"
cd "$RES" && exec python3 -m http.server 8765 --bind 127.0.0.1
