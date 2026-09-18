import json, os, shutil
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path("/home/kiran/lerobot_assets/datasets")
BASE = ROOT / "new30_merged"          # 30 eps: task0 orange(20) + task1 tomato(10), trimmed
RECOV = ROOT / "recovery30_v21"       # 30 eps: task0 orange (recovery)
DST  = ROOT / "new30_plus_recov30"    # -> 60 eps
CAMS = ["observation.images.front", "observation.images.wrist"]

def read_tasks(p):
    return {json.loads(l)["task_index"]: json.loads(l)["task"]
            for l in (p/"meta/tasks.jsonl").read_text().splitlines() if l.strip()}

base_tasks  = read_tasks(BASE)     # {0: orange, 1: tomato}
recov_tasks = read_tasks(RECOV)    # {0: orange}
# unified task table = BASE ordering (0 orange, 1 tomato)
unified = [{"task_index": ti, "task": base_tasks[ti]} for ti in sorted(base_tasks)]
str2idx = {t["task"]: t["task_index"] for t in unified}
# every recovery task string must already exist in BASE
for s in recov_tasks.values():
    assert s in str2idx, f"recovery task {s!r} not in base tasks {list(str2idx)}"

if DST.exists(): shutil.rmtree(DST)
(DST/"data/chunk-000").mkdir(parents=True)
(DST/"meta").mkdir(parents=True)
for c in CAMS: (DST/"videos/chunk-000"/c).mkdir(parents=True)

new_i, running, eps_meta = 0, 0, []
def add(src, tmap):
    global new_i, running
    eps = sorted(int(p.stem.split("_")[-1]) for p in (src/"data/chunk-000").glob("*.parquet"))
    n0 = new_i
    for old_i in eps:
        df = pd.read_parquet(src/f"data/chunk-000/episode_{old_i:06d}.parquet")
        s = tmap[int(df["task_index"].iloc[0])]
        uti = str2idx[s]
        df["episode_index"] = np.int64(new_i)
        df["index"] = np.arange(running, running+len(df), dtype=np.int64)
        df["task_index"] = np.int64(uti)
        running += len(df)
        df.to_parquet(DST/f"data/chunk-000/episode_{new_i:06d}.parquet", index=False)
        for c in CAMS:
            tgt = (src/f"videos/chunk-000/{c}/episode_{old_i:06d}.mp4").resolve()
            os.symlink(tgt, DST/f"videos/chunk-000/{c}/episode_{new_i:06d}.mp4")
        eps_meta.append({"episode_index": new_i, "tasks": [s], "length": int(len(df))})
        new_i += 1
    print(f"  {src.name:22s} {len(eps):2d} eps -> new indices {n0}..{new_i-1}")

add(BASE, base_tasks)
add(RECOV, recov_tasks)

(DST/"meta/episodes.jsonl").write_text("".join(json.dumps(e)+"\n" for e in eps_meta))
(DST/"meta/tasks.jsonl").write_text("".join(json.dumps(t)+"\n" for t in unified))
info = json.loads((BASE/"meta/info.json").read_text())
info["total_episodes"]=new_i; info["total_frames"]=running
info["total_videos"]=new_i*len(CAMS); info["total_tasks"]=len(unified)
info["splits"]={"train":"0:%d"%new_i}
(DST/"meta/info.json").write_text(json.dumps(info,indent=4))
shutil.copy2(BASE/"meta/modality.json", DST/"meta/modality.json")

broken=[p for p in (DST/"videos").rglob("*.mp4") if not p.resolve().exists()]
from collections import Counter
tc=Counter(e["tasks"][0] for e in eps_meta)
print(f"  DONE: {new_i} episodes, {running} frames, broken_links={len(broken)}")
for s,n in tc.items(): print(f"    {n:2d} eps  {s!r}")
print("  meta files:", sorted(p.name for p in (DST/'meta').iterdir()))
