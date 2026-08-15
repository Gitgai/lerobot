"""WHICH parameters never receive a gradient?

The rung-4 checkpoint saved optimiser state for 805 of 813 parameters. The other
8 hold ~894M params — 21.6% of the 4.143B this project calls a "full fine-tune".
Optimiser state is created lazily on a parameter's first gradient, so a missing
entry means that tensor was never updated.

Almost certainly the LM heads: π0.5 trains a flow-matching ACTION objective and
never computes vocabulary logits, so `lm_head` legitimately gets no gradient.
But "almost certainly" is what has been wrong repeatedly here, so this maps the
indices to names instead of assuming.

Uses the meta device: builds the module graph with NO memory allocated, purely
to recover `model.parameters()` ORDER, which is what the optimiser indexes by.
"""

import json
import sys

import torch
from safetensors import safe_open

C = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/kiran/lerobot_assets/probes/pi05_rung4_gate/checkpoints/000060"

from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies.pi05.modeling_pi05 import PI05Policy

cfg = PreTrainedConfig.from_pretrained(f"{C}/pretrained_model")
with torch.device("meta"):
    policy = PI05Policy(cfg)

names = [n for n, p in policy.named_parameters() if p.requires_grad]
sizes = [p.numel() for _, p in policy.named_parameters() if p.requires_grad]

pg = json.load(open(f"{C}/training_state/optimizer_param_groups.json"))
declared = [i for g in pg for i in g["params"]]
with safe_open(f"{C}/training_state/optimizer_state.safetensors", framework="pt") as f:
    have = {int(k.split("/")[1]) for k in f.keys()}

missing = sorted(set(declared) - have)
print("=" * 76)
print("PARAMETERS THAT NEVER RECEIVED A GRADIENT")
print("=" * 76)
print(f"  trainable tensors in the graph  {len(names)}")
print(f"  optimiser declared              {len(declared)}")
print(f"  of which got state              {len(have)}")
print(f"  NEVER UPDATED                   {len(missing)}")
print()
if len(names) != len(declared):
    print(f"  ⚠ graph has {len(names)} trainable tensors but the optimiser declared "
          f"{len(declared)} — index mapping below may be unreliable.")
tot = 0
for i in missing:
    if i < len(names):
        tot += sizes[i]
        print(f"    [{i:4}] {sizes[i]/1e6:9.1f}M  {names[i]}")
    else:
        print(f"    [{i:4}] (index beyond the graph's parameter list)")
print()
print(f"  total never updated  {tot/1e9:.3f}B of {sum(sizes)/1e9:.3f}B "
      f"({100*tot/sum(sizes):.1f}%)")
print("=" * 76)
print("  If these are the LM heads, the behaviour is correct and the honest")
print("  phrasing is 'full fine-tune of the 3.25B parameters the action")
print("  objective touches', not 'of 4.14B'.")
print("=" * 76)
