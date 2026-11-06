#!/usr/bin/env python3
"""Regression checks for the independent 3-D tray-grasp pose guard."""

import unittest

from tray_grasp_pose_guard import evaluate_pose


class TrayGraspPoseGuardTest(unittest.TestCase):
    def test_verified_successful_pose_passes(self):
        result = evaluate_pose([74.5, -64.6, 83.2, 40.8, 0.0, 37.0])
        self.assertTrue(result.safe_pose_for_close)
        self.assertEqual(result.cartesian_distance_mm, 0.0)

    def test_image_matched_failed_pose_is_rejected(self):
        result = evaluate_pose([68.2476, -52.3275, 79.5066, 32.221, 0.0])
        self.assertFalse(result.safe_pose_for_close)
        self.assertGreater(result.cartesian_distance_mm, 19.0)
        self.assertGreater(result.max_joint_error_deg, 12.0)

    def test_cartesian_limit_is_independent_of_joint_limit(self):
        result = evaluate_pose(
            [74.5, -61.6, 83.2, 40.8, 0.0],
            joint_tolerance_deg=3.1,
        )
        self.assertFalse(result.safe_pose_for_close)
        self.assertLess(result.max_joint_error_deg, 3.1)
        self.assertGreater(result.cartesian_distance_mm, 3.0)

    def test_rejects_invalid_shape(self):
        with self.assertRaises(ValueError):
            evaluate_pose([1.0, 2.0, 3.0])


if __name__ == "__main__":
    unittest.main()
