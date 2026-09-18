import os, numpy as np
from PIL import Image, ImageDraw
from lerobot.datasets.lerobot_dataset import LeRobotDataset

root=os.path.expanduser("~/esp_recovery")
ds=LeRobotDataset("local/esp_recovery", root=root)
epcol=list(ds.hf_dataset["episode_index"])
N=ds.meta.total_episodes
SAMPLE=[18,19,20,21,22,27]
outdir=os.path.expanduser("~/rec_sheets"); os.makedirs(outdir,exist_ok=True)

def to_img(t):
    a=(t.numpy()*255).clip(0,255).astype("uint8")
    if a.shape[0] in (1,3): a=np.transpose(a,(1,2,0))
    return Image.fromarray(a)

# lengths for all episodes (sanity)
from collections import Counter
cnt=Counter(epcol)
print("EPLEN " + " ".join(f"{e}:{cnt[e]}" for e in range(N)))

for e in SAMPLE:
    idxs=[i for i,v in enumerate(epcol) if v==e]
    if not idxs:
        print(f"ep{e}: EMPTY"); continue
    pick=[idxs[int(round(p*(len(idxs)-1)))] for p in [0,1/7,2/7,3/7,4/7,5/7,6/7,1.0]]
    fronts=[]; wrists=[]
    for i in pick:
        it=ds[i]
        fronts.append(to_img(it["observation.images.front"]))
        wrists.append(to_img(it["observation.images.wrist"]))
    w,h=fronts[0].size
    sheet=Image.new("RGB",(w*8,h*2+18),(0,0,0))
    d=ImageDraw.Draw(sheet)
    d.text((4,4),f"esp_recovery EP {e}  top=FRONT bottom=WRIST  0->100%",fill=(255,255,0))
    for k,(f,wr) in enumerate(zip(fronts,wrists)):
        sheet.paste(f,(k*w,18)); sheet.paste(wr,(k*w,18+h))
        pct=int(round(100*k/7))
        d.text((k*w+4,20),f"{pct}%",fill=(0,255,0))
        d.text((k*w+4,20+h),f"{pct}%",fill=(0,255,0))
    p=f"{outdir}/ep_{e:02d}.jpg"; sheet.save(p,quality=85)
    print("saved",p)
