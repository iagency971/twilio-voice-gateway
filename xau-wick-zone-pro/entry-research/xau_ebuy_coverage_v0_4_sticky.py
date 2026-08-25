#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

v01=load_module('ebuy_v04_v01',HERE/'xau_ebuy_coverage_v0_1.py')
v02=load_module('ebuy_v04_v02',HERE/'xau_ebuy_coverage_v0_2.py')
v03=load_module('ebuy_v04_v03',HERE/'xau_ebuy_coverage_v0_3.py')
Zone=v01.Zone

FIXED_ESM='ESM_BOTH_G120M'
CATS=('MATCHED_DISPLAY','CROSSED_BELOW','NO_LONGER_LOCAL','UNDERLYING_PRESENT_NOT_DISPLAYED','UNEXPLAINED_DISAPPEARANCE')


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--z4-pkl',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--candidates-csv',required=True)
    return p.parse_args()


def raw_index(raw,t,side='right'):
    arr=raw.time.to_numpy(dtype='datetime64[ns]')
    q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(arr,q,side=side)-1)


def crossed_below(raw,t0,t1,zlo):
    i0=raw_index(raw,t0,'right')+1;i1=raw_index(raw,t1,'right')
    if i1<max(0,i0):return False
    seg=raw.close.iloc[max(0,i0):i1+1].to_numpy(float)
    return bool(len(seg) and np.any(seg<zlo))


def matching(a,b,tol):
    return v01.overlap(a,b) or abs(a.center-b.center)<=tol


def dedup_full_pool(s,z4_list,families):
    close=s['close'];v=s['v']
    z4=[z for z in z4_list if 0<(close-z.center)/v<=2.0]
    supp=[]
    for fam in families:
        supp.extend(z for z in fam if 0<(close-z.center)/v<=2.0)
    z4.sort(key=lambda z:(close-z.center,z.center))
    supp.sort(key=lambda z:(close-z.center,z.family,z.center))
    kept=[]
    for z in z4+supp:
        if any(v01.overlap(z,q) or abs(z.center-q.center)<=.20*v for q in kept):
            continue
        kept.append(z)
    kept.sort(key=lambda z:(close-z.center,0 if z.family=='Z4' else 1,z.family,z.center))
    return kept


def build_fixed_pools(raw,active,z4):
    snaps=v01.make_eval_times(active,z4)
    all_c5=v02.all_c5_snapshots(active)
    z4_lists=[s['z4_below'] for s in snaps]

    esm_map=v03.esm_stateful_outputs(raw,active,all_c5,'BOTH',120,FIXED_ESM)
    esm=[esm_map.get(s['time'],[]) for s in snaps]
    epm_events=v02.pivot_base_events(raw,'M1',2,raw,active)
    epm=v02.pivot_memory_lists(snaps,epm_events,8,'EPM_M1_R2_A8H')
    ewm_map=v02.wick_memory_all_c5(raw,all_c5,60,'EWM_G60M')
    ewm=[ewm_map.get(s['time'],[]) for s in snaps]
    eswing=v02.fixed_swing_lists(raw,snaps)

    pools=[]
    for i,s in enumerate(snaps):
        pools.append(dedup_full_pool(s,z4_lists[i],[esm[i],epm[i],ewm[i],eswing[i]]))
    return snaps,pools


def sticky_display(raw,snaps,pools):
    out=[]
    prev=[];prev_s=None
    for i,(s,pool) in enumerate(zip(snaps,pools)):
        cur=[]
        remaining=list(pool)
        if prev_s is not None and s['time']-prev_s['time']==pd.Timedelta(minutes=5):
            tol=.25*max(prev_s['v'],s['v'])
            for old in prev:
                if crossed_below(raw,prev_s['time'],s['time'],old.zlo):
                    continue
                d=(s['close']-old.center)/s['v']
                if not (0<d<=2.0):
                    continue
                matches=[(abs(old.center-q.center),j,q) for j,q in enumerate(remaining) if matching(old,q,tol)]
                if matches:
                    _,j,q=min(matches,key=lambda x:(x[0],x[2].family,x[2].center,x[1]))
                    if not any(v01.overlap(q,k) or abs(q.center-k.center)<=.20*s['v'] for k in cur):
                        cur.append(q)
                    remaining.pop(j)
                if len(cur)>=3:break
        # New/empty slots use the nearest remaining current candidates. Existing carried zones keep priority.
        for q in remaining:
            if len(cur)>=3:break
            if any(v01.overlap(q,k) or abs(q.center-k.center)<=.20*s['v'] for k in cur):continue
            cur.append(q)
        out.append(cur[:3])
        prev=cur[:3];prev_s=s
    return out


def stability(raw,snaps,displays,pools):
    c=Counter();total=0
    for i,(s,zs) in enumerate(zip(snaps,displays)):
        if i+1>=len(snaps):continue
        sn=snaps[i+1]
        if sn['time']-s['time']!=pd.Timedelta(minutes=5):continue
        nxt=displays[i+1];under=pools[i+1];tol=.25*max(s['v'],sn['v'])
        for z in zs:
            total+=1
            if any(matching(z,q,tol) for q in nxt):cat='MATCHED_DISPLAY'
            elif crossed_below(raw,s['time'],sn['time'],z.zlo):cat='CROSSED_BELOW'
            else:
                d=(sn['close']-z.center)/sn['v']
                if not (0<d<=2.0):cat='NO_LONGER_LOCAL'
                elif any(matching(z,q,tol) for q in under):cat='UNDERLYING_PRESENT_NOT_DISPLAYED'
                else:cat='UNEXPLAINED_DISAPPEARANCE'
            c[cat]+=1
    matched=c['MATCHED_DISPLAY'];hidden=c['UNDERLYING_PRESENT_NOT_DISPLAYED'];unexpl=c['UNEXPLAINED_DISAPPEARANCE']
    survival=matched+hidden+unexpl
    return {
      'transition_denominator':int(total),
      'category_counts':{k:int(c[k]) for k in CATS},
      'category_shares':{k:(float(c[k]/total) if total else None) for k in CATS},
      'raw_display_persistence':float(matched/total) if total else None,
      'survival_eligible_denominator':int(survival),
      'survival_aware_display_persistence':float(matched/survival) if survival else None,
      'unexplained_share_of_survival_eligible':float(unexpl/survival) if survival else None,
      'display_churn_share_of_survival_eligible':float(hidden/survival) if survival else None,
    }


def main():
    a=parse_args()
    raw=v01.load_raw(a.files);active=v01.active_m1(raw)
    z4=pd.read_pickle(a.z4_pkl).copy();z4['time']=pd.to_datetime(z4.time,utc=True)
    bad=sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:raise RuntimeError(f'future outcome columns present: {bad}')

    snaps,pools=build_fixed_pools(raw,active,z4)
    displays=sticky_display(raw,snaps,pools)
    m=v01.metrics(snaps,displays)
    st=stability(raw,snaps,displays,pools)

    checks={
      'coverage_1v_ge_080':m['coverage']['1.0']>=.80,
      'coverage_1_5v_ge_090':m['coverage']['1.5']>=.90,
      'coverage_2v_ge_095':m['coverage']['2.0']>=.95,
      'count_median_1_to_3':1.0<=m['candidate_count_median']<=3.0,
      'count_p90_le_3':m['candidate_count_p90']<=3.0,
      'nearest_p90_le_1_5v':m['nearest_distance_v_p90'] is not None and m['nearest_distance_v_p90']<=1.5,
      'survival_aware_persistence_ge_070':st['survival_aware_display_persistence'] is not None and st['survival_aware_display_persistence']>=.70,
      'unexplained_survival_share_le_005':st['unexplained_share_of_survival_eligible'] is not None and st['unexplained_share_of_survival_eligible']<=.05,
    }
    passed=all(checks.values())
    status='EBUY_COVERAGE_PASS_V04_STICKY' if passed else 'EBUY_COVERAGE_FAIL_V04_STICKY'

    rows=[]
    for s,zs in zip(snaps,displays):
        for rank,z in enumerate(zs,1):
            rows.append({'time':s['time'],'close':s['close'],'v60':s['v'],'upper_z4_count':s['upper_z4_count'],
                         'nearest_upper_z4_dist_v':s['nearest_upper_z4_dist_v'],'entry_rank':rank,'family':z.family,
                         'center':z.center,'zlo':z.zlo,'zhi':z.zhi,'distance_v':(s['close']-z.center)/s['v']})
    pd.DataFrame(rows).to_csv(a.candidates_csv,index=False)

    out={
      'status':status,'scope':'BUY_ONLY_OUTCOME_BLIND_ENTRY_ZONE_COVERAGE_V04_STICKY','future_price_outcomes_used':False,
      'fixed_architecture':'Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50',
      'eligible_snapshot_count':len(snaps),'display_rule':'sticky carry if still local + not crossed + matching current underlying; fill nearest; max3',
      'coverage_count_distance_metrics':m,'stability':st,'checks':checks,
      'candidate_rows':len(rows),
      'authorization':('AUTHORIZE_SEPARATE_PREREGISTERED_REACTION_STUDY' if passed else 'DO_NOT_START_REACTION_STUDY'),
      'explicit_nonclaims':['No reaction-quality claim','No profitable-entry claim','No TP-hit claim','No route/end-of-session claim']}
    Path(a.output).write_text(json.dumps(out,indent=2))
    print(json.dumps({'status':status,'coverage':m['coverage'],'counts':[m['candidate_count_median'],m['candidate_count_p90']],
                      'nearest_p90':m['nearest_distance_v_p90'],'raw_persistence':st['raw_display_persistence'],
                      'survival_persistence':st['survival_aware_display_persistence'],'unexplained':st['unexplained_share_of_survival_eligible']},indent=2),flush=True)

if __name__=='__main__':main()
