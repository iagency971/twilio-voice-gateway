#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

HERE=Path(__file__).resolve().parent


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

r=load_module('dual_c5_runner',HERE/'xau_ebuy_c1_refresh_causal_reaction_v1_1.py')
cs=load_module('dual_c5_common_support',HERE/'xau_ebuy_c1_refresh_common_support_postprocess_v1_0.py')


def args():
    p=argparse.ArgumentParser(); p.add_argument('--window',choices=['H1','H2'],required=True); p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--c5-mechanical-pkl',required=True); p.add_argument('--c5-source-faithful-pkl',required=True)
    p.add_argument('--c1-contacts',required=True); p.add_argument('--c1-trades',required=True)
    p.add_argument('--c5-source-contacts',required=True); p.add_argument('--c5-source-trades',required=True)
    p.add_argument('--output',required=True); p.add_argument('--mechanical-evidence-dir',required=True); return p.parse_args()


def clean_z4(path):
    d=pd.read_pickle(path).copy(); d['time']=pd.to_datetime(d.time,utc=True); return d[['time','side','center','zlo','zhi']].copy()


def geometry_audit(mech,src,lo,hi):
    a=mech[(mech.time>=lo)&(mech.time<hi)].copy(); b=src[(src.time>=lo)&(src.time<hi)].copy()
    ca=a.groupby('time').size(); cb=b.groupby('time').size(); times=ca.index.union(cb.index)
    mismatch=[t for t in times if int(ca.get(t,0))!=int(cb.get(t,0))]
    side_mismatch={'lower':0,'upper':0}; matched=0; mx={'center':0.0,'zlo':0.0,'zhi':0.0}
    for t in times:
        for side,label in [(-1,'lower'),(1,'upper')]:
            x=a[(a.time==t)&(a.side==side)].sort_values('center').reset_index(drop=True)
            y=b[(b.time==t)&(b.side==side)].sort_values('center').reset_index(drop=True)
            if len(x)!=len(y): side_mismatch[label]+=1
            if not len(x) or not len(y): continue
            cost=np.abs(x.center.to_numpy(float)[:,None]-y.center.to_numpy(float)[None,:]); rr,cc=linear_sum_assignment(cost)
            for i,j in zip(rr,cc):
                matched+=1
                for k in mx: mx[k]=max(mx[k],abs(float(x.at[i,k])-float(y.at[j,k])))
    return {'mechanical_rows':int(len(a)),'source_faithful_rows':int(len(b)),'timestamp_union_count':int(len(times)),
            'row_count_mismatch_timestamp_count':int(len(mismatch)),
            'row_count_mismatch_timestamp_share':float(len(mismatch)/len(times)) if len(times) else None,
            'side_count_mismatch_timestamps':side_mismatch,'matched_rows':int(matched),
            'matched_max_abs_error_usd':mx,'first_mismatch_timestamps':[str(t) for t in mismatch[:20]]}


def nearest_upper_target(g,close):
    u=g[g.side==1]
    if len(u)==0:return None
    q=u[u.zlo>close]
    if len(q)==0:q=u
    rr=q.iloc[int(np.argmin(q.zlo.to_numpy(float)-close))]
    return (float(rr.center),float(rr.zlo),float(rr.zhi))


def target_bridge_audit(active,snaps,mech,src):
    am={pd.Timestamp(t):g for t,g in mech.groupby('time',sort=False)}; bm={pd.Timestamp(t):g for t,g in src.groupby('time',sort=False)}
    n=diff=missing=0; maxerr=0.0
    for s in snaps:
        t=pd.Timestamp(s['time']); ga=am.get(t); gb=bm.get(t)
        if ga is None or gb is None: missing+=1; continue
        ta=nearest_upper_target(ga,float(s['close'])); tb=nearest_upper_target(gb,float(s['close']))
        if ta is None or tb is None: missing+=1; continue
        n+=1; err=max(abs(ta[i]-tb[i]) for i in range(3)); maxerr=max(maxerr,err)
        if err>1e-8: diff+=1
    return {'compared_eligible_snapshots':int(n),'missing_target_comparison':int(missing),'nearest_upper_target_diff_gt_1e8_count':int(diff),
            'nearest_upper_target_diff_share':float(diff/n) if n else None,'nearest_upper_target_max_abs_error_usd':float(maxerr)}


def filter_window(snaps,displays,pools,lo,hi):
    ix=[i for i,s in enumerate(snaps) if lo<=pd.Timestamp(s['time'])<hi]
    return [snaps[i] for i in ix],[displays[i] for i in ix],[pools[i] for i in ix]


def filt_records(d,cutoff):
    q=d[d.ny_day.astype(str)<=cutoff].copy().reset_index(drop=True); return q.to_dict('records')


def main():
    a=args(); lo,hi,_=r.WINDOWS[a.window]; raw=r.base.v01.load_raw(a.files); active=r.base.v01.active_m1(raw)
    support=cs.support(raw,a.window); cutoff=support['cutoff_ny_day']; common_days=support['common_raw_trading_days']
    mech=clean_z4(a.c5_mechanical_pkl); src=clean_z4(a.c5_source_faithful_pkl)
    audit=geometry_audit(mech,src,lo,hi)

    # Build mechanically matched C5 E-BUY continuous state using the same architecture as C1.
    all_s,all_p=r.loc.build_fixed(raw,active,mech,5,96); all_d=r.loc.sticky_display(raw,all_s,all_p,5)
    s,d,p=filter_window(all_s,all_d,all_p,lo,hi)
    target_audit=target_bridge_audit(active,s,mech,src)
    mc,mt,_=r.causal_contacts(raw,active,mech,s,d,5,lo,hi)
    mcd=pd.DataFrame(mc); mtd=pd.DataFrame(mt)
    if len(mcd):mcd=mcd[mcd.ny_day.astype(str)<=cutoff].copy()
    if len(mtd):mtd=mtd[mtd.ny_day.astype(str)<=cutoff].copy()

    c1c=cs.filt(cs.load_csv(a.c1_contacts),cutoff); c1t=cs.filt(cs.load_csv(a.c1_trades),cutoff)
    sfc=cs.filt(cs.load_csv(a.c5_source_contacts),cutoff); sft=cs.filt(cs.load_csv(a.c5_source_trades),cutoff)
    C1=r.summarize_causal(c1c.to_dict('records'),c1t.to_dict('records'),common_days)
    CM=r.summarize_causal(mcd.to_dict('records'),mtd.to_dict('records'),common_days)
    CS=r.summarize_causal(sfc.to_dict('records'),sft.to_dict('records'),common_days)
    bm=r.paired_day_bootstrap(c1t.to_dict('records'),mtd.to_dict('records')); bs=r.paired_day_bootstrap(c1t.to_dict('records'),sft.to_dict('records'))

    ev=Path(a.mechanical_evidence_dir);ev.mkdir(parents=True,exist_ok=True)
    mcd.to_csv(ev/f'{a.window}_C5_MECHANICAL_MATCHED_CONTACTS.csv.gz',index=False,compression='gzip');mtd.to_csv(ev/f'{a.window}_C5_MECHANICAL_MATCHED_BR.csv.gz',index=False,compression='gzip')

    def delta(x,y):
        return {'contact_count':int(x['contact_episode_count']-y['contact_episode_count']),
                'contact_ratio':float(x['contact_episode_count']/y['contact_episode_count']) if y['contact_episode_count'] else None,
                'fired_count':int(x['bull_rejection_fired_count']-y['bull_rejection_fired_count']),
                'tp1_resolved_rate':float(x['tp1_resolved_rate']-y['tp1_resolved_rate']) if x['tp1_resolved_rate'] is not None and y['tp1_resolved_rate'] is not None else None,
                'invalidation_resolved_rate':float(x['invalidation_resolved_rate']-y['invalidation_resolved_rate']) if x['invalidation_resolved_rate'] is not None and y['invalidation_resolved_rate'] is not None else None,
                'contact_zone_width_v_median':float(x['contact_zone_width_v']['median']-y['contact_zone_width_v']['median']) if x['contact_zone_width_v']['median'] is not None and y['contact_zone_width_v']['median'] is not None else None,
                'contact_tp_distance_v_median':float(x['contact_tp_distance_v']['median']-y['contact_tp_distance_v']['median']) if x['contact_tp_distance_v']['median'] is not None and y['contact_tp_distance_v']['median'] is not None else None}

    out={'status':'C1_REFRESH_DUAL_C5_COMMON_SUPPORT_POSTPROCESS_COMPLETE_NO_PROMOTION','window':a.window,'support':support,
         'geometry_bridge_audit':audit,'target_bridge_audit':target_audit,
         'common_support_summaries':{'C1_MECHANICAL_CAUSAL':C1,'C5_MECHANICAL_MATCHED_CAUSAL':CM,'C5_SOURCE_FAITHFUL_CAUSAL':CS},
         'primary_cadence_isolate':{'C1_minus_C5_MECHANICAL':delta(C1,CM),'paired_day_bootstrap':bm},
         'historical_bridge_robustness':{'C1_minus_C5_SOURCE_FAITHFUL':delta(C1,CS),'paired_day_bootstrap':bs},
         'direction_coherence_across_C5_controls':bool((bm['delta_tp1_rate'] is not None and bs['delta_tp1_rate'] is not None) and ((bm['delta_tp1_rate']>0)==(bs['delta_tp1_rate']>0))),
         'authorization':'NONE_RETROSPECTIVE_SENSITIVITY_ONLY'}
    Path(a.output).write_text(json.dumps(out,indent=2,default=str))
    print(json.dumps({'window':a.window,'geometry_audit':audit,'target_audit':target_audit,
                      'primary_delta':bm['delta_tp1_rate'],'primary_ci':bm['bootstrap_95'],
                      'bridge_delta':bs['delta_tp1_rate'],'bridge_ci':bs['bootstrap_95'],
                      'coherent':out['direction_coherence_across_C5_controls']},indent=2),flush=True)

if __name__=='__main__':main()
