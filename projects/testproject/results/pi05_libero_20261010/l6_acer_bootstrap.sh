#!/usr/bin/env bash
# L6: prepare the ACER (CPU-only) to run the LIBERO simulator + our scoring loop against a policy
# served on AI90 over ZeroTier. Pins = AI90's probe venv (hf_libero 0.1.4, robosuite 1.4.0,
# mujoco 3.2.7, numpy 2.2.6, torch cpu, websockets 17.2, msgpack 1.2.3). Idempotent.
# Usage on the Acer:  bash l6_acer_bootstrap.sh     (needs ~3 GB disk, internet; ~10 min)
set -eu
BASE=$HOME/l6_libero_remote; mkdir -p "$BASE"; cd "$BASE"
echo "=== $(date -u +%FT%TZ) G0 host: $(hostname) $(nproc) cores $(free -g | awk '/Mem/{print $2}') GB RAM"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH=$HOME/.local/bin:$PATH; }
export PATH=$HOME/.local/bin:$PATH
[ -x .venv/bin/python ] || uv venv --python 3.12 .venv
. .venv/bin/activate
uv pip install "hf_libero==0.1.4" "robosuite==1.4.0" "mujoco==3.2.7" "numpy==2.2.6" "websockets==17.2" "msgpack==1.2.3" \
  "dm-tree>=0.1.8" "tree>=0.2.4" "pillow" "opencv-python" "gymnasium==1.3.0" "easydict" "hydra-core" "termcolor" "cloudpickle" "einops" "thop" "future" "bddl==1.0.1" "matplotlib"
uv pip install "torch==2.7.1" --index-url https://download.pytorch.org/whl/cpu
# openpi-client (not on PyPI the way we use it): copied from AI90 by l6_acer_run.sh into $BASE/openpi-client/src
# headless rendering: EGL if a GPU/driver exists, else OSMesa
sudo -n true 2>/dev/null && sudo apt-get install -y -qq libegl1 libgl1 libosmesa6 libglew2.2 2>/dev/null || echo "(no sudo: assuming libEGL/OSMesa present)"
echo "=== G2 render one LIBERO frame"
for GL in egl osmesa; do
  if MUJOCO_GL=$GL PYOPENGL_PLATFORM=$GL python - <<'PY'
from libero.libero import benchmark, get_libero_path
from libero.libero.envs import OffScreenRenderEnv
import os
b=benchmark.get_benchmark_dict()["libero_spatial"]()
t=b.get_task(0); env=OffScreenRenderEnv(bddl_file_name=os.path.join(get_libero_path("bddl_files"),t.problem_folder,t.bddl_file),camera_heights=256,camera_widths=256)
env.seed(7); o=env.reset(); print("frame", o["agentview_image"].shape); env.close()
PY
  then echo "MUJOCO_GL=$GL works" > "$BASE/gl_backend"; break; fi
done
[ -f "$BASE/gl_backend" ] && cat "$BASE/gl_backend" || { echo "G2 FAILED: no working GL backend"; exit 2; }
echo "=== $(date -u +%FT%TZ) bootstrap done"
