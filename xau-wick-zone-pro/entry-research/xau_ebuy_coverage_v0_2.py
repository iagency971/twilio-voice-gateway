#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v01',HERE/'xau_ebuy_coverage_v0_1.py')
v01=importlib.util.module_from_spec(spec); spec.loader.exec_module(v01)
Zone=v01.Zone


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--z4-pkl',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--selected-csv',required=True)
    return p.parse_args()


def all_c5_snapshots(active):
    idx=active.index[(active.index>=v01.Z4_LOOKBACK-1)&(active.time.dt.minute%5==0)&(active.time.dt.second==0)].to_numpy()
    if len(idx)<=v01.WARMUP_C5:return []
    cut=int(idx[v01.WARMUP_C5-1]);out=[]
    for i in idx:
        if i<cut:continue
        v=float(active.at[i,'v60'])
        if not np.isfinite(v) or v<=0:continue
        out.append({'active_i':int(i),'time':pd.Timestamp(active.at[i,'time']),'close':float(active.at[i,'close']),'v':v})
    return out


def latest_v(active,t):
    a=active.time.to_numpy(dtype='datetime64[ns]')
    q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    i=int(np.searchsorted(a,q,side='right')-1)
    if i<0:return None
    v=float(active.at[i,'v60'])
    return v if np.isfinite(v) and v>0 else None


def pivot_base_events(source,tf,r,raw,active):
    piv=v01.pivot_records(source,r)
    rt=raw.time.to_numpy(dtype='datetime64[ns]');cl=raw.close.to_numpy(float)
    events=[]
    for pi,ci,low in piv:
        pi=int(pi);ci=int(ci);low=float(low)
        confirm=pd.Timestamp(source.at[ci,'time'] if tf=='M1' else source.at[ci,'complete_at'])
        vc=latest_v(active,confirm)
        if vc is None:continue
        zlo=low-.10*vc; zhi=low+.20*vc
        q=np.datetime64(confirm.tz_convert('UTC').tz_localize(None))
        start=int(np.searchsorted(rt,q,side='right')-1)
        if start<0:continue
        end=min(len(raw),start+8*60+2)
        bad=np.where(cl[start+1:end] < zlo)[0]
        invalid=pd.Timestamp(raw.at[start+1+int(bad[0]),'time']) if len(bad) else None
        events.append({'start':confirm,'center':low,'zlo':zlo,'zhi':zhi,'invalid':invalid,'tf':tf,'r':r})
    events.sort(key=lambda e:e['start'])
    return events


def pivot_memory_lists(eval_snaps,events,age_h,config):
    out=[];cap=pd.Timedelta(hours=age_h)
    if not events:return [[] for _ in eval_snaps]
    starts=pd.DatetimeIndex([e['start'] for e in events])
    starts_ns=starts.view('int64')
    for s in eval_snaps:
        t=s['time'];close=s['close'];v=s['v'];zs=[]
        tns=int(pd.Timestamp(t).value); lns=int((pd.Timestamp(t)-cap).value)
        lo=int(np.searchsorted(starts_ns,lns,side='left'));hi=int(np.searchsorted(starts_ns,tns,side='right'))
        for e in events[lo:hi]:
            if e['invalid'] is not None and e['invalid']<=t:continue
            dist=(close-e['center'])/v
            if not (0<dist<=2.0):continue
            age_hours=max(0.,(t-e['start']).total_seconds()/3600.)
            rank=1./((1.+dist)*(1.+age_hours/age_h))
            zs.append(Zone(float(e['center']),float(e['zlo']),float(e['zhi']),config,float(rank)))
        zs.sort(key=lambda z:(-z.rank,close-z.center,z.center));out.append(zs[:3])
    return out


def raw_index(raw,t,side='right'):
    a=raw.time.to_numpy(dtype='datetime64[ns]');q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(a,q,side=side)-1)


def wick_memory_all_c5(raw,all_c5,grace_min,config):
    states=[];outputs={};prev_t=None
    grace=pd.Timedelta(minutes=grace_min)
    for s in all_c5:
        t=s['time'];close=s['close'];v=s['v']
        if prev_t is not None:
            i0=max(0,raw_index(raw,prev_t,'right')+1);i1=raw_index(raw,t,'right')
            seg=raw.close.iloc[i0:i1+1].to_numpy(float) if i1>=i0 else np.array([],float)
        else:seg=np.array([],float)
        kept=[]
        for st in states:
            if t-st['last_seen']>grace:continue
            if len(seg) and np.any(seg < st['zone'].zlo):continue
            kept.append(st)
        states=kept
        ei=v01.source_index_at_snapshot('M1',raw,t)
        det=[] if ei<0 else v01.wick_candidates(raw,ei,480,.25,close,v,'EW_M1_8H_S0.25')
        for z in det:
            matches=[]
            for j,st in enumerate(states):
                if v01.overlap(z,st['zone']) or abs(z.center-st['zone'].center)<=.25*v:
                    matches.append((abs(z.center-st['zone'].center),j))
            if matches:
                _,j=min(matches);states[j]={'zone':Zone(z.center,z.zlo,z.zhi,config,z.rank),'last_seen':t}
            else:
                states.append({'zone':Zone(z.center,z.zlo,z.zhi,config,z.rank),'last_seen':t})
        zs=[]
        for st in states:
            z=st['zone'];dist=(close-z.center)/v
            if 0<dist<=2.0:zs.append(z)
        zs.sort(key=lambda z:(close-z.center,z.center));outputs[t]=zs[:3]
        prev_t=t
    return outputs


def fixed_swing_lists(raw,eval_snaps):
    piv=v01.pivot_records(raw,2);out=[]
    for s in eval_snaps:
        ei=v01.source_index_at_snapshot('M1',raw,s['time'])
        out.append(v01.swing_candidates(piv,ei,480,.50,s['close'],s['v'],'ES_M1_8H_R2_T0.50'))
    return out


def choose(metric_map):return v01.choose_best(metric_map)


def architecture_lists(eval_snaps,z4_lists,*family_lists):
    out=[]
    for i,s in enumerate(eval_snaps):
        fam=[x[i] for x in family_lists]
        out.append(v01.final_pool({**s,'z4_below':z4_lists[i]},fam))
    return out


def main():
    a=args();raw=v01.load_raw(a.files);active=v01.active_m1(raw);m5=v01.build_m5(raw)
    z4=pd.read_pickle(a.z4_pkl).copy();z4['time']=pd.to_datetime(z4.time,utc=True)
    bad=sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:raise RuntimeError(f'future outcome columns present: {bad}')
    eval_snaps=v01.make_eval_times(active,z4);allc5=all_c5_snapshots(active)
    print('eval snapshots',len(eval_snaps),'all mature C5',len(allc5),flush=True)
    z4_lists=[s['z4_below'] for s in eval_snaps]

    sources={'M1':raw,'M5':m5};radii={'M1':[2,3],'M5':[1,2]};event_map={}
    for tf in ['M1','M5']:
        for r in radii[tf]:
            event_map[(tf,r)]=pivot_base_events(sources[tf],tf,r,raw,active)
            print('pivot events',tf,r,len(event_map[(tf,r)]),flush=True)
    pm_lists={};pm_metrics={}
    for tf in ['M1','M5']:
        for r in radii[tf]:
            for age in [2,4,8]:
                k=f'EPM_{tf}_R{r}_A{age}H';L=pivot_memory_lists(eval_snaps,event_map[(tf,r)],age,k)
                pm_lists[k]=L;pm_metrics[k]=v01.metrics(eval_snaps,L)
    best_pm=choose(pm_metrics)

    wm_lists={};wm_metrics={}
    for grace in [15,30,60]:
        k=f'EWM_G{grace}M';mp=wick_memory_all_c5(raw,allc5,grace,k);L=[mp.get(s['time'],[]) for s in eval_snaps]
        wm_lists[k]=L;wm_metrics[k]=v01.metrics(eval_snaps,L)
    best_wm=choose(wm_metrics)
    swing=fixed_swing_lists(raw,eval_snaps);swing_metric=v01.metrics(eval_snaps,swing)
    print('selected state configs',best_pm,best_wm,flush=True)

    arch={}
    arch['Z4_ONLY']=[v01.final_pool({**s,'z4_below':z4_lists[i]},[]) for i,s in enumerate(eval_snaps)]
    for k,L in pm_lists.items():arch[f'Z4_PLUS_{k}']=architecture_lists(eval_snaps,z4_lists,L)
    for k,L in wm_lists.items():arch[f'Z4_PLUS_{k}']=architecture_lists(eval_snaps,z4_lists,L)
    arch['Z4_PLUS_EPM_PLUS_EWM']=architecture_lists(eval_snaps,z4_lists,pm_lists[best_pm],wm_lists[best_wm])
    arch['Z4_PLUS_EPM_PLUS_FIXED_ESWING']=architecture_lists(eval_snaps,z4_lists,pm_lists[best_pm],swing)
    arch['Z4_PLUS_EPM_PLUS_EWM_PLUS_FIXED_ESWING']=architecture_lists(eval_snaps,z4_lists,pm_lists[best_pm],wm_lists[best_wm],swing)

    arch_metrics={k:v01.metrics(eval_snaps,L) for k,L in arch.items()};arch_checks={};passers=[]
    def scount(k):
        if k=='Z4_ONLY':return 0
        if k.startswith('Z4_PLUS_EPM_') and '_PLUS_' not in k[len('Z4_PLUS_'):]:return 1
        if k.startswith('Z4_PLUS_EWM_') and '_PLUS_' not in k[len('Z4_PLUS_'):]:return 1
        if k in ('Z4_PLUS_EPM_PLUS_EWM','Z4_PLUS_EPM_PLUS_FIXED_ESWING'):return 2
        if k=='Z4_PLUS_EPM_PLUS_EWM_PLUS_FIXED_ESWING':return 3
        return 1
    for k,m in arch_metrics.items():
        ch,ok=v01.pass_gate(m);arch_checks[k]=ch
        if ok:passers.append(k)
    if passers:
        def key(k):
            m=arch_metrics[k];pers=m['one_step_persistence'] if m['one_step_persistence'] is not None else -1.;med=m['nearest_distance_v_median'] if m['nearest_distance_v_median'] is not None else 999.
            return (scount(k),-pers,-m['coverage']['1.0'],-m['coverage']['1.5'],med,k)
        selected=sorted(passers,key=key)[0];status='EBUY_COVERAGE_PASS'
    else:selected=None;status='EBUY_COVERAGE_FAIL'

    rows=[]
    if selected:
        for s,zs in zip(eval_snaps,arch[selected]):
            for rank,z in enumerate(zs,1):
                rows.append({'time':s['time'],'close':s['close'],'v60':s['v'],'upper_z4_count':s['upper_z4_count'],'nearest_upper_z4_dist_v':s['nearest_upper_z4_dist_v'],
                             'entry_rank':rank,'family':z.family,'center':z.center,'zlo':z.zlo,'zhi':z.zhi,'distance_v':(s['close']-z.center)/s['v']})
    pd.DataFrame(rows).to_csv(a.selected_csv,index=False)
    out={'status':status,'scope':'BUY_ONLY_OUTCOME_BLIND_ENTRY_ZONE_COVERAGE_V02_STATEFUL','future_price_outcomes_used':False,
      'eligible_snapshot_count':len(eval_snaps),'v01_failure_used_only_for':'coverage_and_stability_repair_design',
      'pivot_memory':{'selected_config':best_pm,'all_config_metrics':pm_metrics},
      'wick_memory':{'fixed_detector':'EW_M1_8H_S0.25','selected_config':best_wm,'all_config_metrics':wm_metrics},
      'fixed_eswing':{'config':'ES_M1_8H_R2_T0.50','metrics':swing_metric},
      'architectures':{k:{'metrics':arch_metrics[k],'checks':arch_checks[k],'supplementary_family_count':scount(k)} for k in arch_metrics},
      'selected_architecture':selected,'selected_candidate_rows':len(rows),
      'authorization':('AUTHORIZE_SEPARATE_PREREGISTERED_REACTION_STUDY' if status=='EBUY_COVERAGE_PASS' else 'DO_NOT_START_REACTION_STUDY_WITHOUT_NEW_PREREG'),
      'explicit_non_claims':['No entry profitability claim','No support/rejection claim','No TP-hit claim','No R_US/UP_FIRST/DOWN_FIRST claim']}
    Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps({'status':status,'best_pm':best_pm,'best_wm':best_wm,'selected_architecture':selected},indent=2),flush=True)

if __name__=='__main__':main()
