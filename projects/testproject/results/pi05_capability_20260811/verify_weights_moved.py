"""Did the VLM backbone actually MOVE during full fine-tuning?

The check phase 1 (pi05_full_finetune_on_5090_plan_20260811.md §4 Gate B) could
not perform, because it depended on the checkpoint that failed to write. Fixing
the checkpoint bug (STEP 1) makes it available.

Compares VLM backbone tensors in a trained checkpoint against lerobot/pi05_base.
trainable == total says the backbone is *allowed* to train; this says it *did*.

Usage:  python verify_weights_moved.py <checkpoint_dir>
"""

import sys
from pathlib import Path

from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

if len(sys.argv) < 2:
    sys.exit("usage: verify_weights_moved.py <checkpoint_dir>")

ckpt_dir = Path(sys.argv[1])
cands = sorted(ckpt_dir.rglob("model.safetensors"))
if not cands:
    sys.exit(f"no model.safetensors under {ckpt_dir}")
ckpt_path = cands[0]
print(f"checkpoint: {ckpt_path}")

base_path = hf_hub_download("lerobot/pi05_base", "model.safetensors")
print(f"base:       {base_path}\n")

trained = load_file(ckpt_path)
base = load_file(base_path)

# pi05 remaps 812 keys when loading pi05_base: the checkpoint stores lerobot's
# internal names ("model.<x>"), the Hub artefact stores OpenPI names ("<x>").
# Normalise to the base namespace so the comparison is like-for-like, rather
# than reporting "0 shared tensors" and calling it a naming mystery.
if not (set(trained) & set(base)):
    stripped = {k[len("model.") :]: v for k, v in trained.items() if k.startswith("model.")}
    if set(stripped) & set(base):
        print(f"key remap detected: stripped 'model.' prefix from {len(stripped)} tensors\n")
        trained = stripped


# VLM backbone vs action expert — by MODULE PATH, not substring.
#
# ⚠ A substring filter does not work here and silently reports zero VLM
#   tensors: the containing module is named `paligemma_with_expert`, so EVERY
#   key contains both "paligemma" and "expert". The real split is one level
#   down:
#       paligemma_with_expert.paligemma.*    the VLM backbone   (frozen in the
#                                                                012000 recipe)
#       paligemma_with_expert.gemma_expert.* the action expert  (always trains)
def is_vlm(name: str) -> bool:
    return "paligemma_with_expert.paligemma." in name


shared = [k for k in trained if k in base]
vlm_keys = [k for k in shared if is_vlm(k)]
other_keys = [k for k in shared if not is_vlm(k)]
print(f"tensors: {len(trained)} in checkpoint, {len(shared)} shared with base")
print(f"  VLM backbone: {len(vlm_keys)}   other (expert/proj/etc): {len(other_keys)}")

if not vlm_keys:
    print("\n⚠ no VLM tensors matched — key naming differs; inspect manually")
    print("  sample keys:", shared[:5])
    sys.exit(1)


def report(keys, label, n_show=5):
    moved, deltas = 0, []
    for k in keys:
        a, b = base[k].float(), trained[k].float()
        if a.shape != b.shape:
            continue
        d = (b - a).norm().item()
        rel = d / (a.norm().item() + 1e-12)
        deltas.append((rel, d, k))
        if d > 0:
            moved += 1
    deltas.sort(reverse=True)
    print(f"\n--- {label}: {moved}/{len(keys)} tensors changed ---")
    for rel, d, k in deltas[:n_show]:
        print(f"  rel {rel:.3e}  abs {d:.6f}  {k[:78]}")
    return moved, len(keys)


vlm_moved, vlm_total = report(vlm_keys, "VLM BACKBONE")
oth_moved, oth_total = report(other_keys, "action expert / projections", n_show=3)

print("\n" + "=" * 72)
print(f"  VLM backbone tensors changed   {vlm_moved}/{vlm_total}")
print(f"  expert/projection tensors      {oth_moved}/{oth_total}")
verdict = vlm_moved > 0
print(
    f"\n  VERDICT: {'PASS — the VLM backbone MOVED. Genuine full fine-tune.' if verdict else 'FAIL — VLM frozen in practice despite requires_grad'}"
)
if not verdict:
    print("  ⇒ trainable==total was necessary but NOT sufficient. Investigate.")
print("=" * 72)
sys.exit(0 if verdict else 1)
