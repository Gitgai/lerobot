"""Print how many episodes a LeRobot dataset holds, 0 if none/unreadable.

Counting *.mp4 files does not work: the recorder writes v3.0, which PACKS many
episodes into one video file, and puts it at videos/<key>/chunk-NNN/ rather than
v2.1's videos/chunk-NNN/<key>/. The old glob therefore always returned 0, which
made rec_esp.sh take its "empty stub" branch and rm -rf a dataset that had real
episodes in it. Read the metadata instead - it is the only honest source.
"""
import json
import sys
from pathlib import Path

try:
    info = json.loads((Path(sys.argv[1]) / "meta/info.json").read_text())
    print(int(info.get("total_episodes", 0)))
except Exception:
    print(0)
