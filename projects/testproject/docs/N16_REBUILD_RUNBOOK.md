# N1.6 REBUILD RUNBOOK — from bare machine to the working policy

Written 2026-08-07. Purpose: if this machine dies, follow this file top to
bottom and end with the exact stack that places 15/15 oranges in sim and is
staged for the real arm. Everything here has been executed and verified on
this machine; nothing is aspirational.

---

## 0. THE ONE THING GIT CANNOT RESTORE — read first

```text
THE CHECKPOINT is a THIRD-PARTY Hugging Face upload. If its author deletes
it, "redownload" stops existing. Weights cannot be rebuilt from our scripts.

  repo      12e21/gr00t_n1d6_leisaac_pick_orange
  revision  6d73eafb528a82b5c9a201f26e7aac3766433c2f   (pinned 2026-08-07,
            lastModified 2026-01-16 - stable for ~7 months)
  size      9.2 GB   local: ~/lerobot_assets/checkpoints/gr00t_n16_leisaac_orange

=> the LOCAL COPY IS THE PRIMARY ARTIFACT; the HF repo is merely its source.
   It is in BACKUP_MANIFEST.md - back it up like the calibration file.
=> RECOMMENDED (needs the user): mirror it to the user's own HF account as a
   private repo. One upload removes the single point of failure entirely.

Second copy of the same risk, smaller: nvidia/GR00T-N1.6-3B base model
(6.2 GB, ungated, NVIDIA-hosted - lower risk) and the gated
nvidia/Cosmos-Reason2-2B backbone cache (4.6 GB; regated = re-request).
```

## 1. Download the checkpoint

```bash
python -c "from huggingface_hub import snapshot_download; snapshot_download(
  '12e21/gr00t_n1d6_leisaac_pick_orange',
  revision='6d73eafb528a82b5c9a201f26e7aac3766433c2f',
  local_dir='~/lerobot_assets/checkpoints/gr00t_n16_leisaac_orange')"
# checkpoint proper: <local_dir>/ckpt/checkpoint-10000
```

## 2. Build the serving environment (~1 h, NO sudo)

```bash
git clone --depth 1 --branch n1.6-release https://github.com/NVIDIA/Isaac-GR00T.git ~/sim/Isaac-GR00T-n16
cd ~/sim/Isaac-GR00T-n16
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
# VERIFY BEFORE CONTINUING: python -c "import torch; assert 'sm_120' in torch.cuda.get_arch_list()"

# the three packaging traps, in order:
uv pip install --python .venv/bin/python wheel_stub setuptools wheel   # tensorrt needs it
uv pip install --python .venv/bin/python \
  "https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1+cu12torch2.7cxx11abiTRUE-cp311-cp311-linux_x86_64.whl"
  # prebuilt wheel - no nvcc on this machine; abi from torch._C._GLIBCXX_USE_CXX11_ABI (True)
uv pip install --python .venv/bin/python -e . --no-build-isolation
uv pip uninstall --python .venv/bin/python deepspeed                   # training-only, breaks import without CUDA_HOME

# apply our local patches (video backend, finetune memory, real-arm client):
git apply /path/to/repo/projects/testproject/patches/isaac-gr00t-n16-local.patch

# real-arm extras:
uv pip install --python .venv/bin/python "lerobot[feetech]==0.4.4"     # newest on py3.11; matches the
                                                                        # calibration's so_follower era
uv pip install --python .venv/bin/python usd-core py-spy               # optional tooling
```

## 3. Start the server (the exact command that produced every result)

```bash
cd ~/sim/Isaac-GR00T-n16 && ./.venv/bin/python -m gr00t.eval.run_gr00t_server \
  --model_path=$HOME/lerobot_assets/checkpoints/gr00t_n16_leisaac_orange/ckpt/checkpoint-10000 \
  --embodiment-tag=NEW_EMBODIMENT --port=5556
# NOTE: --embodiment-tag (HYPHEN) and UPPERCASE - n1.7 differs on both.
# healthy: ~8.2 GB VRAM, 1,091,722,240 DiT params, ZMQ REP on :5556
```

## 4. Validate in sim BEFORE any hardware (the regression gate)

Sim stack per `STATE_20260805.md`: Isaac Sim 5.1 / Isaac Lab 2.3.0 /
LeIsaac @ 24d3bcd, driver PINNED to the R580 branch (580.173.02 - R590
segfaults Isaac 5.1). Then:

```bash
cd ~/sim/leisaac-src && LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets \
ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
~/sim/leisaac-venv/bin/python -u <repo>/projects/testproject/scripts/sim_policy_eval_instrumented.py \
  --policy_type=gr00t-n16 --policy_port=5556 --max_steps=3000 --seed=1001 \
  --out=<repo>/projects/testproject/logs/rebuild_check.csv
```

```text
EXPECTED (n=12 reference): ~94% of oranges placed, lifts 0.13-0.20 m,
1-3 drops/run, last placement possibly as late as step ~2500.
Uses LeIsaac's NATIVE Gr00t16ServicePolicyClient - none of our adapter code.
Score with object LIFT, never the grasp predicate alone.
```

## 5. Real arm (when hardware exists)

```bash
cd ~/sim/Isaac-GR00T-n16 && ./.venv/bin/python -m gr00t.eval.real_robot.SO100.eval_so100 \
  --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=my_so101_follower \
  --policy_host=localhost --policy_port=5556 \
  --lang_instruction="Grab orange and place into plate"
# + camera config: two OpenCV cameras named exactly `front` and `wrist`, 640x480
# calibration: ~/.cache/huggingface/lerobot/calibration/robots/so_follower/my_so101_follower.json
```

Rig spec (measured, priority order): (0) LAYOUT MATCH - plate left, oranges
clustered 10-15 cm right; (1) clean table, nothing orange-ish; (2) LOCK
white balance + exposure on both cameras (v4l2-ctl); (3) camera mount has
~2 cm slack, avoid degrees of tilt. Instruction string comes from the
dataset, verbatim, as above. Score with the finger-stall test.
Stage A of `sim_to_real_preflight_protocol_20260806.md` is DONE for this
client+server pair; re-run Stages B/C only if the policy or client changes.

## 6. Known-good reference numbers (what "working" looks like)

```text
sim, canonical, 3,000 steps, n=12:  94% oranges, 10/12 full completions
robustness at n>=3: appearance ~100%, decoys 67%, scatter 44%, moved plate 33%
serving latency: ~1.3 s per 16-step chunk end to end in the sim loop
```
