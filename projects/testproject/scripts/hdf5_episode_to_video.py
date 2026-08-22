#!/usr/bin/env python3
"""Render a camera stream from a LeIsaac/Isaac Lab HDF5 recording to MP4.

Isaac Lab records camera observations as RAW uint8 frames inside the HDF5
(no video encoding), which is why episodes are ~2.2 GB per camera. This makes
one watchable, so a run can be reviewed without loading 20+ GB.

Episodes carry a per-episode `success` attribute - list them first to pick one:

    ./hdf5_episode_to_video.py --file run.hdf5 --list

Then render:

    ./hdf5_episode_to_video.py --file run.hdf5 --episode demo_1 --camera front

Needs ffmpeg on PATH (installed 2026-08-04) and h5py in the running venv.
The sim venv has both:  ~/sim/leisaac-venv/bin/python

NOTE: writes an MP4. Videos are ARTIFACTS - never commit them (hard rule #2).
Default output goes to logs/, which is already gitignored.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import h5py
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="path to the .hdf5 recording")
    parser.add_argument("--episode", default=None, help="e.g. demo_1 (default: first successful)")
    parser.add_argument("--camera", default="front", help="obs key, e.g. front | wrist")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--out", default=None, help="output mp4 (default: logs/<episode>_<camera>.mp4)")
    parser.add_argument(
        "--list", action="store_true", help="list episodes and their success flags, then exit"
    )
    args = parser.parse_args()

    with h5py.File(args.file, "r") as handle:
        data = handle["data"]

        if args.list:
            for name in data:
                episode = data[name]
                print(
                    f"  {name:<8} steps={episode.attrs.get('num_samples', '?'):<6} "
                    f"success={episode.attrs.get('success', '?')}  "
                    f"cameras={[k for k in episode['obs'] if episode['obs'][k].ndim == 4]}"
                )
            return

        episode_name = args.episode
        if episode_name is None:
            successes = [n for n in data if bool(data[n].attrs.get("success", False))]
            if not successes:
                raise SystemExit("no successful episodes; pass --episode explicitly")
            episode_name = successes[0]
            print(f"picked first successful episode: {episode_name}")

        frames = data[episode_name]["obs"][args.camera]
        count, height, width, _ = frames.shape
        out_path = Path(args.out or f"logs/{episode_name}_{args.camera}.mp4")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"{episode_name}/{args.camera}: {count} frames {width}x{height} -> {out_path}")

        # Pipe raw frames straight into ffmpeg; never materialise the whole
        # array (a single camera stream is ~2.2 GB).
        proc = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                f"{width}x{height}",
                "-r",
                str(args.fps),
                "-i",
                "-",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "23",
                str(out_path),
            ],
            stdin=subprocess.PIPE,
        )
        assert proc.stdin is not None
        for start in range(0, count, 100):
            proc.stdin.write(np.ascontiguousarray(frames[start : start + 100]).tobytes())
        proc.stdin.close()
        proc.wait()

    size_mb = out_path.stat().st_size / 1e6
    print(f"wrote {out_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
