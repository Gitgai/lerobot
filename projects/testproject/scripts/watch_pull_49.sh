#!/bin/bash
SSH="ssh -i /home/prakash-gaikwad/.ssh/runpod_ed25519 -p 24241 -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 root@157.157.221.29"
DEST=/data/act_orange49_checkpoints; mkdir -p "$DEST"
CKPT=/workspace/outputs/act_orange_49/checkpoints/020000/pretrained_model
for i in $(seq 1 220); do
  if $SSH "test -f $CKPT/model.safetensors" 2>/dev/null; then
    echo "20k checkpoint detected; pulling..."
    $SSH "tar czf - -C /workspace/outputs/act_orange_49/checkpoints 020000" 2>/dev/null | tar xzf - -C "$DEST" 2>/dev/null
    ms=$(stat -c %s "$DEST/020000/pretrained_model/model.safetensors" 2>/dev/null || echo 0)
    [ "$ms" -ge 206699736 ] && { echo "PULLED_49_20K_OK $(du -sh $DEST/020000/pretrained_model|cut -f1)"; exit 0; }
    echo "pull incomplete ($ms), retry"
  fi
  if [ $((i % 6)) -eq 0 ]; then echo "[$(printf %03d $i)] $($SSH "grep -aoE '[0-9]+/20000' /workspace/train_49.log | tail -1" 2>/dev/null)"; fi
  sleep 60
done
echo "TIMEOUT after ~220min"; exit 1
