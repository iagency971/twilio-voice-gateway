#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RUNNER = HERE / 'xau_ebuy_c1_refresh_causal_reaction_v1_1.py'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod); return mod


r = load_module('c1_common_support_runner', RUNNER)


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--window',choices=['H1','H2'],required=True)
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--raw-result',required=True)
    p.add_argument('--c1-contacts',required=True); p.add_argument('--c1-trades',required=True)
    p.add_argument('--c5-contacts',required=True); p.add_argument('--c5-trades',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def load_csv(path):
    d=pd.read_csv(path,compression='gzip',low_memory=False)
    for k in ('state_time','contact_time','trigger_time','exec_time'):
        if k in d.columns: d[k]=pd.to_datetime(d[k],utc=True,errors='coerce')
    if 'fired' in d.columns:
        d['fired']=d.fired.astype(str).str.lower().isin(['true','1','yes'])
    return d


def rows(d):
    return d.to_dict('records')


def support(raw, window):
    lo,hi,_=r.WINDOWS[window]
    active=r.base.v01.active_m1(raw)
    n=len(active); guard=r.base.HORIZON+r.base.REACT_MAX
    if n<=guard: raise RuntimeError('insufficient active chronology')
    last=pd.Timestamp(active.at[n-guard-1,'time'])
    ny=last.tz_convert('America/New_York')
    # Under CAUSAL_ACTIVE_INTERVAL_V1 a C1 state at 16:58 governs the final
    # in-session M1 observation stamped 16:59; evaluation stops at 17:00 NY.
    if (ny.hour,ny.minute)>=(16,58):
        cutoff=ny.date()
    else:
        cutoff=(pd.Timestamp(ny.date())-pd.Timedelta(days=1)).date()
    # H1 is interior to the continuous chronology; its calendar end remains the
    # preregistered H1 end regardless of the absolute H2 tail guard.
    if window=='H1': cutoff=(hi.tz_convert('America/New_York')-pd.Timedelta(days=1)).date()
    # Common active raw NY session dates for per-day reporting.
    q=active[(active.time>=lo)&(active.time<hi)].copy(); q['ny']=q.time.dt.tz_convert('America/New_York')
    q=q[(q.ny.dt.hour>=8)&(q.ny.dt.hour<17)]
    raw_days=sorted({x.isoformat() for x in q.ny.dt.date if x<=cutoff})
    excluded=sorted({x.isoformat() for x in q.ny.dt.date if x>cutoff})
    return {'last_mechanical_c1_eligible_time_utc':str(last),'last_mechanical_c1_eligible_time_ny':str(ny),
            'cutoff_ny_day':cutoff.isoformat(),'common_raw_trading_days':raw_days,
            'excluded_tail_ny_days':excluded,'exclusion_reason':'LEGACY_FUTURE_GUARD_COMMON_SUPPORT'}


def filt(d, cutoff):
    if 'ny_day' not in d.columns: raise RuntimeError('ny_day missing from causal evidence')
    return d[d.ny_day.astype(str)<=cutoff].copy().reset_index(drop=True)


def main():
    a=args(); raw=r.base.v01.load_raw(a.files); sup=support(raw,a.window); cutoff=sup['cutoff_ny_day']
    c1c=filt(load_csv(a.c1_contacts),cutoff); c1t=filt(load_csv(a.c1_trades),cutoff)
    c5c=filt(load_csv(a.c5_contacts),cutoff); c5t=filt(load_csv(a.c5_trades),cutoff)
    days=sup['common_raw_trading_days']
    s1=r.summarize_causal(rows(c1c),rows(c1t),days); s5=r.summarize_causal(rows(c5c),rows(c5t),days)
    boot=r.paired_day_bootstrap(rows(c1t),rows(c5t))
    raw_result=json.load(open(a.raw_result))
    out={
      'status':'C1_REFRESH_COMMON_COMPLETE_SESSION_SUPPORT_POSTPROCESS_PASS',
      'window':a.window,
      'source_raw_result_status':raw_result.get('status'),
      'support':sup,
      'evidence_counts_before':{
        'C1_contacts':int(len(load_csv(a.c1_contacts))),'C1_trades':int(len(load_csv(a.c1_trades))),
        'C5_contacts':int(len(load_csv(a.c5_contacts))),'C5_trades':int(len(load_csv(a.c5_trades)))},
      'evidence_counts_after':{
        'C1_contacts':int(len(c1c)),'C1_trades':int(len(c1t)),
        'C5_contacts':int(len(c5c)),'C5_trades':int(len(c5t))},
      'causal_active_interval_v1_common_support':{
        'C1':s1,'C5':s5,
        'C1_minus_C5':{
          'contact_count':int(s1['contact_episode_count']-s5['contact_episode_count']),
          'contact_ratio':float(s1['contact_episode_count']/s5['contact_episode_count']) if s5['contact_episode_count'] else None,
          'fired_count':int(s1['bull_rejection_fired_count']-s5['bull_rejection_fired_count']),
          'tp1_resolved_rate':float(s1['tp1_resolved_rate']-s5['tp1_resolved_rate']) if s1['tp1_resolved_rate'] is not None and s5['tp1_resolved_rate'] is not None else None,
          'invalidation_resolved_rate':float(s1['invalidation_resolved_rate']-s5['invalidation_resolved_rate']) if s1['invalidation_resolved_rate'] is not None and s5['invalidation_resolved_rate'] is not None else None,
          'contact_zone_width_v_median':float(s1['contact_zone_width_v']['median']-s5['contact_zone_width_v']['median']) if s1['contact_zone_width_v']['median'] is not None and s5['contact_zone_width_v']['median'] is not None else None,
          'contact_tp_distance_v_median':float(s1['contact_tp_distance_v']['median']-s5['contact_tp_distance_v']['median']) if s1['contact_tp_distance_v']['median'] is not None and s5['contact_tp_distance_v']['median'] is not None else None},
        'paired_trading_day_bootstrap':boot},
      'authorization':'NONE_RETROSPECTIVE_SENSITIVITY_ONLY'}
    Path(a.output).write_text(json.dumps(out,indent=2,default=str))
    print(json.dumps({'window':a.window,'cutoff':cutoff,'excluded':sup['excluded_tail_ny_days'],
                      'C1_TP':s1['tp1_resolved_rate'],'C5_TP':s5['tp1_resolved_rate'],
                      'delta':boot['delta_tp1_rate'],'ci95':boot['bootstrap_95']},indent=2))


if __name__=='__main__': main()
