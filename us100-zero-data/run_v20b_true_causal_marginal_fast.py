#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import pandas as pd
import run_v17_all24_branch_search as v17

_cache={}
def cached_rescore(trades,bars):
    key=(len(bars),str(bars.iloc[0]['datetime']),str(bars.iloc[-1]['datetime']))
    if key not in _cache:
        exact=dict(zip(bars.datetime.dt.strftime('%Y-%m-%d %H:%M'),bars.spread_price.astype(float)))
        med=bars.assign(date=bars.datetime.dt.date).groupby('date').spread_price.median().to_dict()
        _cache[key]=(exact,med)
    exact,med=_cache[key]; rows=[]
    for t in trades:
        ts=pd.Timestamp(t.entry_time) if str(t.direction).lower()=='long' else pd.Timestamp(t.exit_time)
        k=ts.strftime('%Y-%m-%d %H:%M');c=float(exact.get(k,med[ts.date()]));rp=float(t.risk_ticks)*v17.TICK;raw=float(t.total_r)
        rows.append({'entry_time':t.entry_time,'exit_time':t.exit_time,'model':t.model,'direction':str(t.direction).lower(),'risk_ticks':t.risk_ticks,'raw_r':raw,'primary_r':raw-c/rp,'stress_r':raw-2*c/rp,'reason':t.exit_reason})
    z=pd.DataFrame(rows)
    if len(z):
        z['entry_time']=pd.to_datetime(z.entry_time);z['exit_time']=pd.to_datetime(z.exit_time);z['branch']=z.model+'__'+z.direction;z=z.sort_values('entry_time').reset_index(drop=True)
    return z
v17.rescore=cached_rescore
import run_v20_true_causal_marginal_branches as v20
v20.OUT=Path('us100-zero-data/results/v20b_true_causal_marginal_fast')
if __name__=='__main__':v20.main()
