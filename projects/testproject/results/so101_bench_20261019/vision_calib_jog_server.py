#!/usr/bin/env python3
"""Guarded SO-101 jog server for vision-assisted waypoint calibration.

The server never executes a command left by an earlier session.  Commands are
written to ~/vision_calib_jog_cmd and state is reported in
~/vision_calib_jog_state.json.  Every move is clamped and restricted to the
motion envelope observed in the 169 demonstrations.  ``goto_zguard Z Q``
also stops a move if live FK tool height falls below Z millimetres, while
``goto_closed Q`` uses measured-joint feedback to reach a 0.5 degree tolerance.
``close_stall_live IMAGE`` actively holds the verified pose while capturing the
wrist frame, then applies both gates before closing. ``close_stall_guarded
IMAGE`` remains available for an externally synchronized frame. The legacy
``close_stall`` command is disabled so a 2-D image match cannot bypass the pose
guard. ``hold_capture_test IMAGE`` runs the same synchronized pose hold and
camera capture but never closes the gripper.
"""

import json
import pathlib
import time

import cv2
import numpy as np
from generate_tray_cartesian_path import DEFAULT_URDF, Kinematics
from load_compensated_hold import CompensationLimitError, compensated_arm_command
from tray_grasp_pose_guard import SUCCESSFUL_GRASP_Q, evaluate_pose
from wrist_grasp_gate import DEFAULT_REFERENCE, DEFAULT_TOLERANCE_PX, evaluate

try:
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
except ImportError:
    from lerobot.robots.so101_follower import SO101Follower, SO101FollowerConfig


HOME = pathlib.Path.home()
CMD = HOME / "vision_calib_jog_cmd"
STATE = HOME / "vision_calib_jog_state.json"
SAVED = HOME / "vision_calib_jog_saved.json"
JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
JI = {"pan": 0, "lift": 1, "elbow": 2, "wflex": 3, "wroll": 4, "grip": 5}
ENV_MIN = np.array([-111.4, -104.9, -92.0, -99.6, -75.3, 1.6]) - 5
ENV_MAX = np.array([84.0, 82.9, 97.3, 103.1, 90.9, 88.2]) + 5
PROTECTIONS = {"Max_Torque_Limit": 500, "Protection_Current": 250, "Overload_Torque": 25}
KINEMATICS = Kinematics(DEFAULT_URDF)
MAX_WRIST_IMAGE_AGE_S = 5.0
WRIST_CAMERA = "/dev/video6"
WRIST_WARMUP_FRAMES = 45
WRIST_SYNC_FRAMES = 10
LIVE_CLOSE_APPROVED = False
WRIST_REFERENCE = cv2.imread(str(DEFAULT_REFERENCE))
if WRIST_REFERENCE is None:
    raise RuntimeError(f"missing wrist grasp reference: {DEFAULT_REFERENCE}")


robot = SO101Follower(SO101FollowerConfig(port="/dev/ttyACM0", id="my_so101_follower", cameras={}))


def q():
    obs = robot.get_observation()
    return np.array([float(obs[f"{joint}.pos"]) for joint in JOINTS], dtype=np.float32)


def write_state(message=""):
    STATE.write_text(json.dumps({"q": q().round(1).tolist(), "msg": message, "t": time.time()}))


def tool_z_mm(joints):
    return float(KINEMATICS.fk(np.asarray(joints[:5], dtype=float))[:3, 3][2] * 1000)


def move(target, max_s=30.0, min_tool_z_mm=None):
    target = np.asarray(target, dtype=np.float32)
    if np.any(target < ENV_MIN) or np.any(target > ENV_MAX):
        return f"REFUSED outside envelope {target.round(1).tolist()}"
    current = q()
    if min_tool_z_mm is not None and tool_z_mm(current) < min_tool_z_mm:
        return f"REFUSED tool z {tool_z_mm(current):.1f} mm below {min_tool_z_mm:.1f} mm guard"
    limit = np.array([0.6] * 5 + [1.5], dtype=np.float32)
    started = time.time()
    while time.time() - started < max_s:
        delta = target - current
        if np.abs(delta).max() < 0.5:
            break
        current = current + np.clip(delta, -limit, limit)
        robot.send_action({f"{joint}.pos": float(value) for joint, value in zip(JOINTS, current)})
        time.sleep(1 / 30)
        if min_tool_z_mm is not None:
            measured = q()
            measured_z_mm = tool_z_mm(measured)
            if measured_z_mm < min_tool_z_mm:
                return f"STOPPED clearance, tool z {measured_z_mm:.1f} mm below {min_tool_z_mm:.1f} mm guard"
    time.sleep(0.3)
    reached = q()
    if np.abs(reached - target).max() >= 2.0:
        return f"STOPPED short, target {target.round(1).tolist()}, at {reached.round(1).tolist()}"
    return f"at {reached.round(1).tolist()}"


def align_closed_loop(target, max_s=30.0, tolerance_deg=0.5, initial_bias=None):
    target = np.asarray(target, dtype=np.float32)
    if np.any(target < ENV_MIN) or np.any(target > ENV_MAX):
        return f"REFUSED outside envelope {target.round(1).tolist()}", np.zeros(5, dtype=np.float32)
    initial = q()
    if np.abs((target - initial)[:5]).max() > 5.0:
        return f"REFUSED closed-loop correction over 5 deg, at {initial.round(1).tolist()}", np.zeros(
            5, dtype=np.float32
        )
    bias = (
        np.zeros(5, dtype=np.float32)
        if initial_bias is None
        else np.asarray(initial_bias, dtype=np.float32).copy()
    )
    if bias.shape != (5,) or np.abs(bias).max() > 5.0:
        return "REFUSED invalid initial closed-loop compensation", np.zeros(5, dtype=np.float32)
    started = time.time()
    while time.time() - started < max_s:
        measured = q()
        delta = target - measured
        if np.abs(delta[:5]).max() < tolerance_deg and abs(delta[5]) < 1.0:
            return f"at {measured.round(1).tolist()} closed-loop, bias {bias.round(1).tolist()}", bias
        try:
            arm_command, bias, _ = compensated_arm_command(target[:5], measured[:5], bias)
        except CompensationLimitError:
            return f"STOPPED closed-loop compensation exceeded 5 deg, at {measured.round(1).tolist()}", bias
        command = np.concatenate((arm_command, [target[5]])).astype(np.float32)
        command[5] = target[5]
        if np.any(command < ENV_MIN) or np.any(command > ENV_MAX):
            return f"STOPPED closed-loop command outside envelope {command.round(1).tolist()}", bias
        robot.send_action({f"{joint}.pos": float(value) for joint, value in zip(JOINTS, command)})
        time.sleep(1 / 30)
    reached = q()
    return (
        f"STOPPED closed-loop timeout, target {target.round(1).tolist()}, at {reached.round(1).tolist()}",
        bias,
    )


def move_closed_loop(target, max_s=30.0, tolerance_deg=0.5):
    message, _ = align_closed_loop(target, max_s=max_s, tolerance_deg=tolerance_deg)
    return message


def close_on_stall():
    measured = q()
    arm_target = measured[:5].copy()
    open_grip = float(measured[5])
    grip_target = open_grip
    bias = np.zeros(5, dtype=np.float32)
    max_arm_drift = 0.0
    last = open_grip
    unchanged = 0
    while measured[5] > 2.0:
        arm_error = arm_target - measured[:5]
        max_arm_drift = max(max_arm_drift, float(np.abs(arm_error).max()))
        if np.abs(arm_error).max() > 5.0:
            command = np.concatenate((arm_target + bias, [open_grip])).astype(np.float32)
            robot.send_action({f"{joint}.pos": float(value) for joint, value in zip(JOINTS, command)})
            time.sleep(0.3)
            reached = q()
            return (
                f"STOPPED close arm drift {max_arm_drift:.1f} deg; reopened to {reached[5]:.1f}, "
                f"q {reached.round(1).tolist()}"
            )
        bias += np.clip(arm_error, -0.05, 0.05)
        if np.abs(bias).max() > 5.0:
            command = np.concatenate((arm_target, [open_grip])).astype(np.float32)
            robot.send_action({f"{joint}.pos": float(value) for joint, value in zip(JOINTS, command)})
            time.sleep(0.3)
            reached = q()
            return (
                f"STOPPED close compensation exceeded 5 deg; reopened to {reached[5]:.1f}, "
                f"q {reached.round(1).tolist()}"
            )
        grip_target = max(2.0, grip_target - 2.0)
        command = np.concatenate((arm_target + bias, [grip_target])).astype(np.float32)
        robot.send_action({f"{joint}.pos": float(value) for joint, value in zip(JOINTS, command)})
        time.sleep(1 / 15)
        measured = q()
        unchanged = unchanged + 1 if abs(float(measured[5]) - last) < 0.8 else 0
        last = float(measured[5])
        if unchanged >= 5:
            break
    time.sleep(0.3)
    reached = q()
    max_arm_drift = max(max_arm_drift, float(np.abs(arm_target - reached[:5]).max()))
    return (
        f"close-on-stall-hold at {reached[5]:.1f}, max arm drift {max_arm_drift:.1f} deg, "
        f"bias {bias.round(1).tolist()}, q {reached.round(1).tolist()}"
    )


def guarded_close(image_path):
    """Close only when independent measured-pose and wrist-image gates pass."""
    if not image_path.is_absolute():
        return "REFUSED close: wrist image path must be absolute"
    try:
        image_age_s = time.time() - image_path.stat().st_mtime
    except FileNotFoundError:
        return f"REFUSED close: wrist image does not exist {image_path}"
    if image_age_s < 0 or image_age_s > MAX_WRIST_IMAGE_AGE_S:
        return f"REFUSED close: wrist image is {image_age_s:.1f} s old (limit {MAX_WRIST_IMAGE_AGE_S:.1f} s)"
    measured = q()
    pose = evaluate_pose(measured)
    if not pose.safe_pose_for_close:
        return (
            "REFUSED close: 3-D pose gate rejected; "
            f"distance {pose.cartesian_distance_mm:.3f} mm "
            f"(limit {pose.cartesian_tolerance_mm:.1f}), "
            f"max joint error {pose.max_joint_error_deg:.3f} deg "
            f"(limit {pose.joint_tolerance_deg:.1f})"
        )
    image = cv2.imread(str(image_path))
    if image is None:
        return f"REFUSED close: could not read wrist image {image_path}"
    vision = evaluate(image, WRIST_REFERENCE, tolerance=DEFAULT_TOLERANCE_PX)
    if not vision["safe_to_close"]:
        return (
            "REFUSED close: wrist image gate rejected; "
            f"error {vision['finger_frame_error_px']} px "
            f"(limit +/-{DEFAULT_TOLERANCE_PX:.1f} each axis)"
        )
    # Re-read after vision processing so motion during the image check cannot
    # carry stale pose permission into the close.
    final_pose = evaluate_pose(q())
    if not final_pose.safe_pose_for_close:
        return (
            "REFUSED close: 3-D pose changed after image gate; "
            f"distance {final_pose.cartesian_distance_mm:.3f} mm, "
            f"max joint error {final_pose.max_joint_error_deg:.3f} deg"
        )
    return close_on_stall()


def capture_holding_successful_pose(image_path, *, close_after_capture):
    """Capture while retaining one load-compensation state through every phase."""
    if not image_path.is_absolute():
        return "REFUSED live close: wrist image path must be absolute"
    target = np.concatenate((SUCCESSFUL_GRASP_Q, [37.0])).astype(np.float32)
    alignment, bias = align_closed_loop(target)
    if alignment.startswith(("REFUSED", "STOPPED")):
        return f"REFUSED live close: could not align pose; {alignment}"

    cap = cv2.VideoCapture(WRIST_CAMERA)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        return f"REFUSED live close: could not open wrist camera {WRIST_CAMERA}"

    frame = None
    max_error = 0.0
    try:
        for _ in range(WRIST_WARMUP_FRAMES):
            measured = q()
            try:
                arm_command, bias, error = compensated_arm_command(SUCCESSFUL_GRASP_Q, measured[:5], bias)
            except CompensationLimitError:
                return "REFUSED live close: pose-hold compensation exceeded 5 deg"
            max_error = max(max_error, float(np.abs(error).max()))
            command = np.concatenate((arm_command, [37.0])).astype(np.float32)
            robot.send_action({f"{joint}.pos": float(value) for joint, value in zip(JOINTS, command)})
            ok, candidate = cap.read()
            if ok and candidate is not None:
                frame = candidate
        # Camera startup takes long enough for load-dependent elbow drift. With
        # the device now warm and its one-frame buffer active, restore the pose
        # using measured feedback, then capture only post-correction frames.
        realignment, bias = align_closed_loop(target, initial_bias=bias)
        if realignment.startswith(("REFUSED", "STOPPED")):
            return f"REFUSED live close: post-warmup alignment failed; {realignment}"
        frame = None
        for _ in range(WRIST_SYNC_FRAMES):
            measured = q()
            try:
                arm_command, bias, error = compensated_arm_command(SUCCESSFUL_GRASP_Q, measured[:5], bias)
            except CompensationLimitError:
                return "REFUSED live close: pose-hold compensation exceeded 5 deg"
            max_error = max(max_error, float(np.abs(error).max()))
            command = np.concatenate((arm_command, [37.0])).astype(np.float32)
            robot.send_action({f"{joint}.pos": float(value) for joint, value in zip(JOINTS, command)})
            time.sleep(1 / 30)
            ok, candidate = cap.read()
            if ok and candidate is not None:
                frame = candidate
    finally:
        cap.release()
    if frame is None:
        return "REFUSED live close: wrist camera returned no frame"

    image_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(image_path), frame):
        return f"REFUSED live close: could not save wrist frame {image_path}"
    pose = evaluate_pose(q())
    if not pose.safe_pose_for_close:
        return (
            "REFUSED live close: synchronized pose gate rejected; "
            f"distance {pose.cartesian_distance_mm:.3f} mm, "
            f"max joint error {pose.max_joint_error_deg:.3f} deg, "
            f"max hold error {max_error:.3f} deg"
        )
    if not close_after_capture:
        return (
            "hold-capture PASS without close; "
            f"distance {pose.cartesian_distance_mm:.3f} mm, "
            f"max joint error {pose.max_joint_error_deg:.3f} deg, "
            f"retained bias {bias.round(2).tolist()}"
        )
    return guarded_close(image_path)


try:
    robot.connect(calibrate=False)
    for register, value in PROTECTIONS.items():
        robot.bus.write(register, "gripper", value, normalize=False)
    got = {register: int(robot.bus.read(register, "gripper", normalize=False)) for register in PROTECTIONS}
    if got != PROTECTIONS:
        raise RuntimeError(f"gripper protection mismatch: {got}")

    # Ignore any command left from an earlier invocation.
    last = CMD.read_text().strip() if CMD.exists() else ""
    write_state(f"ready; protections {got}")
    print("vision calibration jog server ready", flush=True)

    while True:
        text = CMD.read_text().strip() if CMD.exists() else ""
        if not text or text == last:
            time.sleep(0.1)
            continue
        last = text
        parts = text.split()
        command = parts[0]
        current = q()
        try:
            if command == "goto":
                message = move([float(value) for value in parts[1].split(",")])
            elif command == "goto_zguard":
                message = move(
                    [float(value) for value in parts[2].split(",")],
                    min_tool_z_mm=float(parts[1]),
                )
            elif command == "goto_closed":
                message = move_closed_loop([float(value) for value in parts[1].split(",")])
            elif command == "delta":
                joint, value = parts[1].split(",")
                target = current.copy()
                target[JI[joint]] += float(value)
                message = move(target)
            elif command == "grip":
                target = current.copy()
                target[5] = float(parts[1])
                message = move(target)
            elif command == "close_stall_guarded":
                if len(parts) != 2:
                    message = "REFUSED close: usage close_stall_guarded /absolute/wrist_image.jpg"
                else:
                    message = guarded_close(pathlib.Path(parts[1]))
            elif command == "close_stall_live":
                if not LIVE_CLOSE_APPROVED:
                    message = (
                        "REFUSED live close: blocked after repeated loaded-pose hold failures; "
                        "preserve learned compensation and empty-test before enabling"
                    )
                elif len(parts) != 2:
                    message = "REFUSED live close: usage close_stall_live /absolute/wrist_image.jpg"
                else:
                    message = capture_holding_successful_pose(
                        pathlib.Path(parts[1]), close_after_capture=True
                    )
            elif command == "hold_capture_test":
                if len(parts) != 2:
                    message = "REFUSED hold test: usage hold_capture_test /absolute/wrist_image.jpg"
                else:
                    message = capture_holding_successful_pose(
                        pathlib.Path(parts[1]), close_after_capture=False
                    )
            elif command == "close_stall":
                message = "REFUSED close: use close_stall_live with a synchronized wrist image"
            elif command == "read":
                message = f"q {current.round(1).tolist()}"
            elif command == "save":
                saved = json.loads(SAVED.read_text()) if SAVED.exists() else {}
                saved[parts[1]] = current.round(1).tolist()
                SAVED.write_text(json.dumps(saved, indent=2))
                message = f"saved {parts[1]} = {saved[parts[1]]}"
            elif command == "off":
                robot.bus.disable_torque()
                message = "TORQUE OFF"
            elif command == "quit":
                write_state("quit")
                break
            else:
                message = f"unknown command {command}"
        except Exception as error:
            message = f"ERROR {type(error).__name__}: {error}"
        write_state(message)
        print(message, flush=True)
finally:
    try:
        robot.disconnect()
    except Exception:
        pass
