import os, numpy as np, cv2
from collections import Counter
from lerobot.datasets.lerobot_dataset import LeRobotDataset

root=os.path.expanduser("~/esp_recovery")
ds=LeRobotDataset("local/esp_recovery", root=root)
epcol=[int(v) for v in ds.hf_dataset["episode_index"]]
N=ds.meta.total_episodes

def rgb_of(i):
    t=ds[i]["observation.images.front"]
    a=(t.numpy()*255).clip(0,255).astype("uint8")
    if a.shape[0] in (1,3): a=np.transpose(a,(1,2,0))
    return a

def find_plate(bgr):
    b,g,r=cv2.split(bgr.astype(np.int16))
    val=bgr.max(2)
    mask=(((b-r)>10)&(val>60)&(val<210)).astype(np.uint8)*255
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((15,15),np.uint8))
    cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    cs=[c for c in cs if cv2.contourArea(c)>12000]
    if not cs: return None,0
    c=max(cs,key=cv2.contourArea)
    return cv2.convexHull(c), cv2.contourArea(c)

def orange_blobs(bgr):
    hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
    m=cv2.inRange(hsv,(5,120,90),(28,255,255))
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
    out=[]
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for c in cs:
        a=cv2.contourArea(c)
        if a<400: continue
        x,y,w,h=cv2.boundingRect(c)
        fill=a/(w*h); aspect=min(w,h)/max(w,h)
        if fill<0.5 or aspect<0.45: continue
        out.append((a,(x+w/2,y+h/2)))
    return out

def inside(hull,pt):
    return cv2.pointPolygonTest(hull,(float(pt[0]),float(pt[1])),False)>=0

rows=[]; panels=[]
for e in range(N):
    idxs=[i for i,v in enumerate(epcol) if v==e]
    # last 40% of the episode, up to 15 samples
    lo=int(len(idxs)*0.60)
    seg=idxs[lo:]
    step=max(1,len(seg)//15); sample=seg[::step][-15:]
    per=[]; best_annot=None; best_platearea=-1
    for i in sample:
        rgb=rgb_of(i); bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
        hull,pa=find_plate(bgr); blobs=orange_blobs(bgr)
        if hull is None:
            per.append("OCC"); continue
        onb=[b for b in blobs if inside(hull,b[1])]
        offb=[b for b in blobs if not inside(hull,b[1])]
        if onb: v="ON"
        elif offb: v="OFF"
        else: v="OCC"
        per.append(v)
        if pa>best_platearea:  # least-occluded plate frame for the panel
            best_platearea=pa; ann=bgr.copy()
            cv2.drawContours(ann,[hull],-1,(255,0,0),2)
            for b in onb: cv2.circle(ann,(int(b[1][0]),int(b[1][1])),8,(0,220,0),-1)
            for b in offb: cv2.circle(ann,(int(b[1][0]),int(b[1][1])),8,(0,0,230),-1)
            best_annot=ann
    c=Counter(per)
    on=c.get("ON",0); off=c.get("OFF",0); occ=c.get("OCC",0)
    if on>=2 and on>=off: final="ON"
    elif off>on and off>=2: final="OFF"
    else: final="UNSURE"
    rows.append((e,final,on,off,occ,len(per)))
    if best_annot is None:
        best_annot=cv2.cvtColor(rgb_of(sample[-1]),cv2.COLOR_RGB2BGR)
    p=cv2.resize(best_annot,(240,180))
    col=(0,200,0) if final=="ON" else ((0,160,230) if final=="UNSURE" else (0,0,230))
    cv2.putText(p,f"e{e} {final} {on}/{off}/{occ}",(4,16),cv2.FONT_HERSHEY_SIMPLEX,0.45,col,2)
    panels.append(p)

rowsimg=[np.hstack(panels[r0:r0+6]) for r0 in range(0,30,6)]
cv2.imwrite(os.path.expanduser("~/place_score_montage2.jpg"),np.vstack(rowsimg))
onc=sum(1 for r in rows if r[1]=="ON")
offc=sum(1 for r in rows if r[1]=="OFF")
unc=sum(1 for r in rows if r[1]=="UNSURE")
print("PER-EPISODE  e verdict ON/OFF/OCC frames")
for r in rows: print(f"  e{r[0]:02d}  {r[1]:6s}  {r[2]}/{r[3]}/{r[4]}")
print("SUMMARY  ON="+str(onc)+"  OFF="+str(offc)+"  UNSURE="+str(unc)+"  (of 30)")
print("  ON list:    "+str([r[0] for r in rows if r[1]=="ON"]))
print("  OFF list:   "+str([r[0] for r in rows if r[1]=="OFF"]))
print("  UNSURE list:"+str([r[0] for r in rows if r[1]=="UNSURE"]))
