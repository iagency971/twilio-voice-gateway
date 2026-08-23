#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
import numpy as np
import pandas as pd
import run_v17_all24_branch_search as v17
import run_native_12model_port_v5_fast as fast

OUT=Path('us100-zero-data/results/v20_true_causal_marginal_branches')
SELECTED={
'ema_rev__long','kalman_mom__long','kalman_mom__short','open_drive__long',
'ou_lunch__long','ou_lunch__short','ou_rev__long','pd_rev__long','pm_mom__long',
'pm_mom__short','sweep__short','trend__long','vwap_rev__short','vwap_scalp__long'}
RISK=.007
SESS={2021:248,2022:249,2023:249,2024:246,2025:83}

def eval_period(z,years,sessions):
    q=z[z.entry_time.dt.year.isin(years)].copy();s=v17.stats(q.stress_r);wi=v17.worst_intraday_r(q);rps=s['sum']/sessions if sessions else 0.;pace=.10/(rps*RISK) if rps>0 else None
    return {'n':len(q),'stress':s,'r_per_session':float(rps),'step1_days_at_070':None if pace is None else float(pace),'scaled_dd_pct':None if s['max_dd'] is None else float(s['max_dd']*RISK),'scaled_worst_intraday_pct':float(abs(min(0.,wi))*RISK),'remove_best10_mean':v17.remove_best10(q.stress_r)}
def main():
    OUT.mkdir(parents=True,exist_ok=True);ext=fast.ensure_external_fast();sys.path.insert(0,str(ext.resolve()))
    cfg,gen,df,filt,bars,total=v17.prepare()
    raw_branches=sorted(set(v17.branch(s) for s in filt))
    from backtest.engine_v2 import BacktestEngineV2,Trade
    from strategy.models.base import GLOBAL_MIN_RISK_TICKS,GLOBAL_MAX_RISK_TICKS
    from strategy.quality import filter_by_quality
    FE0=v17.make_fast_engine(BacktestEngineV2,Trade,GLOBAL_MIN_RISK_TICKS,GLOBAL_MAX_RISK_TICKS)
    class FE(FE0):
        _maps={}
        def run(self,df,signals):
            key=(len(df),str(df.iloc[0]['datetime']),str(df.iloc[-1]['datetime']))
            if key not in self._maps:self._maps[key]={pd.Timestamp(x):i for i,x in enumerate(df.datetime.tolist())}
            self._idxmap=self._maps[key];return BacktestEngineV2.run(self,df,signals)
    engine=FE(cfg)
    def rerun(branches):
        sig=[s for s in filt if v17.branch(s) in branches];res=v17.causal(sig);fin=filter_by_quality(res,df);z=v17.rescore(engine.run(df,fin),bars)
        periods={'ALL':eval_period(z,(2021,2022,2023,2024,2025),1075),'DEV':eval_period(z,(2021,2022,2023),746),'2024':eval_period(z,(2024,),246),'2025':eval_period(z,(2025,),83)}
        return z,{'branches':sorted(branches),'preconflict':len(sig),'postconflict':len(res),'postquality':len(fin),'periods':periods}
    bz,base=rerun(SELECTED);b=base['periods']['ALL'];rem={};add={}
    for x in sorted(SELECTED):
        _,r=rerun(SELECTED-{x});a=r['periods']['ALL'];r['delta_all_r_per_session']=float(a['r_per_session']-b['r_per_session']);r['delta_step1_days']=None if a['step1_days_at_070'] is None else float(a['step1_days_at_070']-b['step1_days_at_070']);r['delta_dd_pct']=None if a['scaled_dd_pct'] is None else float(a['scaled_dd_pct']-b['scaled_dd_pct']);rem[x]=r
    excluded=sorted(set(raw_branches)-SELECTED)
    for x in excluded:
        _,r=rerun(SELECTED|{x});a=r['periods']['ALL'];r['delta_all_r_per_session']=float(a['r_per_session']-b['r_per_session']);r['delta_step1_days']=None if a['step1_days_at_070'] is None else float(a['step1_days_at_070']-b['step1_days_at_070']);r['delta_dd_pct']=None if a['scaled_dd_pct'] is None else float(a['scaled_dd_pct']-b['scaled_dd_pct']);add[x]=r
    out={'status':'V20_TRUE_CAUSAL_MARGINAL_DIAGNOSTIC_COMPLETE','risk_fraction':RISK,'raw_branch_count':len(raw_branches),'raw_branches':raw_branches,'selected':sorted(SELECTED),'baseline':base,'remove_one':rem,'add_one':add,'notes':['Diagnostic only; no branch is changed retroactively from this result.','Every variant is rerun before conflict resolution, so interactions are represented causally.']}
    (OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str));rows=[]
    for typ,d in [('REMOVE',rem),('ADD',add)]:
        for k,r in d.items():rows.append({'action':typ,'branch':k,'delta_r_per_session':r['delta_all_r_per_session'],'delta_step1_days':r['delta_step1_days'],'delta_dd_pct':r['delta_dd_pct'],'all_pf':r['periods']['ALL']['stress']['pf'],'dev_sum':r['periods']['DEV']['stress']['sum'],'y2024_sum':r['periods']['2024']['stress']['sum'],'y2025_sum':r['periods']['2025']['stress']['sum']})
    pd.DataFrame(rows).sort_values(['action','delta_step1_days']).to_csv(OUT/'MARGINAL_SUMMARY.csv',index=False);print(pd.DataFrame(rows).sort_values(['action','delta_step1_days']).to_string(index=False))
if __name__=='__main__':main()
