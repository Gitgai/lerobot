#!/usr/bin/env python3
"""Launch LeRobot's official recorder with the two OpenCV camera type registered."""

from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401
from lerobot.scripts.lerobot_record import main


if __name__ == "__main__":
    main()
