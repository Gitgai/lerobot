"""SO101 trial guards. Importing this module never opens hardware."""

import fcntl
import json
import math
import signal
import sys
import time
from contextlib import contextmanager
from numbers import Integral
from pathlib import Path

FOLLOWER_PATH = Path("/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00")
HOME_TARGETS = {
    "shoulder_pan": -2.6,
    "shoulder_lift": -104.3,
    "elbow_flex": 96.7,
    "wrist_flex": 78.4,
    "wrist_roll": -0.7,
    "gripper": 48.9,
}
# Acceptance checks, NOT motion-step limits or LeRobot defaults. Retain the
# previous arm tolerance; gripper tolerance is explicitly normalized points.
ARM_TOLERANCE_DEG = 6.0
GRIPPER_TOLERANCE_POINTS = 6.0


class MotorFaultError(RuntimeError):
    """A reported motor fault or unusable status must prevent further targets."""


def require_motor_status(values):
    if not isinstance(values, dict) or set(values) != set(HOME_TARGETS):
        raise MotorFaultError(f"Incomplete motor Status read: {values!r}")
    if any(not isinstance(v, Integral) or not 0 <= v <= 255 for v in values.values()):
        raise MotorFaultError(f"Invalid motor Status read: {values!r}")
    faults = {joint: int(value) for joint, value in values.items() if value != 0}
    if faults:
        raise MotorFaultError(f"Motor Status fault; stopping commands: {faults}")


def require_follower_config(config):
    """Validate the implementation, not the registry's lossy SO100/101 alias."""
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

    # The installed registry maps both aliases to this exact class and returns
    # so100_follower for its .type, even when CLI input was so101_follower.
    # Physical identity is checked separately against FOLLOWER_PATH.
    if not isinstance(config, SOFollowerRobotConfig) or config.use_degrees is not True:
        raise ValueError("This trial guard requires SO101 follower with arm positions in degrees")


def resolve_follower():
    if not FOLLOWER_PATH.exists():
        raise RuntimeError(f"Known follower serial is missing: {FOLLOWER_PATH}")
    return str(FOLLOWER_PATH)


@contextmanager
def follower_lock():
    """Cooperative exclusion for the updated homing/client/clear entry points."""
    with (Path.home() / ".so101-follower.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another updated SO101 tool owns the follower; refusing to connect") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def make_bus(port):
    from lerobot.motors import Motor, MotorCalibration, MotorNormMode
    from lerobot.motors.feetech import FeetechMotorsBus
    from lerobot.utils.constants import HF_LEROBOT_CALIBRATION, ROBOTS

    path = Path(HF_LEROBOT_CALIBRATION) / ROBOTS / "so_follower/my_so101_follower.json"
    with path.open() as stream:
        calibration = {key: MotorCalibration(**value) for key, value in json.load(stream).items()}
    motors = {
        joint: Motor(
            index,
            "sts3215",
            MotorNormMode.RANGE_0_100 if joint == "gripper" else MotorNormMode.DEGREES,
        )
        for index, joint in enumerate(HOME_TARGETS, 1)
    }
    return FeetechMotorsBus(port=port, motors=motors, calibration=calibration)


@contextmanager
def stop_on_signals():
    def stop(signum, _frame):
        raise SystemExit(128 + signum)

    old = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        for sig in old:
            signal.signal(sig, stop)
        yield
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


@contextmanager
def cleanup_signals():
    """A second normal stop must not interrupt torque-release attempts."""
    old = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        for sig in old:
            signal.signal(sig, signal.SIG_IGN)
        yield
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


def release_bus(bus):
    """Try every joint, verify torque-off, and close even after an error."""
    errors = []
    if not bus.is_connected:
        return ["bus is not open; torque-off cannot be verified"]
    try:
        for joint in HOME_TARGETS:
            write_error = None
            try:
                # One unreachable joint must not skip release of the rest.
                bus.write("Torque_Enable", joint, 0, num_retry=2)
            except Exception as exc:
                write_error = exc
                print(
                    f"[safety] {joint}: torque-disable write reported {exc}; attempting independent readback",
                    file=sys.stderr,
                    flush=True,
                )
            try:
                # A servo status error in the write response is not proof that
                # the write was ignored. Never skip verification because of it.
                # Keep the driver's normal error checks: a faulted/failed read
                # is NOT accepted as confirmation, even if it carries a value.
                value = bus.read("Torque_Enable", joint, num_retry=2)
                if isinstance(value, bool) or not isinstance(value, Integral) or value != 0:
                    raise RuntimeError(f"torque-off readback invalid or nonzero: {value!r}")
            except Exception as exc:
                detail = f"; write also reported: {write_error}" if write_error else ""
                errors.append(f"{joint}: readback unverified: {exc}{detail}")
    finally:
        try:
            bus.disconnect(disable_torque=False)
        except Exception as exc:
            errors.append(f"closing bus: {exc}")
    if not errors:
        print("[safety] torque-off readback verified for all six motors", flush=True)
    return errors


def report_cleanup(errors, original_error):
    if errors:
        message = (
            "Cleanup incomplete; TORQUE STATE UNKNOWN. Use physical power cutoff if needed. "
            + "; ".join(errors)
        )
        print(f"[safety] {message}", file=sys.stderr, flush=True)
        if original_error is None:
            raise RuntimeError(message)


@contextmanager
def bus_session(bus):
    try:
        bus.connect()
        if not bus.is_calibrated:
            raise RuntimeError("Stored calibration does not match motors; refusing to home")
        require_motor_status(bus.sync_read("Status", normalize=False))
        yield bus
    finally:
        original_error = sys.exc_info()[1]
        with cleanup_signals():
            report_cleanup(release_bus(bus), original_error)


@contextmanager
def robot_session(robot):
    """Cover partial startup failures as well as the policy loop (SOFollower)."""
    try:
        # Explicit SOFollower connection sequence: reject recalibration prompts,
        # and preload holding goals before configure() can enable torque.
        robot.bus.connect()
        if not robot.bus.is_calibrated:
            raise RuntimeError("Stored calibration does not match motors; refusing trial")
        require_motor_status(robot.bus.sync_read("Status", normalize=False))
        current = read_positions(robot.bus)
        require_home(current)
        for joint, value in current.items():
            robot.bus.write("Goal_Position", joint, value)
        for camera in robot.cameras.values():
            camera.connect()
        require_motor_status(robot.bus.sync_read("Status", normalize=False))
        robot.configure()
        yield
    finally:
        original_error = sys.exc_info()[1]
        with cleanup_signals():
            errors = release_bus(robot.bus)
            for name, camera in robot.cameras.items():
                try:
                    if camera.is_connected:
                        camera.disconnect()
                except Exception as exc:
                    errors.append(f"camera {name}: {exc}")
            report_cleanup(errors, original_error)


def read_positions(bus):
    values = {joint: float(bus.read("Present_Position", joint)) for joint in HOME_TARGETS}
    if not all(math.isfinite(value) for value in values.values()):
        raise RuntimeError("Non-finite joint position")
    return values


def require_home(positions):
    rejected = []
    for joint, target in HOME_TARGETS.items():
        value = float(positions[joint])
        tolerance = GRIPPER_TOLERANCE_POINTS if joint == "gripper" else ARM_TOLERANCE_DEG
        unit = "normalized points" if joint == "gripper" else "deg"
        error = abs(value - target)
        print(
            f"[home] {joint}: target={target:.2f} measured={value:.2f} error={error:.2f} {unit}",
            flush=True,
        )
        if not math.isfinite(value) or error >= tolerance:
            rejected.append(f"{joint} (error {error:.2f} {unit}, limit <{tolerance})")
    if rejected:
        raise RuntimeError("NOT at home: " + ", ".join(rejected))


def home_bus(bus, seconds=5.0, hz=30.0, sleep=time.sleep):
    if not (math.isfinite(seconds) and seconds > 0 and math.isfinite(hz) and hz > 0):
        raise ValueError("Homing duration and rate must be positive and finite")
    with bus_session(bus):
        start = read_positions(bus)
        for joint, value in start.items():
            bus.write("Goal_Position", joint, value)
        bus.enable_torque()
        steps = max(1, int(seconds * hz))
        for step in range(1, steps + 1):
            require_motor_status(bus.sync_read("Status", normalize=False))
            fraction = step / steps
            for joint, target in HOME_TARGETS.items():
                bus.write(
                    "Goal_Position",
                    joint,
                    start[joint] + fraction * (target - start[joint]),
                )
            sleep(seconds / steps)
        # Check faults during settling too, not only while sending targets.
        for _ in range(10):
            require_motor_status(bus.sync_read("Status", normalize=False))
            sleep(0.1)
        require_motor_status(bus.sync_read("Status", normalize=False))
        final = read_positions(bus)
        require_home(final)
        return final


def guard_first_action(robot, output_path):
    send = robot.send_action
    pending = True

    def checked(action):
        nonlocal pending
        if pending:
            positions = read_positions(robot.bus)
            with Path(output_path).open("x") as stream:
                json.dump(
                    {
                        "monotonic_s": time.monotonic(),
                        "state": positions,
                        "units": "arm: degrees; gripper: normalized 0-100",
                    },
                    stream,
                    indent=2,
                )
            require_home(positions)
            pending = False
        return send(action)

    robot.send_action = checked
