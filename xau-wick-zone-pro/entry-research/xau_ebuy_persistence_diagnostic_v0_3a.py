#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
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

v01=load_module('ebuy_diag_v01',HERE/'xau_ebuy_coverage_v0_1.py')
v02=load_module('ebuy_diag_v02',HERE/'xau_ebuy_coverage_v0_2.py')
v03=load_module('ebuy_diag_v03',HERE/'xau_ebuy_coverage_v0_3.py')
Zone=v01.Zone

CATS=(
    'MATCHED_DISPLAY',
    'CROSSED_BELOW',
    'NO_LONGER_LOCAL',
    'UNDERLYING_PRESENT_NOT_DISPLAYED',
    'UNEXPLAINED_DISAPPEARANCE',
)
FIXED_ESM='ESM_BOTH_G120M'


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--z4-pkl',required=True)
    p.add_argument('--v03-result',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def match(a,b,tol):
    return v01.overlap(a,b) or abs(a.center-b.center)<=tol


def raw_index(raw,t,side='right'):
    arr=raw.time.to_numpy(dtype='datetime64[ns]')
    q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(arr,q,side=side)-1)


def fixed_architecture(raw,active,z4):
    eval_snaps=v01.make_eval_times(active,z4)
    all_c5=v02.all_c5_snapshots(active)
    z4_lists=[s['z4_below'] for s in eval_snaps]

    # v0.3 fixed ESM selection.
    esm_map=v03.esm_stateful_outputs(raw,active,all_c5,'BOTH',120,FIXED_ESM)
    esm=[esm_map.get(s['time'],[]) for s in eval_snaps]

    # v0.2/v0.1 frozen prior families.
    epm_events=v02.pivot_base_events(raw,'M1',2,raw,active)
    epm=v02.pivot_memory_lists(eval_snaps,epm_events,8,'EPM_M1_R2_A8H')
    ewm_map=v02.wick_memory_all_c5(raw,all_c5,60,'EWM_G60M')
    ewm=[ewm_map.get(s['time'],[]) for s in eval_snaps]
    eswing=v02.fixed_swing_lists(raw,eval_snaps)

    displays=[]; unions=[]
    for i,s in enumerate(eval_snaps):
        fams=[esm[i],epm[i],ewm[i],eswing[i]]
        displays.append(v01.final_pool({**s,'z4_below':z4_lists[i]},fams))
        # Full pre-top3 union requested by the prereg. Keep only current local candidates,
        # but do not apply final cross-family dedup or max-three selection.
        close=s['close'];v=s['v'];u=[]
        for z in z4_lists[i]:
            if 0<(close-z.center)/v<=2.0:u.append(z)
        for fam in fams:
            for z in fam:
                if 0<(close-z.center)/v<=2.0:u.append(z)
        unions.append(u)
    return eval_snaps,displays,unions


def crossed_below(raw,t0,t1,zlo):
    i0=raw_index(raw,t0,'right')+1
    i1=raw_index(raw,t1,'right')
    if i1<max(0,i0):return False
    seg=raw.close.iloc[max(0,i0):i1+1].to_numpy(float)
    return bool(len(seg) and np.any(seg<zlo))


def safe_share(n,d):
    return float(n/d) if d else None


def main():
    a=parse_args()
    raw=v01.load_raw(a.files)
    active=v01.active_m1(raw)
    z4=pd.read_pickle(a.z4_pkl).copy();z4['time']=pd.to_datetime(z4.time,utc=True)
    bad=sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:raise RuntimeError(f'future outcome columns present in Z4 input: {bad}')
    v03_result=json.load(open(a.v03_result))
    if v03_result.get('future_price_outcomes_used') is not False:
        raise RuntimeError('v0.3 result is not marked outcome-blind')

    snaps,displays,unions=fixed_architecture(raw,active,z4)
    base=v01.metrics(snaps,displays)
    expected=v03_result['architectures']['Z4_PLUS_ESM_PLUS_EPM_PLUS_EWM_PLUS_ESWING']['metrics']['one_step_persistence']
    if abs(base['one_step_persistence']-expected)>1e-12:
        raise RuntimeError(f'v0.3 persistence reproduction mismatch {base["one_step_persistence"]} vs {expected}')

    counts=Counter();by_family=defaultdict(Counter)
    examples=[]
    total=0
    for i,(s,zs) in enumerate(zip(snaps,displays)):
        if i+1>=len(snaps):continue
        sn=snaps[i+1]
        if sn['time']-s['time']!=pd.Timedelta(minutes=5):continue
        nxt=displays[i+1];under=unions[i+1]
        tol=.25*max(s['v'],sn['v'])
        for z in zs:
            total+=1
            if any(match(z,q,tol) for q in nxt):
                cat='MATCHED_DISPLAY'
            elif crossed_below(raw,s['time'],sn['time'],z.zlo):
                cat='CROSSED_BELOW'
            else:
                dnext=(sn['close']-z.center)/sn['v']
                if not (0<dnext<=2.0):
                    cat='NO_LONGER_LOCAL'
                elif any(match(z,q,tol) for q in under):
                    cat='UNDERLYING_PRESENT_NOT_DISPLAYED'
                else:
                    cat='UNEXPLAINED_DISAPPEARANCE'
            counts[cat]+=1
            by_family[z.family][cat]+=1
            if cat!='MATCHED_DISPLAY' and len(examples)<200:
                examples.append({'time':str(s['time']),'next_time':str(sn['time']),'family':z.family,'category':cat,
                                 'center':float(z.center),'zlo':float(z.zlo),'zhi':float(z.zhi),'close_t':float(s['close']),'close_next':float(sn['close']),
                                 'distance_t_v':float((s['close']-z.center)/s['v']),'distance_next_v':float((sn['close']-z.center)/sn['v'])})

    if total!=base['persistence_zone_denominator']:
        raise RuntimeError(f'denominator mismatch {total} vs {base["persistence_zone_denominator"]}')
    if sum(counts.values())!=total:raise RuntimeError('classification does not partition denominator')

    matched=counts['MATCHED_DISPLAY'];crossed=counts['CROSSED_BELOW'];nolocal=counts['NO_LONGER_LOCAL']
    hidden=counts['UNDERLYING_PRESENT_NOT_DISPLAYED'];unexpl=counts['UNEXPLAINED_DISAPPEARANCE']
    survival=matched+hidden+unexpl
    nonmatches=total-matched

    famout={}
    for fam,c in sorted(by_family.items()):
        den=sum(c.values())
        famout[fam]={'denominator':den,'counts':{k:int(c[k]) for k in CATS},'shares':{k:safe_share(c[k],den) for k in CATS}}

    nonmatched_survival={'UNDERLYING_PRESENT_NOT_DISPLAYED':hidden,'UNEXPLAINED_DISAPPEARANCE':unexpl}
    dominant=max(nonmatched_survival,key=lambda k:(nonmatched_survival[k],k)) if sum(nonmatched_survival.values()) else None
    resolved_majority=(crossed+nolocal)>nonmatches/2 if nonmatches else False
    survival_presence=safe_share(matched+hidden,survival)

    if dominant=='UNDERLYING_PRESENT_NOT_DISPLAYED':
        next_action='PREREGISTER_STICKY_DISPLAY_POOL_REPAIR'
    elif dominant=='UNEXPLAINED_DISAPPEARANCE':
        next_action='DIAGNOSE_GENERATOR_STATE_IDENTITY'
    elif resolved_majority and survival_presence is not None and survival_presence>=.70:
        next_action='PREREGISTER_SURVIVAL_AWARE_PERSISTENCE_GATE'
    else:
        next_action='NEW_ZONE_ARCHITECTURE_REQUIRED'

    # The prereg interpretation gives resolved-majority precedence only when neither
    # survival-eligible non-match category dominates. Record the raw facts as well so
    # later interpretation is auditable.
    out={
      'status':'DIAGNOSTIC_COMPLETE',
      'scope':'BUY_ONLY_OUTCOME_BLIND_PERSISTENCE_DECOMPOSITION_V03A',
      'future_price_outcomes_used':False,
      'fixed_architecture':'Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50',
      'eligible_snapshot_count':len(snaps),
      'original_v03_metrics':base,
      'transition_denominator':total,
      'category_counts':{k:int(counts[k]) for k in CATS},
      'category_shares':{k:safe_share(counts[k],total) for k in CATS},
      'raw_display_persistence':safe_share(matched,total),
      'raw_nonmatch_count':int(nonmatches),
      'resolved_or_left_local_count':int(crossed+nolocal),
      'resolved_or_left_local_share_of_raw_nonmatches':safe_share(crossed+nolocal,nonmatches),
      'survival_eligible_denominator':int(survival),
      'survival_eligible_state_presence':survival_presence,
      'unexplained_share_of_survival_eligible':safe_share(unexpl,survival),
      'display_churn_share_of_survival_eligible':safe_share(hidden,survival),
      'dominant_survival_eligible_nonmatch_category':dominant,
      'resolved_majority_of_raw_nonmatches':bool(resolved_majority),
      'preregistered_next_action_interpretation':next_action,
      'by_origin_family':famout,
      'nonmatched_examples_first_200':examples,
      'explicit_nonclaims':['No reaction-quality claim','No profitable-entry claim','No TP/SL claim','No future-return claim']
    }
    Path(a.output).write_text(json.dumps(out,indent=2))
    print(json.dumps({k:out[k] for k in ['transition_denominator','category_counts','raw_display_persistence','resolved_or_left_local_share_of_raw_nonmatches','survival_eligible_state_presence','unexplained_share_of_survival_eligible','display_churn_share_of_survival_eligible','preregistered_next_action_interpretation']},indent=2),flush=True)

if __name__=='__main__':main()
