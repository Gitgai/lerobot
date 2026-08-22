"""3f.3c — can the full 33.1 GB of fp32 optimiser state be PINNED?

Decides fp32 offload: +112% (bulk, pinned) vs +785% (chunked, measured in 3f.3b).

SAFETY: pinned memory is UNSWAPPABLE. Allocates incrementally, FREES between
every step, and aborts if MemAvailable falls below the floor.
"""

import gc
import time

import torch

FLOOR_GB = 6.0


def avail():
    for ln in open("/proc/meminfo"):
        if ln.startswith("MemAvailable"):
            return int(ln.split()[1]) / 1048576


dev = torch.empty(int(1e9 // 4), dtype=torch.float32, device="cuda")  # 1 GB staging on GPU

print(f"  floor: abort if MemAvailable < {FLOOR_GB} GB")
print(f"  start: {avail():.1f} GB available\n")
print(f"  {'target':>9}{'pin time':>10}{'bulk H2D':>11}{'avail after':>13}  status")

for gb in (16, 24, 33.1):
    if avail() < gb + FLOOR_GB:
        print(f"  {gb:>7.1f} GB{'—':>10}{'—':>11}{avail():>11.1f} GB  ⛔ SKIP: would breach floor")
        break
    el = int(gb * 1e9 // 4)
    t0 = time.perf_counter()
    try:
        host = torch.empty(el, dtype=torch.float32, pin_memory=True)
    except RuntimeError as e:
        print(f"  {gb:>7.1f} GB{'—':>10}{'—':>11}{avail():>11.1f} GB  ⛔ PIN FAILED: {str(e)[:40]}")
        break
    t_pin = time.perf_counter() - t0
    # bulk transfer rate, 1 GB at a time out of the pinned region
    n = int(1e9 // 4)
    torch.cuda.synchronize()
    t1 = time.perf_counter()
    reps = 5
    for i in range(reps):
        dev.copy_(host[i * n : (i + 1) * n], non_blocking=True)
    torch.cuda.synchronize()
    rate = reps * 1.0 / (time.perf_counter() - t1)
    a = avail()
    flag = "⚠ slow pin (swapping?)" if t_pin > 10 else "✅ ok"
    print(f"  {gb:>7.1f} GB{t_pin:>9.1f}s{rate:>9.1f} GB/s{a:>11.1f} GB  {flag}")
    del host
    gc.collect()
    time.sleep(1)

del dev
gc.collect()
print(f"\n  end: {avail():.1f} GB available")
