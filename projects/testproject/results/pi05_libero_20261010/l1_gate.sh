#!/usr/bin/env bash
# L1 — openpi JAX gate on the 5090. Plan: docs/pi05_libero_openpi_vs_ours_plan_20261010.md
# Everything here is GREEN under the plan's autonomy contract: venv INSIDE
# ~/sim/openpi, checkpoint download from gs://openpi-assets, writes under results/.
# The script never edits the openpi source tree.
#
# Ends by serving this results dir over HTTP so the preview pane can show the log.
set -u
OPENPI=/home/kiran/sim/openpi
OUT=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
LOG=$OUT/l1_gate.log
PORT=${L1_PORT:-8765}
mkdir -p "$OUT"
# /tmp is a tmpfs with a per-user quota that is EXHAUSTED on this box
# (diag_tmp.log, 2026-10-10): every write there fails with "Disk quota
# exceeded", which killed the first uv sync. Stage temp files on /home.
export TMPDIR=/home/kiran/tmp TMP=/home/kiran/tmp TEMP=/home/kiran/tmp
mkdir -p "$TMPDIR"
exec > >(tee -a "$LOG") 2>&1
echo "TMPDIR=$TMPDIR  (rerun after the /tmp quota failure)"

step() { echo; echo "=== $(date -u +%FT%TZ) $* ==="; }

step "L1.0 environment facts"
echo "host $(hostname)  user $(whoami)"
nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total --format=csv,noheader || echo "nvidia-smi FAILED"
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader || true
df -h /home | tail -1
command -v uv && uv --version || { echo "uv NOT FOUND"; }
cd "$OPENPI" || { echo "openpi checkout missing"; exit 2; }
git -C "$OPENPI" rev-parse HEAD
git -C "$OPENPI" status --short | head -5

step "L1.1 uv sync (jax[cuda12]==0.5.3 pinned; several GB of wheels)"
export GIT_LFS_SKIP_SMUDGE=1
uv sync 2>&1 | tail -20
rc_sync=${PIPESTATUS[0]}
echo "uv sync rc=$rc_sync"
if [ "$rc_sync" != "0" ]; then echo "L1.1 FAIL — venv did not build"; fi
uv pip install -e . 2>&1 | tail -5

step "L1.2 does jax see the 5090?"
"$OPENPI/.venv/bin/python" - <<'PY' ; rc_jax=$?
import jax, jaxlib
print("jax", jax.__version__, "jaxlib", jaxlib.__version__)
devs = jax.devices()
print("devices", devs)
assert any(d.platform == "gpu" for d in devs), "NO GPU DEVICE — jax fell back to CPU"
import jax.numpy as jnp
x = jnp.ones((1024, 1024)); y = (x @ x).block_until_ready()
print("matmul on", y.devices(), "ok")
PY
echo "L1.2 rc=$rc_jax  (0 = GPU seen and a matmul ran)"

step "L1.3 download pi05_libero and run ONE forward pass"
"$OPENPI/.venv/bin/python" - <<'PY' ; rc_fwd=$?
import time, numpy as np
from openpi.training import config as _config
from openpi.policies import policy_config
from openpi.policies.libero_policy import make_libero_example
from openpi.shared import download
cfg = _config.get_config("pi05_libero")
t0 = time.time()
ckpt = download.maybe_download("gs://openpi-assets/checkpoints/pi05_libero")
print("checkpoint at", ckpt, f"download+resolve {time.time()-t0:.0f}s")
policy = policy_config.create_trained_policy(cfg, ckpt)
ex = make_libero_example()
t1 = time.time(); out = policy.infer(ex); dt = time.time()-t1
a = np.asarray(out["actions"])
print("actions shape", a.shape, "finite", bool(np.isfinite(a).all()), f"first call {dt:.1f}s (includes jit)")
t2 = time.time(); out = policy.infer(ex); print(f"second call {time.time()-t2:.3f}s")
assert a.shape == (cfg.model.action_horizon, 7), a.shape
assert np.isfinite(a).all()
PY
echo "L1.3 rc=$rc_fwd  (0 = finite (10,7) actions)"

step "L1 VERDICT"
if [ "$rc_sync" = "0" ] && [ "$rc_jax" = "0" ] && [ "$rc_fwd" = "0" ]; then
  echo "L1 PASS — openpi JAX stack runs on this card. L2/L3 proceed on openpi."
else
  echo "L1 FAIL — sync=$rc_sync jax=$rc_jax fwd=$rc_fwd. Next per plan: PyTorch port, then LeRobot LoRA fallback."
fi
nvidia-smi --query-gpu=memory.used --format=csv,noheader || true

step "serving $OUT on :$PORT so the log is viewable; Ctrl-C / preview_stop to end"
cd "$OUT" && exec python3 -m http.server "$PORT" --bind 127.0.0.1
