"""Convert the 2026-09-15 recordings from LeRobot v3.0 to v2.1, trimming orange.

GR00T trains on v2.1; everything recorded on the Acer is v3.0. The layouts are:

    v3.0  data/chunk-000/file-NNN.parquet
          videos/observation.images.CAM/chunk-000/file-NNN.mp4   (episodes PACKED)
    v2.1  data/chunk-000/episode_NNNNNN.parquet
          videos/chunk-000/observation.images.CAM/episode_NNNNNN.mp4

Trimming (orange only) follows the operator's rule of 2026-09-15:

    1. Never touch the front of the episode - it starts at rest already.
    2. Find the moment the arm reaches its rest posture AT THE END and stays there.
    3. Keep 3 more seconds after that moment.
    4. Cut everything after.

"At the end" is load-bearing: the arm is at rest at the START too, so the search
runs BACKWARD from the last frame. See docs/EPISODE_TRIMMING.md.

An episode that does not end parked at home is NOT trimmed - it is copied whole
and reported. The tool never guesses where to cut.

Each source video is decoded ONCE and split into its episodes in a single
ffmpeg pass; seeking to frame 14000 of an AV1 file per episode would otherwise
dominate the runtime.
"""

import glob
import json
import os
import shutil
import subprocess
import sys

import av
import numpy as np
import pandas as pd

SRC = "/data/lerobot_datasets"
DST = "/data/lerobot_v21"
REST_J = [1, 2, 3]
HOME_TOL = 5.0
STILL_DEG = 0.2
SAFETY_S = 3.0
FPS = 30
CAMS = ["front", "wrist"]

SETS = [
    ("so101_pick_test_c270_wrist_10eps_final",    "orange_final10_v21",    True,
     "pick up the orange and place it on the plate"),
    ("so101_pick_test_c270_wrist_10eps_adjusted", "orange_adjusted10_v21", True,
     "pick up the orange and place it on the plate"),
    ("so101_pick_test_c270_wrist_tomato_10eps",   "tomato10_v21",          False,
     "pick up the tomato and place it on the plate"),
]


def state_col(df):
    return "observation.state" if "observation.state" in df.columns else "action"


def video_files(d, cam):
    vs = sorted(glob.glob("%s/%s/videos/observation.images.%s/**/*.mp4" % (SRC, d, cam), recursive=True))
    out, n = [], 0
    for v in vs:
        with av.open(v) as c:
            k = c.streams.video[0].frames or sum(1 for _ in c.decode(c.streams.video[0]))
        out.append((v, n, n + k - 1))
        n += k
    return out


def frame_count(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", mp4],
                       capture_output=True, text=True).stdout.strip()
    return int(r) if r.isdigit() else -1


def canonical_rest():
    finals = []
    for d, _, _, _ in SETS:
        ps = sorted(glob.glob("%s/%s/data/**/*.parquet" % (SRC, d), recursive=True))
        df = pd.concat([pd.read_parquet(p) for p in ps])
        c = state_col(df)
        finals += [np.stack(g[c].values)[-1] for _, g in df.groupby("episode_index")]
    return np.median(np.array(finals), axis=0)[REST_J]


CANON = canonical_rest()


def keep_frames(st, do_trim):
    """How many frames to keep, and why. Never guesses."""
    if not do_trim:
        return len(st), "kept whole (not trimmed)"
    if np.any(np.abs(st[-1, REST_J] - CANON) > HOME_TOL):
        return len(st), "REFUSED: does not end at home - kept whole"
    if len(st) > FPS and np.abs(np.diff(st[-FPS:], axis=0)).max() > STILL_DEG:
        return len(st), "REFUSED: still moving at the end - kept whole"
    at = np.all(np.abs(st[:, REST_J] - CANON) <= HOME_TOL, axis=1)
    i = len(st) - 1
    while i > 0 and at[i - 1]:
        i -= 1
    return min(len(st), i + SAFETY_S * FPS), "trimmed at rest +%gs" % SAFETY_S


def cut_video(src_mp4, clips, outdir, cam):
    """One decode pass, many outputs. clips = [(local_start, local_count, ep_index)]."""
    if not clips:
        return
    parts, maps, outs = [], [], []
    parts.append("[0:v]split=%d%s" % (len(clips), "".join("[s%d]" % i for i in range(len(clips)))))
    for i, (a, n, ep) in enumerate(clips):
        parts.append("[s%d]select='between(n\\,%d\\,%d)',setpts=N/%d/TB[o%d]" % (i, a, a + n - 1, FPS, i))
        maps += ["-map", "[o%d]" % i]
        outs.append("%s/observation.images.%s/episode_%06d.mp4" % (outdir, cam, ep))
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src_mp4, "-filter_complex", ";".join(parts)]
    for i, o in enumerate(outs):
        cmd += ["-map", "[o%d]" % i, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "18", "-preset", "veryfast", "-r", str(FPS), o]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("ffmpeg failed on %s\n%s" % (src_mp4, r.stderr[-1500:]))


def convert(src_name, dst_name, do_trim, task):
    src = "%s/%s" % (SRC, src_name)
    dst = "%s/%s" % (DST, dst_name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs("%s/data/chunk-000" % dst)
    os.makedirs("%s/meta" % dst)
    for c in CAMS:
        os.makedirs("%s/videos/chunk-000/observation.images.%s" % (dst, c))

    ps = sorted(glob.glob("%s/data/**/*.parquet" % src, recursive=True))
    df = pd.concat([pd.read_parquet(p) for p in ps]).reset_index(drop=True)
    col = state_col(df)
    vf = {c: video_files(src_name, c) for c in CAMS}

    print("\n  === %s -> %s ===" % (src_name.replace("so101_pick_test_c270_wrist_", ""), dst_name))
    print("     ep   rows    keep   note")

    rows, running, notes = [], 0, []
    clips = {c: {} for c in CAMS}          # source file -> list of clips
    for new_i, (ep, g) in enumerate(df.groupby("episode_index")):
        st = np.stack(g[col].values)
        a_glob = int(g.index[0])
        keep, why = keep_frames(st, do_trim)
        keep = int(keep)
        print("     %2d %5d  %6d   %s" % (ep, len(st), keep, why))
        if why.startswith("REFUSED"):
            notes.append("%s ep%d: %s" % (dst_name, ep, why))

        sub = g.iloc[:keep].copy()
        sub["episode_index"] = np.int64(new_i)
        sub["index"] = np.arange(running, running + keep, dtype=np.int64)
        sub["frame_index"] = np.arange(keep, dtype=np.int64)
        sub["task_index"] = np.int64(0)
        if "timestamp" in sub.columns:
            sub["timestamp"] = np.arange(keep, dtype=np.float64) / FPS
        running += keep
        sub.to_parquet("%s/data/chunk-000/episode_%06d.parquet" % (dst, new_i), index=False)
        rows.append({"episode_index": new_i, "tasks": [task], "length": keep})

        for c in CAMS:
            hit = [(v, x) for v, x, y in vf[c] if x <= a_glob <= y]
            if len(hit) != 1:
                raise SystemExit("episode %d straddles video files in %s" % (ep, c))
            v, x = hit[0]
            clips[c].setdefault(v, []).append((a_glob - x, keep, new_i))

    for c in CAMS:
        for v, cl in clips[c].items():
            cut_video(v, cl, "%s/videos/chunk-000" % dst, c)

    # verify: every output video must have exactly as many frames as its parquet
    bad = []
    for r in rows:
        for c in CAMS:
            mp4 = "%s/videos/chunk-000/observation.images.%s/episode_%06d.mp4" % (dst, c, r["episode_index"])
            n = frame_count(mp4)
            if n != r["length"]:
                bad.append("ep%d %s: %d video frames vs %d rows" % (r["episode_index"], c, n, r["length"]))

    with open("%s/meta/episodes.jsonl" % dst, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    with open("%s/meta/tasks.jsonl" % dst, "w") as fh:
        fh.write(json.dumps({"task_index": 0, "task": task}) + "\n")

    info = json.load(open("%s/meta/info.json" % src))
    info["codebase_version"] = "v2.1"
    info["total_episodes"] = len(rows)
    info["total_frames"] = running
    info["total_videos"] = len(rows) * len(CAMS)
    info["total_chunks"] = 1
    info["total_tasks"] = 1
    info["splits"] = {"train": "0:%d" % len(rows)}
    info["data_path"] = "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet"
    info["video_path"] = "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"
    json.dump(info, open("%s/meta/info.json" % dst, "w"), indent=4)

    print("     wrote %d episodes, %d frames -> %s" % (len(rows), running, dst))
    return running, bad, notes


os.makedirs(DST, exist_ok=True)
print("  canonical rest pose: %s   home tol +/-%.0f deg, still within %.1f deg"
      % (np.round(CANON, 1), HOME_TOL, STILL_DEG))
total, all_bad, all_notes = 0, [], []
for a, b, t, task in SETS:
    n, bad, notes = convert(a, b, t, task)
    total += n; all_bad += bad; all_notes += notes

print("\n  TOTAL %d frames written to %s" % (total, DST))
if all_notes:
    print("\n  EPISODES NOT TRIMMED (flagged, kept whole):")
    for n in all_notes:
        print("    " + n)
if all_bad:
    print("\n  *** FRAME-COUNT MISMATCHES - DO NOT TRAIN ON THIS ***")
    for b in all_bad:
        print("    " + b)
    sys.exit(1)
print("\n  all episodes verified: video frames == parquet rows")
