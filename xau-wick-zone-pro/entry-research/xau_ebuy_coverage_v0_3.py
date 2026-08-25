#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
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

v01=load_module('ebuy_v01',HERE/'xau_ebuy_coverage_v0_1.py')
v02=load_module('ebuy_v02',HERE/'xau_ebuy_coverage_v0_2.py')
Zone=v01.Zone

WINDOWS=(5,10,20,40)
MODES=('LOW','BODYLOW','BOTH')
GRACES=(30,60,120)


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--z4-pkl',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--selected-csv',required=True)
    return p.parse_args()


def dedup_observations(zones,close,v):
    if not zones:return []
    zones=sorted(zones,key=lambda z:(close-z.center,z.center,z.zlo,z.zhi))
    kept=[]
    for z in zones:
        duplicate=False
        for q in kept:
            if v01.overlap(z,q) or abs(z.center-q.center)<=0.15*v:
                duplicate=True
                break
        if not duplicate:kept.append(z)
    return kept


def structure_observations(active,snapshot,mode,config):
    i=int(snapshot['active_i']);close=float(snapshot['close']);v=float(snapshot['v'])
    raw=[]
    for w in WINDOWS:
        lo=max(0,i-w+1);seg=active.iloc[lo:i+1]
        vals=[]
        if mode in ('LOW','BOTH'):
            vals.append(float(seg.low.min()))
        if mode in ('BODYLOW','BOTH'):
            vals.append(float(np.minimum(seg.open.to_numpy(float),seg.close.to_numpy(float)).min()))
        for level in vals:
            dist=(close-level)/v
            if not (0.10<=dist<=2.00):continue
            raw.append(Zone(level,level-0.10*v,level+0.15*v,config,1.0/(1.0+dist)))
    return dedup_observations(raw,close,v)


def raw_index(raw,t):
    arr=raw.time.to_numpy(dtype='datetime64[ns]')
    q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(arr,q,side='right')-1)


def esm_stateful_outputs(raw,active,all_c5,mode,grace_min,config):
    states=[];outputs={};prev_t=None
    grace=pd.Timedelta(minutes=grace_min)
    for s in all_c5:
        t=s['time'];close=s['close'];v=s['v']
        if prev_t is None:
            seg=np.array([],dtype=float)
        else:
            i0=raw_index(raw,prev_t)+1;i1=raw_index(raw,t)
            seg=raw.close.iloc[max(0,i0):i1+1].to_numpy(float) if i1>=max(0,i0) else np.array([],dtype=float)

        # First apply only causal invalidation/expiry to states carried from the prior snapshot.
        kept=[]
        for st in states:
            if t-st['last_seen']>grace:continue
            if len(seg) and np.any(seg < st['zone'].zlo):continue
            kept.append(st)
        states=kept

        observations=structure_observations(active,s,mode,config)
        matched_states=set()
        for z in observations:
            candidates=[]
            for j,st in enumerate(states):
                if j in matched_states:continue
                q=st['zone']
                if v01.overlap(z,q) or abs(z.center-q.center)<=0.20*v:
                    candidates.append((abs(z.center-q.center),j))
            if candidates:
                _,j=min(candidates,key=lambda x:(x[0],x[1]))
                states[j]={'zone':z,'last_seen':t}
                matched_states.add(j)
            else:
                states.append({'zone':z,'last_seen':t})
                matched_states.add(len(states)-1)

        current=[]
        for st in states:
            z=st['zone'];dist=(close-z.center)/v
            if 0<dist<=2.0:
                current.append(z)
        current.sort(key=lambda z:(close-z.center,z.center,z.zlo,z.zhi))
        outputs[t]=current[:3]
        prev_t=t
    return outputs


def build_fixed_prior_lists(raw,active,m5,eval_snaps,all_c5):
    # Frozen v0.2 E-PIVOT-MEMORY selection.
    epm_events=v02.pivot_base_events(raw,'M1',2,raw,active)
    epm=v02.pivot_memory_lists(eval_snaps,epm_events,8,'EPM_M1_R2_A8H')

    # Frozen v0.2 E-WICK-MEMORY selection and v0.1 fixed E-SWING.
    ewm_map=v02.wick_memory_all_c5(raw,all_c5,60,'EWM_G60M')
    ewm=[ewm_map.get(s['time'],[]) for s in eval_snaps]
    eswing=v02.fixed_swing_lists(raw,eval_snaps)
    return epm,ewm,eswing


def architecture_lists(eval_snaps,z4_lists,*families):
    out=[]
    for i,s in enumerate(eval_snaps):
        fam=[f[i] for f in families]
        out.append(v01.final_pool({**s,'z4_below':z4_lists[i]},fam))
    return out


def supp_count(name):
    if name.startswith('Z4_PLUS_ESM_') and '_PLUS_' not in name[len('Z4_PLUS_'):]:return 1
    if name=='Z4_PLUS_ESM_PLUS_EPM':return 2
    if name=='Z4_PLUS_ESM_PLUS_EWM':return 2
    if name=='Z4_PLUS_ESM_PLUS_EPM_PLUS_EWM':return 3
    if name=='Z4_PLUS_ESM_PLUS_EPM_PLUS_EWM_PLUS_ESWING':return 4
    return 99


def main():
    a=parse_args()
    raw=v01.load_raw(a.files)
    active=v01.active_m1(raw)
    m5=v01.build_m5(raw)
    z4=pd.read_pickle(a.z4_pkl).copy();z4['time']=pd.to_datetime(z4.time,utc=True)
    bad=sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:raise RuntimeError(f'future outcome columns present in Z4 input: {bad}')

    eval_snaps=v01.make_eval_times(active,z4)
    all_c5=v02.all_c5_snapshots(active)
    z4_lists=[s['z4_below'] for s in eval_snaps]
    print({'eligible_eval_snapshots':len(eval_snaps),'all_mature_c5':len(all_c5)},flush=True)

    # Nine preregistered ESM configurations, computed over all mature C5 so memory is causal even outside US/evaluation snapshots.
    esm_lists={};esm_metrics={}
    for mode in MODES:
        for grace in GRACES:
            k=f'ESM_{mode}_G{grace}M'
            mp=esm_stateful_outputs(raw,active,all_c5,mode,grace,k)
            L=[mp.get(s['time'],[]) for s in eval_snaps]
            esm_lists[k]=L
            esm_metrics[k]=v01.metrics(eval_snaps,L)
            print(k,esm_metrics[k]['coverage'],esm_metrics[k]['one_step_persistence'],flush=True)

    best_esm=v01.choose_best(esm_metrics)
    print('selected ESM outcome-blind',best_esm,flush=True)

    epm,ewm,eswing=build_fixed_prior_lists(raw,active,m5,eval_snaps,all_c5)

    architectures={}
    for k,L in esm_lists.items():
        architectures[f'Z4_PLUS_{k}']=architecture_lists(eval_snaps,z4_lists,L)
    architectures['Z4_PLUS_ESM_PLUS_EPM']=architecture_lists(eval_snaps,z4_lists,esm_lists[best_esm],epm)
    architectures['Z4_PLUS_ESM_PLUS_EWM']=architecture_lists(eval_snaps,z4_lists,esm_lists[best_esm],ewm)
    architectures['Z4_PLUS_ESM_PLUS_EPM_PLUS_EWM']=architecture_lists(eval_snaps,z4_lists,esm_lists[best_esm],epm,ewm)
    architectures['Z4_PLUS_ESM_PLUS_EPM_PLUS_EWM_PLUS_ESWING']=architecture_lists(eval_snaps,z4_lists,esm_lists[best_esm],epm,ewm,eswing)

    arch_metrics={k:v01.metrics(eval_snaps,L) for k,L in architectures.items()}
    arch_checks={};passers=[]
    for k,m in arch_metrics.items():
        checks,ok=v01.pass_gate(m);arch_checks[k]=checks
        if ok:passers.append(k)

    if passers:
        def key(k):
            m=arch_metrics[k]
            pers=m['one_step_persistence'] if m['one_step_persistence'] is not None else -1.0
            med=m['nearest_distance_v_median'] if m['nearest_distance_v_median'] is not None else 999.0
            return (supp_count(k),-pers,-m['coverage']['1.0'],-m['coverage']['1.5'],med,k)
        selected=sorted(passers,key=key)[0]
        status='EBUY_COVERAGE_PASS'
    else:
        selected=None;status='EBUY_COVERAGE_FAIL'

    rows=[]
    if selected:
        for s,zs in zip(eval_snaps,architectures[selected]):
            for rank,z in enumerate(zs,1):
                rows.append({'time':s['time'],'close':s['close'],'v60':s['v'],'upper_z4_count':s['upper_z4_count'],
                             'nearest_upper_z4_dist_v':s['nearest_upper_z4_dist_v'],'entry_rank':rank,'family':z.family,
                             'center':z.center,'zlo':z.zlo,'zhi':z.zhi,'distance_v':(s['close']-z.center)/s['v']})
    pd.DataFrame(rows).to_csv(a.selected_csv,index=False)

    out={
      'status':status,
      'scope':'BUY_ONLY_OUTCOME_BLIND_ENTRY_ZONE_COVERAGE_V03_STRUCTURE_MEMORY',
      'future_price_outcomes_used':False,
      'eligible_snapshot_count':len(eval_snaps),
      'esm':{'selected_config':best_esm,'all_config_metrics':esm_metrics},
      'fixed_prior_families':{'EPM':'EPM_M1_R2_A8H','EWM':'EWM_G60M / EW_M1_8H_S0.25','ESWING':'ES_M1_8H_R2_T0.50'},
      'architectures':{k:{'metrics':arch_metrics[k],'checks':arch_checks[k],'supplementary_family_count':supp_count(k)} for k in arch_metrics},
      'selected_architecture':selected,
      'selected_candidate_rows':len(rows),
      'authorization':('AUTHORIZE_SEPARATE_PREREGISTERED_REACTION_STUDY' if status=='EBUY_COVERAGE_PASS' else 'DO_NOT_START_REACTION_STUDY_WITHOUT_NEW_PREREG'),
      'explicit_non_claims':['No entry profitability claim','No support/rejection claim','No TP-hit claim','No R_US/UP_FIRST/DOWN_FIRST claim']
    }
    Path(a.output).write_text(json.dumps(out,indent=2))
    print(json.dumps({'status':status,'selected_esm':best_esm,'selected_architecture':selected,'passer_count':len(passers)},indent=2),flush=True)

if __name__=='__main__':main()
