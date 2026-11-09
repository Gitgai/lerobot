#!/usr/bin/env python3
"""Regression tests for the read-only live shadow verifier."""

from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from shadow_grasp_verifier import ShadowGraspVerifier, front_tray_retention  # noqa: E402


TRACE = Path("/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_small_orange_restoredcam_20261109_t2_t5")


class ShadowGraspVerifierTest(unittest.TestCase):
    def read_rgb(self, path: Path) -> np.ndarray:
        image = cv2.imread(str(path))
        self.assertIsNotNone(image, path)
        return np.ascontiguousarray(image[:, :, ::-1])

    def test_tray_release_success_and_miss_are_separated(self):
        success = self.read_rgb(TRACE / "frames/ep02_chunk047_front.jpg")
        miss = self.read_rgb(TRACE / "frames/ep03_chunk032_front.jpg")
        self.assertEqual(front_tray_retention(success)["status"], "inside")
        self.assertEqual(front_tray_retention(miss)["status"], "outside")

    def test_verifier_has_no_action_method_or_robot_reference(self):
        verifier = ShadowGraspVerifier()
        self.assertFalse(hasattr(verifier, "action"))
        self.assertFalse(hasattr(verifier, "robot"))


if __name__ == "__main__":
    unittest.main()
