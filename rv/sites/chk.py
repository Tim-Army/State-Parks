import sys
L=open(sys.argv[1]).read().splitlines();n=0;h=0
for l in L:
  if (len(l)>1 and l[1]=='|' and l[0] in 'TEACSMH') or '|' not in l: continue
  for x in l.split('|',1)[1].split(','):
    a=x.split(':');v=int(a[-1]);r=7
    for b in a[:-1]:r=r*31+int(b)
    n+=v;h=(h+r*v)%10**9
print(sys.argv[1],n,h)
