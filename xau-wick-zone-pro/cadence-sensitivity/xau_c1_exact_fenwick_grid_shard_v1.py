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

RAW_ROOT='https://raw.githubusercontent.com/kevingtlin/Market-Data-Lab/main/xauusd/bid/m1/'


def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--target',required=True)
    p.add_argument('--manifest',required=True)
    p.add_argument('--source-detector',required=True)
    p.add_argument('--input-dir',required=True)
    p.add_argument('--output-dir',required=True)
    return p.parse_args()


def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def context_months(target:str):
    y,m=map(int,target.split('-'))
    py,pm=y,m-1
    if pm==0: py,pm=y-1,12
    ny,nm=y,m+1
    if nm==13: ny,nm=y+1,1
    return [f'{py:04d}-{pm:02d}',target,f'{ny:04d}-{nm:02d}']


def download(target:str,manifest:Path,out:Path):
    data=json.load(open(manifest))
    ix={f"{int(x['year']):04d}-{int(x['month']):02d}":x for x in data['files'] if str(x.get('side','')).lower()=='bid'}
    out.mkdir(parents=True,exist_ok=True); files=[]
    for mm in context_months(target):
        x=ix[mm]; p=out/x['file']
        subprocess.run(['curl','--fail','--location','--retry','5','--retry-delay','2',RAW_ROOT+x['file'],'-o',str(p)],check=True,stdout=subprocess.DEVNULL)
        got=sha256(p)
        if got!=x['sha256']: raise RuntimeError((p.name,got,x['sha256']))
        files.append(p)
    print('FENWICK_SOURCE_HASH_PASS',target,context_months(target),flush=True)
    return files


def replace_once(src:str,old:str,new:str,label:str)->str:
    n=src.count(old)
    if n!=1: raise RuntimeError(f'{label}: anchor count={n}')
    return src.replace(old,new)


def build_projector(source:Path,dest:Path)->str:
    src=source.read_text()
    src=replace_once(src,'p=utc_ts(ts); return p.minute%15==0 and p.second==0','p=utc_ts(ts); return p.minute%1==0 and p.second==0','cadence')
    src=replace_once(src,'out=outcome_zone(i,zlo,zhi,center,side,v)','out={}','outcome-disable')
    src=replace_once(src,'def zone_detect(wick, vs, lo_idx, hi_idx):','def zone_detect(wick, vs, lo_idx, hi_idx, global_offset=0):','zone-detect-signature')
    src=replace_once(src,
        'gi=lo_idx+m; center=base+gi*STEP; zlo=base+(lo_idx+float(left_ips[0]))*STEP; zhi=base+(lo_idx+float(right_ips[0]))*STEP',
        'gi=global_offset+lo_idx+m; center=base+gi*STEP; zlo=base+(global_offset+lo_idx+float(left_ips[0]))*STEP; zhi=base+(global_offset+lo_idx+float(right_ips[0]))*STEP',
        'global-zone-coordinates')
    src=replace_once(src,
        'out.append((center,zlo,zhi,prom,bg,strength,mass,gi,lo_idx+lb,lo_idx+rb))',
        'out.append((center,zlo,zhi,prom,bg,strength,mass,gi,global_offset+lo_idx+lb,global_offset+lo_idx+rb))',
        'global-prominence-bounds')

    old="""    dL=np.zeros(nlevels+1,np.int32); dB=np.zeros_like(dL); dU=np.zeros_like(dL)
    def upd(d,s,e,delta):
        if s<=e:
            d[s]+=delta
            if e+1<len(d): d[e+1]-=delta
"""
    new="""    dL=np.zeros(nlevels+1,np.int32); dB=np.zeros_like(dL); dU=np.zeros_like(dL)
    class Fenwick:
        def __init__(self,n): self.n=n; self.t=np.zeros(n+1,np.int32)
        def add(self,idx,delta):
            j=int(idx)+1
            while j<=self.n:
                self.t[j]+=delta; j+=j&-j
        def prefix(self,idx):
            if idx<0: return 0
            j=min(int(idx)+1,self.n); s=0
            while j>0:
                s+=int(self.t[j]); j-=j&-j
            return s
    fL=Fenwick(len(dL)); fB=Fenwick(len(dB)); fU=Fenwick(len(dU))
    def upd(d,ft,s,e,delta):
        if s<=e:
            d[s]+=delta; ft.add(s,delta)
            if e+1<len(d): d[e+1]-=delta; ft.add(e+1,-delta)
"""
    src=replace_once(src,old,new,'fenwick-definition')

    old="""        upd(dL,int(ls[i]),int(le[i]),1); upd(dB,int(bs[i]),int(be[i]),1); upd(dU,int(us[i]),int(ue[i]),1)
        old=i-LOOKBACK
        if old>=0:
            upd(dL,int(ls[old]),int(le[old]),-1); upd(dB,int(bs[old]),int(be[old]),-1); upd(dU,int(us[old]),int(ue[old]),-1)
"""
    new="""        upd(dL,fL,int(ls[i]),int(le[i]),1); upd(dB,fB,int(bs[i]),int(be[i]),1); upd(dU,fU,int(us[i]),int(ue[i]),1)
        old=i-LOOKBACK
        if old>=0:
            upd(dL,fL,int(ls[old]),int(le[old]),-1); upd(dB,fB,int(bs[old]),int(be[old]),-1); upd(dU,fU,int(us[old]),int(ue[old]),-1)
"""
    src=replace_once(src,old,new,'fenwick-updates')

    old="""        cntL=np.cumsum(dL[:-1],dtype=np.int32); cntB=np.cumsum(dB[:-1],dtype=np.int32); cntU=np.cumsum(dU[:-1],dtype=np.int32); wick=cntL+cntU
        ilo=max(0,int(math.floor((rlo[i]-base)/STEP))-5); ihi=min(nlevels-1,int(math.ceil((rhi[i]-base)/STEP))+5)
        zones=zone_detect(wick,vs,ilo,ihi); zone_counts.append(len(zones)); landmarks+=1
"""
    new="""        ilo=max(0,int(math.floor((rlo[i]-base)/STEP))-5); ihi=min(nlevels-1,int(math.ceil((rhi[i]-base)/STEP))+5)
        def local_counts(d,ft):
            off=ft.prefix(ilo-1)
            return (off+np.cumsum(d[ilo:ihi+1],dtype=np.int32)).astype(np.int32,copy=False)
        cntL=local_counts(dL,fL); cntB=local_counts(dB,fB); cntU=local_counts(dU,fU); wick=cntL+cntU
        zones=zone_detect(wick,vs,0,len(wick)-1,ilo); zone_counts.append(len(zones)); landmarks+=1
"""
    src=replace_once(src,old,new,'local-counts')

    old="""            exp_center=float(cntL[gi]+cntB[gi]+cntU[gi]); same_center=float(cntL[gi] if side<0 else cntU[gi]); body_center=float(cntB[gi])
            zl=max(0,int(math.floor((zlo-base)/STEP))); zh=min(nlevels-1,int(math.ceil((zhi-base)/STEP)))
            mean_wick=float(wick[zl:zh+1].mean()); mean_body=float(cntB[zl:zh+1].mean()); mean_exp=mean_wick+mean_body
"""
    new="""            li=gi-ilo
            exp_center=float(cntL[li]+cntB[li]+cntU[li]); same_center=float(cntL[li] if side<0 else cntU[li]); body_center=float(cntB[li])
            zl=max(ilo,int(math.floor((zlo-base)/STEP))); zh=min(ihi,int(math.ceil((zhi-base)/STEP))); lzl=zl-ilo; lzh=zh-ilo
            mean_wick=float(wick[lzl:lzh+1].mean()); mean_body=float(cntB[lzl:lzh+1].mean()); mean_exp=mean_wick+mean_body
"""
    src=replace_once(src,old,new,'local-exposure')

    anchor='    m=len(Z)\n'
    if src.count(anchor)!=1: raise RuntimeError('projection-return anchor')
    src=src.replace(anchor,"    keep=['time','side','center','zlo','zhi']\n    Z[keep].to_pickle(args.output)\n    return\n\n"+anchor)
    if 'i+HORIZON+REACT_MAX>=N' not in src: raise RuntimeError('future guard missing')
    if 'out=outcome_zone(' in src: raise RuntimeError('outcome call remains')
    dest.write_text(src)
    return sha256(dest)


def main():
    a=parse(); target=a.target; inp=Path(a.input_dir); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    source=Path(a.source_detector); text=source.read_text()
    for token in ('STEP=.01; LOOKBACK=1440; HORIZON=240; REACT_MAX=60; EPS=1e-9','i+HORIZON+REACT_MAX>=N'):
        if token not in text: raise RuntimeError(f'frozen token missing: {token}')
    files=download(target,Path(a.manifest),inp)
    projector=Path('/tmp/c1_fenwick_projector.py'); patch_sha=build_projector(source,projector)
    (out/'FENWICK_PATCH_SHA256.txt').write_text(patch_sha+'\n')
    all_pkl=Path('/tmp/c1_fenwick_all.pkl'); t0=time.time()
    subprocess.run([sys.executable,str(projector),'--files',*[str(x) for x in files],'--output',str(all_pkl),'--tag',f'C1_{target}_FENWICK'],check=True)
    runtime=time.time()-t0
    d=pd.read_pickle(all_pkl); d['time']=pd.to_datetime(d.time,utc=True)
    lo=pd.Timestamp(target+'-01T00:00:00Z'); hi=lo+pd.offsets.MonthBegin(1)
    q=d[(d.time>=lo)&(d.time<hi)].copy().reset_index(drop=True)
    if not len(q): raise RuntimeError((target,len(d)))
    stem='C1_'+target.replace('-','_'); q.to_pickle(out/f'{stem}.pkl'); (out/f'{stem}_RUNTIME_SEC.txt').write_text(f'{runtime:.6f}\n')
    print('FENWICK_TARGET_READY',target,len(q),q.time.min(),q.time.max(),'runtime_sec',runtime,flush=True)

if __name__=='__main__': main()
