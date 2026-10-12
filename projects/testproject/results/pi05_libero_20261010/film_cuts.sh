#!/usr/bin/env bash
# Film selected LIBERO episodes for three checkpoints (operator, 2026-10-12).
set -u
OPENPI=/home/kiran/sim/openpi; PROBE_PY=/home/kiran/sim/pi05-fullft-probe/.venv312/bin/python
RES=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/pi05_libero_20261010
CFG=pi05_libero_low_mem_finetune; EXP=lora_libero_20261010; PORT=8002
export TMPDIR=/home/kiran/tmp MUJOCO_GL=egl PYOPENGL_PLATFORM=egl HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTHONPATH=$OPENPI/packages/openpi-client/src XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.45
VID=$RES/videos; mkdir -p "$VID"
exec > >(tee -a "$RES/film_cuts.log") 2>&1
step(){ echo; echo "=== $(date -u +%FT%TZ) $* ==="; }
SRV=""; stop(){ [ -n "$SRV" ] && kill "$SRV" 2>/dev/null && sleep 3; SRV=""; }; trap stop EXIT
serve(){ cd "$OPENPI"; "$OPENPI/.venv/bin/python" scripts/serve_policy.py --port $PORT policy:checkpoint --policy.config "$CFG" --policy.dir "$1" > "$RES/film_server.log" 2>&1 & SRV=$!
  for i in $(seq 1 60); do "$PROBE_PY" -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',$PORT)))" && return 0; kill -0 $SRV || { tail -5 "$RES/film_server.log"; return 1; }; sleep 5; done; return 1; }
film(){ # ckpt label tasks trials
  step "cut $2: checkpoint $1 tasks=$3 trials=$4"
  serve "$OPENPI/checkpoints/$CFG/$EXP/$1" || { echo "server failed"; return; }
  "$PROBE_PY" "$RES/l2_eval_openpi.py" --task-ids "$3" --trials "$4" --trials-per-task 20 --port $PORT --out "$VID/$2/log" --row "film_$2" --video-dir "$VID/$2"
  echo "cut $2 rc=$?"; stop; }
ALL20=$(seq -s, 0 19)
film 22500 "step22500_task4_drawer"  4 "$ALL20"
film 15000 "step15000_task4_drawer"  4 "$ALL20"
film 20000 "step20000_alltasks_trial0" "$(seq -s, 0 9)" 0
step "montages (last frame of each episode, labelled)"
"$PROBE_PY" - "$VID" <<'PY'
import sys,pathlib,subprocess,glob
from PIL import Image, ImageDraw
vid=pathlib.Path(sys.argv[1])
for cut in sorted(p for p in vid.iterdir() if p.is_dir()):
    files=sorted(cut.glob("*.mp4"))
    if not files: continue
    tiles=[]
    for f in files:
        png=f.with_suffix(".last.png")
        subprocess.run(["ffmpeg","-v","error","-y","-sseof","-0.2","-i",str(f),"-frames:v","1",str(png)],check=False)
        if not png.exists(): continue
        im=Image.open(png).convert("RGB"); d=ImageDraw.Draw(im)
        lab=f.stem.replace("_"," "); color=(255,60,60) if "FAIL" in f.stem else (60,220,60)
        d.rectangle([0,0,im.width,18],fill=(0,0,0)); d.text((4,3),lab,fill=color); tiles.append(im); png.unlink()
    cols=4; rows=(len(tiles)+cols-1)//cols; w,h=tiles[0].size
    sheet=Image.new("RGB",(cols*w,rows*h),(20,20,20))
    for i,t in enumerate(tiles): sheet.paste(t,((i%cols)*w,(i//cols)*h))
    sheet.save(cut/"montage_last_frames.png"); print(cut.name, len(tiles), "episodes ->", cut/"montage_last_frames.png")
PY
ls -la "$VID"/*/ | head -80
echo "=== FILM DONE $(date -u +%FT%TZ) ==="
