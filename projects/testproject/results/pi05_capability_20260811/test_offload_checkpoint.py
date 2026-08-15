"""GATE TEST (seconds, not hours): does CPUOffloadAdamW survive lerobot's
checkpoint round-trip with its state STILL fp32 AND STILL ON THE HOST?

Toy model, real lerobot save/load code path. Catches at zero cost what would
otherwise show up 200 steps into a real run.
"""
import sys, tempfile, torch
from pathlib import Path
sys.path.insert(0, "/home/kiran/sim/pi05-fullft-probe")
from cpu_offload_adamw import CPUOffloadAdamW
from lerobot.optim.optimizers import save_optimizer_state, load_optimizer_state

# params exactly as pi05 has them: bf16, on the GPU
m = torch.nn.Linear(64, 64).cuda().to(torch.bfloat16)
opt = CPUOffloadAdamW(m.parameters(), lr=1e-4)
m(torch.randn(8, 64, device="cuda", dtype=torch.bfloat16)).sum().backward()
opt.step()

def describe(tag, o):
    st = next(iter(o.state.values()))
    ea = st["exp_avg"]
    print(f"  {tag:9} dtype={str(ea.dtype):16} device={str(ea.device):6} "
          f"pinned={ea.is_pinned() if ea.device.type=='cpu' else 'n/a'}")
    return ea

print("=" * 70); print("CPUOffloadAdamW  ->  lerobot checkpoint round-trip"); print("=" * 70)
before = describe("BEFORE", opt).clone().float()

d = Path(tempfile.mkdtemp())
save_optimizer_state(opt, d)
print(f"  saved     {(d/'optimizer_state.safetensors').stat().st_size/1e6:.1f} MB")

# fresh optimizer, as a resume would build it
m2 = torch.nn.Linear(64, 64).cuda().to(torch.bfloat16)
m2.load_state_dict(m.state_dict())
opt2 = CPUOffloadAdamW(m2.parameters(), lr=1e-4)
load_optimizer_state(opt2, d)
after = describe("AFTER", opt2)

print("=" * 70)
ok = True
if after.dtype != torch.float32:
    print(f"  ⛔ DTYPE LOST: fp32 -> {after.dtype}. The fp32-state experiment is void."); ok = False
if after.device.type != "cpu":
    print(f"  ⛔ STATE MOVED TO {str(after.device).upper()}: offload defeated on resume."); ok = False
    print(f"     at pi05 scale that is 4.14B x 2 x {after.element_size()}B = "
          f"{4.14e9*2*after.element_size()/1e9:.1f} GB landing on a 32 GB card.")
elif not after.is_pinned():
    print("  ⚠ UNPINNED on resume: correct, but transfers fall back to a staged"); ok = False
    print("    pageable path — expect the step time to regress sharply.")
if ok and torch.allclose(before, after.float()):
    print("  ✅ PASS — values, dtype, device and pinning all survive.")
print("=" * 70)
sys.exit(0 if ok else 1)
