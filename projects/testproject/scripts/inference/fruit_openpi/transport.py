"""WebSocket worker in existing network venv. No robot imports or device access."""

import json
import sys
import time

import numpy as np
import websockets.sync.client

# Preserve the existing pinned codec; do not copy an environment or vendor code.
sys.path.insert(0, "/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/openpi_split_validation_20261015/vendor")
from contract import actions, metadata
from freshness import boottime
from openpi_client import msgpack_numpy


def main():
    with websockets.sync.client.connect(
        "ws://127.0.0.1:18762", compression=None, max_size=None, open_timeout=10
    ) as ws:
        meta = metadata(msgpack_numpy.unpackb(ws.recv(timeout=15)))
        print(json.dumps({"kind": "ready", "metadata": meta}), flush=True)
        for line in sys.stdin:
            req = json.loads(line)
            with np.load(req["input"], allow_pickle=False) as f:
                obs = {k: (str(f[k].item()) if k == "prompt" else f[k]) for k in f.files}
            payload = msgpack_numpy.packb(obs)
            start = time.monotonic()
            ws.send(payload)
            result = ws.recv(timeout=60)
            received_at = boottime()
            if not isinstance(result, bytes):
                raise RuntimeError(result)
            reply = msgpack_numpy.unpackb(result)
            a = actions(reply)
            print(
                json.dumps(
                    {
                        "kind": "response",
                        "request_id": req["request_id"],
                        "actions": a.tolist(),
                        "elapsed_s": time.monotonic() - start,
                        "received_boottime_s": received_at,
                        "bytes": len(payload),
                        "server_timing": reply.get("server_timing"),
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
