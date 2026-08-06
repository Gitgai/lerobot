#!/usr/bin/env python3
"""Minimal Isaac Sim startup check - does the Kit engine start and stop at all?

Deliberately builds NO scene: no World, no ground plane, no asset fetch. That
separates "the engine starts" from "the engine can build a scene", so a failure
points at one or the other rather than both.

This is the script that diagnosed the 2026-08-04 driver problem:

    Isaac Sim 5.1 on driver 595.84 (R590)  -> SIGSEGV in librtx.scenedb.plugin.so
    Isaac Sim 6.0 on driver 595.84         -> clean
    Isaac Sim 5.1 on driver 580.173.02     -> clean

See docs/isaac_sim_blackwell_investigation_20260804.md.

Usage (native venv):
    cd projects/testproject
    ACCEPT_EULA=Y PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES \
        ~/sim/leisaac-venv/bin/python -u scripts/isaac_sim_smoke_test.py

Usage (container):
    docker run --rm --gpus all -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y \
        -v $PWD/scripts/isaac_sim_smoke_test.py:/test.py:ro \
        --entrypoint /isaac-sim/python.sh nvcr.io/nvidia/isaac-sim:6.0.1 /test.py

ALWAYS pass `python -u`. Kit tears down stdout during shutdown, so buffered
prints are lost and a successful run looks silent. Grep the log for
"Simulation App Startup Complete" as the authoritative success marker.
"""

import time

t0 = time.perf_counter()
from isaacsim import SimulationApp  # noqa: E402

app = SimulationApp({"headless": True})
print(f"SIM APP STARTED   {time.perf_counter() - t0:.1f}s")

for _ in range(10):
    app.update()
print("UPDATED 10x       engine loop runs")

app.close()
print("CLOSED CLEAN")
