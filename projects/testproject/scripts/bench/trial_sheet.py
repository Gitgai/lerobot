import sys, glob, os
from PIL import Image, ImageDraw
d=os.path.expanduser("~/trial_%s_frames"%sys.argv[1])
fronts=sorted(glob.glob(d+"/c*_front.jpg"))
n=len(fronts)
idx=[int(round(p*(n-1))) for p in [0,1/7,2/7,3/7,4/7,5/7,6/7,1.0]]
ims_f=[Image.open(fronts[i]) for i in idx]
ims_w=[Image.open(fronts[i].replace("_front","_wrist")) for i in idx]
w,h=ims_f[0].size
sheet=Image.new("RGB",(w*8,h*2+18),(0,0,0)); dr=ImageDraw.Draw(sheet)
dr.text((4,4),"TRIAL %s  top=FRONT bottom=WRIST  chunk 0..%d"%(sys.argv[1],n-1),fill=(255,255,0))
for k,(a,b) in enumerate(zip(ims_f,ims_w)):
    sheet.paste(a,(k*w,18)); sheet.paste(b,(k*w,18+h))
    dr.text((k*w+4,20),"c%d"%idx[k],fill=(0,255,0))
p=os.path.expanduser("~/trial_%s_sheet.jpg"%sys.argv[1]); sheet.save(p,quality=85); print("saved",p)
