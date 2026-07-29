"""JPEG codec for observation images sent from robot_client to policy_server.

Raw 640x480x3 frames are ~0.9 MB each; three cameras make every observation
~2.8 MB, which dominates upload time on residential links and stalls the
control cycle. JPEG at quality ~92 shrinks the payload ~20x and matches the
compression already applied to dataset frames the policy was trained on.

The wire format stays pickle: compressed entries are dicts marked with
JPEG_KEY, so servers without this codec fail loudly (shape mismatch) rather
than silently misreading pixels, and uncompressed clients keep working with
patched servers.
"""

from __future__ import annotations

import numpy as np

JPEG_KEY = "__jpeg__"


def compress_observation_images(observation: dict, quality: int) -> dict:
    """Replace HxWx3 uint8 image arrays with JPEG-bytes markers, in place."""
    import cv2

    for key, value in list(observation.items()):
        if isinstance(value, np.ndarray) and value.ndim == 3 and value.dtype == np.uint8 and value.shape[2] == 3:
            ok, buffer = cv2.imencode(
                ".jpg", cv2.cvtColor(value, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, int(quality)]
            )
            if ok:
                observation[key] = {JPEG_KEY: buffer.tobytes(), "shape": value.shape}
    return observation


def decompress_observation_images(observation: dict) -> dict:
    """Decode JPEG-bytes markers produced by compress_observation_images, in place."""
    import cv2

    for key, value in list(observation.items()):
        if isinstance(value, dict) and JPEG_KEY in value:
            array = cv2.imdecode(np.frombuffer(value[JPEG_KEY], dtype=np.uint8), cv2.IMREAD_COLOR)
            observation[key] = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
    return observation
