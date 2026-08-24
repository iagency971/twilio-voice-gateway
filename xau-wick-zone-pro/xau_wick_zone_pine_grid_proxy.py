import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xau_zone_episode_dev_z4 as z4  # noqa: E402


def box_pass_truncated(x, radius):
    x=np.asarray(x,dtype=float); n=len(x)
    if n==0 or radius<=0:return x.copy()
    p=np.concatenate(([0.0],np.cumsum(x,dtype=float)));i=np.arange(n,dtype=np.int64);l=np.maximum(0,i-radius);r=np.minimum(n-1,i+radius)
    return (p[r+1]-p[l])/(r-l+1)


def pine_box3(x,sigma,*args,**kwargs):
    sigma=float(sigma)
    raw=(math.sqrt(1+4*sigma*sigma)-1)/2 if sigma>0 else 0.0
    radius=int(math.floor(raw+0.5)); y=np.asarray(x,dtype=float)
    for _ in range(3):y=box_pass_truncated(y,radius)
    return y


def main():
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--step',type=float,required=True)
    known,rest=p.parse_known_args()
    if known.step not in (0.02,0.05,0.10): raise SystemExit('step must be one of preregistered 0.02,0.05,0.10')
    z4.STEP=float(known.step)
    z4.gaussian_filter1d=pine_box3
    sys.argv=[sys.argv[0]]+rest
    z4.main()

if __name__=='__main__':main()
