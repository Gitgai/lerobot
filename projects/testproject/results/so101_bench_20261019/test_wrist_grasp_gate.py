#!/usr/bin/env python3
"""Regression checks for the vision-only pre-close wrist gate."""

from pathlib import Path
import unittest

import cv2

from wrist_grasp_gate import DEFAULT_REFERENCE, evaluate


HERE = Path(__file__).resolve().parent
REJECTED = (
    HERE
    / "reset/calibration_evidence/tray_centre_replay_gate_rejected_20261105/01_final_open_wrist.jpg"
)
KNOWN_MISS = (
    HERE
    / "reset/calibration_evidence/tray_left_guarded_hold_miss_20261105/04_final_open_wrist.jpg"
)


class WristGraspGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = cv2.imread(str(DEFAULT_REFERENCE))
        if cls.reference is None:
            raise RuntimeError(f"missing reference frame: {DEFAULT_REFERENCE}")

    def evaluate_path(self, path: Path) -> dict:
        image = cv2.imread(str(path))
        self.assertIsNotNone(image, path)
        return evaluate(image, self.reference, tolerance=14.0)

    def test_verified_grasp_alignment_passes(self):
        result = self.evaluate_path(DEFAULT_REFERENCE)
        self.assertTrue(result["safe_to_close"])
        self.assertEqual(result["finger_frame_error_px"], [0.0, 0.0])

    def test_watched_centre_replay_is_rejected(self):
        result = self.evaluate_path(REJECTED)
        self.assertFalse(result["safe_to_close"])
        self.assertLess(result["finger_frame_error_px"][0], -45)
        self.assertLess(result["finger_frame_error_px"][1], -25)

    def test_known_close_beside_frame_is_rejected(self):
        result = self.evaluate_path(KNOWN_MISS)
        self.assertFalse(result["safe_to_close"])
        self.assertGreater(max(abs(v) for v in result["finger_frame_error_px"]), 100)


if __name__ == "__main__":
    unittest.main()
