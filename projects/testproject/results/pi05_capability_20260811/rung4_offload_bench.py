"""3f.3 / rung 4 — measure the CPU-optimiser-offload MECHANISM directly.

Does NOT need DeepSpeed. Measures the thing rung 4 actually costs: moving
optimiser state host<->device around the update step, at pi05's real sizes.

What this measures:   transfer + update cost per optimiser step
What it does NOT:     integration overhead, scheduling, transfer/compute overlap
                      (a real ZeRO-Offload does better on overlap and worse on
                       bookkeeping — see the 2-4x figures in the literature)
"""
import torch, time

N = 4_143_404_816                     # pi05 trainable params
CASES = [("8-bit Adam state", 1), ("fp32 Adam state", 4)]
ITERS = 5

print(f"  pi05 params: {N/1e9:.2f}B · {ITERS} iterations\n")
print(f"  {'state':<18}{'bytes/param':>12}{'size':>10}{'H2D+D2H':>10}{'update':>9}{'total':>9}")
for label, bpp in CASES:
    # m and v, one tensor each
    elems = N
    dt = torch.uint8 if bpp == 1 else torch.float32
    gb = 2 * elems * bpp / 1e9
    try:
        m_h = torch.empty(elems, dtype=dt, pin_memory=True)
        v_h = torch.empty(elems, dtype=dt, pin_memory=True)
        m_d = torch.empty(elems, dtype=dt, device="cuda")
        v_d = torch.empty(elems, dtype=dt, device="cuda")
    except RuntimeError as e:
        print(f"  {label:<18}{bpp:>12}{gb:>8.1f} GB   ALLOC FAILED: {str(e)[:40]}")
        continue
    torch.cuda.synchronize()
    t_xfer = t_upd = 0.0
    for _ in range(ITERS):
        t0 = time.perf_counter()
        m_d.copy_(m_h, non_blocking=True); v_d.copy_(v_h, non_blocking=True)
        torch.cuda.synchronize(); t1 = time.perf_counter()
        m_d.add_(1); v_d.add_(1)                      # stand-in for the update
        torch.cuda.synchronize(); t2 = time.perf_counter()
        m_h.copy_(m_d, non_blocking=True); v_h.copy_(v_d, non_blocking=True)
        torch.cuda.synchronize(); t3 = time.perf_counter()
        t_xfer += (t1-t0) + (t3-t2); t_upd += (t2-t1)
    x, u = t_xfer/ITERS, t_upd/ITERS
    print(f"  {label:<18}{bpp:>12}{gb:>8.1f} GB{x:>9.3f}s{u:>8.3f}s{x+u:>8.3f}s")
    del m_h, v_h, m_d, v_d; torch.cuda.empty_cache()

print(f"\n  baseline step time (measured, bs8, no offload): 1.05 s")
