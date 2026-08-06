#!/usr/bin/env python3
"""Start the training-era LeRobot policy server so LeIsaac can talk to it.

WHY THIS EXISTS
---------------
LeIsaac's gRPC client pickles its RemotePolicyConfig and, in
`leisaac/policy/lerobot/__init__.py`, DELIBERATELY rewrites the pickled module
path to where those classes lived in lerobot 0.4.2:

    helpers_path = "lerobot.scripts.server.helpers"
    RemotePolicyConfig.__module__ = helpers_path
    TimedObservation.__module__   = helpers_path
    TimedAction.__module__        = helpers_path

Our training-era lerobot (upstream e40b58a8 - the ONLY code that serves the
012000 checkpoint correctly, see the Era 1 trust exam) has them at
`lerobot.async_inference.helpers`. So the server cannot unpickle and fails with:

    Client connected and ready
    ERROR Exception calling application: No module named 'lerobot.scripts.server'

This creates the mirror-image alias ON THE SERVER, then starts the real server.
Nothing about how the checkpoint is served changes - the Era 1 code-pairing rule
is preserved.

FIELD MISMATCH HANDLED
----------------------
Training-era RemotePolicyConfig has an extra field `rename_map` that LeIsaac's
copy does not send. Pickle restores dataclasses via __dict__ WITHOUT calling
__init__, so dataclass defaults never run and the attribute would simply be
absent - the server then dies on `policy_specs.rename_map`. Setting it as a
CLASS attribute gives a fallback for instances whose __dict__ lacks it.

USAGE
-----
    cd ~/lerobot_assets/lerobot_trainingera
    HF_HUB_OFFLINE=1 ./.venv/bin/python \
        ~/projects/git/nvidia/lerobot/projects/testproject/scripts/policy_server_leisaac_shim.py \
        --host=0.0.0.0 --port=8080

Then point LeIsaac at it:
    --policy_type=lerobot-pi05 --policy_host=localhost --policy_port=8080 \
    --policy_checkpoint_path=$HOME/lerobot_assets/checkpoints/pi05_012000
"""

import sys
import types

# Where LeIsaac pins its pickled classes (lerobot 0.4.2 layout).
LEISAAC_PATH = "lerobot.scripts.server.helpers"


def alias_module(path: str, source_module) -> None:
    """Register `path` in sys.modules, populated from `source_module`."""
    parts = path.split(".")
    for i in range(1, len(parts) + 1):
        sub_path = ".".join(parts[:i])
        if sub_path not in sys.modules:
            module = types.ModuleType(sub_path)
            sys.modules[sub_path] = module
            if i > 1:
                setattr(sys.modules[".".join(parts[: i - 1])], parts[i - 1], module)
    sys.modules[path].__dict__.update(source_module.__dict__)


def main() -> None:
    from lerobot.async_inference import helpers as trainingera_helpers

    # Class-level fallback for the field LeIsaac never sends (see docstring).
    if hasattr(trainingera_helpers, "RemotePolicyConfig"):
        trainingera_helpers.RemotePolicyConfig.rename_map = {}

    alias_module(LEISAAC_PATH, trainingera_helpers)

    # BOTH DIRECTIONS matter. The alias above lets us RECEIVE LeIsaac's pickles.
    # We must also SEND pickles it can read: LeIsaac's fake `lerobot` module is a
    # plain ModuleType, not a package, so a reply tagged
    # `lerobot.async_inference.helpers` fails on its side with
    #   ModuleNotFoundError: No module named 'lerobot.async_inference';
    #   'lerobot' is not a package
    # Rewriting __module__ on the classes we send makes our pickles land in the
    # namespace LeIsaac already fabricated.
    for class_name in ("TimedAction", "TimedObservation", "TimedData", "RemotePolicyConfig"):
        klass = getattr(trainingera_helpers, class_name, None)
        if klass is not None:
            klass.__module__ = LEISAAC_PATH

    print(f"[shim] aliased {LEISAAC_PATH} <-> lerobot.async_inference.helpers", flush=True)

    from lerobot.async_inference import policy_server

    # Hand the remaining argv to the real server's CLI.
    sys.argv = [sys.argv[0]] + sys.argv[1:]
    policy_server.serve() if hasattr(policy_server, "serve") else policy_server.main()


if __name__ == "__main__":
    main()
