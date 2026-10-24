import unittest

import numpy as np
from contract import CHECKPOINT, JOINTS, actions, metadata, observation, target


class ContractTests(unittest.TestCase):
    def test_exact_order_units(self):
        row = np.array([1, -102, 97, 78, -4, 46.0])
        self.assertEqual(list(target(row)), [j + ".pos" for j in JOINTS])
        self.assertEqual(list(target(row).values()), row.tolist())

    def test_reply_shape(self):
        self.assertEqual(actions({"actions": np.zeros((30, 6))}).shape, (30, 6))
        for a in [np.zeros((16, 6)), np.full((30, 6), np.nan)]:
            with self.assertRaises(ValueError):
                actions({"actions": a})

    def test_observation_rgb_unmodified(self):
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        image[0, 0] = [1, 2, 3]
        raw = {j + ".pos": i for i, j in enumerate(JOINTS)} | {"front": image, "wrist": image.copy()}
        out = observation(raw)
        np.testing.assert_array_equal(out["observation/image"][0, 0], [1, 2, 3])
        np.testing.assert_array_equal(out["observation/state"], np.arange(6))

    def test_wrong_image(self):
        raw = {j + ".pos": 0 for j in JOINTS} | {
            "front": np.zeros((224, 224, 3)),
            "wrist": np.zeros((480, 640, 3)),
        }
        with self.assertRaises(ValueError):
            observation(raw)

    def test_metadata(self):
        metadata({"checkpoint": CHECKPOINT, "rtc": False, "jpeg": False})
        with self.assertRaises(ValueError):
            metadata({"checkpoint": CHECKPOINT, "rtc": True, "jpeg": False})

    def test_target_invalid(self):
        with self.assertRaises(ValueError):
            target([0] * 5)
        with self.assertRaises(ValueError):
            target([0] * 5 + [float("nan")])


if __name__ == "__main__":
    unittest.main()
