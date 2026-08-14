"""3f.3b — CHUNKED offload, the way a real implementation must do it.

The earlier bench allocated the FULL state on BOTH sides and fp32 (33.1 GB)
failed to allocate on a 32 GB card. Operator's point: allocate on CPU and stream
in chunks — which is exactly what DeepSpeed/ZeRO does.

Design measured here:
  state lives in ORDINARY host memory (may exceed pinnable RAM)
  copied to GPU through a SMALL PINNED staging buffer, chunk by chunk
  update applied per chunk, result copied back

Measures effective throughput at several sizes, then extrapolates to pi05's
real state sizes. Deliberately avoids allocating 33 GB pinned, which would
nearly exhaust this machine's 34 GB of available RAM.
"""
import torch, time

CHUNK_GB = 1.0
chunk_el = int(CHUNK_GB * 1e9 // 4)
stage = torch.empty(chunk_el, dtype=torch.float32, pin_memory=True)
dev   = torch.empty(chunk_el, dtype=torch.float32, device="cuda")

def bench(total_gb):
    el = int(total_gb * 1e9 // 4)
    host = torch.empty(el, dtype=torch.float32)          # pageable, like real state
    torch.cuda.synchronize(); t0 = time.perf_counter()
    off = 0
    while off < el:
        n = min(chunk_el, el - off)
        stage[:n].copy_(host[off:off+n])                 # pageable -> pinned (CPU)
        dev[:n].copy_(stage[:n], non_blocking=True)      # pinned -> GPU (DMA)
        dev[:n].add_(1)                                  # the update
        stage[:n].copy_(dev[:n], non_blocking=True)      # GPU -> pinned
        torch.cuda.synchronize()
        host[off:off+n].copy_(stage[:n])                 # pinned -> pageable
        off += n
    dt = time.perf_counter() - t0
    del host
    return dt, 2*total_gb/dt

print(f"  chunked through a {CHUNK_GB:.0f} GB pinned staging buffer\n")
print(f"  {'state size':>12}{'time':>9}{'effective':>13}")
rates = []
for gb in (2, 4, 8, 16):
    dt, rate = bench(gb)
    rates.append(rate)
    print(f"  {gb:>9.0f} GB{dt:>8.2f}s{rate:>11.1f} GB/s")

r = sum(rates[-2:]) / 2      # use the larger, steadier sizes
print(f"\n  effective chunked round-trip rate: {r:.1f} GB/s")
print(f"  (vs {56.6:.1f} GB/s for a single bulk pinned transfer — 3f.1)\n")
for lbl, gb in (("8-bit Adam state", 8.3), ("fp32 Adam state", 33.1)):
    t = 2*gb/r
    print(f"  {lbl:<20}{gb:>6.1f} GB  ->  +{t:.2f} s/step  = +{100*t/1.05:.0f}%")
print(f"\n  baseline step 1.05 s · direct (non-chunked) 8-bit measured +29.4%")
