import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
import xau_zone_episode_dev_z4 as z4  # noqa:E402


def box_pass(x,radius):
    x=np.asarray(x,float);n=len(x)
    if n==0 or radius<=0:return x.copy()
    p=np.concatenate(([0.0],np.cumsum(x,dtype=float)));i=np.arange(n,dtype=np.int64);l=np.maximum(0,i-radius);r=np.minimum(n-1,i+radius)
    return (p[r+1]-p[l])/(r-l+1)


def box3(x,sigma,*args,**kwargs):
    s=float(sigma);raw=(math.sqrt(1+4*s*s)-1)/2 if s>0 else 0.0;r=int(math.floor(raw+0.5));y=np.asarray(x,float)
    for _ in range(3):y=box_pass(y,r)
    return y


def pine_find_peaks(x,*args,**kwargs):
    x=np.asarray(x,float);p=[]
    for i in range(1,len(x)-1):
        if x[i]>x[i-1] and x[i]>=x[i+1]:p.append(i)
    return np.asarray(p,dtype=np.int64),{}


def one_prom(x,p):
    h=float(x[p]);left_limit=0;scan=p-1
    while scan>=0:
        if x[scan]>h:
            left_limit=scan+1;break
        scan-=1
    left_min=h;lb=p
    for j in range(left_limit,p):
        if x[j]<left_min:left_min=float(x[j]);lb=j
    right_limit=len(x)-1;scan=p+1
    while scan<len(x):
        if x[scan]>h:
            right_limit=scan-1;break
        scan+=1
    right_min=h;rb=p
    for j in range(p+1,right_limit+1):
        if x[j]<right_min:right_min=float(x[j]);rb=j
    bg=max(left_min,right_min);return h-bg,lb,rb


def pine_peak_prominences(x,peaks,*args,**kwargs):
    x=np.asarray(x,float);ps=np.asarray(peaks,dtype=np.int64);pr=[];lb=[];rb=[]
    for p in ps:
        a,b,c=one_prom(x,int(p));pr.append(a);lb.append(b);rb.append(c)
    return np.asarray(pr,float),np.asarray(lb,np.int64),np.asarray(rb,np.int64)


def interp_left(x,p,lb,target):
    j=int(p)
    while j>lb and x[j]>target:j-=1
    if j==p:return float(p)
    y0=float(x[j]);y1=float(x[j+1])
    if abs(y1-y0)<=1e-15:return float(j)
    a=(target-y0)/(y1-y0);return float(j)+max(0.0,min(1.0,a))


def interp_right(x,p,rb,target):
    j=int(p)
    while j<rb and x[j]>target:j+=1
    if j==p:return float(p)
    ya=float(x[j-1]);yb=float(x[j])
    if abs(ya-yb)<=1e-15:return float(j)
    a=(ya-target)/(ya-yb);return float(j-1)+max(0.0,min(1.0,a))


def pine_peak_widths(x,peaks,rel_height=.5,prominence_data=None,*args,**kwargs):
    x=np.asarray(x,float);ps=np.asarray(peaks,dtype=np.int64)
    if prominence_data is None:prom,lb,rb=pine_peak_prominences(x,ps)
    else:prom,lb,rb=prominence_data;prom=np.asarray(prom,float);lb=np.asarray(lb,np.int64);rb=np.asarray(rb,np.int64)
    widths=[];heights=[];left=[];right=[]
    for k,p in enumerate(ps):
        target=float(x[p])-float(rel_height)*float(prom[k]);l=interp_left(x,int(p),int(lb[k]),target);r=interp_right(x,int(p),int(rb[k]),target)
        widths.append(r-l);heights.append(target);left.append(l);right.append(r)
    return np.asarray(widths,float),np.asarray(heights,float),np.asarray(left,float),np.asarray(right,float)


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--step',type=float,required=True);known,rest=p.parse_known_args()
    if known.step not in (0.01,0.02,0.05,0.10):raise SystemExit('unsupported step')
    z4.STEP=float(known.step);z4.gaussian_filter1d=box3;z4.find_peaks=pine_find_peaks;z4.peak_prominences=pine_peak_prominences;z4.peak_widths=pine_peak_widths
    sys.argv=[sys.argv[0]]+rest;z4.main()

if __name__=='__main__':main()
