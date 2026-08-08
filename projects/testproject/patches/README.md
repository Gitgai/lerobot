# Third-party source pins and local patches

Everything needed to recreate the third-party trees after a crash. Our own
scripts live in ../scripts and are fully committed; this directory covers
code that lives OUTSIDE this repo.

## Source pins (clone these exact commits)

```text
~/sim/leisaac-src        github.com/LightwheelAI/leisaac  @ 24d3bcd
                         (the scripted state machine that generated every
                          episode: source/leisaac/leisaac/datagen/
                          state_machine/pick_orange.py - UNMODIFIED upstream;
                          working tree clean)
~/sim/Isaac-GR00T-n16    github.com/NVIDIA/Isaac-GR00T @ n1.6-release (ead5283)
                         shallow clone + THE PATCH BELOW
~/sim/Isaac-GR00T        github.com/NVIDIA/Isaac-GR00T @ n1.7 era (b995540)
                         unmodified
```

## isaac-gr00t-n16-local.patch (apply with `git apply` in that repo)

Three files, each change documented inline and with .orig backups locally:

```text
gr00t/configs/data/data_config.py      video_backend torchcodec -> decord
                                       (torchcodec can't link FFmpeg 8; pyav
                                       fallback is unimplemented; dataset was
                                       transcoded AV1->H.264 to enable decord)
gr00t/experiment/launch_finetune.py    gradient_checkpointing=True,
                                       load_bf16=True, and optim="adamw_bnb_8bit"
                                       (needs bitsandbytes in the venv; together
                                       these hold full fine-tune at 23.1 GB -
                                       under the 26 GB ceiling that blocked it)
gr00t/eval/real_robot/SO100/eval_so100.py
                                       so100_follower/so101_follower imports ->
                                       so_follower (lerobot 0.4.4, the newest
                                       on py3.11; CLI names unchanged)
```

## Venv rebuild notes (the non-obvious parts)

```text
leisaac venv    + lerobot==0.4.2 installed --no-deps (its numpy>=2 metadata
                conflicts with Isaac's numpy 1.26) + datasets pyarrow dill
                multiprocess xxhash jsonlines draccus accelerate safetensors
                av einops (all --no-deps)
n1.6 venv       torch 2.7.1+cu128; flash-attn from the PREBUILT cxx11abiTRUE
                cp311 wheel (no nvcc on this machine); deepspeed UNINSTALLED;
                lerobot==0.4.4 + lerobot[feetech]; usd-core; py-spy
```
