# Brev L4 Setup

This document records the cloud GPU setup used for LeRobot simulator evaluation.

## Instance

- Provider: Brev
- GPU: NVIDIA L4
- Instance name used: `itchy-teal-gazelle`
- Remote user: `ubuntu`
- Main working directory: `/home/ubuntu/lerobot`

## Environment

Remote environment:

```bash
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda activate lerobot312
cd "$HOME/lerobot"
export MUJOCO_GL=egl
export TOKENIZERS_PARALLELISM=false
export WANDB_DISABLED=true
```

Important details:

- Python 3.12 was required by the newer LeRobot code.
- Miniforge was used because the default system Python was too old.
- `--policy.compile_model=false` was used because compile mode was slow or unstable on this instance.

## Copying Videos Locally

Use `scp` from the local machine:

```bash
scp -r itchy-teal-gazelle:/remote/path/to/videos /data/downloads/
```

Do not run `brev copy` from inside the Brev instance. Run Brev commands from the local machine.

## Stopping the Instance

After every run:

```bash
brev stop itchy-teal-gazelle
brev ls
```

If the CLI remains stuck, use the Brev web UI Stop button.

## Known Issue

`LIBERO 10` caused the 16 GB RAM L4 instance to become unhealthy twice during startup/loading.

Recommendation:

- Retry `LIBERO 10` only on a larger instance.
- Prefer 32 GB or more system RAM.
- Prefer 24 GB or more GPU memory if available.

