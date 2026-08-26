# Launch finetuning for N1.6 on "single node".
# This script tries to provide a similar user experience as current OSS.

import json
import os
from pathlib import Path

import tyro

from gr00t.configs.base_config import get_default_config
from gr00t.configs.finetune_config import FinetuneConfig
from gr00t.experiment.experiment import run


# Make sure the user provided modality config is registered.
def _write_lineage(ft_config, config) -> None:
    """Record parent, dataset and settings alongside the output checkpoints."""
    import datetime
    import subprocess

    out = Path(ft_config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    parent = ft_config.base_model_path
    resolved = str(Path(parent).resolve()) if Path(parent).exists() else parent
    try:
        commit = subprocess.run(
            ["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        commit = None
    lineage = {
        "trained": datetime.datetime.now().isoformat(timespec="seconds"),
        "parent": parent,
        "parent_resolved": resolved,
        "dataset": ft_config.dataset_path,
        "steps": ft_config.max_steps,
        "learning_rate": ft_config.learning_rate,
        "global_batch_size": ft_config.global_batch_size,
        "gradient_accumulation_steps": ft_config.gradient_accumulation_steps,
        "tune": {
            "llm": ft_config.tune_llm,
            "visual": ft_config.tune_visual,
            "projector": ft_config.tune_projector,
            "diffusion_model": ft_config.tune_diffusion_model,
        },
        "optim": config.training.optim,
        "embodiment_tag": ft_config.embodiment_tag.value,
        "gr00t_commit": commit,
        "output_dir": str(out),
    }
    (out / "LINEAGE.json").write_text(json.dumps(lineage, indent=2) + "\n")
    print(f"[lineage] wrote {out / 'LINEAGE.json'}  parent={resolved}")


def load_modality_config(modality_config_path: str):
    import importlib
    import sys

    path = Path(modality_config_path)
    if path.exists() and path.suffix == ".py":
        sys.path.append(str(path.parent))
        importlib.import_module(path.stem)
        print(f"Loaded modality config: {path}")
    else:
        raise FileNotFoundError(f"Modality config path does not exist: {modality_config_path}")


if __name__ == "__main__":
    # Set LOGURU_LEVEL environment variable if not already set (default: INFO)
    if "LOGURU_LEVEL" not in os.environ:
        os.environ["LOGURU_LEVEL"] = "INFO"
    # Use tyro for clean CLI
    ft_config = tyro.cli(FinetuneConfig, description=__doc__)
    embodiment_tag = ft_config.embodiment_tag.value

    # all rank workers should register for the modality config
    if ft_config.modality_config_path is not None:
        load_modality_config(ft_config.modality_config_path)

    config = get_default_config().load_dict(
        {
            "data": {
                "download_cache": False,
                "datasets": [
                    {
                        "dataset_paths": [ft_config.dataset_path],
                        "mix_ratio": 1.0,
                        "embodiment_tag": embodiment_tag,
                    }
                ],
            }
        }
    )
    config.load_config_path = None

    # overwrite with finetune config supplied by the user
    config.model.tune_llm = ft_config.tune_llm
    config.model.tune_visual = ft_config.tune_visual
    config.model.tune_projector = ft_config.tune_projector
    config.model.tune_diffusion_model = ft_config.tune_diffusion_model
    config.model.state_dropout_prob = ft_config.state_dropout_prob
    config.model.random_rotation_angle = ft_config.random_rotation_angle
    config.model.color_jitter_params = ft_config.color_jitter_params
    if ft_config.extra_augmentation_config:
        config.model.extra_augmentation_config = json.loads(ft_config.extra_augmentation_config)
    else:
        config.model.extra_augmentation_config = None

    config.model.load_bf16 = False
    config.model.reproject_vision = False
    config.model.eagle_collator = True
    config.model.model_name = "nvidia/Eagle-Block2A-2B-v2"
    config.model.backbone_trainable_params_fp32 = True
    config.model.use_relative_action = True

    config.training.experiment_name = ft_config.experiment_name
    config.training.start_from_checkpoint = ft_config.base_model_path
    # Env-gated optimizer override (added 2026-08-17). The stock fp32 AdamW puts
    # ~29.8 GB on a 31.3 GB card - OOM at optimizer-state creation regardless of
    # batch size (measured: batch 8 -> 29.57 GB, batch 4 -> 29.81 GB). 8-bit Adam
    # cuts the optimizer states by ~6 GB. Default behaviour unchanged.
    config.training.optim = os.environ.get("N16_OPTIM", "adamw_torch")
    config.training.global_batch_size = ft_config.global_batch_size
    config.training.dataloader_num_workers = ft_config.dataloader_num_workers
    config.training.learning_rate = ft_config.learning_rate
    config.training.gradient_accumulation_steps = ft_config.gradient_accumulation_steps
    config.training.output_dir = ft_config.output_dir
    config.training.save_steps = ft_config.save_steps
    config.training.save_total_limit = ft_config.save_total_limit
    config.training.num_gpus = ft_config.num_gpus
    config.training.use_wandb = ft_config.use_wandb
    config.training.max_steps = ft_config.max_steps
    config.training.weight_decay = ft_config.weight_decay
    config.training.warmup_ratio = ft_config.warmup_ratio
    config.training.wandb_project = ft_config.wandb_project

    config.data.shard_size = ft_config.shard_size
    config.data.episode_sampling_rate = ft_config.episode_sampling_rate
    config.data.num_shards_per_epoch = ft_config.num_shards_per_epoch

    # LINEAGE (added 2026-08-26). A checkpoint must be able to answer "where
    # did I come from". On 2026-08-26 the operator asked which model that day's
    # fine-tune started from and NOTHING recorded it - not the config, not
    # training_args, not the logs. It took comparing action-head weights against
    # three candidates to establish. Writing it at launch costs nothing and
    # ends that class of forensics. Placed BEFORE run() so the record exists
    # even if training later crashes.
    _write_lineage(ft_config, config)

    run(config)
