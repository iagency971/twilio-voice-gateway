#!/usr/bin/env python3
from __future__ import annotations

import os
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

final=load_module('reaction_v103_final',HERE/'xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py')
base=final.base
Zone=base.v01.Zone

CANDIDATES=os.environ.get('EBUY_PRECOMPUTED_CANDIDATES')
if not CANDIDATES:
    raise RuntimeError('EBUY_PRECOMPUTED_CANDIDATES is required')

_orig_metrics=base.v01.metrics

def build_precomputed(raw,active,z4):
    snaps=base.v01.make_eval_times(active,z4)
    c=pd.read_csv(CANDIDATES)
    if 'window' in c.columns:
        c=c[c['window'].astype(str)=='OOS_H1'].copy()
    c['time']=pd.to_datetime(c.time,utc=True)
    c=c[(c.time>=base.DEV_LO)&(c.time<base.DEV_HI)].copy()
    assert len(c)>0
    assert c.time.max()<base.DEV_HI
    by={pd.Timestamp(t):g.sort_values('entry_rank') for t,g in c.groupby('time',sort=True)}
    displays=[]
    for s in snaps:
        g=by.get(s['time'])
        zs=[]
        if g is not None:
            # Integrity: candidate table must describe the same causal C5 state.
            assert np.allclose(g['close'].to_numpy(float),float(s['close']),rtol=0,atol=1e-9)
            assert np.allclose(g['v60'].to_numpy(float),float(s['v']),rtol=0,atol=1e-9)
            for _,r in g.iterrows():
                zs.append(Zone(float(r.center),float(r.zlo),float(r.zhi),str(r.family),0.0))
        assert len(zs)<=3
        displays.append(zs)

    # Exact integrity check against the already published frozen OOS H1 metrics.
    import json
    cov=json.load(open('xau-wick-zone-pro/entry-research/ebuy-coverage-oos-v1-0/XAUUSD_Z4_EBUY_COVERAGE_OOS_REPLICATION_RESULT_v1_0.json'))
    exp=cov['results']['OOS_H1']['metrics']
    got=_orig_metrics(snaps,displays)
    for b in ('0.5','1.0','1.5','2.0'):
        assert abs(got['coverage'][b]-exp['coverage'][b])<=1e-12,(b,got['coverage'][b],exp['coverage'][b])
    for k in ('candidate_count_median','candidate_count_p90','nearest_distance_v_median','nearest_distance_v_p90'):
        assert abs(float(got[k])-float(exp[k]))<=1e-12,(k,got[k],exp[k])
    assert len(snaps)==int(cov['results']['OOS_H1']['eligible_snapshot_count'])
    print('PRECOMPUTED_EBUY_H1_LOCATION_PARITY_PASS',len(snaps),len(c),flush=True)
    return snaps,displays


def sticky_identity(raw,snaps,pools):
    return pools

# Replace only the already-frozen location recomputation. All episode, arming,
# contact, trigger and outcome logic remains the final pre-outcome v1.0.3 code.
base.v04.build_fixed_pools=build_precomputed
base.v04.sticky_display=sticky_identity

if __name__=='__main__':
    base.main()
