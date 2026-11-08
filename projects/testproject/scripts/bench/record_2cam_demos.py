#!/usr/bin/env python3
"""Launch LeRobot's official recorder with two cameras and a live timer."""

from __future__ import annotations

import os
import threading
import time

from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401
import lerobot.scripts.lerobot_record as lerobot_record


def install_live_timer() -> None:
    """Add a terminal and Rerun countdown without changing recorded actions."""

    original = lerobot_record.record_loop

    def timed_record_loop(*args, **kwargs):
        duration = kwargs.get("control_time_s")
        dataset = kwargs.get("dataset")
        if duration is None:
            return original(*args, **kwargs)

        phase = "RECORDING" if dataset is not None else "RESET"
        stop = threading.Event()

        def publish_timer() -> None:
            started = time.perf_counter()
            live = os.getenv("ORANGE_DEMO_LIVE") == "1"
            rr = None
            if live:
                import rerun as rr_module

                rr = rr_module
            while not stop.is_set():
                elapsed = min(time.perf_counter() - started, float(duration))
                remaining = max(float(duration) - elapsed, 0.0)
                print(
                    f"\r{phase}: {elapsed:4.1f}s elapsed, {remaining:4.1f}s remaining",
                    end="",
                    flush=True,
                )
                if rr is not None:
                    rr.log("recording/elapsed_seconds", rr.Scalars(elapsed))
                    rr.log("recording/remaining_seconds", rr.Scalars(remaining))
                    rr.log(
                        "recording/status",
                        rr.TextDocument(
                            f"# {phase}\n\n**{remaining:0.1f} seconds remaining**\n\n"
                            "Open → centre → close → lift → tray → open → move clear"
                        ),
                    )
                stop.wait(0.25)
            print()

        thread = threading.Thread(target=publish_timer, daemon=True)
        thread.start()
        try:
            return original(*args, **kwargs)
        finally:
            stop.set()
            thread.join(timeout=1.0)

    lerobot_record.record_loop = timed_record_loop


if __name__ == "__main__":
    install_live_timer()
    lerobot_record.main()
