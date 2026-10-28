"""Scripted auto-reset for the SO-101 bench: take the orange out of the tray and put it on a grid slot on the table
between trials, WITHOUT the policy. Plan: docs/so101_bench_auto_reset_plan_20261028.md (steps R0–R9).

Used by bench_client.py (--reset-between). Pure joint-space moves through the same clamped-step mover the client
uses for --return-start, plus: LOOK (overhead frame → orange + tray position), a stop-on-stall gripper close with a
hold check, a per-leg correcting move, a motion-envelope guard, and a camera VERIFY at the end.

Waypoint file (results/so101_bench_20261019/reset/reset_waypoints.json, written at the calibration session):
{
  "date": "...", "tray_photo": "reset/tray_calib.jpg",
  "start": [pan, lift, elbow, wflex, wroll, grip],
  "tray": {"px_centre": [x, y], "px_radius": r,
           "hover": [...6...],
           "descend": {"centre": [...], "near": [...], "far": [...], "left": [...], "right": [...]}},
  "slots": [{"slot": 0, "px": [x, y], "hover": [...], "place": [...]}, ...],
  "envelope": {"min": [...6...], "max": [...6...], "margin_deg": 5}
}
All joint values in LeRobot units (degrees; gripper 0–100). Nothing in here is run until the operator says go.
"""
import json, time, pathlib
import numpy as np

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
HOLD_LO, HOLD_HI = 16, 30          # gripper reading when an orange is held (bench 2026-10-26: 16–26; tomato 28–32)
AIR_HI = 12                        # ≤ this after a close = shut on air
STEP_DEG, STEP_GRIP = 1.5, 3.0     # per-step clamp at 30 Hz (same as --return-start)


class ResetFailed(RuntimeError):
    pass


# ---------- vision (the September recovery-work detector) ----------
def orange_centroid(bgr):
    import cv2
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); m = cv2.inRange(hsv, (5, 120, 90), (28, 255, 255))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)); m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    best = None
    for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        a = cv2.contourArea(c)
        if a < 400: continue
        x, y, w, h = cv2.boundingRect(c)
        if a / (w * h) < 0.5 or min(w, h) / max(w, h) < 0.45: continue
        if best is None or a > best[0]: best = (a, (x + w / 2, y + h / 2))
    return None if best is None else best[1]


def tray_centre(bgr):
    import cv2
    b, g, r = cv2.split(bgr.astype(np.int16)); val = bgr.max(2)
    mask = (((b - r) > 10) & (val > 60) & (val < 210)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)); mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cs = [c for c in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0] if cv2.contourArea(c) > 12000]
    if not cs: return None
    M = cv2.moments(max(cs, key=cv2.contourArea)); return (M["m10"] / M["m00"], M["m01"] / M["m00"])


# ---------- the routine ----------
class Reset:
    def __init__(self, robot, front_cam, waypoints_path, log, dry_run=False, px_per_cm=None):
        self.robot, self.cam, self.log, self.dry = robot, front_cam, log, dry_run
        self.W = json.loads(pathlib.Path(waypoints_path).read_text())
        self.env = self.W.get("envelope"); self.px_per_cm = px_per_cm or self.W.get("px_per_cm", 8.0)
        self.frames_dir = pathlib.Path(waypoints_path).parent / "frames"; self.frames_dir.mkdir(exist_ok=True)

    # -- primitives --
    def q(self):
        o = self.robot.get_observation(); return np.array([float(o[f"{j}.pos"]) for j in JOINTS], dtype=np.float32)

    def in_envelope(self, target):
        if not self.env: return True
        lo = np.array(self.env["min"]) - self.env.get("margin_deg", 5); hi = np.array(self.env["max"]) + self.env.get("margin_deg", 5)
        return bool(np.all(target >= lo) and np.all(target <= hi))

    def move(self, target, name, max_s=15.0, grip_override=None):
        """Clamped move; refuses targets outside the training envelope; one correcting move at the end (R1b)."""
        target = np.array(target, dtype=np.float32).copy()
        if grip_override is not None: target[5] = grip_override
        if not self.in_envelope(target): raise ResetFailed(f"{name}: target outside the motion envelope {target.round(0).tolist()}")
        cur = self.q(); lim = np.array([STEP_DEG] * 5 + [STEP_GRIP], dtype=np.float32); t0 = time.time()
        while time.time() - t0 < max_s:
            d = target - cur
            if np.abs(d).max() < 0.5: break
            cur = cur + np.clip(d, -lim, lim)
            if not self.dry: self.robot.send_action({f"{j}.pos": float(v) for j, v in zip(JOINTS, cur)})
            time.sleep(1 / 30)
        time.sleep(0.25); got = self.q()
        if np.abs(got[:5] - target[:5]).max() > 2.0 and not self.dry:        # R1b correcting move
            for _ in range(60):
                d = target - got
                if np.abs(d[:5]).max() < 1.0: break
                got = got + np.clip(d, -lim, lim); self.robot.send_action({f"{j}.pos": float(v) for j, v in zip(JOINTS, got)}); time.sleep(1 / 30)
            time.sleep(0.25); got = self.q()
        self.log({"event": "reset_leg", "leg": name, "target": target.round(1).tolist(), "reached": got.round(1).tolist()})
        return got

    def close_on_stall(self):
        """R3: close in 2-unit steps, stop when the reading stops changing; return the stall reading."""
        if self.dry: return 45.0
        cur = self.q(); last = cur[5]; same = 0
        while cur[5] > 2:
            cur[5] = max(2.0, cur[5] - 2.0); self.robot.send_action({f"{j}.pos": float(v) for j, v in zip(JOINTS, cur)}); time.sleep(1 / 15)
            now = self.q()[5]
            same = same + 1 if abs(now - last) < 0.8 else 0
            last = now
            if same >= 5: break
        time.sleep(0.3); return float(self.q()[5])

    def snap(self, tag):
        bgr = self.cam.read()[:, :, ::-1].copy()
        import cv2; cv2.imwrite(str(self.frames_dir / f"{int(time.time())}_{tag}.jpg"), bgr); return bgr

    # -- steps --
    def look(self):
        bgr = self.snap("look"); o = orange_centroid(bgr); t = tray_centre(bgr)
        if t is None: raise ResetFailed("tray not found in the overhead frame")
        tc = np.array(self.W["tray"]["px_centre"]); drift = float(np.hypot(*(np.array(t) - tc)))
        if drift > 1.0 * self.px_per_cm: raise ResetFailed(f"tray moved {drift / self.px_per_cm:.1f} cm from calibration")
        if o is None or np.hypot(*(np.array(o) - tc)) > self.W["tray"]["px_radius"]: raise ResetFailed("no orange inside the tray")
        dx, dy = np.array(o) - tc; r = self.W["tray"]["px_radius"] * 0.35
        key = "centre" if np.hypot(dx, dy) < r else ("left" if abs(dx) > abs(dy) and dx < 0 else "right" if abs(dx) > abs(dy) else "near" if dy > 0 else "far")
        self.log({"event": "reset_look", "orange_px": [float(o[0]), float(o[1])], "tray_px": [float(t[0]), float(t[1])], "descent": key})
        return key

    def run(self, slot_idx):
        """R0–R9 for one reset. Raises ResetFailed; the caller stops the row."""
        W = self.W; t0 = time.time(); slot = W["slots"][slot_idx]
        q0 = self.q()
        if np.abs(q0[:5] - np.array(W["start"][:5])).max() > 4: self.move(W["start"], "R0_to_start")
        held = None
        for attempt in range(3):
            key = self.look()                                                             # R0b (and R4's re-look)
            self.move(W["tray"]["hover"], "R1_hover_tray", grip_override=45)              # R1 (+R1b inside)
            self.move(W["tray"]["descend"][key], "R2_descend_" + key, grip_override=45)   # R2
            if self.dry:
                self.log({"event": "reset_dry", "note": "would close here"}); held = 45; break
            g = self.close_on_stall()                                                      # R3
            self.log({"event": "reset_close", "attempt": attempt, "gripper": g})
            if HOLD_LO <= g <= HOLD_HI: held = g; break
            self.move(W["tray"]["hover"], "R4_reopen_lift", grip_override=45)             # R4
        if held is None: self.move(W["start"], "R4_fail_to_start", grip_override=45); raise ResetFailed("no hold after 3 attempts")
        hov = np.array(W["tray"]["hover"], dtype=np.float32); hov[5] = held
        self.move(hov, "R5_lift")                                                          # R5
        sh = np.array(slot["hover"], dtype=np.float32); sh[5] = held; self.move(sh, f"R6_carry_slot{slot_idx}")   # R6
        pl = np.array(slot["place"], dtype=np.float32); pl[5] = held; self.move(pl, "R7_lower")                   # R7
        self.move(pl, "R7_open", grip_override=45); time.sleep(0.5)
        self.move(sh, "R8_retreat", grip_override=45); self.move(W["start"], "R8_to_start", grip_override=45)     # R8
        bgr = self.snap("verify"); o = orange_centroid(bgr); t = tray_centre(bgr)                                 # R9
        ok_slot = o is not None and np.hypot(*(np.array(o) - np.array(slot["px"]))) <= 3.0 * self.px_per_cm
        ok_tray = t is not None and np.hypot(*(np.array(t) - np.array(W["tray"]["px_centre"]))) <= 1.0 * self.px_per_cm
        ok_arm = np.abs(self.q()[:5] - np.array(W["start"][:5])).max() <= 2.0 and self.q()[5] >= 40
        rec = {"event": "reset", "slot": slot_idx, "held_gripper": held, "orange_px": None if o is None else [float(o[0]), float(o[1])],
               "ok_slot": bool(ok_slot), "ok_tray": bool(ok_tray), "ok_arm": bool(ok_arm), "wall_s": round(time.time() - t0, 1), "dry_run": self.dry}
        self.log(rec)
        if not self.dry and not (ok_slot and ok_tray and ok_arm): raise ResetFailed(f"verify failed: {rec}")
        return rec
