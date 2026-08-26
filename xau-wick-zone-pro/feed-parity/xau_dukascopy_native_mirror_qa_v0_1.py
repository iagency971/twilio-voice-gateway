#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr

def cli():
    p=argparse.ArgumentParser();p.add_argument('--mirror',required=True);p.add_argument('--native',required=True);p.add_argument('--output',required=True);return p.parse_args()

def load(path):
    d=pd.read_csv(path);d['time']=pd.to_datetime(d.timestamp,utc=True);return d.sort_values('time').drop_duplicates('time').reset_index(drop=True)

def side_metrics(m,n,side):
    suf='_'+side.lower();cols=[c+suf for c in ['open','high','low','close']]
    a=m[['time']+cols].copy();b=n[['time']+cols].copy();x=a.merge(b,on='time',suffixes=('_m','_n'))
    coverage=len(x)/len(a) if len(a) else 0.;cm=x[f'close{suf}_m'].to_numpy(float);cn=x[f'close{suf}_n'].to_numpy(float)
    rm=np.diff(cm);rn=np.diff(cn);rho=float(spearmanr(rm,rn).statistic) if len(rm)>2 else None
    errs={}
    pooled=[]
    for c in cols:
        e=np.abs(x[c+'_m'].to_numpy(float)-x[c+'_n'].to_numpy(float));pooled.extend(e.tolist());errs[c]={'median':float(np.median(e)),'p95':float(np.quantile(e,.95))}
    med=float(np.median(np.asarray(pooled,float)))
    checks={'common_m1_ge_2000':len(x)>=2000,'mirror_coverage_ge_099':coverage>=.99,'return_spearman_ge_0999':rho is not None and rho>=.999,'median_abs_ohlc_error_le_0005':med<=.005,'p95_close_le_001':errs['close'+suf]['p95']<=.01,'p95_high_le_002':errs['high'+suf]['p95']<=.02,'p95_low_le_002':errs['low'+suf]['p95']<=.02}
    return {'common_m1':len(x),'mirror_rows':len(a),'native_rows':len(b),'mirror_coverage':coverage,'return_spearman':rho,'median_abs_ohlc_error':med,'errors':errs,'checks':checks,'pass':all(checks.values())}

def main():
    a=cli();m=load(a.mirror);n=load(a.native);lo=pd.Timestamp('2026-08-19T00:00:00Z');hi=pd.Timestamp('2026-08-21T00:00:00Z');m=m[(m.time>=lo)&(m.time<hi)];n=n[(n.time>=lo)&(n.time<hi)]
    bid=side_metrics(m,n,'BID');ask=side_metrics(m,n,'ASK');passed=bid['pass'] and ask['pass'];out={'status':'DUKASCOPY_NATIVE_RECOVERY_PASS' if passed else 'DUKASCOPY_NATIVE_RECOVERY_FAIL','scope':'OUTCOME_BLIND_NATIVE_BI5_VS_MONTHLY_MIRROR_M1','window_utc':[str(lo),str(hi)],'future_trade_outcomes_used':False,'BID':bid,'ASK':ask,'authorization':'AUTHORIZE_CONDITIONAL_ENTRY_TRANSFER_STAGE_B' if passed else 'DO_NOT_USE_NATIVE_FOR_ENTRY_TRANSFER'};Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
