#!/usr/bin/env python3
"""Read-only orange grasp and release verifier for the controlled SO-101 bench.

The verifier observes the same front/wrist RGB frames and measured joints that
the policy receives.  It never returns an action and has no robot reference.
Its thresholds are provisional and must be validated in shadow mode before any
motor gate is considered.
"""

from __future__ import annotations

from collections import deque
import math

import cv2
import numpy as np


WIDTH, HEIGHT = 640, 480
WRIST_X_BAND = (220 / WIDTH, 480 / WIDTH)
WRIST_Y_BAND = (90 / HEIGHT, 310 / HEIGHT)
WRIST_RADIUS_BAND = (70 / HEIGHT, 180 / HEIGHT)
TRAY_POLYGON = np.array([[65, 10], [230, 10], [245, 185], [205, 210], [75, 195]], np.int32)


def wrist_orange(image_rgb: np.ndarray) -> dict:
    """Return the unchanged broad wrist-circle diagnostic on an RGB frame."""
    image = cv2.resize(image_rgb[:, :, ::-1], (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    gray = cv2.medianBlur(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 9)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=80,
        param1=80, param2=35, minRadius=60, maxRadius=180,
    )
    yy, xx = np.ogrid[:HEIGHT, :WIDTH]
    candidates = []
    for x, y, radius in ([] if circles is None else circles[0]):
        mask = (xx - x) ** 2 + (yy - y) ** 2 <= (0.72 * radius) ** 2
        saturation = float(np.mean(hsv[:, :, 1][mask]))
        value = float(np.mean(hsv[:, :, 2][mask]))
        if saturation < 90 or value < 180:
            continue
        candidates.append((saturation + value + 0.7 * radius, float(x), float(y), float(radius)))
    if not candidates:
        return {"status": "unknown", "reason": "no confident fruit circle"}
    _, x, y, radius = max(candidates)
    inside = (
        WRIST_X_BAND[0] <= x / WIDTH <= WRIST_X_BAND[1]
        and WRIST_Y_BAND[0] <= y / HEIGHT <= WRIST_Y_BAND[1]
        and WRIST_RADIUS_BAND[0] <= radius / HEIGHT <= WRIST_RADIUS_BAND[1]
    )
    return {
        "status": "eligible" if inside else "ineligible",
        "reason": "inside reviewed grasp band" if inside else "outside reviewed grasp band",
        "x": round(x, 1), "y": round(y, 1), "radius": round(radius, 1),
    }


def _front_colour_candidate(image_bgr: np.ndarray) -> tuple[float, float] | None:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([3, 100, 70]), np.array([28, 255, 255]))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, _, stats, centres = cv2.connectedComponentsWithStats(mask)
    candidates = []
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        if 300 <= area <= 10_000 and x > 1 and y > 1 and x + width < WIDTH - 1:
            aspect = min(width, height) / max(width, height)
            fill = area / (width * height)
            if aspect >= 0.35 and fill >= 0.25:
                candidates.append((area, float(centres[index][0]), float(centres[index][1])))
    candidates = [item for item in candidates if 50 <= item[1] <= 300 and 60 <= item[2] <= 280]
    if not candidates:
        return None
    # Release verification runs only after transport to the fixed upper-left
    # tray.  Select the compact orange-coloured component nearest that work
    # region; the wooden table and a cable at the top-left share some hue.
    _, x, y = min(candidates, key=lambda item: math.hypot(item[1] - 160, item[2] - 145))
    return x, y


def _front_circle_candidate(image_bgr: np.ndarray) -> tuple[float, float] | None:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.medianBlur(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY), 9)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=40,
        param1=80, param2=20, minRadius=15, maxRadius=50,
    )
    if circles is None:
        return None
    yy, xx = np.ogrid[:HEIGHT, :WIDTH]
    candidates = []
    for x, y, radius in circles[0]:
        mask = (xx - x) ** 2 + (yy - y) ** 2 <= (0.65 * radius) ** 2
        hue = float(np.mean(hsv[:, :, 0][mask]))
        saturation = float(np.mean(hsv[:, :, 1][mask]))
        value = float(np.mean(hsv[:, :, 2][mask]))
        if 3 <= hue <= 28 and saturation >= 120 and value >= 90:
            candidates.append((saturation + 0.2 * value + radius, float(x), float(y)))
    if not candidates:
        return None
    _, x, y = max(candidates)
    return x, y


def front_tray_retention(image_rgb: np.ndarray) -> dict:
    """Locate the orange and classify it against the fixed overhead tray ROI."""
    image = cv2.resize(image_rgb[:, :, ::-1], (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    centre = _front_colour_candidate(image) or _front_circle_candidate(image)
    if centre is None:
        return {"status": "unknown", "reason": "orange not confidently located in front view"}
    x, y = centre
    inside = cv2.pointPolygonTest(TRAY_POLYGON, (x, y), False) >= 0
    return {
        "status": "inside" if inside else "outside",
        "reason": "orange centre inside fixed tray ROI" if inside else "orange centre outside fixed tray ROI",
        "x": round(x, 1), "y": round(y, 1),
    }


class ShadowGraspVerifier:
    """Stateful, read-only verifier. ``update`` only returns JSON-safe data."""

    def __init__(self) -> None:
        self.episode = None
        self.previous_grip = None
        self.preclose = deque(maxlen=3)
        self.attempt = None
        self.attempt_number = 0
        self.retained = False
        self.release_checked = False
        self.tray_result = {"status": "not_checked", "reason": "release not observed"}

    def reset(self, episode: int) -> None:
        self.episode = episode
        self.previous_grip = None
        self.preclose.clear()
        self.attempt = None
        self.attempt_number = 0
        self.retained = False
        self.release_checked = False
        self.tray_result = {"status": "not_checked", "reason": "release not observed"}

    def update(
        self, episode: int, chunk: int, front_rgb: np.ndarray,
        wrist_rgb: np.ndarray, state: np.ndarray,
    ) -> dict:
        if episode != self.episode:
            self.reset(episode)
        state = np.asarray(state, dtype=float)
        grip = float(state[5])
        wrist = wrist_orange(wrist_rgb)
        prior_two_eligible = len(self.preclose) >= 2 and list(self.preclose)[-2:] == ["eligible", "eligible"]
        transition = None

        close_started = (
            self.attempt is None and self.previous_grip is not None
            and self.previous_grip - grip >= 6.0 and grip <= 42.0
        )
        if close_started:
            self.attempt_number += 1
            self.attempt = {
                "number": self.attempt_number,
                "start_chunk": chunk,
                "start_state": state[:5].copy(),
                "preclose": "eligible" if prior_two_eligible else "blocked",
                "closed_samples": 0,
                "eligible_closed_samples": 0,
                "minimum_grip": grip,
            }
            transition = "close_started"

        if self.attempt is not None and not self.retained:
            attempt = self.attempt
            attempt["minimum_grip"] = min(attempt["minimum_grip"], grip)
            if grip <= 35.0:
                attempt["closed_samples"] += 1
                if wrist["status"] == "eligible":
                    attempt["eligible_closed_samples"] += 1
            motion = float(np.max(np.abs(state[:5] - attempt["start_state"])))
            enough_evidence = (
                attempt["closed_samples"] >= 2
                and attempt["eligible_closed_samples"] >= 2
                and motion >= 5.0
                and grip <= 35.0
            )
            if enough_evidence:
                self.retained = True
                transition = "retained_lift"
            elif (
                attempt["closed_samples"] >= 1 and grip >= 38.0
            ) or chunk - attempt["start_chunk"] >= 12:
                transition = "grasp_not_retained"
                self.attempt = None

        if self.retained and not self.release_checked and self.attempt is not None:
            minimum = self.attempt["minimum_grip"]
            if grip >= 35.0 and grip - minimum >= 10.0:
                self.tray_result = front_tray_retention(front_rgb)
                self.release_checked = True
                transition = (
                    "release_verified" if self.tray_result["status"] == "inside"
                    else "release_failed_or_unknown"
                )

        result = {
            "ep": episode,
            "chunk": chunk,
            "mode": "shadow_only",
            "wrist": wrist,
            "preclose_two_consecutive": prior_two_eligible,
            "gripper": round(grip, 3),
            "phase": (
                "released" if self.release_checked and self.tray_result["status"] == "inside"
                else "release_failed_or_unknown" if self.release_checked
                else "retained_lift" if self.retained
                else "evaluating_close" if self.attempt is not None
                else "observing"
            ),
            "transition": transition,
            "attempt": None if self.attempt is None else {
                key: value for key, value in self.attempt.items() if key != "start_state"
            },
            "tray": self.tray_result,
        }
        self.preclose.append(wrist["status"])
        self.previous_grip = grip
        return result

    def episode_summary(self) -> dict:
        if self.release_checked and self.tray_result["status"] == "inside":
            verdict = "success"
        elif self.retained and self.release_checked:
            verdict = "delivery_failure"
        elif self.retained:
            verdict = "retained_without_verified_release"
        else:
            verdict = "acquisition_failure"
        return {
            "ep": self.episode,
            "mode": "shadow_only",
            "verdict": verdict,
            "attempts": self.attempt_number,
            "retained_lift": self.retained,
            "tray": self.tray_result,
            "active_attempt_at_cap": self.attempt is not None and not self.retained,
        }
