#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, peak_prominences, peak_widths

STEP = 0.05
Z4_LOOKBACK = 1440
WARMUP_C5 = 96
EPS = 1e-12
BANDS = (0.5, 1.0, 1.5, 2.0)

FORBIDDEN = {
    'revisited','touch_idx','touch_us','time_to_touch_min','peak_touch','first_state',
    'sweep_far','reclaim_far','reclaim_peak','reclaim_full',
    'mfe5_v','mfe15_v','mfe30_v','mfe60_v',
    'mae5_v','mae15_v','mae30_v','mae60_v',
    'pos5','pos15','pos30','pos60'
}

@dataclass(frozen=True)
class Zone:
    center: float
    zlo: float
    zhi: float
    family: str
    rank: float = 0.0


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--z4-pkl', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--selected-csv', required=True)
    return p.parse_args()


def load_raw(patterns):
    frames = []
    for pat in patterns:
        for f in sorted(glob.glob(pat)):
            d = pd.read_csv(f)
            d['time'] = pd.to_datetime(d['timestamp'], unit='ms', utc=True)
            frames.append(d[['time','open','high','low','close']])
    if not frames:
        raise RuntimeError('no raw files')
    d = pd.concat(frames, ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    for c in ['open','high','low','close']:
        d[c] = pd.to_numeric(d[c], errors='raise').astype(float)
    return d


def build_m5(raw):
    x = raw.copy()
    x['bucket'] = x.time.dt.floor('5min')
    g = x.groupby('bucket', sort=True)
    m = g.agg(open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last'), n=('close','size')).reset_index()
    m['time'] = m['bucket']
    m['complete_at'] = m['bucket'] + pd.Timedelta(minutes=5)
    return m[['time','complete_at','open','high','low','close','n']].reset_index(drop=True)


def active_m1(raw):
    a = raw[raw.high > raw.low].copy().reset_index(drop=True)
    prev = a.close.shift(1).fillna(a.close.iloc[0])
    tr = np.maximum(a.high-a.low, np.maximum((a.high-prev).abs(), (a.low-prev).abs()))
    a['v60'] = tr.rolling(60, min_periods=20).median()
    return a


def ny_us(t):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    return 8 <= q.hour < 17


def make_eval_times(active, z4):
    eligible = active.index[(active.index >= Z4_LOOKBACK-1) & (active.time.dt.minute % 5 == 0) & (active.time.dt.second == 0)].to_numpy()
    if len(eligible) <= WARMUP_C5:
        raise RuntimeError('too few C5 landmarks')
    warm_cut = int(eligible[WARMUP_C5-1])
    z4_by = {pd.Timestamp(t): g.copy() for t,g in z4.groupby('time', sort=True)}
    out = []
    for i in eligible:
        if i < warm_cut:
            continue
        t = pd.Timestamp(active.at[i,'time'])
        if not ny_us(t):
            continue
        g = z4_by.get(t)
        if g is None or not (g.side == 1).any():
            continue
        v = float(active.at[i,'v60'])
        if not np.isfinite(v) or v <= 0:
            continue
        close = float(active.at[i,'close'])
        upper = g[g.side == 1]
        below = g[g.side == -1]
        out.append({
            'active_i': int(i), 'time': t, 'close': close, 'v': v,
            'upper_z4_count': int(len(upper)),
            'nearest_upper_z4_dist_v': float(((upper.center-close)/v).min()),
            'z4_below': [Zone(float(r.center),float(r.zlo),float(r.zhi),'Z4',0.0) for _,r in below.iterrows() if 0 < (close-float(r.center))/v <= 2.0]
        })
    if not out:
        raise RuntimeError('no eligible BUY-context snapshots')
    return out


def lower_wick_density(source, end_idx, window, close, v):
    start = max(0, end_idx-window+1)
    s = source.iloc[start:end_idx+1]
    band_lo = close - 2.0*v
    band_hi = close - STEP*0.5
    gi0 = int(math.ceil(band_lo/STEP - EPS))
    gi1 = int(math.floor(band_hi/STEP + EPS))
    if gi1-gi0 < 4:
        return None, gi0
    d = np.zeros(gi1-gi0+2, dtype=np.int32)
    lows = s.low.to_numpy(float)
    bodylo = np.minimum(s.open.to_numpy(float), s.close.to_numpy(float))
    a = np.ceil(lows/STEP - EPS).astype(np.int64)
    b = np.ceil(bodylo/STEP - EPS).astype(np.int64)-1
    a = np.maximum(a, gi0)
    b = np.minimum(b, gi1)
    ok = a <= b
    if ok.any():
        aa = a[ok]-gi0; bb = b[ok]-gi0
        np.add.at(d, aa, 1)
        np.add.at(d, bb+1, -1)
    return np.cumsum(d[:-1]).astype(float), gi0


def wick_candidates(source, end_idx, window, sigma_mult, close, v, family):
    dens, gi0 = lower_wick_density(source,end_idx,window,close,v)
    if dens is None or len(dens) < 5:
        return []
    sigma = max(sigma_mult*v/STEP, 0.5)
    sm = gaussian_filter1d(dens, sigma, mode='nearest', truncate=4.0)
    peaks,_ = find_peaks(sm)
    if not len(peaks):
        return []
    prom, lb, rb = peak_prominences(sm, peaks)
    rows = []
    for k,p in enumerate(peaks):
        if prom[k] <= 0 or sm[p] < 2.0:
            continue
        widths, heights, li, ri = peak_widths(sm, np.array([p]), rel_height=.5,
                                               prominence_data=(np.array([prom[k]]),np.array([lb[k]]),np.array([rb[k]])))
        center = (gi0 + int(p))*STEP
        zlo = (gi0 + float(li[0]))*STEP
        zhi = (gi0 + float(ri[0]))*STEP
        if not (zhi < close-STEP*0.5):
            continue
        dist = (close-center)/v
        if not (0 < dist <= 2.0):
            continue
        bg = float(sm[p]-prom[k])
        strength = float(prom[k])/math.sqrt(max(bg+1.0,1.0))
        rank = strength/(1.0+dist)
        rows.append(Zone(float(center),float(zlo),float(zhi),family,float(rank)))
    rows.sort(key=lambda z:(-z.rank, close-z.center, z.center))
    return rows[:3]


def source_index_at_snapshot(tf, source, t):
    if tf == 'M1':
        a = source.time.to_numpy(dtype='datetime64[ns]')
        return int(np.searchsorted(a, np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None)), side='right')-1)
    a = source.complete_at.to_numpy(dtype='datetime64[ns]')
    return int(np.searchsorted(a, np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None)), side='right')-1)


def pivot_records(source, radius):
    L = source.low.to_numpy(float)
    rec = []
    for j in range(radius, len(source)-radius):
        x = L[j]
        if x < np.min(L[j-radius:j]) and x < np.min(L[j+1:j+radius+1]):
            rec.append((j, j+radius, float(x)))
    if not rec:
        return np.empty((0,3),float)
    return np.asarray(rec,float)


def swing_candidates(pivots, end_idx, window, tol_mult, close, v, family):
    if end_idx < 0 or len(pivots)==0:
        return []
    lo_i = max(0, end_idx-window+1)
    m = (pivots[:,1] <= end_idx) & (pivots[:,0] >= lo_i)
    vals = pivots[m,2]
    vals = vals[(vals < close) & (vals >= close-2*v)]
    if len(vals) < 2:
        return []
    vals = np.sort(vals)
    tol = tol_mult*v
    clusters=[]; cur=[float(vals[0])]
    for x in vals[1:]:
        x=float(x)
        if x-cur[-1] <= tol+EPS:
            cur.append(x)
        else:
            clusters.append(cur); cur=[x]
    clusters.append(cur)
    out=[]
    for cl in clusters:
        if len(cl)<2:
            continue
        center=float(np.median(cl)); dist=(close-center)/v
        if not (0<dist<=2.0):
            continue
        zlo=float(min(cl)-0.10*v); zhi=float(max(cl)+0.10*v)
        if center>=close:
            continue
        rank=len(cl)/(1.0+dist)
        out.append(Zone(center,zlo,zhi,family,float(rank)))
    out.sort(key=lambda z:(-z.rank, close-z.center, z.center))
    return out[:3]


def overlap(a,b):
    return min(a.zhi,b.zhi) >= max(a.zlo,b.zlo)


def metrics(snapshots, lists):
    n=len(snapshots)
    cover={b:0 for b in BANDS}; counts=[]; nearest=[]
    persist_num=0; persist_den=0
    for i,(s,zs) in enumerate(zip(snapshots,lists)):
        d=[(s['close']-z.center)/s['v'] for z in zs if 0 < (s['close']-z.center)/s['v'] <= 2.0]
        counts.append(len(d))
        if d:
            nearest.append(min(d))
            for b in BANDS:
                if min(d)<=b: cover[b]+=1
        if i+1<n and snapshots[i+1]['time']-s['time']==pd.Timedelta(minutes=5):
            nxt=lists[i+1]; tol=.25*max(s['v'],snapshots[i+1]['v'])
            for z in zs:
                persist_den+=1
                if any(overlap(z,q) or abs(z.center-q.center)<=tol for q in nxt):
                    persist_num+=1
    nearest_arr=np.asarray(nearest,float)
    return {
        'snapshots':n,
        'coverage':{str(b):float(cover[b]/n) for b in BANDS},
        'candidate_count_median':float(np.median(counts)),
        'candidate_count_p90':float(np.quantile(counts,.9)),
        'nearest_distance_v_median':float(np.median(nearest_arr)) if len(nearest_arr) else None,
        'nearest_distance_v_p90':float(np.quantile(nearest_arr,.9)) if len(nearest_arr) else None,
        'one_step_persistence':float(persist_num/persist_den) if persist_den else None,
        'persistence_zone_denominator':int(persist_den)
    }


def choose_best(metric_map):
    def key(k):
        m=metric_map[k]
        med=m['nearest_distance_v_median'] if m['nearest_distance_v_median'] is not None else 999.0
        pers=m['one_step_persistence'] if m['one_step_persistence'] is not None else -1.0
        return (-m['coverage']['1.5'],-pers,-m['coverage']['1.0'],med,k)
    return sorted(metric_map,key=key)[0]


def final_pool(s, families):
    close=s['close']; v=s['v']
    z4=[z for z in s['z4_below'] if 0<(close-z.center)/v<=2.0]
    supp=[]
    for fam in families:
        supp.extend(fam)
    z4.sort(key=lambda z:(close-z.center,z.center))
    supp.sort(key=lambda z:(close-z.center,z.family,z.center))
    kept=[]
    for z in z4+supp:
        if not (0<(close-z.center)/v<=2.0):
            continue
        dup=False
        for q in kept:
            if overlap(z,q) or abs(z.center-q.center)<=.20*v:
                dup=True; break
        if not dup:
            kept.append(z)
    kept.sort(key=lambda z:(close-z.center, 0 if z.family=='Z4' else 1, z.family, z.center))
    return kept[:3]


def pass_gate(m):
    checks={
        'coverage_1v_ge_080':m['coverage']['1.0']>=.80,
        'coverage_1_5v_ge_090':m['coverage']['1.5']>=.90,
        'coverage_2v_ge_095':m['coverage']['2.0']>=.95,
        'count_median_1_to_3':1.0<=m['candidate_count_median']<=3.0,
        'count_p90_le_3':m['candidate_count_p90']<=3.0,
        'nearest_p90_le_1_5v':m['nearest_distance_v_p90'] is not None and m['nearest_distance_v_p90']<=1.5,
        'persistence_ge_070':m['one_step_persistence'] is not None and m['one_step_persistence']>=.70,
    }
    return checks, all(checks.values())


def main():
    a=parse_args()
    raw=load_raw(a.files)
    active=active_m1(raw)
    m5=build_m5(raw)
    z4=pd.read_pickle(a.z4_pkl).copy()
    z4['time']=pd.to_datetime(z4.time,utc=True)
    bad=sorted(FORBIDDEN & set(z4.columns))
    if bad:
        raise RuntimeError(f'future outcome columns present in Z4 geometry input: {bad}')
    snapshots=make_eval_times(active,z4)
    print('eligible BUY-context snapshots',len(snapshots),flush=True)

    # Static source arrays and pivot tables.
    src={'M1':raw,'M5':m5}
    pivots={}
    for tf,rs in [('M1',[2,3]),('M5',[1,2])]:
        for r in rs:
            pivots[(tf,r)]=pivot_records(src[tf],r)

    wick_cfg=[]
    for tf in ['M1','M5']:
        for hours,window in [(4,240 if tf=='M1' else 48),(8,480 if tf=='M1' else 96)]:
            for sig in [.25,.50]:
                wick_cfg.append((f'EW_{tf}_{hours}H_S{sig:.2f}',tf,window,sig))
    swing_cfg=[]
    for tf in ['M1','M5']:
        radii=[2,3] if tf=='M1' else [1,2]
        for hours,window in [(4,240 if tf=='M1' else 48),(8,480 if tf=='M1' else 96)]:
            for r in radii:
                for tol in [.25,.50]:
                    swing_cfg.append((f'ES_{tf}_{hours}H_R{r}_T{tol:.2f}',tf,window,r,tol))

    wick_lists={k:[] for k,*_ in wick_cfg}
    swing_lists={k:[] for k,*_ in swing_cfg}
    z4_lists=[]

    for ix,s in enumerate(snapshots):
        t=s['time']; close=s['close']; v=s['v']
        z4_lists.append(s['z4_below'])
        idx_tf={tf:source_index_at_snapshot(tf,src[tf],t) for tf in ['M1','M5']}
        for k,tf,w,sig in wick_cfg:
            ei=idx_tf[tf]
            zs=[] if ei<0 else wick_candidates(src[tf],ei,w,sig,close,v,k)
            wick_lists[k].append(zs)
        for k,tf,w,r,tol in swing_cfg:
            ei=idx_tf[tf]
            zs=swing_candidates(pivots[(tf,r)],ei,w,tol,close,v,k)
            swing_lists[k].append(zs)
        if (ix+1)%2000==0:
            print('processed',ix+1,'/',len(snapshots),flush=True)

    z4_metric=metrics(snapshots,z4_lists)
    wick_metrics={k:metrics(snapshots,v) for k,v in wick_lists.items()}
    swing_metrics={k:metrics(snapshots,v) for k,v in swing_lists.items()}
    best_wick=choose_best(wick_metrics)
    best_swing=choose_best(swing_metrics)
    print('selected outcome-blind family configs',best_wick,best_swing,flush=True)

    arch_lists={
        'Z4_BELOW_ONLY':z4_lists,
        'Z4_BELOW_PLUS_EWICK':[],
        'Z4_BELOW_PLUS_ESWING':[],
        'Z4_BELOW_PLUS_EWICK_PLUS_ESWING':[]
    }
    for i,s in enumerate(snapshots):
        arch_lists['Z4_BELOW_PLUS_EWICK'].append(final_pool(s,[wick_lists[best_wick][i]]))
        arch_lists['Z4_BELOW_PLUS_ESWING'].append(final_pool(s,[swing_lists[best_swing][i]]))
        arch_lists['Z4_BELOW_PLUS_EWICK_PLUS_ESWING'].append(final_pool(s,[wick_lists[best_wick][i],swing_lists[best_swing][i]]))
    # Apply the same max-3/dedup rule to Z4-only for fair operational counts.
    arch_lists['Z4_BELOW_ONLY']=[final_pool(s,[]) for s in snapshots]

    arch_metrics={k:metrics(snapshots,v) for k,v in arch_lists.items()}
    arch_checks={}; passers=[]
    supp_count={'Z4_BELOW_ONLY':0,'Z4_BELOW_PLUS_EWICK':1,'Z4_BELOW_PLUS_ESWING':1,'Z4_BELOW_PLUS_EWICK_PLUS_ESWING':2}
    for k,m in arch_metrics.items():
        ch,ok=pass_gate(m); arch_checks[k]=ch
        if ok: passers.append(k)
    if passers:
        def akey(k):
            m=arch_metrics[k]; pers=m['one_step_persistence'] or -1.; med=m['nearest_distance_v_median'] if m['nearest_distance_v_median'] is not None else 999.
            return (supp_count[k],-pers,-m['coverage']['1.0'],-m['coverage']['1.5'],med,k)
        selected=sorted(passers,key=akey)[0]
        status='EBUY_COVERAGE_PASS'
    else:
        selected=None; status='EBUY_COVERAGE_FAIL'

    # Immutable selected candidate table for a future separately preregistered reaction study.
    rows=[]
    if selected:
        for s,zs in zip(snapshots,arch_lists[selected]):
            for rank,z in enumerate(zs,1):
                rows.append({'time':s['time'],'close':s['close'],'v60':s['v'],'upper_z4_count':s['upper_z4_count'],
                             'nearest_upper_z4_dist_v':s['nearest_upper_z4_dist_v'],'entry_rank':rank,'family':z.family,
                             'center':z.center,'zlo':z.zlo,'zhi':z.zhi,'distance_v':(s['close']-z.center)/s['v']})
    pd.DataFrame(rows).to_csv(a.selected_csv,index=False)

    result={
        'status':status,
        'scope':'BUY_ONLY_OUTCOME_BLIND_ENTRY_ZONE_COVERAGE',
        'future_price_outcomes_used':False,
        'source':'Dukascopy XAUUSD BID Jan-Jul 2024 frozen DEV',
        'eligible_snapshot_count':len(snapshots),
        'session':'08:00-17:00 America/New_York',
        'condition':'at least one causal Z4 strictly above current close',
        'normalizer':'median TR60 active M1',
        'baseline_z4_below':z4_metric,
        'ewick':{'selected_config':best_wick,'all_config_metrics':wick_metrics},
        'eswing':{'selected_config':best_swing,'all_config_metrics':swing_metrics},
        'architectures':{k:{'metrics':arch_metrics[k],'checks':arch_checks[k],'supplementary_family_count':supp_count[k]} for k in arch_metrics},
        'selected_architecture':selected,
        'selected_candidate_rows':len(rows),
        'authorization':('AUTHORIZE_SEPARATE_PREREGISTERED_REACTION_STUDY' if status=='EBUY_COVERAGE_PASS' else 'DO_NOT_START_REACTION_STUDY_WITHOUT_NEW_PREREG'),
        'explicit_non_claims':['No entry profitability claim','No support/rejection claim','No TP-hit claim','No R_US/UP_FIRST/DOWN_FIRST claim']
    }
    Path(a.output).write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ['status','eligible_snapshot_count','selected_architecture','authorization']},indent=2),flush=True)

if __name__=='__main__':
    main()
