"""Pure launcher/config tests. Never call hardware or launch a child process."""

import argparse
import unittest
from pathlib import Path
from unittest.mock import patch

import so101_runner as runner


class RunnerConfigTests(unittest.TestCase):
    def setUp(self):
        self.cfg = runner.load_config()

    def test_two_camera_builder(self):
        result = runner.camera_config(self.cfg)
        self.assertIn("front:", result)
        self.assertIn("wrist:", result)
        self.assertNotIn("top:", result)
        self.assertIn(self.cfg["camera_index"], result)
        self.assertIn(self.cfg["wrist_camera_index"], result)

    def test_no_relative_limit_when_none(self):
        result = runner.base_robot_args(self.cfg, None)
        self.assertIn("--robot.disable_torque_on_disconnect=true", result)
        self.assertFalse(any("max_relative_target" in item for item in result))

    def test_explicit_relative_limit(self):
        self.assertIn("--robot.max_relative_target=5", runner.base_robot_args(self.cfg, 5))

    def test_config_paths_are_parsed(self):
        self.assertIsInstance(self.cfg["dataset_root"], Path)
        self.assertIsInstance(self.cfg["lerobot_dir"], Path)

    def test_record_command_without_execution(self):
        args = argparse.Namespace(
            no_max_relative_target=False,
            max_relative_target=None,
            dataset_root="nonexecuted-recording-command-test",
            delete=False,
            episodes=10,
            episode_time=30,
            reset_time=15,
            resume=True,
            no_log=False,
        )
        with patch.object(runner, "run") as capture:
            runner.record(args, self.cfg)
        command = capture.call_args.args[0]
        self.assertEqual(command[0], "lerobot-record")
        for option in (
            "--dataset.num_episodes=10",
            "--dataset.episode_time_s=30",
            "--dataset.reset_time_s=15",
            "--resume=true",
            "--dataset.push_to_hub=false",
        ):
            self.assertIn(option, command)
        self.assertEqual(capture.call_args.kwargs["countdown"], (30, 15))


if __name__ == "__main__":
    unittest.main()
