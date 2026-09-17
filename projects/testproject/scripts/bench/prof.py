import re, sys, numpy as np
PAT=re.compile(r"lift=([-+\d.]+) grip=([-+\d.]+)")
L=[];G=[]
for line in open(sys.argv[1],errors="replace"):
    m=PAT.search(line)
    if m: L.append(float(m.group(1)));G.append(float(m.group(2)))
L=np.array(L);G=np.array(G)
closed=G<25;best=cur=0
for c in closed:
    cur=cur+1 if c else 0;best=max(best,cur)
grasp=best>=21
reopened = G[-15:].mean()>40   # gripper open at the end = released
print("GRASP=%s hold=%d gripEnd=%.0f reopened=%s liftEnd=%.0f down=%.0f%%"
      % ("YES" if grasp else "no", best, G[-15:].mean(), "yes" if reopened else "NO", L[-1], 100*(L<-60).mean()))
