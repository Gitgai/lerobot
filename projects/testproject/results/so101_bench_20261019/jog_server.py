#!/usr/bin/env python3
"""Tiny jog server for the waypoint recording session (auto-reset plan). Keeps the SO-101 connected (torque on, so the arm
never sags between steps) and executes one command at a time read from ~/jog_cmd; writes the joint state to ~/jog_state.json
after every command. Driven over ssh from AI90; the operator watches and says ok / lower / left...
Commands (one line in ~/jog_cmd):
  goto p,l,e,wf,wr,g        slow clamped move to an absolute pose (LeRobot units)
  delta j,val               nudge one joint by val (j = pan|lift|elbow|wflex|wroll|grip)
  down N | up N             lower / raise the gripper tip ~N cm (lift +/-3 deg per cm, wrist_flex compensated)
  fwd N | back N            extend / retract ~N cm (lift +2, elbow -4, wflex +2 per cm, and the reverse)
  left N | right N          pan +/-3 deg per cm at ~30 cm reach
  grip G                    gripper to G
  save NAME                 append {NAME: current pose} to ~/jog_saved.json
  read                      just refresh the state file
  quit
Moves are clamped to 1.5 deg/step (3 for the gripper) at 30 Hz and refused outside the training envelope (+5 deg).
"""
import json, time, pathlib, sys
import numpy as np

HOME = pathlib.Path.home(); CMD = HOME / "jog_cmd"; STATE = HOME / "jog_state.json"; SAVED = HOME / "jog_saved.json"
JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]; JI = {"pan": 0, "lift": 1, "elbow": 2, "wflex": 3, "wroll": 4, "grip": 5}
ENV_MIN = np.array([-111.4, -104.9, -92.0, -99.6, -75.3, 1.6]) - 5; ENV_MAX = np.array([84.0, 82.9, 97.3, 103.1, 90.9, 88.2]) + 5
try:
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
except ImportError:
    from lerobot.robots.so101_follower import SO101Follower, SO101FollowerConfig
robot = SO101Follower(SO101FollowerConfig(port="/dev/ttyACM0", id="my_so101_follower", cameras={})); robot.connect(calibrate=False)


def q():
    o = robot.get_observation(); return np.array([float(o[f"{j}.pos"]) for j in JOINTS], dtype=np.float32)


def write_state(msg=""):
    STATE.write_text(json.dumps({"q": q().round(1).tolist(), "msg": msg, "t": time.time()}))


def move(target, max_s=20.0):
    target = np.array(target, dtype=np.float32)
    if np.any(target < ENV_MIN) or np.any(target > ENV_MAX): return f"REFUSED outside envelope {target.round(0).tolist()}"
    cur = q(); lim = np.array([1.5] * 5 + [3.0], dtype=np.float32); t0 = time.time()
    while time.time() - t0 < max_s:
        d = target - cur
        if np.abs(d).max() < 0.5: break
        cur = cur + np.clip(d, -lim, lim); robot.send_action({f"{j}.pos": float(v) for j, v in zip(JOINTS, cur)}); time.sleep(1 / 30)
    time.sleep(0.3); return f"at {q().round(1).tolist()}"


write_state("ready"); last = ""
print("jog server ready", flush=True)
while True:
    try:
        txt = CMD.read_text().strip() if CMD.exists() else ""
    except Exception:
        txt = ""
    if not txt or txt == last: time.sleep(0.2); continue
    last = txt; parts = txt.split(); c = parts[0]; cur = q(); msg = ""
    try:
        if c == "goto": msg = move([float(x) for x in parts[1].split(",")])
        elif c == "delta": j, v = parts[1].split(","); t = cur.copy(); t[JI[j]] += float(v); msg = move(t)
        elif c in ("down", "up"): n = float(parts[1]); s = 1 if c == "down" else -1; t = cur.copy(); t[1] += 3 * n * s; t[3] -= 1 * n * s; msg = move(t)
        elif c in ("fwd", "back"): n = float(parts[1]); s = 1 if c == "fwd" else -1; t = cur.copy(); t[1] += 2 * n * s; t[2] -= 4 * n * s; t[3] += 2 * n * s; msg = move(t)
        elif c in ("left", "right"): n = float(parts[1]); s = 1 if c == "left" else -1; t = cur.copy(); t[0] += 3 * n * s; msg = move(t)
        elif c == "grip": t = cur.copy(); t[5] = float(parts[1]); msg = move(t)
        elif c == "save":
            d = json.loads(SAVED.read_text()) if SAVED.exists() else {}; d[parts[1]] = q().round(1).tolist(); SAVED.write_text(json.dumps(d, indent=1)); msg = f"saved {parts[1]} = {d[parts[1]]}"
        elif c == "read": msg = f"q {cur.round(1).tolist()}"
        elif c == "free":   # motors off: the operator positions the arm by hand (they must be holding it)
            robot.bus.disable_torque(); msg = "FREE (torque off) — hold the arm"
        elif c == "hold":   # motors on at the current position, then report it
            now = q(); robot.bus.enable_torque(); robot.send_action({f"{j}.pos": float(v) for j, v in zip(JOINTS, now)}); time.sleep(0.3); msg = f"HOLD at {q().round(1).tolist()}"
        elif c == "quit": write_state("quit"); break
        else: msg = f"unknown {c}"
    except Exception as e:
        msg = f"ERROR {e}"
    write_state(msg); print(msg, flush=True)
robot.disconnect()
