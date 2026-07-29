#!/usr/bin/env bash
# Apply the JPEG-observation decode patch to the POD's policy_server (old lerobot code).
# Run FROM THE LAPTOP repo root. Usage: bash projects/testproject/scripts/runpod/apply_jpeg_decode_patch.sh <POD_IP> <POD_PORT>
# Idempotent: safe to run twice. Makes a .bak of the pod's policy_server.py once.
set -euo pipefail

POD_IP="${1:?pod ip}"
POD_PORT="${2:?pod ssh port}"
KEY="$HOME/.ssh/runpod_ed25519"
POD="root@$POD_IP"
AI=/workspace/lerobot/src/lerobot/async_inference
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o BatchMode=yes"

scp -q $SSH_OPTS -P "$POD_PORT" -i "$KEY" src/lerobot/async_inference/image_codec.py "$POD:$AI/image_codec.py"

ssh $SSH_OPTS -p "$POD_PORT" -i "$KEY" "$POD" "python3 - <<'EOF'
from pathlib import Path
p = Path('$AI/policy_server.py')
src = p.read_text()
if 'decompress_observation_images' in src:
    print('pod policy_server already patched')
    raise SystemExit(0)
anchor_import = 'from .configs import PolicyServerConfig'
anchor_decode = 'timed_observation = pickle.loads(received_bytes)  # nosec'
assert anchor_import in src, 'import anchor not found - pod code differs, patch manually'
assert anchor_decode in src, 'decode anchor not found - pod code differs, patch manually'
Path(str(p) + '.bak').write_text(src)
src = src.replace(anchor_import, anchor_import + '\nfrom .image_codec import decompress_observation_images', 1)
src = src.replace(anchor_decode, anchor_decode + '\n        decompress_observation_images(timed_observation.observation)', 1)
p.write_text(src)
print('pod policy_server patched OK (backup: policy_server.py.bak)')
EOF"
