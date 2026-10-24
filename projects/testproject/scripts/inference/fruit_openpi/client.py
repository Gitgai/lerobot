"""Isolated synchronous OpenPI/LeRobot client; default is real-hardware read-only.

Explicit --execute enables movement. No configure(), EEPROM changes, homing,
automatic retry, RTC, JPEG, clipping, or simulator-coordinate conversion.
"""

import argparse
import json
import selectors
import subprocess
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
# Helpers are co-located in the repository; preserve the existing network venv.
NETWORK_PYTHON = Path(
    "/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/openpi_split_validation_20261015/venv/bin/python"
)
from contract import CHECKPOINT, JOINTS, TASK, actions, metadata, observation, target
from frame_recorder import FrameRecorder
from freshness import FreshnessGuard
from so101_trial_safety import (
    cleanup_signals,
    follower_lock,
    release_bus,
    require_motor_status,
    resolve_follower,
    stop_on_signals,
)

PROTECTIONS = (
    "Operating_Mode",
    "P_Coefficient",
    "I_Coefficient",
    "D_Coefficient",
    "Max_Torque_Limit",
    "Protection_Current",
    "Overload_Torque",
)
CAMERAS = {
    "front": "/dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0",
    "wrist": "/dev/v4l/by-id/usb-SunplusIT_Inc_AK-Camera_JV-video-index0",
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--max-control-gap-s", type=float, default=1.0)
    p.add_argument("--max-response-age-s", type=float, default=2.0)
    args = p.parse_args()
    guard = FreshnessGuard(args.max_control_gap_s, args.max_response_age_s)
    args.output.mkdir(parents=True, exist_ok=False)
    trace = (args.output / "trace.jsonl").open("x", buffering=1)

    def event(kind, **data):
        trace.write(
            json.dumps(dict(kind=kind, monotonic_ns=time.monotonic_ns(), unix_ns=time.time_ns(), **data))
            + "\n"
        )

    manifest = {
        "checkpoint": CHECKPOINT,
        "task": TASK,
        "execute": args.execute,
        "rtc": False,
        "jpeg": False,
        "control_hz": 30,
        "executed_rows_per_response": 30,
        "units": "arm degrees; gripper 0..100",
        "joint_order": JOINTS,
        "custom_integration": True,
        "trial_timer": False,
        "camera_fourcc": "MJPG",
        "camera_warmup_s": 8,
        "max_control_gap_s": args.max_control_gap_s,
        "max_response_age_s": args.max_response_age_s,
        "freshness_clock": "CLOCK_BOOTTIME; includes suspend",
        "timing_limits_are_project_policy": True,
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    robot = worker = recorder = None
    result = {"commands_sent": 0, "torque_enable_attempted": False, "torque_off_verified": False}
    workerlog = (args.output / "transport.log").open("x")
    sel = selectors.DefaultSelector()

    def check():
        guard.check()
        if (args.output / "STOP").exists():
            raise InterruptedError("Operator STOP file")
        if recorder:
            recorder.check()
            with recorder.lock:
                dropped = any(k.startswith("dropped_") for k in recorder.counts)
            if dropped:
                raise RuntimeError("Recording queue lost coverage")
        if robot and robot.bus.is_connected:
            require_motor_status(robot.bus.sync_read("Status", normalize=False))
        guard.check()

    def receive(timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            check()
            if sel.select(0.1):
                line = worker.stdout.readline()
                if not line:
                    raise RuntimeError("Transport worker exited; inspect transport.log")
                return json.loads(line)
            if worker.poll() is not None:
                raise RuntimeError("Transport worker exited")
        raise TimeoutError("Transport response deadline exceeded")

    def snapshot():
        check()
        start = time.monotonic_ns()
        raw = robot.get_observation()
        event(
            "observation",
            start_ns=start,
            state={j: raw[f"{j}.pos"] for j in JOINTS},
            camera_host_timestamps={n: c.latest_timestamp for n, c in robot.cameras.items()},
        )
        return observation(raw)

    def infer(index):
        obs = snapshot()
        path = args.output / f"request_{index:06d}.npz"
        np.savez_compressed(path, **obs)
        event("request", request_id=index, input_file=str(path))
        worker.stdin.write(json.dumps({"request_id": index, "input": str(path)}) + "\n")
        worker.stdin.flush()
        reply = receive(70)
        if reply.get("kind") != "response" or reply.get("request_id") != index:
            raise RuntimeError("Transport response ID mismatch")
        a = actions(reply)
        received_at = reply["received_boottime_s"]
        guard.check(received_at)
        event("response", **{k: v for k, v in reply.items() if k != "kind"})
        return a, received_at

    with follower_lock(), stop_on_signals():
        try:
            worker = subprocess.Popen(
                [str(NETWORK_PYTHON), str(ROOT / "transport.py")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=workerlog,
                text=True,
                bufsize=1,
            )
            sel.register(worker.stdout, selectors.EVENT_READ)
            ready = receive(25)
            if ready.get("kind") != "ready":
                raise RuntimeError("Missing transport ready")
            metadata(ready["metadata"])
            event("server_ready", metadata=ready["metadata"])
            from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
            from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
            from lerobot.robots.so_follower.so_follower import SOFollower

            robot = SOFollower(
                SOFollowerRobotConfig(
                    port=resolve_follower(),
                    id="my_so101_follower",
                    use_degrees=True,
                    max_relative_target=None,
                    disable_torque_on_disconnect=True,
                    cameras={
                        n: OpenCVCameraConfig(
                            index_or_path=v, width=640, height=480, fps=30, fourcc="MJPG", warmup_s=8
                        )
                        for n, v in CAMERAS.items()
                    },
                )
            )
            if not args.execute:

                def forbidden(*a, **kw):
                    raise RuntimeError("Motor write forbidden in observation-only mode")

                for name in (
                    "write",
                    "_write",
                    "sync_write",
                    "_sync_write",
                    "enable_torque",
                    "disable_torque",
                    "write_calibration",
                ):
                    setattr(robot.bus, name, forbidden)
            robot.bus.connect()
            check()
            if not robot.bus.is_calibrated:
                raise RuntimeError("Calibration mismatch")
            torque = robot.bus.sync_read("Torque_Enable", normalize=False)
            if set(torque) != set(JOINTS) or any(torque.values()):
                raise RuntimeError("Expected torque-off start")
            before = {k: robot.bus.sync_read(k, normalize=False) for k in PROTECTIONS}
            if any(before["Operating_Mode"].values()):
                raise RuntimeError("Expected position mode")
            event("settings_before", registers=before)
            recorder = FrameRecorder(args.output / "recording")
            for name, camera in robot.cameras.items():
                recorder.attach_camera(camera, name)
                camera.connect()
            until = time.monotonic() + 8
            while time.monotonic() < until:
                check()
                time.sleep(0.1)
            # Warm up from actual observations with torque still off; discard reply.
            infer(0)
            event("warmup_discard", request_id=0)
            guard.arm()
            if not args.execute:
                infer(1)
                after = {k: robot.bus.sync_read(k, normalize=False) for k in PROTECTIONS}
                if before != after:
                    raise RuntimeError("Settings changed unexpectedly")
                event("settings_after", registers=after)
                result["status"] = "observation_only_passed"
            else:
                # Preload raw current encoders before torque, preserving all other settings.
                current = robot.bus.sync_read("Present_Position", normalize=False)
                check()
                robot.bus.sync_write("Goal_Position", current, normalize=False)
                if robot.bus.sync_read("Goal_Position", normalize=False) != current:
                    raise RuntimeError("Holding-goal readback mismatch")
                check()
                result["torque_enable_attempted"] = True
                for joint in JOINTS:
                    check()
                    robot.bus.write("Torque_Enable", joint, 1, normalize=False)
                if robot.bus.sync_read("Torque_Enable", normalize=False) != dict.fromkeys(JOINTS, 1):
                    raise RuntimeError("Torque enable readback mismatch")
                check()
                event("holding_enabled")
                request_id = 1
                while True:
                    a, received_at = infer(request_id)
                    for row, values in enumerate(a):
                        start = time.monotonic()
                        check()
                        command = target(values)
                        guard.check(received_at)
                        event("dispatch_attempt", request_id=request_id, row=row, action=command)
                        # A stalled log write must not be followed by an old command.
                        guard.check(received_at)
                        sent = robot.send_action(command)
                        result["commands_sent"] += 1
                        event(
                            "dispatch_return",
                            request_id=request_id,
                            row=row,
                            action=sent,
                            measured=robot.bus.sync_read("Present_Position"),
                        )
                        time.sleep(max(0, 1 / 30 - (time.monotonic() - start)))
                    request_id += 1
        except BaseException as exc:
            result["status"] = (
                "stopped" if isinstance(exc, (KeyboardInterrupt, SystemExit, InterruptedError)) else "error"
            )
            result["error"] = repr(exc)
            event("termination", **result)
        finally:
            with cleanup_signals():
                errors = []
                if robot and robot.bus.is_connected:
                    try:
                        if result["torque_enable_attempted"]:
                            errors.extend(release_bus(robot.bus))
                            result["torque_off_verified"] = not errors
                        else:
                            result["torque_off_verified"] = robot.bus.sync_read(
                                "Torque_Enable", normalize=False
                            ) == dict.fromkeys(JOINTS, 0)
                    except Exception as exc:
                        errors.append(repr(exc))
                    finally:
                        if robot.bus.is_connected:
                            robot.bus.disconnect(disable_torque=False)
                if robot:
                    for camera in robot.cameras.values():
                        try:
                            if camera.is_connected:
                                camera.disconnect()
                        except Exception as exc:
                            errors.append(repr(exc))
                if worker:
                    worker.terminate()
                    try:
                        worker.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        worker.kill()
                        worker.wait()
                if recorder:
                    try:
                        recorder.close()
                    except Exception as exc:
                        errors.append(repr(exc))
                result["cleanup_errors"] = errors
                event("cleanup", **result)
                (args.output / "result.json").write_text(json.dumps(result, indent=2))
                print(json.dumps(result, indent=2), flush=True)
                sel.close()
                workerlog.close()
                trace.close()
    if result.get("status") == "error" or result["cleanup_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
