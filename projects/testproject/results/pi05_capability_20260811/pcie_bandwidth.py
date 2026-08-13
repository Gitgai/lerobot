"""3f.1 — measure REAL PCIe bandwidth, host<->device, pinned vs pageable.

Replaces the 63 GB/s spec figure the escalation-ladder arithmetic was built on.
Real achievable is typically 50-80% of spec.
"""
import torch, time

def bench(nbytes, pinned, h2d, iters=20):
    n = nbytes // 4
    host = torch.empty(n, dtype=torch.float32, pin_memory=pinned)
    dev = torch.empty(n, dtype=torch.float32, device="cuda")
    src, dst = (host, dev) if h2d else (dev, host)
    for _ in range(3):                       # warm up
        dst.copy_(src, non_blocking=pinned)
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        dst.copy_(src, non_blocking=pinned)
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    return nbytes * iters / dt / 1e9

SIZE = 1 << 30   # 1 GiB
print(f"  transfer size {SIZE/2**30:.0f} GiB, 20 iterations\n")
print(f"  {'direction':<22}{'pageable':>12}{'pinned':>12}")
for label, h2d in (("host -> device (H2D)", True), ("device -> host (D2H)", False)):
    pg = bench(SIZE, False, h2d)
    pn = bench(SIZE, True, h2d)
    print(f"  {label:<22}{pg:9.1f} GB/s{pn:9.1f} GB/s")
print(f"\n  PCIe Gen5 x16 theoretical: 63.0 GB/s")
