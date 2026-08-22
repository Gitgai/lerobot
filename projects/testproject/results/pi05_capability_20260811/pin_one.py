import sys
import time

import torch

gb = float(sys.argv[1])


def avail():
    for ln in open("/proc/meminfo"):
        if ln.startswith("MemAvailable"):
            return int(ln.split()[1]) / 1048576


if avail() < gb + 6.0:
    print(f"  {gb:>5.1f} GB  SKIP — only {avail():.1f} GB available, floor 6 GB")
    sys.exit(2)
dev = torch.empty(int(1e9 // 4), dtype=torch.float32, device="cuda")
t0 = time.perf_counter()
try:
    host = torch.empty(int(gb * 1e9 // 4), dtype=torch.float32, pin_memory=True)
except RuntimeError as e:
    print(f"  {gb:>5.1f} GB  ⛔ PIN FAILED: {str(e)[:50]}")
    sys.exit(1)
t_pin = time.perf_counter() - t0
n = int(1e9 // 4)
torch.cuda.synchronize()
t1 = time.perf_counter()
for i in range(5):
    dev.copy_(host[i * n : (i + 1) * n], non_blocking=True)
torch.cuda.synchronize()
rate = 5.0 / (time.perf_counter() - t1)
print(
    f"  {gb:>5.1f} GB  pin {t_pin:5.1f}s   bulk {rate:5.1f} GB/s   avail during {avail():5.1f} GB"
    f"   {'⚠ slow pin' if t_pin > 10 else '✅'}"
)
