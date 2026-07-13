#!/bin/bash
SSH="ssh -i /home/prakash-gaikwad/.ssh/runpod_ed25519 -p 24305 -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 root@157.157.221.29"
DEST=/data/act_orange_checkpoints
CKPT=/workspace/outputs/act_orange/checkpoints/020000/pretrained_model
for i in $(seq 1 150); do
  if $SSH "test -f $CKPT/model.safetensors" 2>/dev/null; then
    echo "20k checkpoint detected; pulling..."
    $SSH "tar czf - -C /workspace/outputs/act_orange/checkpoints 020000" 2>/dev/null | tar xzf - -C "$DEST" 2>/dev/null
    ms=$(stat -c %s "$DEST/020000/pretrained_model/model.safetensors" 2>/dev/null || echo 0)
    if [ "$ms" -ge 206699736 ]; then echo "PULLED_20K_OK $(du -sh $DEST/020000/pretrained_model|cut -f1)"; exit 0; fi
    echo "pull incomplete ($ms bytes), retrying next round"
  fi
  # progress heartbeat every ~5 min
  if [ $((i % 5)) -eq 0 ]; then
    P=$($SSH "grep -aoE '[0-9]+/20000' /workspace/resume.log | tail -1" 2>/dev/null)
    echo "[$(printf %03d $i)] progress: ${P:-unreachable}"
  fi
  sleep 60
done
echo "TIMEOUT: 20k not ready after ~150 min"
exit 1
