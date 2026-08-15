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

from collections import defaultdict
from itertools import chain

import torch
from torch.optim import Optimizer


class CPUOffloadAdamW(Optimizer):
    """AdamW with exp_avg / exp_avg_sq held in pinned host memory."""

    # 128 MB of fp32 per staged buffer. Large enough to hold bulk DMA rate,
    # small enough that the transient working set is negligible. See the
    # CHUNKING note in the module docstring for why this is not optional.
    CHUNK_ELEMS = 32 * 1024 * 1024

    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=1e-2,
                 chunk_elems=None):
        super().__init__(params, dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay))
        self._pinned_bytes = 0
        self.chunk_elems = chunk_elems or self.CHUNK_ELEMS

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
                bc1 = 1 - beta1 ** t
                bc2 = 1 - beta2 ** t

                if not p.is_contiguous() or not p.grad.is_contiguous():
                    raise RuntimeError(
                        "CPUOffloadAdamW streams parameters through flat views and "
                        f"needs contiguous tensors; got shape {tuple(p.shape)}."
                    )

                n = p.numel()
                pv, gv = p.data.view(-1), p.grad.view(-1)
                mv, vv = st["exp_avg"].view(-1), st["exp_avg_sq"].view(-1)

                for i in range(0, n, self.chunk_elems):
                    j = min(i + self.chunk_elems, n)

                    # host -> device. Slices of pinned storage are themselves
                    # pinned, so this stays a DMA, not a staged copy.
                    m = mv[i:j].to(p.device, non_blocking=True)
                    v = vv[i:j].to(p.device, non_blocking=True)
                    g = gv[i:j].float()

                    if wd != 0:
                        pv[i:j].mul_(1 - lr * wd)          # decoupled weight decay

                    m.mul_(beta1).add_(g, alpha=1 - beta1)
                    v.mul_(beta2).addcmul_(g, g, value=1 - beta2)

                    # reuse g as the denominator buffer, and fold the bias
                    # correction into the scalar, so the chunk needs THREE
                    # fp32 buffers rather than five.
                    g.copy_(v).div_(bc2).sqrt_().add_(eps)
                    pv[i:j].addcdiv_(m, g, value=-lr / bc1)

                    # device -> host
                    mv[i:j].copy_(m, non_blocking=True)
                    vv[i:j].copy_(v, non_blocking=True)
                    del m, v, g

        torch.cuda.synchronize()
        return loss

    def load_state_dict(self, state_dict):
        """Restore state as fp32 PINNED HOST tensors.

        WHY THIS OVERRIDE EXISTS — measured, not anticipated
        ---------------------------------------------------
        `Optimizer.load_state_dict` casts every floating-point state tensor to
        the *parameter's* dtype and device (torch/optim/optimizer.py:754):

            return value.to(dtype=param.dtype, device=param.device)

        π0.5's parameters are bf16 on cuda, so the stock path would resume by
        turning this optimiser into an ordinary GPU-resident bf16 one:

            fp32 -> bf16    the precision this rung exists to provide is gone
            cpu  -> cuda:0  4.14B x 2 x 2B = 16.6 GB back onto a 32 GB card

        and it does NOT raise — the toy round-trip in test_offload_checkpoint.py
        showed it completing "successfully" with both invariants destroyed. So we
        map ids to params ourselves and never let the base class touch the large
        tensors; going through super() would allocate that 16.6 GB before any
        post-hook could undo it.
        """
        groups, saved = self.param_groups, state_dict["param_groups"]
        if len(groups) != len(saved) or any(
            len(g["params"]) != len(s["params"]) for g, s in zip(groups, saved)
        ):
            raise ValueError("loaded state dict does not match this optimizer's param groups")

        id_map = dict(
            zip(
                chain.from_iterable(s["params"] for s in saved),
                chain.from_iterable(g["params"] for g in groups),
            )
        )

        state = defaultdict(dict)
        for k, v in state_dict["state"].items():
            if k not in id_map:
                state[k] = v
                continue
            restored = {}
            for key, val in v.items():
                if key == "step":
                    restored[key] = (
                        val.detach().clone().float().cpu()
                        if torch.is_tensor(val)
                        else torch.tensor(float(val))
                    )
                else:
                    host = torch.empty(val.shape, dtype=torch.float32, pin_memory=True)
                    host.copy_(val)          # fp32, host, pinned — the invariant
                    restored[key] = host
                    self._pinned_bytes += host.numel() * 4
            state[id_map[k]] = restored

        # hyperparameters from the checkpoint, parameters from the live model
        merged = [{**g, **{k: v for k, v in s.items() if k != "params"},
                   "params": g["params"]} for g, s in zip(groups, saved)]
        self.__setstate__({"state": state, "param_groups": merged})

    @property
    def pinned_gb(self):
        return self._pinned_bytes / 1e9
