# Reference: What Exactly Goes Over The Network To Pi05 (And Why)

Last updated: 2026-08-01

Quick-answer doc for a question that keeps coming back: what image sizes do we
send to the policy server, and what did the JPEG fix actually change?

## 1. Per Observation (one request to the server)

```text
images:      3 (top, front, wrist)
pixel size:  640x480 each - FULL RESOLUTION, UNCHANGED from training
wire format: JPEG quality 92 (client-side encode, server-side decode)
bytes:       ~60-65 KB per image -> ~190 KB total per observation
             (plus a few hundred bytes: 6 joint positions + task string)
```

## 2. The Distinction People Forget

```text
We NEVER reduced image RESOLUTION. We reduced image BYTES.

BEFORE (raw pixels, pickled):  640x480x3 x 3 cameras = ~2.77 MB / observation
AFTER  (JPEG-92):              ~190 KB / observation  (14.6x lighter)

The server decodes back to full 640x480 arrays before the model sees them.
The model's input geometry (the 4:3 world it was trained on) was never
touched - that is exactly why the fix was safe.
```

Why quality loss does not matter: measured round-trip pixel error is 0.4/255
(invisible), and Pi05 internally resizes every image to 224x224 anyway - fine
detail is discarded by the model itself. Note the training dataset frames were
also stored JPEG/video-compressed, so JPEG input matches training conditions.

Never "optimize" by capturing at a smaller resolution (e.g. 640x360): that
changes the aspect ratio/geometry of what the model sees and breaks its
learned aim (see the 2026-07-31 front-camera saga in
pi05_rtc_first_live_sessions_20260801.md).

## 3. Timing Budget (measured, RTX 3090 serving)

```text
BEFORE the JPEG fix:
  upload ~1.4 s (2.77 MB through gRPC-over-SSH-tunnel at ~2 MB/s effective)
  + GPU inference ~0.4-0.6 s  => ~1.8 s total response
AFTER:
  upload ~0.10-0.15 s + inference ~0.4-0.6 s => ~0.6-1.0 s total response

"Milliseconds" refers to the TRANSPORT part. The full response can never be
milliseconds while the GPU needs ~0.5 s to think.
The raw internet uplink was never the bottleneck (2.77 MB in ~0.1-0.3 s via
plain ssh); the tunneled gRPC path was (~2 MB/s effective).
```

## 4. Where This Lives In Code

```text
client encode: src/lerobot/async_inference/image_codec.py
               (enabled with --jpeg_quality / wrapper --jpeg-quality 92;
               OFF by default -> raw pixels, old behavior)
server decode: policy_server.py after deserialization
               (local tree patched; pod patched via
               scripts/runpod/apply_jpeg_decode_patch.sh)
Trace recording keeps FULL uncompressed frames (compression happens after
the trace recorder), so saved traces are unaffected.
```
