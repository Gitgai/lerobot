#!/usr/bin/env bash
set -euo pipefail

echo "== GPU =="
nvidia-smi

echo "== Miniforge =="
cd "$HOME"
if [ ! -d "$HOME/miniforge3" ]; then
  wget -O Miniforge3.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
  bash Miniforge3.sh -b -p "$HOME/miniforge3"
fi

source "$HOME/miniforge3/etc/profile.d/conda.sh"

echo "== Python 3.12 environment =="
if ! conda env list | awk '{print $1}' | grep -qx "smolvla-vlabench312"; then
  conda create -n smolvla-vlabench312 python=3.12 -y
fi
conda activate smolvla-vlabench312
python --version
python -m pip install --upgrade pip setuptools wheel

echo "== LeRobot =="
if [ ! -d "$HOME/lerobot/.git" ]; then
  git clone "https://github.com/huggingface/lerobot.git" "$HOME/lerobot"
fi
cd "$HOME/lerobot"
git status --short
python -m pip install -e ".[smolvla]"

echo "== VLABench repositories =="
if [ ! -d "$HOME/VLABench/.git" ]; then
  git clone "https://github.com/OpenMOSS/VLABench.git" "$HOME/VLABench"
fi
if [ ! -d "$HOME/rrt-algorithms/.git" ]; then
  git clone "https://github.com/motion-planning/rrt-algorithms.git" "$HOME/rrt-algorithms"
fi

python -m pip install -e "$HOME/VLABench" -e "$HOME/rrt-algorithms"

echo "== VLABench runtime deps =="
python -m pip install "mujoco==3.2.2" "dm-control==1.0.22" open3d colorlog scikit-learn openai gdown

echo "== Assets =="
python "$HOME/VLABench/scripts/download_assets.py"

echo "== Smoke imports =="
MUJOCO_GL=egl python - <<'PY'
import torch
import mujoco
import dm_control
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
print("mujoco", mujoco.__version__)
print("dm_control ok")
PY

echo "Setup complete. Activate with:"
echo "source \$HOME/miniforge3/etc/profile.d/conda.sh && conda activate smolvla-vlabench312"
