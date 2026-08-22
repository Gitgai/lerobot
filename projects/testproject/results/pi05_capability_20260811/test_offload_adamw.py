"""Correctness + speed check for CPUOffloadAdamW, BEFORE touching lerobot.

1) does it match torch.optim.AdamW numerically?
2) at pi05 scale, what does a step actually cost?
"""

import copy
import time

import torch
from cpu_offload_adamw import CPUOffloadAdamW

# --- 1. correctness vs the reference implementation ---
torch.manual_seed(0)
ref_m = torch.nn.Sequential(torch.nn.Linear(256, 256), torch.nn.GELU(), torch.nn.Linear(256, 256)).cuda()
off_m = copy.deepcopy(ref_m)
ref_o = torch.optim.AdamW(ref_m.parameters(), lr=1e-3, weight_decay=1e-2)
off_o = CPUOffloadAdamW(off_m.parameters(), lr=1e-3, weight_decay=1e-2)

for _i in range(10):
    x = torch.randn(16, 256, device="cuda")
    for m_, o_ in ((ref_m, ref_o), (off_m, off_o)):
        o_.zero_grad()
        m_(x).square().mean().backward()
        o_.step()

md = max((a - b).abs().max().item() for a, b in zip(ref_m.parameters(), off_m.parameters(), strict=False))
print(f"  correctness: max |offload - torch AdamW| after 10 steps = {md:.3e}")
print(f"    {'✅ MATCHES' if md < 1e-5 else '⛔ DIVERGES — do not use'}")

# --- 2. cost at pi05 scale ---
print("\n  scale test: 4.14B params' worth of state, in pi05-like tensor sizes")
sizes = [(4096, 4096)] * 60 + [(2048, 8192)] * 40  # ~1.67B params
params = [torch.zeros(s, device="cuda", requires_grad=True) for s in sizes]
for p in params:
    p.grad = torch.randn_like(p)
n = sum(p.numel() for p in params)
print(f"    {len(params)} tensors, {n / 1e9:.2f}B params, fp32 state = {2 * n * 4 / 1e9:.1f} GB")

o = CPUOffloadAdamW(params, lr=1e-3)
t0 = time.perf_counter()
o.step()
t_first = time.perf_counter() - t0
print(f"    first step (allocates {o.pinned_gb:.1f} GB pinned): {t_first:.2f}s")
ts = []
for _ in range(3):
    t0 = time.perf_counter()
    o.step()
    ts.append(time.perf_counter() - t0)
t = sum(ts) / len(ts)
print(f"    steady-state step: {t:.3f}s for {n / 1e9:.2f}B params")
print(f"    ⇒ extrapolated to 4.14B: {t * 4.143 / (n / 1e9):.2f}s of optimiser time")
print("    (predicted ~1.18s from 55.9 GB/s; baseline train step is 1.05s)")
