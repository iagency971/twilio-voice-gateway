#!/usr/bin/env python3
from __future__ import annotations
import copy
from pathlib import Path
import pandas as pd

import run_v17_all24_branch_search as v17

# Cache immutable spread maps across all candidate reruns.
_spread_cache={}
def cached_rescore(trades,bars):
    key=(len(bars),str(bars.iloc[0]['datetime']),str(bars.iloc[-1]['datetime']))
    if key not in _spread_cache:
        exact=dict(zip(bars.datetime.dt.strftime('%Y-%m-%d %H:%M'),bars.spread_price.astype(float)))
        med=bars.assign(date=bars.datetime.dt.date).groupby('date').spread_price.median().to_dict()
        _spread_cache[key]=(exact,med)
    exact,med=_spread_cache[key]
    rows=[]
    for t in trades:
        ts=pd.Timestamp(t.entry_time) if str(t.direction).lower()=='long' else pd.Timestamp(t.exit_time)
        k=ts.strftime('%Y-%m-%d %H:%M'); c=float(exact.get(k,med[ts.date()])); rp=float(t.risk_ticks)*v17.TICK; raw=float(t.total_r)
        rows.append({'entry_time':t.entry_time,'exit_time':t.exit_time,'model':t.model,'direction':str(t.direction).lower(),'risk_ticks':t.risk_ticks,'raw_r':raw,'primary_r':raw-c/rp,'stress_r':raw-2*c/rp,'reason':t.exit_reason})
    z=pd.DataFrame(rows)
    if len(z):
        z['entry_time']=pd.to_datetime(z.entry_time); z['exit_time']=pd.to_datetime(z.exit_time)
        z['branch']=z.model+'__'+z.direction; z=z.sort_values('entry_time').reset_index(drop=True)
    return z
v17.rescore=cached_rescore

_orig_make=v17.make_fast_engine
def cached_sim_make_fast_engine(BaseEngine,Trade,GLOBAL_MIN,GLOBAL_MAX):
    FE=_orig_make(BaseEngine,Trade,GLOBAL_MIN,GLOBAL_MAX)
    class CachedSimFE(FE):
        _sim_cache={}
        _idx_maps={}
        def run(self,df,signals):
            # Keep identical FE index lookup, but share map across instances.
            key=(len(df),str(df.iloc[0]['datetime']),str(df.iloc[-1]['datetime']))
            if key not in self._idx_maps:
                self._idx_maps[key]={pd.Timestamp(x):i for i,x in enumerate(df['datetime'].tolist())}
            self._idxmap=self._idx_maps[key]
            # Call frozen BaseEngine.run directly so it uses our cached _sim.
            return BaseEngine.run(self,df,signals)
        def _sim(self,df,sig):
            # Signal objects are generated once and reused by every true candidate rerun.
            # Frozen _sim is deterministic for fixed df/cfg/signal, so memoization is exact.
            key=id(sig)
            if key in self._sim_cache:
                val=self._sim_cache[key]
                return None if val is None else copy.deepcopy(val)
            val=FE._sim(self,df,sig)
            self._sim_cache[key]=None if val is None else copy.deepcopy(val)
            return val
    return CachedSimFE
v17.make_fast_engine=cached_sim_make_fast_engine

import run_v18_selection_walkforward as v18
v18.OUT=Path('us100-zero-data/results/v18d_selection_walkforward_cachedsim')

if __name__=='__main__':
    v18.main()
