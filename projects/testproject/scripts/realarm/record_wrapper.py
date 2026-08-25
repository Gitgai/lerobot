"""lerobot-record, with our HTTP wrist camera registered first.

The wrist camera is a Raspberry Pi stream served over HTTP by pi_wrist_proxy.
lerobot-record only knows the camera types that have been IMPORTED before the
config is parsed, so importing http_camera here is what makes
`{wrist: {type: http, ...}}` legal on the command line. Without this the
recorder would reject the config - or worse, a future edit could silently
drop the wrist camera and produce a dataset the policies cannot use.
"""
import sys

sys.path.insert(
    0, "/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/scripts"
)
import http_camera  # noqa: F401  - registers the "http" camera type

# the front camera is a normal USB camera; its type must be registered too,
# or `{front: {type: opencv, ...}}` is rejected on the command line
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401

from lerobot.scripts.lerobot_record import main

if __name__ == "__main__":
    main()
