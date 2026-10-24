"""R0.5: exact and near duplicate EPISODES across the whole merged set, plus degenerate episodes.
Runs over every parquet (no video). Outputs manifest.csv (one row per episode with verdict) and prints a summary.
exact dup  = identical action stream (sha1 of float32 bytes rounded to 1e-3) → same trajectory, any source
near dup   = same length AND |mean action| within 0.05 per joint AND different source (the author's fingerprint, per episode)
degenerate = length < 60 frames, or total action motion (sum over joints of std) < 2.0, or NaN
"""

import collections
import csv
import glob
import hashlib
import json
import os
import sys

import numpy as np
import pyarrow.parquet as pq

D, OUT = sys.argv[1], sys.argv[2]
eps = {e["episode_index"]: e for e in map(json.loads, open(D + "/meta/episodes.jsonl"))}
files = sorted(glob.glob(D + "/data/chunk-*/episode_*.parquet"))
print("parquet files:", len(files), "of", len(eps), flush=True)
rows = []
for i, f in enumerate(files):
    ep = int(os.path.basename(f)[8:14])
    t = pq.read_table(f, columns=["action", "observation.state", "timestamp"])
    a = np.asarray(t["action"].to_pylist(), dtype=np.float32)
    n = len(a)
    nan = bool(np.isnan(a).any())
    motion = float(np.nan_to_num(a).std(axis=0).sum()) if n > 1 else 0.0
    h = hashlib.sha1(np.round(np.nan_to_num(a), 3).tobytes()).hexdigest()[:16]
    ma = np.nan_to_num(a).mean(axis=0) if n else np.zeros(6)
    rows.append(
        dict(
            episode_index=ep,
            source=eps[ep]["source_dataset"],
            length=n,
            task=eps[ep]["tasks"][0] if eps[ep]["tasks"] else "",
            motion=round(motion, 2),
            nan=nan,
            hash=h,
            mean=ma.round(2).tolist(),
        )
    )
    if i % 2000 == 0:
        print(f"  {i}/{len(files)}", flush=True)
byhash = collections.defaultdict(list)
for r in rows:
    byhash[r["hash"]].append(r)
exact_groups = [g for g in byhash.values() if len(g) > 1]
exact_dup_eps = sum(len(g) - 1 for g in exact_groups)
cross = sum(1 for g in exact_groups if len({r["source"] for r in g}) > 1)
# near dups: bucket by length, compare means
bylen = collections.defaultdict(list)
for r in rows:
    bylen[r["length"]].append(r)
near = set()
for L, g in bylen.items():
    if len(g) < 2:
        continue
    M = np.array([r["mean"] for r in g])
    S = [r["source"] for r in g]
    H = [r["hash"] for r in g]
    for i in range(len(g)):
        d = np.abs(M - M[i]).max(axis=1)
        for j in np.where(d < 0.05)[0]:
            if j > i and S[i] != S[j] and H[i] != H[j]:
                near.add((g[i]["episode_index"], g[j]["episode_index"]))
for r in rows:
    v = []
    if r["nan"]:
        v.append("nan")
    if r["length"] < 60:
        v.append("short")
    if r["motion"] < 2.0:
        v.append("static")
    if len(byhash[r["hash"]]) > 1 and byhash[r["hash"]][0]["episode_index"] != r["episode_index"]:
        v.append("exact_dup")
    r["verdict"] = ",".join(v) if v else "keep"
with open(OUT + "/manifest.csv", "w", newline="") as f:
    w = csv.DictWriter(
        f, fieldnames=["episode_index", "source", "length", "task", "motion", "nan", "hash", "verdict"]
    )
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in w.fieldnames})
vc = collections.Counter(r["verdict"] for r in rows)
print("\nVERDICTS:", dict(vc.most_common()))
print(
    f"exact duplicate groups: {len(exact_groups)} ({exact_dup_eps} redundant episodes; {cross} groups span >1 source)"
)
src_of_dups = collections.Counter(r["source"] for g in exact_groups for r in g)
print("sources with most exact duplicates:", src_of_dups.most_common(8))
print(f"near-duplicate pairs across sources (same length, mean within 0.05, different hash): {len(near)}")
pairs = collections.Counter(
    tuple(sorted((eps[a]["source_dataset"], eps[b]["source_dataset"]))) for a, b in list(near)[:5000]
)
print("top cross-source near-dup pairs:", pairs.most_common(6))
print(
    "degenerate: short",
    sum("short" in r["verdict"] for r in rows),
    "static",
    sum("static" in r["verdict"] for r in rows),
    "nan",
    sum(r["nan"] for r in rows),
)
print("wrote", OUT + "/manifest.csv")
