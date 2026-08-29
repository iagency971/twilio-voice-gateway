#!/usr/bin/env python3
from __future__ import annotations

import argparse, glob, json, math, time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, peak_prominences, peak_widths

STEP = 0.01
LOOKBACK = 1440
EPS = 1e-9


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--output-pkl', required=True)
    p.add_argument('--output-csv', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--tag', default='Z4_GEOMETRY_ONLY_V2')
    return p.parse_args()


def utc_ts(x):
    t = pd.Timestamp(x)
    return t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')


def landmark_ok(x):
    t = utc_ts(x)
    return t.minute % 5 == 0 and t.second == 0


def load_raw(patterns):
    frames = []
    files = []
    for pat in patterns:
        for f in sorted(glob.glob(pat)):
            d = pd.read_csv(f)
            if list(d.columns) != ['timestamp','open','high','low','close']:
                raise RuntimeError(f'{f}: unexpected schema {list(d.columns)}')
            d['time'] = pd.to_datetime(d['timestamp'], unit='ms', utc=True)
            frames.append(d[['time','open','high','low','close']])
            files.append(str(f))
    if not frames:
        raise RuntimeError('no input files')
    d = pd.concat(frames, ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    for c in ['open','high','low','close']:
        d[c] = pd.to_numeric(d[c], errors='raise').astype(float)
    return d, files


def build_geometry(raw: pd.DataFrame):
    a = raw[raw.high > raw.low].reset_index(drop=True)
    if len(a) < LOOKBACK + 100:
        raise RuntimeError('too few active M1 bars')
    O = a.open.to_numpy(float); H = a.high.to_numpy(float); L = a.low.to_numpy(float); C = a.close.to_numpy(float); T = a.time.to_numpy(); N = len(a)
    bodylo = np.minimum(O, C); bodyhi = np.maximum(O, C)
    prev = np.r_[C[0], C[:-1]]
    TR = np.maximum(H-L, np.maximum(abs(H-prev), abs(L-prev)))
    v60 = pd.Series(TR).rolling(60, min_periods=20).median().to_numpy()
    vseg = pd.Series(TR).rolling(LOOKBACK, min_periods=240).median().to_numpy()
    rhi = pd.Series(H).rolling(LOOKBACK, min_periods=1).max().to_numpy()
    rlo = pd.Series(L).rolling(LOOKBACK, min_periods=1).min().to_numpy()

    # Absolute 0.01 grid: changing the input window may move the array origin,
    # but never the absolute grid levels themselves.
    base = (math.floor(L.min()/STEP)-100)*STEP
    maxp = math.ceil(H.max()/STEP)*STEP
    nlevels = int(round((maxp-base)/STEP))+16

    def ci(x): return np.ceil((x-base)/STEP-EPS).astype(np.int64)
    def fi(x): return np.floor((x-base)/STEP+EPS).astype(np.int64)
    ls=ci(L); le=ci(bodylo)-1; bs=ci(bodylo); be=fi(bodyhi); us=fi(bodyhi)+1; ue=fi(H)
    for x in (ls,bs,us): np.clip(x,0,nlevels-1,out=x)
    for x in (le,be,ue): np.clip(x,-1,nlevels-1,out=x)
    dL=np.zeros(nlevels+1,np.int32); dB=np.zeros_like(dL); dU=np.zeros_like(dL)

    def upd(d,s,e,delta):
        if s <= e:
            d[s] += delta
            if e+1 < len(d): d[e+1] -= delta

    def zone_detect(wick, vs, lo_idx, hi_idx):
        x = wick[lo_idx:hi_idx+1].astype(float)
        if len(x) < 5 or not np.isfinite(vs) or vs <= 0: return []
        sf=max(.25*vs/STEP,.5); sm=max(.50*vs/STEP,.5); sc=max(1.0*vs/STEP,.5)
        fine=gaussian_filter1d(x,sf,mode='nearest',truncate=4.0)
        med=gaussian_filter1d(x,sm,mode='nearest',truncate=4.0)
        coarse=gaussian_filter1d(x,sc,mode='nearest',truncate=4.0)
        fp,_=find_peaks(fine); mp,_=find_peaks(med); cp,_=find_peaks(coarse); mins,_=find_peaks(-coarse)
        if not len(cp) or not len(mp) or not len(fp): return []
        out=[]; used=set(); tol=max(1,int(round(.5*vs/STEP)))
        for c in cp:
            lc=mins[mins<c]; rc=mins[mins>c]
            bl=int(lc[-1]) if len(lc) else 0; br=int(rc[0]) if len(rc) else len(x)-1
            mps=mp[(mp>=bl)&(mp<=br)]
            if not len(mps): continue
            m=int(mps[np.argmax(med[mps])])
            if m in used or np.min(np.abs(fp-m)) > tol: continue
            used.add(m)
            prom,lb,rb=peak_prominences(med,np.array([m])); prom=float(prom[0]); lb=int(lb[0]); rb=int(rb[0])
            if prom <= 0: continue
            _,_,left_ips,right_ips=peak_widths(med,np.array([m]),rel_height=.5,prominence_data=(np.array([prom]),np.array([lb]),np.array([rb])))
            bg=float(med[m]-prom); strength=prom/math.sqrt(max(bg+1,1)); mass=float(np.maximum(med[lb:rb+1]-bg,0).sum()*STEP)
            gi=lo_idx+m
            center=base+gi*STEP; zlo=base+(lo_idx+float(left_ips[0]))*STEP; zhi=base+(lo_idx+float(right_ips[0]))*STEP
            out.append((center,zlo,zhi,prom,bg,strength,mass,gi,lo_idx+lb,lo_idx+rb))
        return out

    rows=[]; landmarks=0; zone_counts=[]
    for i in range(N):
        upd(dL,int(ls[i]),int(le[i]),1); upd(dB,int(bs[i]),int(be[i]),1); upd(dU,int(us[i]),int(ue[i]),1)
        old=i-LOOKBACK
        if old>=0:
            upd(dL,int(ls[old]),int(le[old]),-1); upd(dB,int(bs[old]),int(be[old]),-1); upd(dU,int(us[old]),int(ue[old]),-1)
        if i < LOOKBACK-1 or not landmark_ok(T[i]): continue
        v=float(v60[i]); vs=float(vseg[i])
        if not np.isfinite(v) or v<=0 or not np.isfinite(vs) or vs<=0: continue
        cntL=np.cumsum(dL[:-1],dtype=np.int32); cntB=np.cumsum(dB[:-1],dtype=np.int32); cntU=np.cumsum(dU[:-1],dtype=np.int32); wick=cntL+cntU
        ilo=max(0,int(math.floor((rlo[i]-base)/STEP))-5); ihi=min(nlevels-1,int(math.ceil((rhi[i]-base)/STEP))+5)
        zones=zone_detect(wick,vs,ilo,ihi); zone_counts.append(len(zones)); landmarks += 1
        close=float(C[i]); t=utc_ts(T[i])
        for center,zlo,zhi,prom,bg,strength,mass,gi,lb,rb in zones:
            if zhi < close-STEP*.5: side=-1
            elif zlo > close+STEP*.5: side=1
            else: continue
            rows.append({
                'time':t,'landmark_i':int(i),'center':float(center),'zlo':float(zlo),'zhi':float(zhi),'side':int(side),
                'tr':v,'vseg':vs,'prominence':float(prom),'background':float(bg),'strength_raw':float(strength),'mass':float(mass),
            })
    z = pd.DataFrame(rows)
    if len(z): z = z.sort_values(['time','side','center','zlo','zhi']).reset_index(drop=True)
    qa = {
        'active_m1_rows': int(len(a)), 'landmarks': int(landmarks), 'geometry_rows': int(len(z)),
        'first_geometry_time_utc': str(z.time.min()) if len(z) else None,
        'last_geometry_time_utc': str(z.time.max()) if len(z) else None,
        'zone_count_median': float(np.median(zone_counts)) if zone_counts else None,
        'zone_count_p90': float(np.quantile(zone_counts,.9)) if zone_counts else None,
        'forbidden_outcome_columns_present': False,
    }
    return z, qa


def main():
    a = parse_args(); t0=time.time(); raw, files=load_raw(a.files); z,qa=build_geometry(raw)
    Path(a.output_pkl).parent.mkdir(parents=True,exist_ok=True)
    z.to_pickle(a.output_pkl)
    z.to_csv(a.output_csv,index=False,float_format='%.17g')
    m={'status':'Z4_GEOMETRY_ONLY_V2_PASS','future_price_outcomes_used':False,'input_files':files,'qa':qa,'elapsed_sec':time.time()-t0}
    Path(a.manifest).write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    print(json.dumps(m,indent=2,sort_keys=True))

if __name__=='__main__': main()
