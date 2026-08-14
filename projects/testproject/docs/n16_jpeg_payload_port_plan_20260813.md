# Plan: port the JPEG observation fix to the N1.6 pipeline

Created 2026-08-13. **APPROVED 2026-08-14 — see section 7 for the
remeasured numbers from the live run, which supersede section 0.**

---

## 0. Why

The measured root cause of the Aug 8 real-arm failure. From the run's own frame
mtimes:

```text
  143 chunks over 143 s   = 1.007 s per chunk
    267 ms   arm actually moving (8 actions @ 30 Hz)
    740 ms   blocked waiting on the policy server in New Jersey
  duty cycle: 26.5% moving, 73.5% FROZEN
```

And the sim battery that isolated which half of that matters
(`st_*` runs, n=6 each, same session):

```text
  condition     placed    rate    vs control
  canonical     16/18      89%    -
  stall22       11/18      61%    p = 0.121   NOT significant
  delay22        4/18      22%    p < 0.001
  both22         2/18      11%    p < 0.001
```

**Freezing the arm is survivable. Serving the policy a stale observation is
not.** So the target is observation AGE, and 409 ms of the 740 ms is payload
transfer.

```text
  measured ping NJ -> Pune      331 ms
  remainder                     409 ms   <- 1.76 MiB of uncompressed images
```

---

## 1. Prior art: this fix already exists, on the other pipeline

`docs/pi05_network_payload_reference_20260801.md`, measured 2026-08-01:

```text
  BEFORE  3 cameras, 640x480 raw, pickled   2.77 MB / observation
  AFTER   JPEG quality 92                   ~190 KB   (14.6x)
  upload  1.4 s -> 0.10-0.15 s
```

Two findings from that work carry over and materially de-risk this one:

* **Quality 92 round-trip pixel error is 0.4/255** — invisible.
* **The training frames were themselves JPEG/video-compressed**, so JPEG input
  *matches* training conditions rather than departing from them.

And one prohibition, from a prior incident:

> Never "optimize" by capturing at a smaller resolution — that changes the
> aspect ratio/geometry of what the model sees and breaks its learned aim.

⇒ **Reduce BYTES, never RESOLUTION.** Downscaling is explicitly off the table.

### Why it did not transfer

Two independent implementations:

```text
  pi0.5   LeRobot async_inference   gRPC + pickle     policy_server.py
          encode: src/lerobot/async_inference/image_codec.py
          decode: patched via scripts/runpod/apply_jpeg_decode_patch.sh

  N1.6    GR00T policy server       ZMQ + msgpack     gr00t.eval.run_gr00t_server
          encode: MsgSerializer.encode_custom_classes  (np.save, NO compression)
          decode: MsgSerializer.decode_custom_classes  (np.load)
```

`n16_realarm_client.py` is a hand-vendored single file reimplementing the GR00T
wire protocol. It shares no code with `image_codec.py`. Nothing was dropped —
the work simply does not span the two.

---

## 2. Design

Symmetric, additive, backward-compatible. Both sides keep accepting raw arrays,
so an unpatched client and a patched server still interoperate, and vice versa.

### Server — `~/sim/Isaac-GR00T-n16/gr00t/policy/server_client.py` (HEAD ead5283)

Add one branch to `decode_custom_classes`, alongside the existing
`__ndarray_class__` branch:

```python
if "__jpeg_ndarray__" in obj:
    buf = np.frombuffer(obj["as_jpg"], dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)          # BGR
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)        # server expects RGB
```

**The colour-order conversion is the sharp edge.** `cv2.imdecode` returns BGR;
the pipeline carries RGB. B1 (`--img-bgr-swap`) exists in the sim harness
precisely because a channel swap is a known, plausible, silent failure. Get this
wrong and the policy sees blue oranges.

### Client — `scripts/realarm/n16_realarm_client.py`

`encode_custom_classes` cannot simply compress every ndarray — joint state is
also an ndarray. Compress only the camera frames, at the point they are
assembled:

```python
# in So100Adapter.obs_to_policy_inputs
model_obs["video"] = {k: _jpeg(obs[k]) for k in self.camera_keys}
```

where `_jpeg` returns a tagged dict that `MsgSerializer` passes through
untouched. Quality **92**, matching the π0.5 measurement.

### Not in scope

RTC, changing `action_horizon`, or any resolution change. One variable at a time
— the horizon change is a separate experiment with its own risk (following a
stale plan further), and mixing them makes both uninterpretable.

---

## 3. Validation — in sim, before anything touches the arm

The sim eval talks to the **same** GR00T server, so the whole path is testable
here.

```text
  V1  unit: encode->decode round trip on a real frame. Assert shape, dtype,
      and CHANNEL ORDER against the original. Fails loudly on BGR/RGB error.
  V2  smoke: one sim run through the patched server. Must complete.
  V3  battery: n=6 canonical WITH patch vs the existing n=6 canonical baseline
      (89%, 16/18). Scores must be statistically indistinguishable.
  V4  payload: log encoded bytes per call. Expect ~1.76 MiB -> ~130 KB.
```

**V3 is the gate.** If compression costs task performance, abandon. The π0.5
evidence says it should not, but that was a different model and this checkpoint
has never been tested under compression.

---

## 4. Rollout

```text
  1. patch server, keep raw path intact           this machine
  2. V1-V4                                        this machine, ~1 h
  3. patch client, deploy to the arm machine      already have a deploy path;
                                                  .aug8-original backup pattern
  4. dry run from the arm machine (--dry_run)     no robot motion
  5. real run, with the instrumented client       needs an operator in Pune
```

Step 5 needs someone at the bench. Steps 1-4 do not.

---

## 5. Rollback

```text
  server   git -C ~/sim/Isaac-GR00T-n16 checkout gr00t/policy/server_client.py
  client   restore n16_realarm_client.py.aug8-original on the arm machine
```

Because both sides stay backward-compatible, a partial rollback is also safe:
reverting only the client leaves a patched server that still accepts raw arrays.

---

## 6. Expected outcome, and what would falsify it

```text
  per-chunk cycle   740 ms -> ~370 ms
  observation age   halved
```

Against the measured curve (89% at zero delay, 22% at 740 ms), halving the delay
should recover a substantial fraction of the loss — **but the relationship
between delay and success has only been sampled at two points.** It is not known
to be linear. A 370 ms condition has never been run.

⇒ **Run `--obs-delay 11` in sim first** (370 ms at 30 Hz). If 11 is barely better
than 22, the JPEG port buys much less than this plan assumes, and the answer is
RTC or moving the server — not compression. That single battery is cheaper than
the port and should arguably precede it.

### Honest risks

```text
  - channel order (BGR/RGB) - silent, and the harness has a flag for it because
    it has bitten this project before
  - modifying a server that currently works. Additive and reverted by one git
    checkout, but it is the component in the critical path.
  - the 370 ms benefit assumes a delay/success curve sampled at two points.
```


---

## 7. REMEASURED 2026-08-14, after the first instrumented live run

The live run replaced every estimate in section 0 with a direct measurement.

### The cycle, now measured rather than inferred

```text
  187 chunks over 171.8 s     chunk period 924 ms
  round trip   median 615 ms   p95 685   max 2078   min 586
  arm moving   267 ms/chunk    (8 of 16 actions @ 30 Hz)
  DUTY CYCLE   28.9% moving, 71.1% FROZEN
               total motion 49.9 s out of 172 s
```

Breakdown of the 615 ms:

```text
   56 ms   GPU inference          measured on loopback, same machine
  245 ms   distance to Pune       measured by ping
  314 ms   pushing 1.76 MiB       the remainder  <- THIS IS WHAT THE PORT REMOVES
```

**Only 9% of the wait is the model working. 91% is network.** Section 0's
estimate was 740 ms total with 409 ms of payload; the truth is 615 ms with
314 ms. Same conclusion, better numbers.

### What the port buys, restated

```text
  1.76 MiB -> ~130 KB at quality 92      (pi0.5 measured 14.6x on this link)
  314 ms of transfer -> ~22 ms
  cycle 615 ms -> ~300 ms
  duty cycle 28.9% moving -> ~47% moving
```

Halves the cycle. Does **not** reach continuous motion on its own — that needs
pipelining as well (option 3 in the latency analysis), and pipelining only works
once the round trip is shorter than a chunk's execution time. **Compression is
the enabler for that, which is the strongest argument for doing it first.**

### An argument for it that section 0 did not have

The training demonstrations were recorded by a human teleoperating at **30 Hz,
continuously and smoothly**. The rig executes 267 ms of motion then freezes for
657 ms. The policy is being run in a motion regime that appears nowhere in its
training data. Compression does not fix that by itself, but it halves the
discrepancy, and pipelining after it closes the gap.

### What it will NOT fix — stated plainly

The live run identified a likely root cause that is **independent of latency**: a
systematic leftward bias on `shoulder_pan` (mean -0.83, negative in **99%** of
chunks) and on `elbow_flex` (mean -2.46, also 99%), present in the policy's
output **even when replayed offline against its own training data**, where timing
plays no part.

```text
  gripper.pos bias   -0.00, negative in 50% of chunks   <- what unbiased looks like
```

⇒ **Do not expect this port to make the arm work.** It makes the system
  operable; the bias is a separate problem. Conflating them would repeat the
  mistake this investigation has already made several times.

### Section 6's precondition is now moot

Section 6 said to run `--obs-delay 11` first, to check whether halving the delay
buys anything on a curve sampled at only two points. That was the right call when
staleness was the leading hypothesis. It no longer is - the bias explains the
observed failure and staleness does not. So the justification for the port shifts:

```text
  BEFORE   "halving the delay may recover much of the 86% -> 22% loss"   speculative
  NOW      "the arm is frozen 71% of the time in a regime the policy has
            never seen, and 314 ms of that is pure waste"                measured
```

That case does not depend on the delay/success curve, so the `--obs-delay 11`
battery is no longer a precondition. Worth running eventually; not a blocker.

### Status

**Approved to implement.** Design in section 2 is unchanged and still correct.
Validation in section 3 still applies, with V3 (scores must be statistically
indistinguishable from the 86% baseline) as the gate.
