"""3f.3d — AdamW whose optimiser state lives in PINNED CPU memory.

Rung 4 of the escalation ladder, in a form that runs inside a real training loop.

DESIGN (justified by the 3f.3c measurement, not by guesswork)
-------------------------------------------------------------
3f.3c showed that 33.1 GB pins in <5 s and streams to the GPU in 1 GB chunks at
55.9 GB/s — full bulk rate. So the design is simply:

    at init   allocate m, v per parameter as PINNED fp32 CPU tensors
    at step   for each parameter:
                copy m,v -> GPU   (DMA out of pinned memory)
                apply the AdamW update there
                copy m,v -> CPU   (DMA back)

Per-parameter rather than one flat buffer: π0.5's 812 tensors average ~5M
elements (~20 MB of fp32 state each), which is large enough to reach good DMA
rates, and it avoids the gather/scatter bookkeeping a flat view would need.

WHAT IT COSTS, predicted from measurement
    fp32 state for 4.14B params = 33.1 GB, moved down AND back each step
    at 55.9 GB/s  ->  ~1.18 s/step on top of a 1.05 s baseline  =  +112%
    ⇒ ~2.2 s/step. If it comes out near 8 s the pinning did not take effect and
      it fell back to a pageable path.
"""

import torch
from torch.optim import Optimizer


class CPUOffloadAdamW(Optimizer):
    """AdamW with exp_avg / exp_avg_sq held in pinned host memory."""

    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=1e-2):
        super().__init__(params, dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay))
        self._pinned_bytes = 0

    @torch.no_grad()
    def step(self, closure=None):
        loss = closure() if closure is not None else None

        for group in self.param_groups:
            beta1, beta2 = group["betas"]
            lr, eps, wd = group["lr"], group["eps"], group["weight_decay"]

            for p in group["params"]:
                if p.grad is None:
                    continue
                st = self.state[p]

                if len(st) == 0:
                    # state lives on the HOST, pinned so transfers are DMA
                    st["step"] = torch.zeros((), dtype=torch.float32)
                    st["exp_avg"] = torch.zeros(
                        p.shape, dtype=torch.float32, pin_memory=True)
                    st["exp_avg_sq"] = torch.zeros(
                        p.shape, dtype=torch.float32, pin_memory=True)
                    self._pinned_bytes += 2 * p.numel() * 4

                st["step"] += 1
                t = st["step"].item()

                # --- host -> device -------------------------------------
                m = st["exp_avg"].to(p.device, non_blocking=True)
                v = st["exp_avg_sq"].to(p.device, non_blocking=True)

                g = p.grad.float()
                if wd != 0:
                    p.mul_(1 - lr * wd)                    # decoupled weight decay

                m.mul_(beta1).add_(g, alpha=1 - beta1)
                v.mul_(beta2).addcmul_(g, g, value=1 - beta2)

                bc1 = 1 - beta1 ** t
                bc2 = 1 - beta2 ** t
                denom = (v / bc2).sqrt_().add_(eps)
                p.addcdiv_(m / bc1, denom, value=-lr)

                # --- device -> host -------------------------------------
                st["exp_avg"].copy_(m, non_blocking=True)
                st["exp_avg_sq"].copy_(v, non_blocking=True)
                del m, v, g, denom

        torch.cuda.synchronize()
        return loss

    @property
    def pinned_gb(self):
        return self._pinned_bytes / 1e9
