#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

FROZEN_BLOB = 'a8a147615c3fd366c49e93b340fd2018b5b66e9e'
C1_PATCH_SHA256 = '86a5b1af2e77d0e78526652c03f4c6f1a6bfbdaaf92d21e34c1b121f6fdf4dcb'
RAW_ROOT = 'https://raw.githubusercontent.com/kevingtlin/Market-Data-Lab/main/xauusd/bid/m1/'


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--target',required=True)
    p.add_argument('--manifest',required=True)
    p.add_argument('--source-detector',required=True)
    p.add_argument('--input-dir',required=True)
    p.add_argument('--output-dir',required=True)
    return p.parse_args()


def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ym_context(target:str):
    y,m=map(int,target.split('-'))
    pm=m-1;py=y
    if pm==0:pm=12;py-=1
    nm=m+1;ny=y
    if nm==13:nm=1;ny+=1
    return [f'{py:04d}-{pm:02d}',target,f'{ny:04d}-{nm:02d}']


def download_context(target,manifest_path,out_dir):
    man=json.load(open(manifest_path))
    ix={f"{int(x['year']):04d}-{int(x['month']):02d}":x for x in man['files'] if str(x.get('side','')).lower()=='bid'}
    months=ym_context(target);files=[]
    out_dir.mkdir(parents=True,exist_ok=True)
    for mm in months:
        x=ix[mm];p=out_dir/x['file']
        subprocess.run(['curl','--fail','--location','--retry','5','--retry-delay','2',RAW_ROOT+x['file'],'-o',str(p)],check=True,stdout=subprocess.DEVNULL)
        got=sha256(p)
        if got!=x['sha256']: raise RuntimeError((p.name,got,x['sha256']))
        files.append(p)
    print('LOCAL_GRID_SOURCE_HASH_PASS',target,months,flush=True)
    return files


def build_patch(source_path:Path,patch_path:Path):
    src=source_path.read_text()
    changes=[
      ('p=utc_ts(ts); return p.minute%15==0 and p.second==0','p=utc_ts(ts); return p.minute%1==0 and p.second==0'),
      ('out=outcome_zone(i,zlo,zhi,center,side,v)','out={}'),
      ('def zone_detect(wick, vs, lo_idx, hi_idx):','def zone_detect(wick, vs, lo_idx, hi_idx, global_offset=0):'),
      ('gi=lo_idx+m; center=base+gi*STEP; zlo=base+(lo_idx+float(left_ips[0]))*STEP; zhi=base+(lo_idx+float(right_ips[0]))*STEP',
       'gi=global_offset+lo_idx+m; center=base+gi*STEP; zlo=base+(global_offset+lo_idx+float(left_ips[0]))*STEP; zhi=base+(global_offset+lo_idx+float(right_ips[0]))*STEP'),
      ('out.append((center,zlo,zhi,prom,bg,strength,mass,gi,lo_idx+lb,lo_idx+rb))',
       'out.append((center,zlo,zhi,prom,bg,strength,mass,gi,global_offset+lo_idx+lb,global_offset+lo_idx+rb))')]
    for old,new in changes:
        n=src.count(old)
        if n!=1: raise RuntimeError(f'patch anchor count {n}: {old[:80]}')
        src=src.replace(old,new)

    old="""        cntL=np.cumsum(dL[:-1],dtype=np.int32); cntB=np.cumsum(dB[:-1],dtype=np.int32); cntU=np.cumsum(dU[:-1],dtype=np.int32); wick=cntL+cntU
        ilo=max(0,int(math.floor((rlo[i]-base)/STEP))-5); ihi=min(nlevels-1,int(math.ceil((rhi[i]-base)/STEP))+5)
        zones=zone_detect(wick,vs,ilo,ihi); zone_counts.append(len(zones)); landmarks+=1
"""
    new="""        ilo=max(0,int(math.floor((rlo[i]-base)/STEP))-5); ihi=min(nlevels-1,int(math.ceil((rhi[i]-base)/STEP))+5)
        def local_counts(d):
            offset=int(np.sum(d[:ilo],dtype=np.int64))
            return (offset+np.cumsum(d[ilo:ihi+1],dtype=np.int64)).astype(np.int32)
        cntL=local_counts(dL); cntB=local_counts(dB); cntU=local_counts(dU); wick=cntL+cntU
        zones=zone_detect(wick,vs,0,len(wick)-1,ilo); zone_counts.append(len(zones)); landmarks+=1
"""
    if src.count(old)!=1: raise RuntimeError('full-grid cumsum anchor missing')
    src=src.replace(old,new)

    old="""            exp_center=float(cntL[gi]+cntB[gi]+cntU[gi]); same_center=float(cntL[gi] if side<0 else cntU[gi]); body_center=float(cntB[gi])
            zl=max(0,int(math.floor((zlo-base)/STEP))); zh=min(nlevels-1,int(math.ceil((zhi-base)/STEP)))
            mean_wick=float(wick[zl:zh+1].mean()); mean_body=float(cntB[zl:zh+1].mean()); mean_exp=mean_wick+mean_body
"""
    new="""            li=gi-ilo
            exp_center=float(cntL[li]+cntB[li]+cntU[li]); same_center=float(cntL[li] if side<0 else cntU[li]); body_center=float(cntB[li])
            zl=max(ilo,int(math.floor((zlo-base)/STEP))); zh=min(ihi,int(math.ceil((zhi-base)/STEP))); lzl=zl-ilo; lzh=zh-ilo
            mean_wick=float(wick[lzl:lzh+1].mean()); mean_body=float(cntB[lzl:lzh+1].mean()); mean_exp=mean_wick+mean_body
"""
    if src.count(old)!=1: raise RuntimeError('global exposure lookup anchor missing')
    src=src.replace(old,new)

    anchor='    m=len(Z)\n'
    if src.count(anchor)!=1: raise RuntimeError('early-projection anchor missing')
    src=src.replace(anchor,"    keep=['time','side','center','zlo','zhi']\n    Z[keep].to_pickle(args.output)\n    return\n\n"+anchor)
    if 'i+HORIZON+REACT_MAX>=N' not in src: raise RuntimeError('future guard mutated/missing')
    if 'out=outcome_zone(' in src: raise RuntimeError('outcome call remains')
    patch_path.write_text(src)
    return hashlib.sha256(patch_path.read_bytes()).hexdigest()


def main():
    a=args();target=a.target
    inp=Path(a.input_dir);out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    source=Path(a.source_detector)
    # Git blob is checked independently by the workflow; SHA-256 C1 mechanical
    # identity is checked by the already-frozen v1.2 source run. Here we guard
    # the exact source text anchors and the frozen constants before projection.
    text=source.read_text()
    for token in ('STEP=.01; LOOKBACK=1440; HORIZON=240; REACT_MAX=60; EPS=1e-9','i+HORIZON+REACT_MAX>=N'):
        if token not in text: raise RuntimeError(f'frozen token missing: {token}')
    files=download_context(target,Path(a.manifest),inp)
    patch=Path('/tmp/c1_exact_local_grid_projector.py')
    patch_sha=build_patch(source,patch)
    (out/'LOCAL_GRID_PATCH_SHA256.txt').write_text(patch_sha+'\n')
    print('LOCAL_GRID_PATCH_READY',patch_sha,flush=True)
    all_pkl=Path('/tmp/c1_local_grid_all.pkl')
    t0=time.time()
    subprocess.run([sys.executable,str(patch),'--files',*[str(x) for x in files],'--output',str(all_pkl),'--tag',f'C1_{target}_LOCAL_GRID'],check=True)
    runtime=time.time()-t0
    d=pd.read_pickle(all_pkl);d['time']=pd.to_datetime(d.time,utc=True)
    lo=pd.Timestamp(target+'-01T00:00:00Z');hi=lo+pd.offsets.MonthBegin(1)
    q=d[(d.time>=lo)&(d.time<hi)].copy().reset_index(drop=True)
    if not len(q): raise RuntimeError((target,len(d)))
    stem='C1_'+target.replace('-','_')
    q.to_pickle(out/f'{stem}.pkl');(out/f'{stem}_RUNTIME_SEC.txt').write_text(f'{runtime:.6f}\n')
    print('LOCAL_GRID_TARGET_READY',target,len(q),q.time.min(),q.time.max(),'runtime_sec',runtime,flush=True)

if __name__=='__main__':main()
