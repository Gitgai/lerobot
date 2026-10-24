"""Loopback-only existing OpenPI loader; no robot access."""

import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX")
from contract import CHECKPOINT
from openpi.policies.policy_config import create_trained_policy
from openpi.serving.websocket_policy_server import WebsocketPolicyServer
from openpi_fruit import config

if __name__ == "__main__":
    Path(__file__).with_suffix(".pid").write_text(str(os.getpid()))
    policy = create_trained_policy(config(), Path(CHECKPOINT))
    print("CHECKPOINT_READY", CHECKPOINT, flush=True)
    WebsocketPolicyServer(
        policy, host="127.0.0.1", port=18762, metadata={"checkpoint": CHECKPOINT, "rtc": False, "jpeg": False}
    ).serve_forever()
