"""STEP -1: does bitsandbytes 8-bit Adam actually work on this Blackwell (sm_120) card?

Gates the entire pi05 full-fine-tune experiment. See
projects/testproject/docs/pi05_full_finetune_on_5090_plan_20260811.md

A CUDA kernel/arch error here is THE RESULT, not a setup bug: without working
8-bit optimizer states the persistent bill for pi05 stays at ~46 GiB (FP32 Adam),
32 GB is hopeless, and the answer is "not by this route".
"""

import sys
import traceback

import torch

print("=" * 70)
print("STEP -1  bitsandbytes 8-bit Adam on Blackwell sm_120")
print("=" * 70)

print(f"torch            {torch.__version__}")
print(f"cuda runtime     {torch.version.cuda}")
print(f"cuda available   {torch.cuda.is_available()}")
if not torch.cuda.is_available():
    print("\nFAIL: no CUDA device visible.")
    sys.exit(1)

cap = torch.cuda.get_device_capability(0)
print(f"device           {torch.cuda.get_device_name(0)}")
print(f"capability       sm_{cap[0]}{cap[1]}")
print(f"arch list        {torch.cuda.get_arch_list()}")

try:
    import bitsandbytes as bnb

    print(f"bitsandbytes     {bnb.__version__}")
except Exception:
    print("\nFAIL: bitsandbytes did not import.")
    traceback.print_exc()
    sys.exit(1)

# A real optimizer step on a real (small) parameter set. Large enough that bnb
# uses its blockwise quantised path rather than any trivial fallback.
print("\n--- running one AdamW8bit step ---")
try:
    torch.manual_seed(0)
    model = torch.nn.Sequential(
        torch.nn.Linear(4096, 4096),
        torch.nn.GELU(),
        torch.nn.Linear(4096, 4096),
    ).cuda()

    opt = bnb.optim.AdamW8bit(model.parameters(), lr=1e-3)

    key = "0.weight"
    before = model.state_dict()[key].detach().clone().float().norm().item()

    x = torch.randn(8, 4096, device="cuda")
    loss = model(x).square().mean()
    loss.backward()
    opt.step()
    opt.zero_grad()
    torch.cuda.synchronize()

    after = model.state_dict()[key].detach().float().norm().item()

    # Confirm the optimizer really allocated 8-bit state, not a fp32 fallback.
    st = opt.state[next(iter(model.parameters()))]
    state_dtypes = {k: (v.dtype if torch.is_tensor(v) else type(v).__name__) for k, v in st.items()}

    print(f"loss             {loss.item():.6f}")
    print(f"{key} norm before {before:.6f}")
    print(f"{key} norm after  {after:.6f}")
    print(f"delta            {abs(after - before):.3e}")
    print(f"optimizer state  {state_dtypes}")

    moved = abs(after - before) > 0
    finite = torch.isfinite(torch.tensor(loss.item())).item()
    eight_bit = any(getattr(v, "dtype", None) == torch.uint8 for v in st.values())

    print("\n" + "=" * 70)
    print(f"  step completed      {'YES'}")
    print(f"  param changed       {'YES' if moved else 'NO'}")
    print(f"  loss finite         {'YES' if finite else 'NO'}")
    print(f"  state is uint8      {'YES' if eight_bit else 'NO  <- not actually 8-bit!'}")
    verdict = moved and finite and eight_bit
    print(f"\n  VERDICT: {'PASS' if verdict else 'FAIL'}")
    print("=" * 70)
    sys.exit(0 if verdict else 1)

except Exception:
    print("\n" + "=" * 70)
    print("  VERDICT: FAIL - exception during the 8-bit step")
    print("  ⇒ This IS the result. Record it. Without 8-bit states the pi05")
    print("    persistent bill stays ~46 GiB and 32 GB is hopeless.")
    print("=" * 70)
    traceback.print_exc()
    sys.exit(1)
