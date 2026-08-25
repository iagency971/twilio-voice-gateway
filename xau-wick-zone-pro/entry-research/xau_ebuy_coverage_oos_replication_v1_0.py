#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

HERE=Path(__file__).resolve().parent

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

v01=load_module('ebuy_oos_v01',HERE/'xau_ebuy_coverage_v0_1.py')
v04=load_module('ebuy_oos_v04',HERE/'xau_ebuy_coverage_v0_4_sticky.py')

WINDOWS={
 'OOS_H1':(pd.Timestamp('2024-08-01T00:00:00Z'),pd.Timestamp('2025-08-01T00:00:00Z')),
 'OOS_H2':(pd.Timestamp('2025-08-01T00:00:00Z'),pd.Timestamp('2026-08-01T00:00:00Z')),
 'OOS_ALL':(pd.Timestamp('2024-08-01T00:00:00Z'),pd.Timestamp('2026-08-01T00:00:00Z')),
}


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--z4-pkl',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--candidates-csv',required=True)
    return p.parse_args()


def subset(snaps,pools,displays,lo,hi):
    idx=[i for i,s in enumerate(snaps) if lo<=s['time']<hi]
    return [snaps[i] for i in idx],[pools[i] for i in idx],[displays[i] for i in idx]


def checks(m,st):
    c={
      'coverage_1v_ge_080':m['coverage']['1.0']>=.80,
      'coverage_1_5v_ge_090':m['coverage']['1.5']>=.90,
      'coverage_2v_ge_095':m['coverage']['2.0']>=.95,
      'count_median_1_to_3':1.0<=m['candidate_count_median']<=3.0,
      'count_p90_le_3':m['candidate_count_p90']<=3.0,
      'nearest_p90_le_1_5v':m['nearest_distance_v_p90'] is not None and m['nearest_distance_v_p90']<=1.5,
      'survival_aware_persistence_ge_070':st['survival_aware_display_persistence'] is not None and st['survival_aware_display_persistence']>=.70,
      'unexplained_survival_share_le_005':st['unexplained_share_of_survival_eligible'] is not None and st['unexplained_share_of_survival_eligible']<=.05,
    }
    return c,all(c.values())


def main():
    a=args();raw=v01.load_raw(a.files);active=v01.active_m1(raw)
    z4=pd.read_pickle(a.z4_pkl).copy();z4['time']=pd.to_datetime(z4.time,utc=True)
    bad=sorted(v01.FORBIDDEN & set(z4.columns))
    if bad:raise RuntimeError(f'future outcome columns in Z4 input: {bad}')

    snaps,pools=v04.build_fixed_pools(raw,active,z4)
    displays=v04.sticky_display(raw,snaps,pools)

    results={};rows=[]
    for name,(lo,hi) in WINDOWS.items():
        ss,pp,dd=subset(snaps,pools,displays,lo,hi)
        m=v01.metrics(ss,dd);st=v04.stability(raw,ss,dd,pp);ch,ok=checks(m,st)
        results[name]={'status':'PASS' if ok else 'FAIL','window_utc':[str(lo),str(hi)],'eligible_snapshot_count':len(ss),'metrics':m,'stability':st,'checks':ch}
        for s,zs in zip(ss,dd):
            for rank,z in enumerate(zs,1):
                rows.append({'window':name,'time':s['time'],'close':s['close'],'v60':s['v'],'upper_z4_count':s['upper_z4_count'],
                             'nearest_upper_z4_dist_v':s['nearest_upper_z4_dist_v'],'entry_rank':rank,'family':z.family,
                             'center':z.center,'zlo':z.zlo,'zhi':z.zhi,'distance_v':(s['close']-z.center)/s['v']})
        print(name,results[name]['status'],m['coverage'],st['survival_aware_display_persistence'],flush=True)

    status='EBUY_COVERAGE_OOS_REPLICATION_PASS' if results['OOS_H1']['status']=='PASS' and results['OOS_H2']['status']=='PASS' else 'EBUY_COVERAGE_OOS_REPLICATION_FAIL'
    out={'status':status,'scope':'BUY_ONLY_EBUY_COVERAGE_OOS_REPLICATION_V1_0','future_price_outcomes_used':False,
         'fixed_architecture':'Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50','display_rule':'v0.4 sticky top3',
         'results':results,'authorization':('FREEZE_EBUY_LOCATION_ENGINE_AND_AUTHORIZE_REACTION_PREREG' if status.endswith('PASS') else 'NO_REACTION_OUTCOMES'),
         'explicit_nonclaims':['No reaction-quality claim','No TP-hit claim','No profitability claim','No route/end-of-session claim']}
    Path(a.output).write_text(json.dumps(out,indent=2));pd.DataFrame(rows).to_csv(a.candidates_csv,index=False)
    print(json.dumps({'status':status,'H1':results['OOS_H1']['status'],'H2':results['OOS_H2']['status']},indent=2),flush=True)

if __name__=='__main__':main()
